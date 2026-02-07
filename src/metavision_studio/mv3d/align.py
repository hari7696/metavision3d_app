# Adapted from MetaVision3D (https://github.com/XinBiostats/MetaVision3D, commit a108fe8).
# © 2023 University of Florida Research Foundation, Inc. Licensed under CC BY-NC-SA 4.0
# (https://creativecommons.org/licenses/by-nc-sa/4.0/).
# Changes: pure functions, per-section warps, identity on ECC failure, empty-image guards,
# per-section alignment scores, cancellable progress.
"""MetaAlign3D: sequential rigid registration of serial sections with ECC.

Each non-empty section of the reference-feature stack is registered (OpenCV
``findTransformECC``, ``MOTION_EUCLIDEAN``, i.e. rotation plus translation) to the previous
non-empty section *after* that one has been aligned. The chain therefore puts every section
into the frame of the first section. The resulting warps are then applied to any feature's
stack built from the same :class:`~metavision_studio.io.Raster`.

Deviations from upstream ``MetaAlign3D``:

* **ECC failure** (non-convergence): upstream returned the *uint8-rescaled* image as the
  "aligned" section, which then became the reference for the next section and corrupted the
  chain. Here the section keeps the identity transform, its unwarped image is used as the
  next reference, and its index is reported in :attr:`Alignment.failed`.
* **Empty images:** upstream divided by ``image.max()`` and produced NaNs for all-zero
  sections. Empty sections are now skipped (identity warp, NaN score), and the next section is
  aligned to the last non-empty one. That matches upstream's intent, without its placeholder
  copy of the next section.
* **Warps per section:** ``warps`` has one entry per section (identity for the first). Upstream
  stored ``n-1`` warps offset by one.
* **No hidden cache.** Upstream silently reused ``./warpmatrix/warp_matrix_<group>.npy`` from
  disk, keyed only by name. Use :func:`save_alignment` / :func:`load_alignment` explicitly. The
  project layer stores them keyed by a fingerprint of the data and parameters.
* **Centring** is decided once by :func:`~metavision_studio.io.build_raster`, so the reference
  and the feature stacks share one rule (upstream mixed ``ceil`` and ``int``).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

import cv2
import numpy as np

from metavision_studio._progress import ProgressFn, report
from metavision_studio.io.data import MSIData
from metavision_studio.io.raster import Raster
from metavision_studio.mv3d.preprocess import reference_feature

__all__ = ["Alignment", "apply_alignment", "compute_alignment", "load_alignment", "save_alignment"]


@dataclass(frozen=True, eq=False)
class Alignment:
    """Rigid warps that put every section into the first section's frame.

    Attributes:
        reference: feature ID the warps were estimated from.
        warps: ``(n_sections, 2, 3)`` float32 affine matrices, in OpenCV's inverse-map
            convention (as passed to ``cv2.warpAffine(..., WARP_INVERSE_MAP)``).
        scores: ``(n_sections,)`` Pearson correlation of each aligned reference section with
            the previous non-empty aligned section, over pixels where either has signal.
            NaN for the first section and for empty sections.
        failed: indices of sections where ECC did not converge (identity kept).
        sections: section IDs in stack order.
    """

    reference: str
    warps: np.ndarray
    scores: np.ndarray
    failed: list[int] = field(default_factory=list)
    sections: tuple[str, ...] = ()

    @property
    def n_sections(self) -> int:
        return int(self.warps.shape[0])


def _to_uint8(img: np.ndarray) -> np.ndarray:
    peak = float(img.max())
    return (
        cv2.convertScaleAbs(img, alpha=255.0 / peak) if peak > 0 else np.zeros(img.shape, np.uint8)
    )


def _warp(img: np.ndarray, warp: np.ndarray) -> np.ndarray:
    h, w = img.shape
    return cv2.warpAffine(
        img.astype(np.float32, copy=False),
        warp.astype(np.float32, copy=False),
        (w, h),
        flags=cv2.INTER_LINEAR + cv2.WARP_INVERSE_MAP,
    )


def _correlation(a: np.ndarray, b: np.ndarray) -> float:
    m = (a > 0) | (b > 0)
    if m.sum() < 3:
        return float("nan")
    x, y = a[m].astype(np.float64), b[m].astype(np.float64)
    if x.std() == 0 or y.std() == 0:
        return float("nan")
    return float(np.corrcoef(x, y)[0, 1])


def _ecc(template: np.ndarray, moving: np.ndarray, max_iter: int, eps: float) -> np.ndarray | None:
    warp = np.eye(2, 3, dtype=np.float32)
    criteria = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, max_iter, eps)
    try:
        _, warp = cv2.findTransformECC(
            _to_uint8(template), _to_uint8(moving), warp, cv2.MOTION_EUCLIDEAN, criteria, None, 5
        )
    except cv2.error:
        return None
    return warp


def compute_alignment(
    data: MSIData,
    raster: Raster,
    *,
    reference: str | None = None,
    max_iter: int = 5000,
    eps: float = 1e-10,
    progress: ProgressFn | None = None,
) -> Alignment:
    """Estimate per-section rigid warps from one feature (default: the most prevalent).

    Pass *normalised* data. Upstream's demo and the 2024 app estimated warps from raw
    intensities.

    Args:
        data: pixel intensities.
        raster: canvas mapping for ``data`` (from :func:`~metavision_studio.io.build_raster`).
        reference: feature ID or name used for registration. ``None`` picks the most
            prevalent feature.
        max_iter, eps: ECC termination criteria (upstream: 5000 and 1e-10).
        progress: ``progress(done, total, message)``. Raise ``Cancelled`` from it to stop.
    """
    ref_id = (
        reference_feature(data)
        if reference is None
        else data.feature_ids[data.feature_index(reference)]
    )
    stack = raster.stack_feature(data, ref_id)
    n = stack.shape[0]
    warps = np.repeat(np.eye(2, 3, dtype=np.float32)[None], n, axis=0)
    scores = np.full(n, np.nan, dtype=np.float32)
    failed: list[int] = []

    previous: np.ndarray | None = None  # last non-empty aligned section
    for i in range(n):
        report(progress, i, n, f"Aligning section {i + 1}/{n}")
        img = stack[i]
        if not np.any(img > 0):
            continue
        if previous is None:
            previous = img
            continue
        warp = _ecc(previous, img, max_iter, eps)
        if warp is None:
            failed.append(i)
            aligned = img
        else:
            warps[i] = warp
            aligned = _warp(img, warp)
        scores[i] = _correlation(previous, aligned)
        previous = aligned
    report(progress, n, n, "Alignment done")
    return Alignment(
        reference=ref_id, warps=warps, scores=scores, failed=failed, sections=raster.sections
    )


def apply_alignment(stack: np.ndarray, alignment: Alignment) -> np.ndarray:
    """Apply the warps to a ``(sections, rows, cols)`` stack; returns a new float32 stack."""
    if stack.shape[0] != alignment.n_sections:
        raise ValueError(
            f"Stack has {stack.shape[0]} sections but the alignment has {alignment.n_sections}."
        )
    out = np.zeros(stack.shape, dtype=np.float32)
    for i in range(stack.shape[0]):
        img = stack[i]
        if not np.any(img != 0):
            continue
        w = alignment.warps[i]
        out[i] = img if np.allclose(w, np.eye(2, 3)) else _warp(img, w)
    return out


def save_alignment(alignment: Alignment, path: str | os.PathLike[str]) -> None:
    """Save to ``.npz`` (the caller chooses where; core code never picks a path)."""
    np.savez(
        path,
        reference=np.array(alignment.reference),
        warps=alignment.warps,
        scores=alignment.scores,
        failed=np.asarray(alignment.failed, dtype=np.int64),
        sections=np.asarray(alignment.sections, dtype=str),
    )


def load_alignment(path: str | os.PathLike[str]) -> Alignment:
    with np.load(path, allow_pickle=False) as z:
        return Alignment(
            reference=str(z["reference"]),
            warps=z["warps"].astype(np.float32),
            scores=z["scores"].astype(np.float32),
            failed=[int(i) for i in z["failed"]],
            sections=tuple(str(s) for s in z["sections"]),
        )
