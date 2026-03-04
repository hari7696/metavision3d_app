# Adapted from MetaVision3D (https://github.com/XinBiostats/MetaVision3D, commit a108fe8).
# © 2023 University of Florida Research Foundation, Inc. Licensed under CC BY-NC-SA 4.0
# (https://creativecommons.org/licenses/by-nc-sa/4.0/).
# Changes: one tidy DataFrame per evaluation; empty sections give NaN instead of errors.
"""Quality metrics for alignment and imputation (upstream ``evaluate.py``).

* :func:`adjacent_similarity`: similarity of each section to the next one (upstream
  ``calculate_metric(..., 'alignment', ...)``). Higher correlation/ECC/SSIM and lower MSE after
  alignment mean better registration.
* :func:`paired_similarity`: section-by-section similarity of two stacks, e.g. before vs after
  imputation (upstream ``calculate_metric(..., 'imputation', ...)``).

Metrics: Pearson correlation over pixels where either image has signal (new), OpenCV ECC,
SSIM on min-max-scaled uint8 images, and MSE, all as in upstream. An empty or constant
section gives NaN where upstream raised or divided by zero.
"""

from __future__ import annotations

import cv2
import numpy as np
import pandas as pd
from skimage.metrics import mean_squared_error, structural_similarity

__all__ = ["adjacent_similarity", "paired_similarity"]


def _minmax_uint8(img: np.ndarray) -> np.ndarray:
    lo, hi = float(img.min()), float(img.max())
    if hi == lo:
        return np.zeros(img.shape, dtype=np.uint8)
    return ((img - lo) / (hi - lo) * 255).astype(np.uint8)


def _metrics(a: np.ndarray, b: np.ndarray) -> dict[str, float]:
    a = a.astype(np.float32, copy=False)
    b = b.astype(np.float32, copy=False)
    nan = float("nan")
    if not (np.any(a) and np.any(b)):
        return {"corr": nan, "ecc": nan, "ssim": nan, "mse": nan}
    m = (a > 0) | (b > 0)
    x, y = a[m].astype(np.float64), b[m].astype(np.float64)
    corr = float(np.corrcoef(x, y)[0, 1]) if x.std() > 0 and y.std() > 0 else nan
    try:
        ecc = float(cv2.computeECC(a, b))
    except cv2.error:
        ecc = nan
    ssim = float(structural_similarity(_minmax_uint8(a), _minmax_uint8(b), data_range=255))
    mse = float(mean_squared_error(a, b))
    return {"corr": corr, "ecc": ecc, "ssim": ssim, "mse": mse}


def adjacent_similarity(stack: np.ndarray) -> pd.DataFrame:
    """One row per adjacent pair ``(i, i+1)``.

    Columns: ``section``, ``next``, ``corr``, ``ecc``, ``ssim``, ``mse``.
    """
    rows = [
        {"section": i, "next": i + 1, **_metrics(stack[i], stack[i + 1])}
        for i in range(len(stack) - 1)
    ]
    return pd.DataFrame(rows, columns=["section", "next", "corr", "ecc", "ssim", "mse"])


def paired_similarity(stack_a: np.ndarray, stack_b: np.ndarray) -> pd.DataFrame:
    """One row per section comparing ``stack_a[i]`` with ``stack_b[i]``."""
    if stack_a.shape != stack_b.shape:
        raise ValueError("stacks must have the same shape")
    rows = [{"section": i, **_metrics(stack_a[i], stack_b[i])} for i in range(len(stack_a))]
    return pd.DataFrame(rows, columns=["section", "corr", "ecc", "ssim", "mse"])
