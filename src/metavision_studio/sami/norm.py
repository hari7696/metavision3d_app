"""SAMI normalisation: row (pixel-wise) normalisation, transformation and scaling.

Adapted from SAMI (https://github.com/XinBiostats/SAMI, commit 80da10b), ``SAMI/norm.py``.
© 2023 University of Florida Research Foundation, Inc. Licensed under CC BY-NC-SA 4.0
(https://creativecommons.org/licenses/by-nc-sa/4.0/). The methods follow MetaboAnalyst's
normalisation module (Xia Lab, MetaboAnalystR, MIT).

Changes from upstream:

* Works on :class:`~metavision_studio.io.MSIData` and returns a new object. Upstream
  modified DataFrames and wrote ``*_norm.csv`` files.
* ``per_omics=True`` (default) applies row normalisation separately within each omics block.
  This reproduces upstream's workflow, where each omics CSV was normalised on its own before
  pooling. With merged data a single sum would mix lipid, metabolite and glycan intensities.
* Pixels whose row sum is zero are removed (as upstream did), in *any* omics block when
  ``per_omics`` (upstream dropped them per file and the inner join removed them from the pool).
  Pixels whose normalisation denominator is zero or non-finite (e.g. a zero median on sparse
  data) are also removed and counted in ``meta["dropped_pixels"]``. Upstream printed a warning
  and kept ``inf``/``NaN`` values.
* ``GroupMedianPQN`` used undefined globals upstream (NameError). It is implemented here as
  ``row="section_median_pqn"`` with sections as the groups.
* ``ParetoNorm`` was referenced but never defined upstream. It is implemented as
  ``(x - mean) / sqrt(sd)``.
* ``pqn`` is group PQN with every pixel as the reference group (the mean spectrum), because
  imaging data has no designated reference sample.
* Zero-variance features under ``auto``/``pareto``/``range`` scaling become 0 instead of NaN.
"""

from __future__ import annotations

import warnings
from typing import Literal

import numpy as np

from metavision_studio.io.data import MSIData

__all__ = ["RowNorm", "Scale", "Transform", "normalize"]

RowNorm = Literal["sum", "median", "comp", "pqn", "section_median_pqn", "none"]
Transform = Literal["log2", "log10", "glog2", "glog10", "sqrt", "cbrt", "none"]
Scale = Literal["none", "mean_center", "auto", "pareto", "range"]

_ROW = ("sum", "median", "comp", "pqn", "section_median_pqn", "none")
_TRANS = ("log2", "log10", "glog2", "glog10", "sqrt", "cbrt", "none")
_SCALE = ("none", "mean_center", "auto", "pareto", "range")


# ---------------------------------------------------------------------------- row methods
def _sum_norm(x: np.ndarray, c: float = 1.0) -> np.ndarray:
    return c * x / np.nansum(x, axis=1, keepdims=True)


def _median_norm(x: np.ndarray) -> np.ndarray:
    return x / np.nanmedian(x, axis=1, keepdims=True)


def _pqn(x: np.ndarray, ref_spectrum: np.ndarray) -> np.ndarray:
    with np.errstate(divide="ignore", invalid="ignore"):
        quotients = x / ref_spectrum
        quotients[~np.isfinite(quotients)] = np.nan
        factor = np.nanmedian(quotients, axis=1, keepdims=True)
    return x / factor


def _section_median_pqn(x: np.ndarray, groups: np.ndarray) -> np.ndarray:
    """GroupMedianPQN, fixed: scale each group so its median spectrum matches the overall one."""
    uniq = np.unique(groups)
    medians = np.vstack([np.median(x[groups == g], axis=0) for g in uniq])
    overall = np.nanmedian(medians, axis=0)
    with np.errstate(divide="ignore", invalid="ignore"):
        factors = overall / medians
    factors[~np.isfinite(factors)] = 1.0
    out = x.astype(np.float64, copy=True)
    for g, f in zip(uniq, factors, strict=True):
        out[groups == g] *= f
    return out


# ---------------------------------------------------------------------------- transforms
def _shifted(x: np.ndarray, divisor: float) -> np.ndarray:
    nz = np.abs(x[x != 0])
    min_val = (nz.min() / divisor) if nz.size else 1.0
    return (x + np.sqrt(x**2 + min_val**2)) / 2


def _transform(x: np.ndarray, method: str) -> np.ndarray:
    if method == "log2":  # LogTrans2
        return np.log2(x + 1)
    if method == "log10":
        return np.log10(x + 1)
    if method == "glog2":  # LogTrans1
        return np.log2(_shifted(x, 100))
    if method == "glog10":
        return np.log10(_shifted(x, 100))
    if method == "sqrt":  # SquareRootTrans
        return np.sqrt(_shifted(x, 10))
    if method == "cbrt":  # CubeRootTrans
        return _shifted(x, 10) ** (1 / 3)
    return x


def _scale(x: np.ndarray, method: str) -> np.ndarray:
    if method == "none":
        return x
    mean = np.nanmean(x, axis=0)
    if method == "mean_center":
        return x - mean
    if method == "range":
        denom = np.nanmax(x, axis=0) - np.nanmin(x, axis=0)
    else:
        sd = np.nanstd(x, axis=0)  # ddof=0, as upstream's AutoNorm
        denom = sd if method == "auto" else np.sqrt(sd)
    with np.errstate(divide="ignore", invalid="ignore"):
        out = (x - mean) / denom
    out[:, ~(denom > 0)] = 0.0
    return out


# ---------------------------------------------------------------------------- public
def normalize(
    data: MSIData,
    *,
    row: RowNorm = "sum",
    transform: Transform = "log2",
    scale: Scale = "none",
    reference: str | None = None,
    per_omics: bool = True,
) -> MSIData:
    """Normalise → transform → scale, as in SAMI (defaults: ``SumNorm`` + ``LogTrans2``).

    Args:
        data: pixel data, one or several omics (see :func:`~metavision_studio.io.merge_omics`).
        row: pixel-wise normalisation. ``sum`` scales each pixel to a total of 1 (TIC).
            ``median`` divides by the pixel median. ``comp`` divides by a reference feature,
            which is then removed. ``pqn`` is probabilistic quotient normalisation against
            the mean spectrum. ``section_median_pqn`` matches each section's median spectrum
            to the overall median.
        transform: ``log2`` / ``log10`` are log(x + 1) (upstream ``LogTrans2``). ``glog2`` /
            ``glog10`` are the generalised log (``LogTrans1``). ``sqrt`` / ``cbrt`` are shifted
            roots.
        scale: per-feature scaling: ``mean_center``, ``auto`` (z-score), ``pareto``, ``range``.
        reference: feature id or name for ``row="comp"``.
        per_omics: apply row normalisation within each omics block separately.

    Returns:
        A new :class:`MSIData` (pixels with a zero denominator are removed).
    """
    if row not in _ROW:
        raise ValueError(f"row must be one of {_ROW}, got {row!r}")
    if transform not in _TRANS:
        raise ValueError(f"transform must be one of {_TRANS}, got {transform!r}")
    if scale not in _SCALE:
        raise ValueError(f"scale must be one of {_SCALE}, got {scale!r}")

    x = data.values.astype(np.float64)
    omics = data.features["omics"].to_numpy()
    blocks = (
        [np.flatnonzero(omics == o) for o in dict.fromkeys(omics)]
        if per_omics
        else [np.arange(data.n_features)]
    )

    # Upstream: drop pixels whose (per-file) feature sum is zero.
    keep = np.ones(data.n_pixels, dtype=bool)
    for cols in blocks:
        keep &= np.nansum(x[:, cols], axis=1) != 0

    ref_idx: int | None = None
    if row == "comp":
        if reference is None:
            raise ValueError("row='comp' needs a reference feature.")
        ref_idx = data.feature_index(reference)
        keep &= np.isfinite(x[:, ref_idx]) & (x[:, ref_idx] != 0)

    x_kept = x[keep]
    with np.errstate(divide="ignore", invalid="ignore"):
        if row in ("sum", "median", "pqn"):
            out = np.empty_like(x_kept)
            for cols in blocks:
                sub = x_kept[:, cols]
                if row == "sum":
                    out[:, cols] = _sum_norm(sub)
                elif row == "median":
                    out[:, cols] = _median_norm(sub)
                else:
                    out[:, cols] = _pqn(sub, np.nanmean(sub, axis=0))
        elif row == "comp":
            out = x_kept / x_kept[:, [ref_idx]]
        elif row == "section_median_pqn":
            out = _section_median_pqn(x_kept, data.pixels["section"].to_numpy()[keep])
        else:
            out = x_kept

    # Pixels whose denominator was zero/non-finite (e.g. median 0 on sparse spectra).
    finite_rows = np.isfinite(out).all(axis=1)
    keep_idx = np.flatnonzero(keep)[finite_rows]
    out = out[finite_rows]
    dropped = data.n_pixels - len(keep_idx)
    if row in ("median", "pqn") and (~finite_rows).any():
        warnings.warn(
            f"{int((~finite_rows).sum())} pixels had a zero {row} denominator and were removed.",
            stacklevel=2,
        )

    # Upstream normalised each omics file separately, so the shift used by glog/sqrt/cbrt
    # (the block's smallest non-zero value) is computed per block too.
    if per_omics and transform in ("glog2", "glog10", "sqrt", "cbrt"):
        for cols in blocks:
            out[:, cols] = _transform(out[:, cols], transform)
    else:
        out = _transform(out, transform)
    out = _scale(out, scale)

    mask = np.zeros(data.n_pixels, dtype=bool)
    mask[keep_idx] = True
    result = data.subset(pixel_mask=mask)
    if ref_idx is not None:
        cols = np.delete(np.arange(data.n_features), ref_idx)
        result = result.subset(features=[data.feature_ids[i] for i in cols])
        out = np.delete(out, ref_idx, axis=1)
    return result.with_values(
        out,
        normalisation={
            "pipeline": "sami",
            "row": row,
            "transform": transform,
            "scale": scale,
            "reference": reference,
            "per_omics": per_omics,
        },
        dropped_pixels=int(dropped),
    )
