"""SAMI clustering and cross-sample cluster transfer.

Adapted from SAMI (https://github.com/XinBiostats/SAMI, commit 80da10b),
``SAMI/clustering.py`` (``Clusters.clustering``, ``Cluster_Integration.integrate``).
© 2023 University of Florida Research Foundation, Inc. Licensed under CC BY-NC-SA 4.0
(https://creativecommons.org/licenses/by-nc-sa/4.0/).

Pipeline (as upstream): PCA → (Harmony on ``section`` when there are several sections) →
neighbours on ≤ 20 PCs → UMAP → Leiden.

Changes from upstream:

* Pure functions returning :class:`anndata.AnnData`. Upstream read and wrote ``.h5ad``
  files under fixed folder layouts and parsed region names out of file names.
* Harmony is opt-in (``harmony=True``). Upstream ran it automatically whenever an AnnData had
  several regions. ``harmonypy`` is an optional extra because it pulls in PyTorch.
* Clusters are stored in ``obs["cluster"]`` (categorical, ordered numerically) rather than
  ``obs["leiden"]``. ``random_state`` is fixed (7) for PCA, UMAP and Leiden, so reruns match.
* Leiden uses the ``leidenalg`` flavour with iterations until convergence, which is what
  upstream's scanpy version did by default.
* :func:`transfer_clusters` subsets both datasets to their **shared** features before
  ``scanpy.tl.ingest``. Upstream computed the intersection but never used it, so ingest failed
  whenever the feature sets differed.
"""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

from metavision_studio._progress import ProgressFn, report
from metavision_studio.io.data import MSIData

__all__ = ["cluster", "transfer_clusters"]

CLUSTER_KEY = "cluster"


def _ordered_categories(labels: pd.Series) -> pd.Categorical:
    cats = sorted(pd.unique(labels.astype(str)), key=lambda s: (len(s), s))
    return pd.Categorical(labels.astype(str), categories=cats)


def _require_harmony() -> None:
    try:
        import harmonypy  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            "Batch correction (Harmony) needs the optional 'harmonypy' package: "
            'pip install "metavision-studio[harmony]"'
        ) from exc


def _embed(adata, *, harmony: bool, random_state: int, progress: ProgressFn | None) -> str:
    """PCA (+ Harmony) and neighbours. Returns the representation used."""
    import scanpy as sc

    n_comps = max(1, min(50, adata.n_obs - 1, adata.n_vars - 1))
    report(progress, 1, 5, "PCA")
    sc.pp.pca(adata, n_comps=n_comps, random_state=random_state)
    rep = "X_pca"
    n_sections = adata.obs["section"].nunique()
    if harmony and n_sections > 1:
        _require_harmony()
        report(progress, 2, 5, "Harmony batch correction")
        sc.external.pp.harmony_integrate(adata, key="section", max_iter_harmony=20)
        rep = "X_pca_harmony"
    report(progress, 2, 5, "Nearest neighbours")
    n_pcs = min(20, adata.obsm[rep].shape[1])
    if rep == "X_pca":
        # As upstream: record n_pcs (not use_rep) so scanpy.tl.ingest can project new data
        # onto these PCs. With use_rep recorded, ingest would compare raw X instead.
        sc.pp.neighbors(adata, n_pcs=n_pcs, random_state=random_state)
    else:
        sc.pp.neighbors(adata, use_rep=rep, n_pcs=n_pcs, random_state=random_state)
    return rep


def cluster(
    data: MSIData,
    *,
    resolution: float = 1.0,
    harmony: bool = False,
    random_state: int = 7,
    progress: ProgressFn | None = None,
):
    """Cluster pixels into spatial domains (SAMI's ``Clusters.clustering``).

    Args:
        data: normalised data (one or several sections).
        resolution: Leiden resolution. Higher gives more clusters (SAMI demos use 1.0-1.5).
        harmony: correct section/batch effects with Harmony (only used with several sections).
        random_state: seed for PCA, UMAP and Leiden.

    Returns:
        AnnData with ``obs``: ``section``, ``x``, ``y``, ``cluster`` (categorical str) and
        ``obsm``: ``X_pca``, ``X_umap``, ``spatial``.
    """
    import scanpy as sc

    if resolution <= 0:
        raise ValueError("resolution must be positive")
    if data.n_pixels < 3 or data.n_features < 2:
        raise ValueError("Clustering needs at least 3 pixels and 2 features.")
    if harmony and data.n_sections > 1:
        _require_harmony()

    adata = data.to_anndata()
    rep = _embed(adata, harmony=harmony, random_state=random_state, progress=progress)
    report(progress, 3, 5, "UMAP")
    sc.tl.umap(adata, random_state=random_state)
    report(progress, 4, 5, "Leiden clustering")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", FutureWarning)
        sc.tl.leiden(
            adata,
            resolution=resolution,
            random_state=random_state,
            key_added=CLUSTER_KEY,
            flavor="leidenalg",
            n_iterations=-1,
        )
    adata.obs[CLUSTER_KEY] = _ordered_categories(adata.obs[CLUSTER_KEY])
    adata.uns.setdefault("metavision", {})["cluster"] = {
        "resolution": float(resolution),
        "harmony": bool(harmony and data.n_sections > 1),
        "representation": rep,
        "random_state": int(random_state),
        "n_clusters": int(adata.obs[CLUSTER_KEY].cat.categories.size),
    }
    report(progress, 5, 5, "Clustering done")
    return adata


def transfer_clusters(
    reference,
    target,
    *,
    random_state: int = 7,
    progress: ProgressFn | None = None,
):
    """Map the clusters of ``reference`` onto ``target`` (SAMI's ``Cluster_Integration``).

    Uses ``scanpy.tl.ingest`` on the features the two datasets share, so cluster *k* means the
    same tissue domain in both, e.g. to compare AD and WT brains cluster by cluster.

    Args:
        reference: clustered AnnData (from :func:`cluster`).
        target: :class:`MSIData` (normalised the same way) or AnnData to label.

    Returns:
        AnnData for ``target`` with ``obs["cluster"]`` and ``obsm["X_umap"]`` from the reference.
    """
    import scanpy as sc

    if CLUSTER_KEY not in reference.obs:
        raise ValueError("The reference has no clusters; run cluster() on it first.")
    tgt = target.to_anndata() if isinstance(target, MSIData) else target.copy()
    shared = [v for v in reference.var_names if v in set(tgt.var_names)]
    if len(shared) < 2:
        raise ValueError(
            "The two datasets share fewer than 2 features, so clusters can't be transferred. "
            "Check that both were measured with the same panel and normalised the same way."
        )

    report(progress, 0, 3, "Preparing reference")
    ref = reference[:, shared].copy()
    tgt = tgt[:, shared].copy()
    used_rep = ref.uns.get("neighbors", {}).get("params", {}).get("use_rep") or "X_pca"
    if len(shared) != reference.n_vars or "neighbors" not in ref.uns or used_rep != "X_pca":
        # ingest projects onto the reference PCA, so rebuild it on the shared features
        # (and without Harmony, which ingest can't project onto).
        _embed(ref, harmony=False, random_state=random_state, progress=None)
        sc.tl.umap(ref, random_state=random_state)
    report(progress, 1, 3, "Mapping clusters")
    sc.tl.ingest(tgt, ref, obs=CLUSTER_KEY, embedding_method=("umap", "pca"))
    tgt.obs[CLUSTER_KEY] = pd.Categorical(
        tgt.obs[CLUSTER_KEY].astype(str),
        categories=list(reference.obs[CLUSTER_KEY].cat.categories),
    )
    tgt.uns.setdefault("metavision", {})["transfer"] = {
        "reference_sections": [str(s) for s in np.unique(reference.obs["section"])],
        "shared_features": len(shared),
    }
    report(progress, 3, 3, "Transfer done")
    return tgt
