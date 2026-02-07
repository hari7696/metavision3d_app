# Adapted from MetaVision3D (https://github.com/XinBiostats/MetaVision3D, commit a108fe8).
# © 2023 University of Florida Research Foundation, Inc. Licensed under CC BY-NC-SA 4.0
# (https://creativecommons.org/licenses/by-nc-sa/4.0/).
# Changes: pure functions on MSIData/stacks; section IDs instead of reversed indices;
# added section_quality for automatic QC.
"""Preprocessing utilities from upstream ``utils.py``, plus section quality control.

* :func:`reference_feature`: the most prevalent feature, used for alignment
  (upstream ``get_ref_compound``)
* :func:`remove_low_prevalence`: drop rarely detected features
  (upstream ``delete_low_prevalence_compound``)
* :func:`blank_sections`: zero a section's intensities but keep its pixels
  (upstream ``delete_inferior_tissues``). This keeps the z spacing of the stack, and the empty
  section is then filled by imputation. Prefer it over dropping a damaged section.
* :func:`shell_mask` / :func:`drop_masked_pixels`: Otsu-based detection of the off-tissue
  "shell" around a section (upstream ``get_shell_mask`` / ``remove_shell``)
* :func:`section_quality`: flags empty or low-signal sections (new)

Deviations: NaN is treated as "not detected" when computing prevalence (upstream's
``astype(bool)`` counted NaN as detected). ``blank_sections`` takes section IDs directly, not
indices that were reversed when ``reverse=True``.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

from metavision_studio._progress import ProgressFn, track
from metavision_studio.io.data import MSIData
from metavision_studio.io.raster import Raster

__all__ = [
    "blank_sections",
    "drop_masked_pixels",
    "prevalence",
    "reference_feature",
    "remove_low_prevalence",
    "section_quality",
    "shell_mask",
]


def prevalence(data: MSIData) -> pd.Series:
    """Fraction of pixels in which each feature is detected (non-zero, non-NaN)."""
    detected = np.nan_to_num(data.values, nan=0.0) != 0
    return pd.Series(detected.mean(axis=0), index=data.features.index, name="prevalence")


def reference_feature(data: MSIData) -> str:
    """The most prevalent feature: a stable image for estimating the alignment."""
    return str(prevalence(data).idxmax())


def remove_low_prevalence(data: MSIData, min_prevalence: float = 0.1) -> tuple[MSIData, list[str]]:
    """Keep features detected in more than ``min_prevalence`` of pixels.

    Returns:
        The filtered data and the list of removed feature IDs.
    """
    prev = prevalence(data)
    keep = prev.index[prev > min_prevalence].tolist()
    removed = prev.index[prev <= min_prevalence].tolist()
    return data.subset(features=keep), removed


def blank_sections(data: MSIData, sections: Sequence[str]) -> MSIData:
    """Set every intensity in ``sections`` to zero but keep the sections in the stack."""
    mask = data.pixels["section"].isin([str(s) for s in sections]).to_numpy()
    values = data.values.copy()
    values[mask] = 0
    return data.with_values(values, blanked_sections=[str(s) for s in sections])


def section_quality(
    data: MSIData,
    *,
    min_pixel_fraction: float = 0.25,
    min_signal_fraction: float = 0.1,
) -> pd.DataFrame:
    """Flag sections that look empty, tiny or unusually weak.

    A section is flagged when it has no signal, fewer than ``min_pixel_fraction`` x the median
    pixel count, or a mean total intensity per pixel below ``min_signal_fraction`` x the median
    across sections. Medians make the thresholds robust to a few bad sections.

    Returns:
        One row per section, in natural order: ``section``, ``n_pixels``, ``total``,
        ``mean_signal``, ``flagged`` (bool) and ``reason`` (human-readable, empty when fine).
    """
    values = np.nan_to_num(data.values, nan=0.0)
    row_total = values.sum(axis=1, dtype=np.float64)
    df = pd.DataFrame({"section": data.pixels["section"].to_numpy(), "total": row_total})
    agg = df.groupby("section", sort=False)["total"].agg(n_pixels="size", total="sum")
    agg = agg.reindex(data.sections)
    agg["mean_signal"] = agg["total"] / agg["n_pixels"].clip(lower=1)
    med_px = float(np.median(agg["n_pixels"]))
    med_sig = float(np.median(agg["mean_signal"]))

    reasons = []
    for n_px, total, mean_sig in agg[["n_pixels", "total", "mean_signal"]].itertuples(index=False):
        if total == 0:
            reasons.append("no signal")
        elif n_px < min_pixel_fraction * med_px:
            reasons.append(f"only {int(n_px):,} pixels (typical {int(med_px):,})")
        elif med_sig > 0 and mean_sig < min_signal_fraction * med_sig:
            reasons.append(f"signal {med_sig / mean_sig:.0f}× weaker than typical")  # noqa: RUF001
        else:
            reasons.append("")
    agg["reason"] = reasons
    agg["flagged"] = agg["reason"] != ""
    return agg.reset_index().rename(columns={"index": "section"})[
        ["section", "n_pixels", "total", "mean_signal", "flagged", "reason"]
    ]


def _remove_small(fn, img: np.ndarray, below: int) -> np.ndarray:
    """``remove_small_objects/holes`` for objects smaller than ``below`` (any skimage >= 0.24)."""
    import inspect

    if "max_size" in inspect.signature(fn).parameters:  # scikit-image >= 0.26
        return fn(img, max_size=below - 1)
    key = "min_size" if "min_size" in inspect.signature(fn).parameters else "area_threshold"
    return fn(img, **{key: below})


def shell_mask(
    stack: np.ndarray,
    *,
    gaussian_sigma: float = 1.0,
    closing_disk_radius: int = 5,
    progress: ProgressFn | None = None,
) -> np.ndarray:
    """Boolean stack marking the off-tissue "shell" pixels in each section.

    Port of upstream ``get_shell_mask``: Otsu-threshold a smoothed image of a feature that
    lights up the shell, close it morphologically, and keep measured pixels outside the cleaned
    tissue body.
    """
    from skimage import exposure, filters, morphology

    out = np.zeros(stack.shape, dtype=bool)
    for i in track(range(stack.shape[0]), progress, stack.shape[0], "Detecting shell"):
        img = stack[i].astype(np.float64)
        if not np.any(img > 0) or img.max() == img.min():
            continue
        rescaled = exposure.rescale_intensity(img)
        smooth = filters.gaussian(rescaled, sigma=gaussian_sigma)
        binary = smooth > filters.threshold_otsu(smooth)
        closed = morphology.closing(binary, morphology.disk(closing_disk_radius)).astype(bool)
        background = _remove_small(morphology.remove_small_objects, ~(img > 0), 100)
        tissue = ~(background | closed)
        tissue = _remove_small(morphology.remove_small_objects, tissue, 500)
        tissue = _remove_small(morphology.remove_small_holes, tissue, 1000)
        out[i] = ~tissue & (img > 0)
    return out


def drop_masked_pixels(data: MSIData, raster: Raster, mask: np.ndarray) -> MSIData:
    """Remove the pixels that fall on ``True`` voxels of ``mask`` (a stack from ``raster``)."""
    hit = mask[raster.slice_index, raster.rows, raster.cols]
    return data.subset(pixel_mask=~hit)
