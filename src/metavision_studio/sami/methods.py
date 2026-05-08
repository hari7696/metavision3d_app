"""Methods-section sentences for SAMI steps (used by "Copy methods text")."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

__all__ = ["CITATION", "METABOANALYST_CITATION", "describe"]

CITATION = (
    "Ma X. XinBiostats/SAMI: Spatial Augmented Multiomics Interface (v1.0.0). Zenodo; 2025. "
    "doi:10.5281/zenodo.15022514"
)
METABOANALYST_CITATION = (
    "Pang Z, et al. MetaboAnalystR 4.0: a unified LC-MS workflow for global metabolomics. "
    "Nat Commun. 2024;15:3675. doi:10.1038/s41467-024-48009-6"
)

_ROW = {
    "sum": "to a constant total ion count (sum normalisation)",
    "median": "by the pixel median",
    "comp": "by a reference feature ({reference})",
    "pqn": "by probabilistic quotient normalisation against the mean spectrum",
    "section_median_pqn": "by section-wise median PQN",
    "none": None,
}
_TRANS = {
    "log2": "log2(x + 1) transformed",
    "log10": "log10(x + 1) transformed",
    "glog2": "generalised-log2 transformed",
    "glog10": "generalised-log10 transformed",
    "sqrt": "square-root transformed",
    "cbrt": "cube-root transformed",
    "none": None,
}
_SCALE = {
    "mean_center": "mean-centred",
    "auto": "autoscaled (z-scores)",
    "pareto": "Pareto-scaled",
    "range": "range-scaled",
    "none": None,
}


def _fmt(x: Any) -> str:
    return f"{x:g}" if isinstance(x, float) else str(x)


def describe(step: str, params: Mapping[str, Any]) -> str:
    """One or two sentences describing a SAMI step run with ``params``."""
    p = dict(params)
    if step == "normalise":
        parts = []
        row = _ROW.get(p.get("row", "sum"))
        if row:
            scope = " within each omics layer" if p.get("per_omics", True) else ""
            parts.append(f"normalised {row.format(reference=p.get('reference'))}{scope}")
        if t := _TRANS.get(p.get("transform", "log2")):
            parts.append(t)
        if s := _SCALE.get(p.get("scale", "none")):
            parts.append(s)
        body = ", ".join(parts) if parts else "left unnormalised"
        return (
            f"Pixel intensities were {body}, following SAMI ({CITATION}); pixels with zero "
            "total intensity were excluded."
        )
    if step == "cluster":
        harmony = (
            " Section effects were corrected with Harmony before building the neighbour graph."
            if p.get("harmony")
            else ""
        )
        return (
            "Spatial domains were identified as in SAMI: principal component analysis, a "
            "k-nearest-neighbour graph on up to 20 components, UMAP embedding and Leiden "
            f"clustering (resolution {_fmt(p.get('resolution', 1.0))}, random seed "
            f"{p.get('random_state', 7)}), implemented with Scanpy.{harmony}"
        )
    if step == "transfer":
        return (
            "Cluster labels were transferred between samples with Scanpy's ingest, using the "
            "features shared by both samples, as in SAMI's cluster integration."
        )
    if step == "markers":
        control = (
            " between case and control samples within the same clusters" if p.get("control") else ""
        )
        top = p.get("top", 50)
        top_txt = f", retaining the top {top} by absolute log2 fold change" if top else ""
        return (
            f"Marker molecules{control} were identified with two-sided Wilcoxon rank-sum tests "
            f"after excluding pixels with < {_fmt(p.get('min_abundance', 0.1))} feature "
            f"abundance and features detected in < {_fmt(p.get('min_prevalence', 0.1))} of "
            f"pixels, testing features detected in > {_fmt(p.get('min_pct', 0.1))} of pixels "
            "of both groups. P-values were adjusted with the Benjamini-Hochberg procedure and "
            f"markers called at FDR ≤ {_fmt(p.get('fdr', 0.05))}{top_txt} (SAMI; {CITATION})."
        )
    if step == "pathways":
        return (
            "Pathway over-representation of marker molecules was tested with a hypergeometric "
            "test against SMPDB metabolic pathways (metabolites and glycans) and lipid "
            f"sub-classes (lipids), excluding sets with < {p.get('min_set_size', 2)} members, "
            "using MetaboAnalystR-derived functions as implemented in SAMI "
            f"({METABOANALYST_CITATION}; {CITATION}). P-values were adjusted with the "
            f"Benjamini-Hochberg procedure (FDR ≤ {_fmt(p.get('fdr', 0.05))}). Pathway "
            "direction was called from log2 of the summed mean intensities of all measured "
            f"pathway molecules (|log2FC| > {_fmt(p.get('direction_threshold', 0.1))})."
        )
    raise KeyError(f"No methods text for SAMI step {step!r}")
