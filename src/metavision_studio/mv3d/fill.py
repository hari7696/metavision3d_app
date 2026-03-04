# Adapted from MetaVision3D (https://github.com/XinBiostats/MetaVision3D, commit a108fe8).
# © 2023 University of Florida Research Foundation, Inc. Licensed under CC BY-NC-SA 4.0
# (https://creativecommons.org/licenses/by-nc-sa/4.0/).
# Changes: vectorised (no per-pixel loops, no neighbour copies), float32, cancellable progress.
"""MetaImpute3D and MetaInterp3D: fill gaps within and between sections.

**Imputation** (:func:`impute`, port of ``MetaImpute3D.seq_impute``) visits sections in
order. For each section ``t`` it uses the neighbours within ``radius`` sections (earlier
neighbours already imputed, later ones not yet) and replaces two sets of pixels with the
neighbours' mean non-zero intensity:

1. pixels that are empty in ``t`` but measured in a *later* neighbour (or in an earlier one,
   at the last section): holes and missing tissue;
2. a 3-pixel band along the inside of the tissue outline in ``t``, which smooths ragged edges.

This is the same algorithm and output as upstream; only the implementation is vectorised.

**Interpolation** (:func:`interpolate`, port of ``MetaInterp3D``) inserts ``n_insert``
linearly interpolated sections between each pair of neighbours. It's equivalent to upstream's
per-pixel ``scipy.interpolate.interp1d`` loop, but computed in one vectorised pass (hundreds
of times faster).
"""

from __future__ import annotations

import cv2
import numpy as np

from metavision_studio._progress import ProgressFn, report

__all__ = ["impute", "interpolate"]


def _edge_band(target: np.ndarray, thickness: int = 3) -> np.ndarray:
    binary = (target > 0).astype(np.uint8)
    if not binary.any():
        return np.zeros(target.shape, dtype=bool)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    band = np.zeros_like(binary)
    cv2.drawContours(band, contours, -1, 255, thickness=thickness)
    return cv2.bitwise_and(binary, band).astype(bool)


def impute(
    stack: np.ndarray,
    *,
    radius: int = 1,
    progress: ProgressFn | None = None,
) -> np.ndarray:
    """Fill missing pixels from neighbouring sections; returns a new float32 stack.

    Args:
        stack: ``(sections, rows, cols)`` intensities, usually after alignment.
        radius: how many sections on each side to borrow from (upstream default 1 in the demo).
        progress: ``progress(done, total, message)``. Raise ``Cancelled`` from it to stop.
    """
    if radius < 1:
        raise ValueError("radius must be at least 1")
    out = np.array(stack, dtype=np.float32, copy=True)
    n = out.shape[0]
    for t in range(n):
        report(progress, t, n, f"Imputing section {t + 1}/{n}")
        lo, hi = max(0, t - radius), min(n, t + radius + 1)
        before, after = out[lo:t], out[t + 1 : hi]
        target = out[t]

        if len(after):
            gap = (after > 0).any(axis=0) & (target == 0)
        else:
            gap = (before > 0).any(axis=0) & (target == 0)
        mask = gap | _edge_band(target)
        if not mask.any():
            continue

        total = before.sum(axis=0, dtype=np.float64) + after.sum(axis=0, dtype=np.float64)
        count = (before != 0).sum(axis=0) + (after != 0).sum(axis=0)
        mean = np.zeros(target.shape, dtype=np.float64)
        np.divide(total, count, out=mean, where=count != 0)
        target[mask] = mean[mask].astype(np.float32)
    report(progress, n, n, "Imputation done")
    return out


def interpolate(
    stack: np.ndarray,
    *,
    n_insert: int = 1,
    progress: ProgressFn | None = None,
) -> np.ndarray:
    """Insert ``n_insert`` linearly interpolated sections between each pair of sections.

    Output has ``n + n_insert * (n - 1)`` sections; the originals are kept at every
    ``(n_insert + 1)``-th position.
    """
    if n_insert < 0:
        raise ValueError("n_insert must be >= 0")
    src = np.asarray(stack, dtype=np.float32)
    n = src.shape[0]
    if n_insert == 0 or n < 2:
        return src.copy()
    n_out = n + n_insert * (n - 1)
    # Same sample positions as upstream: linspace(1, n, n) -> linspace(1, n, n_out).
    pos = np.linspace(0.0, n - 1.0, n_out)
    i0 = np.minimum(np.floor(pos).astype(np.int64), n - 2)
    frac = (pos - i0).astype(np.float32)
    out = np.empty((n_out, *src.shape[1:]), dtype=np.float32)
    for k in range(n_out):
        if k % 16 == 0:
            report(progress, k, n_out, f"Interpolating {k + 1}/{n_out}")
        f = frac[k]
        a, b = src[i0[k]], src[i0[k] + 1]
        out[k] = a if f == 0 else (b if f == 1 else a + f * (b - a))
    report(progress, n_out, n_out, "Interpolation done")
    return out
