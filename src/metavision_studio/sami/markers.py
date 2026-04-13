"""SAMI marker detection: which molecules distinguish one group of clusters from another.

Adapted from SAMI (https://github.com/XinBiostats/SAMI, commit 80da10b),
``SAMI/markers.py`` (``Markers.findmarkers``) and ``SAMI/utils.py`` (``adata_filter``,
``adj_pvalue``). © 2023 University of Florida Research Foundation, Inc. Licensed under
CC BY-NC-SA 4.0 (https://creativecommons.org/licenses/by-nc-sa/4.0/).

Method (as upstream):

1. Filter pixels and features (``adata_filter``): keep pixels where at least
   ``min_abundance`` of features are non-zero, and features non-zero in at least
   ``min_prevalence`` of pixels. Computed on the whole dataset (and on ``control``).
2. Test each feature expressed (non-zero) in **more than** ``min_pct`` of pixels of *both*
   groups with the Wilcoxon rank-sum test (``scipy.stats.ranksums``, normal approximation).
3. Fold change ``log2fc = log2(mean_a / mean_b)``, computed on the normalised values exactly
   as upstream. SAMI's default normalisation is ``log2(x + 1)`` of TIC-scaled intensities, which
   are close to 0, so this ratio of means behaves like a fold change of intensities. ``delta``
   (``mean_a - mean_b``) is also reported. If scaling made the values signed and
   ``layers["counts"]`` is present, the means come from the measured intensities instead;
   otherwise a non-positive mean gives ``log2fc = NaN``.
4. Adjust p-values within the comparison (Benjamini-Hochberg), and call markers ``padj <= fdr``,
   keeping the ``top`` with the largest ``|log2fc|``.

Changes from upstream:

* **Correct Benjamini-Hochberg** (``scipy.stats.false_discovery_control``). Upstream computed
  ``p * n / rank`` with no cumulative minimum and no cap at 1, so adjusted p-values were not
  monotone and could exceed 1.
* Arbitrary comparisons: any set of clusters against any other set (default: the rest), or
  against the same clusters in a ``control`` sample (upstream's ``adata2`` mode). Upstream
  only did each-cluster-vs-rest.
* "Detected" (non-zero) is judged on ``layers["counts"]`` (measured intensities) when present,
  so the filters still work after transforms or scaling that turn zeros into non-zeros.
* Vectorised over features. Upstream concatenated one-row DataFrames per feature, which was
  quadratic.
* Returns one table with every tested feature and a ``significant`` flag, instead of writing
  ``_pvalue.csv`` and ``_marker.csv``. Pathway enrichment uses the full table for direction.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd
from scipy import sparse
from scipy.stats import false_discovery_control, ranksums

from metavision_studio._progress import ProgressFn, report

__all__ = ["MARKER_COLUMNS", "filter_abundance_prevalence", "find_all_markers", "find_markers"]

CLUSTER_KEY = "cluster"
MARKER_COLUMNS = [
    "feature",
    "name",
    "omics",
    "mean_a",
    "mean_b",
    "log2fc",
    "delta",
    "pct_a",
    "pct_b",
    "pvalue",
    "padj",
    "significant",
]


def _dense(x) -> np.ndarray:
    return np.asarray(x.toarray() if sparse.issparse(x) else x, dtype=np.float64)


def _detection_matrix(adata):
    """Values that define *detected* (non-zero): ``layers["counts"]`` when present, else ``X``.

    Deviation from upstream, which always used ``X``. That is equivalent for the default
    log2(x + 1) transform (0 stays 0), but after sqrt/cbrt/glog or scaling every value in
    ``X`` is non-zero, so the abundance, prevalence and % expressing filters would pass
    everything. The workflows attach the measured intensities as ``counts``.
    """
    return adata.layers.get("counts", adata.X)


def filter_abundance_prevalence(adata, min_abundance: float = 0.1, min_prevalence: float = 0.1):
    """SAMI's ``adata_filter``: drop sparse pixels and rarely detected features (returns a copy)."""
    x = _detection_matrix(adata)
    nz = (x != 0) if not sparse.issparse(x) else (x != 0).toarray()
    abundance = nz.sum(axis=1) / adata.n_vars
    prevalence = nz.sum(axis=0) / adata.n_obs
    out = adata[abundance >= min_abundance, prevalence >= min_prevalence].copy()
    out.obs["abundance"] = abundance[abundance >= min_abundance]
    out.var["prevalence"] = prevalence[prevalence >= min_prevalence]
    return out


def _labels(groups: Sequence[str] | str | int) -> list[str]:
    if isinstance(groups, (str, int, np.integer)):
        return [str(groups)]
    return [str(g) for g in groups]


def find_markers(
    adata,
    group_a: Sequence[str] | str,
    group_b: Sequence[str] | str | None = None,
    *,
    control=None,
    cluster_key: str = CLUSTER_KEY,
    min_abundance: float = 0.1,
    min_prevalence: float = 0.1,
    min_pct: float = 0.1,
    fdr: float = 0.05,
    top: int | None = 50,
) -> pd.DataFrame:
    """Find marker molecules of ``group_a`` versus ``group_b``.

    Args:
        adata: clustered AnnData (from :func:`~metavision_studio.sami.cluster`).
        group_a: cluster label(s) of interest.
        group_b: cluster label(s) to compare against. ``None`` means all other clusters, or,
            with ``control``, the same labels as ``group_a``.
        control: optional second (control) sample whose clusters were transferred with
            :func:`~metavision_studio.sami.transfer_clusters`. Compares ``group_a`` in ``adata``
            with ``group_b`` in ``control`` (SAMI's case-vs-control mode).
        min_abundance, min_prevalence: pixel and feature filters (SAMI ``adata_filter``).
            Set both to 0 to disable.
        min_pct: a feature is tested only if non-zero in more than this fraction of *both* groups.
        fdr: Benjamini-Hochberg threshold for ``significant``.
        top: keep at most this many significant markers (largest ``|log2fc|``). SAMI demos use 50.
            ``None`` keeps all.

    Returns:
        One row per tested feature: ``feature, name, omics, mean_a, mean_b, log2fc, delta,
        pct_a, pct_b, pvalue, padj, significant``, sorted with markers first.
    """
    a_labels = _labels(group_a)
    case = filter_abundance_prevalence(adata, min_abundance, min_prevalence)
    if control is None:
        ctrl = case
        b_labels = _labels(group_b) if group_b is not None else None
    else:
        ctrl = filter_abundance_prevalence(control, min_abundance, min_prevalence)
        b_labels = _labels(group_b) if group_b is not None else a_labels

    features = [f for f in case.var_names if f in set(ctrl.var_names)]
    if not features:
        return pd.DataFrame(columns=MARKER_COLUMNS)

    in_a = case.obs[cluster_key].astype(str).isin(a_labels).to_numpy()
    if b_labels is None:
        in_b = ~in_a
    else:
        in_b = ctrl.obs[cluster_key].astype(str).isin(b_labels).to_numpy()
        if control is None and np.any(in_a & in_b):
            raise ValueError("group_a and group_b overlap; choose different clusters.")
    if not in_a.any() or not in_b.any():
        raise ValueError(
            "One of the groups has no pixels after filtering "
            f"(group A: {int(in_a.sum())}, group B: {int(in_b.sum())})."
        )

    a = _dense(case[in_a, features].X)
    b = _dense(ctrl[in_b, features].X)
    det_a = _dense(_detection_matrix(case[in_a, features]))
    det_b = _dense(_detection_matrix(ctrl[in_b, features]))
    pct_a = (det_a != 0).mean(axis=0)
    pct_b = (det_b != 0).mean(axis=0)
    tested = (pct_a > min_pct) & (pct_b > min_pct)

    # Fold change on the normalised values, as upstream. If scaling made them signed (mean
    # centring, auto, Pareto, range), a ratio of means is meaningless; use the measured
    # intensities instead when available.
    fc_a, fc_b = (det_a, det_b) if (a.min(initial=0) < 0 or b.min(initial=0) < 0) else (a, b)
    mean_a = fc_a.mean(axis=0)
    mean_b = fc_b.mean(axis=0)
    with np.errstate(divide="ignore", invalid="ignore"):
        log2fc = np.log2(mean_a / mean_b)
    log2fc[~((mean_a > 0) & (mean_b > 0))] = np.nan

    pvalue = np.full(len(features), np.nan)
    if tested.any():
        _, p = ranksums(a[:, tested], b[:, tested], axis=0)
        pvalue[tested] = p

    var = case.var.loc[features]
    names = var["name"].astype(str).to_numpy() if "name" in var else np.asarray(features)
    omics = (
        var["omics"].astype(str).to_numpy() if "omics" in var else np.full(len(features), "other")
    )

    df = pd.DataFrame(
        {
            "feature": features,
            "name": names,
            "omics": omics,
            "mean_a": mean_a,
            "mean_b": mean_b,
            "log2fc": log2fc,
            "delta": mean_a - mean_b,
            "pct_a": pct_a,
            "pct_b": pct_b,
            "pvalue": pvalue,
        }
    )
    df = df.loc[tested].reset_index(drop=True)
    df["padj"] = false_discovery_control(df["pvalue"].to_numpy()) if len(df) else []
    passed = df["padj"] <= fdr
    df["significant"] = False
    order = (
        df.loc[passed]
        .assign(_abs=df["log2fc"].abs())
        .sort_values(["_abs", "pvalue"], ascending=[False, True], na_position="last")
    )
    chosen = order.index if top is None else order.index[:top]
    df.loc[chosen, "significant"] = True
    df = df.assign(_abs=df["log2fc"].abs()).sort_values(
        ["significant", "_abs", "pvalue"], ascending=[False, False, True], na_position="last"
    )
    df = df.drop(columns="_abs").reset_index(drop=True)
    df.attrs["comparison"] = {
        "group_a": a_labels,
        "group_b": b_labels if b_labels is not None else "rest",
        "control": control is not None,
        "n_a": int(in_a.sum()),
        "n_b": int(in_b.sum()),
    }
    return df[MARKER_COLUMNS]


def find_all_markers(
    adata,
    *,
    control=None,
    cluster_key: str = CLUSTER_KEY,
    progress: ProgressFn | None = None,
    **kwargs,
) -> pd.DataFrame:
    """Markers for every cluster vs the rest (or vs the same cluster in ``control``).

    Returns the tables of :func:`find_markers` stacked, with a leading ``comparison`` column
    holding the cluster label.
    """
    clusters = list(adata.obs[cluster_key].cat.categories)
    if control is not None:
        present = set(control.obs[cluster_key].astype(str))
        clusters = [c for c in clusters if c in present]
    tables = []
    for i, c in enumerate(clusters):
        report(progress, i, len(clusters), f"Markers for cluster {c} ({i + 1}/{len(clusters)})")
        try:
            t = find_markers(adata, [c], control=control, cluster_key=cluster_key, **kwargs)
        except ValueError:
            continue  # cluster empty after filtering
        tables.append(t.assign(comparison=str(c)))
    report(progress, len(clusters), len(clusters), "Markers done")
    if not tables:
        return pd.DataFrame(columns=["comparison", *MARKER_COLUMNS])
    out = pd.concat(tables, ignore_index=True)
    return out[["comparison", *MARKER_COLUMNS]]
