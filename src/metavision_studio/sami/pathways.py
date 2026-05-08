"""SAMI pathway enrichment: over-representation analysis (ORA) of marker molecules.

Adapted from SAMI (https://github.com/XinBiostats/SAMI, commit 80da10b), ``SAMI/pathway.py``
(``Pathway.findpathway``) and ``SAMI/MetabAnalystR.R`` (``PathwayEnrichment``, from
MetaboAnalystR, © Xia Lab, MIT). © 2023 University of Florida Research Foundation, Inc.
Licensed under CC BY-NC-SA 4.0 (https://creativecommons.org/licenses/by-nc-sa/4.0/).

Method (as upstream):

* Metabolite and glycan markers are tested against **SMPDB pathways**, lipid markers against
  **lipid sub-classes**. Sets with fewer than 2 members are excluded.
* Marker names are matched to the compound library (exact name, then synonyms), and each set
  is tested with a hypergeometric test against the library universe. Holm and BH (FDR)
  adjustment are applied across all sets.
* **Direction** (SAMI 2025-03-05 method): for each pathway,
  ``log2(Σ mean_a / Σ mean_b)`` over the *measured* molecules in that pathway. It is ``up`` if
  above ``direction_threshold``, ``down`` if below ``-direction_threshold``, otherwise ``neutral``.

The ORA runs in R (``R/ora.R``) through :mod:`metavision_studio.rbridge`.

Changes from upstream:

* Runs per comparison from the markers table (no files, folders or R globals). Errors are
  returned as messages instead of being swallowed by ``tryCatch``.
* For the direction, every measured molecule is matched to the library (by name and
  synonyms), not just the markers, which is what SAMI's 2025 direction method describes.
  Upstream only translated marker names, so measured non-marker molecules whose names
  differed from the library spelling were left out.
* P-values are not rounded to 3 significant figures.
"""

from __future__ import annotations

import json
import re
import tempfile
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from metavision_studio._progress import ProgressFn, report

__all__ = ["PATHWAY_COLUMNS", "enrich_pathways", "library_for_omics"]

PATHWAY_COLUMNS = [
    "comparison",
    "pathway",
    "set_id",
    "library",
    "omics",
    "hits",
    "size",
    "expected",
    "enrichment",
    "pvalue",
    "padj",
    "holm",
    "significant",
    "log2fc",
    "direction",
    "members",
    "measured",
]

_DEDUPE_SUFFIX = re.compile(r" \[\d+\]$")


def library_for_omics(omics: str) -> str | None:
    """``smpdb_pathway`` for metabolomics/glycomics, ``sub_class`` for lipidomics, else None."""
    if omics in ("metabolomics", "glycomics"):
        return "smpdb_pathway"
    if omics == "lipidomics":
        return "sub_class"
    return None


def _query_name(name: str) -> str:
    return _DEDUPE_SUFFIX.sub("", str(name))


def enrich_pathways(
    markers: pd.DataFrame,
    *,
    libraries: Path | str | None = None,
    fdr: float = 0.05,
    direction_threshold: float = 0.1,
    min_set_size: int = 2,
    progress: ProgressFn | None = None,
) -> pd.DataFrame:
    """Pathway over-representation for the significant markers of each comparison.

    Args:
        markers: output of :func:`~metavision_studio.sami.find_markers` (one comparison) or
            :func:`~metavision_studio.sami.find_all_markers` (``comparison`` column). All tested
            features are used for the direction; ``significant`` ones are the ORA input.
        libraries: Parquet library directory. Defaults to
            :func:`~metavision_studio.sami.libraries.library_dir` (prepare it with
            :func:`~metavision_studio.sami.libraries.prepare_libraries`).
        fdr: threshold on the BH-adjusted p-value for ``significant``.
        direction_threshold: |log2 FC| needed to call a pathway up or down (SAMI demo: 0.1).
        min_set_size: smallest set tested (MetaboAnalyst ``excludeNum``, SAMI: 2).

    Returns:
        One row per (comparison, set with ≥ 1 hit): ``comparison, pathway, set_id, library,
        omics, hits, size, expected, enrichment, pvalue, padj, holm, significant, log2fc,
        direction, members`` (the marker hits) ``, measured`` (measured molecules in the set).
        ``attrs["messages"]`` holds notes from the matching step.
    """
    from metavision_studio import rbridge
    from metavision_studio.sami.libraries import library_dir

    lib = Path(libraries) if libraries is not None else library_dir()
    if lib is None or not lib.is_dir():
        raise FileNotFoundError(
            "Pathway libraries are not prepared yet. Run "
            "metavision_studio.sami.libraries.prepare_libraries() (downloads ~20 MB)."
        )

    df = markers.copy()
    if "comparison" not in df:
        df["comparison"] = "1"
    df["comparison"] = df["comparison"].astype(str)
    df["_query"] = df["name"].map(_query_name)
    df["_branch"] = df["omics"].map(library_for_omics)
    df = df[df["_branch"].notna()]

    comparisons, keys = [], []
    for (cmp, branch), g in df.groupby(["comparison", "_branch"], sort=False):
        cid = f"{cmp}\x1f{branch}"
        keys.append(cid)
        comparisons.append(
            {
                "id": cid,
                "lipid": branch == "sub_class",
                "queries": g.loc[g["significant"].astype(bool), "_query"].unique().tolist(),
                "background": g["_query"].unique().tolist(),
            }
        )
    if not comparisons:
        out = pd.DataFrame(columns=PATHWAY_COLUMNS)
        out.attrs["messages"] = ["No lipid, metabolite or glycan markers to test."]
        return out

    report(progress, 0, 2, f"Pathway enrichment for {len(comparisons)} comparison(s)")
    with tempfile.TemporaryDirectory(prefix="mvs-ora-") as tmp:
        tmp_path = Path(tmp)
        req = {
            "library_dir": str(lib),
            "min_set_size": int(min_set_size),
            "comparisons": comparisons,
        }
        (tmp_path / "request.json").write_text(json.dumps(req), encoding="utf-8")
        rbridge.run_script("ora.R", str(tmp_path / "request.json"), str(tmp_path / "out"))
        res = pd.read_parquet(tmp_path / "out" / "results.parquet")
        mapping = pd.read_parquet(tmp_path / "out" / "mapping.parquet")
        messages = json.loads((tmp_path / "out" / "messages.json").read_text(encoding="utf-8"))
    report(progress, 1, 2, "Computing pathway direction")

    msgs = []
    for m in messages or []:
        cmp, _, branch = str(m["comparison"]).partition("\x1f")
        text = f"[{cmp} · {branch}] {m['message']}"
        msgs.append(text)
        if m.get("level") == "error":
            warnings.warn(text, stacklevel=2)

    rows = []
    for cid, g in res.groupby("comparison", sort=False):
        cmp, _, branch = cid.partition("\x1f")
        sub = df[(df["comparison"] == cmp) & (df["_branch"] == branch)]
        mp = mapping[mapping["comparison"] == cid]
        matched_to_query: dict[str, list[str]] = {}
        for q, mname in zip(mp["query"], mp["matched"], strict=True):
            if isinstance(mname, str):
                matched_to_query.setdefault(mname, []).append(q)
        by_query = sub.groupby("_query")[["mean_a", "mean_b"]].sum()
        for r in g.itertuples(index=False):
            lib_members = set(str(r.all_compounds).split(";"))
            # all_compounds is in library names except for markers (already back-mapped)
            measured_q = set()
            for name in lib_members:
                if name in by_query.index:
                    measured_q.add(name)
                measured_q.update(matched_to_query.get(name, []))
            measured_q &= set(by_query.index)
            sa = by_query.loc[list(measured_q), "mean_a"].sum() if measured_q else np.nan
            sb = by_query.loc[list(measured_q), "mean_b"].sum() if measured_q else np.nan
            with np.errstate(divide="ignore", invalid="ignore"):
                fc = float(np.log2(sa / sb)) if measured_q and sa > 0 and sb > 0 else np.nan
            if np.isnan(fc):
                direction = "unknown"
            elif fc > direction_threshold:
                direction = "up"
            elif fc < -direction_threshold:
                direction = "down"
            else:
                direction = "neutral"
            rows.append(
                {
                    "comparison": cmp,
                    "pathway": r.pathway,
                    "set_id": r.set_id,
                    "library": branch,
                    "omics": "lipidomics" if branch == "sub_class" else "metabolomics_glycomics",
                    "hits": int(r.hits),
                    "size": int(r.total),
                    "expected": float(r.expected),
                    "enrichment": float(r.hits) / float(r.expected) if r.expected else np.nan,
                    "pvalue": float(r.raw_p),
                    "padj": float(r.fdr),
                    "holm": float(r.holm_p),
                    "significant": bool(r.fdr <= fdr),
                    "log2fc": fc,
                    "direction": direction,
                    "members": str(r.overlap_compounds),
                    "measured": ";".join(sorted(measured_q)),
                }
            )
    out = pd.DataFrame(rows, columns=PATHWAY_COLUMNS)
    out = out.sort_values(["comparison", "pvalue"], kind="stable").reset_index(drop=True)
    out.attrs["messages"] = msgs
    report(progress, 2, 2, "Pathway enrichment done")
    return out
