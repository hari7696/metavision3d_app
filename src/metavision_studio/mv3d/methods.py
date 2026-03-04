"""Methods-text sentences for MetaVision3D steps (used by "Copy methods text")."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

__all__ = ["CITATION", "describe"]

CITATION = (
    "Ma X, et al. MetaVision3D: Automated Framework for the Generation of Spatial Metabolome "
    "Atlas in 3D. bioRxiv (2023). doi:10.1101/2023.11.27.568931"
)

_NORM = {
    "tic+section": "normalised to total ion current (TIC) and then, for each feature, "
    "scaled so that every section's median matched the median across sections",
    "tic": "normalised to total ion current (TIC)",
    "section": "scaled per feature so that every section's median matched the median across "
    "sections",
    "none": "not normalised",
}


def describe(step: str, params: Mapping[str, Any]) -> str:
    """One or two sentences describing a completed step with its parameters."""
    p = dict(params)
    if step == "normalise":
        method = p.get("method", "tic+section")
        return f"Pixel intensities were {_NORM.get(method, method)} (MetaNorm3D; Ma et al., 2023)."
    if step == "align":
        ref = p.get("reference") or "the most prevalent feature"
        return (
            "Serial sections were aligned by sequential rigid (Euclidean) registration using the "
            f"enhanced correlation coefficient (ECC) algorithm on {ref}, with each section "
            "registered to the previously aligned section (MetaAlign3D; Ma et al., 2023; "
            f"max {p.get('max_iter', 5000)} iterations, ε = {p.get('eps', 1e-10):g})."
        )
    if step == "fill":
        parts = []
        if p.get("impute", True):
            parts.append(
                "missing pixels and tissue edges were imputed from the mean of non-zero "
                f"intensities in the {p.get('radius', 1)} neighbouring section(s) on each side "
                "(MetaImpute3D)"
            )
        if p.get("n_insert", 0):
            parts.append(
                f"{p['n_insert']} linearly interpolated section(s) were inserted between each "
                "pair of adjacent sections (MetaInterp3D)"
            )
        if not parts:
            return "No imputation or interpolation was applied."
        text = "; ".join(parts) + " (Ma et al., 2023)."
        return text[0].upper() + text[1:]
    if step == "atlas":
        vs = p.get("voxel_size_um")
        size = f" with a voxel size of {vs[1]:g} × {vs[2]:g} × {vs[0]:g} µm" if vs else ""  # noqa: RUF001
        return (
            f"The aligned stack was assembled into a 3D volume (NIfTI-1){size}, from "
            f"{p.get('thickness_um', '?')} µm sections with a {p.get('gap_um', 0)} µm gap "
            "(MetaAtlas3D; Ma et al., 2023)."
        )
    return ""
