"""Turn pixel tables into image stacks: one 2-D image per section on a shared canvas.

Follows MetaVision3D's convention (image rows = ``x``, columns = ``y``, sections centred on
a canvas 10% larger than the biggest section, rounded up to a multiple of 10) with three
changes from the reference implementation:

* **Grid indexing by step, not rank.** Each section's coordinates are snapped to its own
  regular grid, ``round((x - x_min) / step)``. Upstream used the rank among unique values,
  which squashes a section if a whole row or column of pixels is missing.
* **One centring rule.** Upstream centred the reference stack with ``ceil`` but applied the
  warps to stacks centred with ``int``, which could shift images by one pixel.
* **Vectorised, float32.** No per-pixel Python loop, and no float16 overflow above 65 504.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from metavision_studio.io.data import MSIData

__all__ = ["Raster", "build_raster", "estimate_step"]


def estimate_step(coords: np.ndarray) -> float:
    """Grid spacing of one coordinate axis: the smallest common gap between unique values."""
    u = np.unique(np.asarray(coords, dtype=np.float64))
    if len(u) < 2:
        return 1.0
    diffs = np.diff(u)
    diffs = diffs[diffs > 1e-6 * max(1.0, float(np.abs(u).max()))]
    if len(diffs) == 0:
        return 1.0
    step = float(np.median(diffs))
    # A missing row/column produces a gap of 2*step; the median ignores those.
    small = diffs[diffs < 1.5 * step]
    return float(np.median(small)) if len(small) else step


@dataclass(frozen=True, eq=False)
class Raster:
    """Where each pixel of an :class:`MSIData` lands in a ``(sections, rows, cols)`` stack."""

    sections: tuple[str, ...]
    shape: tuple[int, int]
    slice_index: np.ndarray  # (n_pixels,) int32
    rows: np.ndarray  # (n_pixels,) int32
    cols: np.ndarray  # (n_pixels,) int32
    step: float  # grid spacing in input coordinate units (typically µm)

    @property
    def stack_shape(self) -> tuple[int, int, int]:
        return (len(self.sections), *self.shape)

    def stack(self, column: np.ndarray, *, fill: float = 0.0) -> np.ndarray:
        """Place one value per pixel into a float32 stack. NaN becomes ``fill``."""
        out = np.full(self.stack_shape, fill, dtype=np.float32)
        vals = np.asarray(column, dtype=np.float32)
        ok = np.isfinite(vals) & (self.rows >= 0)
        out[self.slice_index[ok], self.rows[ok], self.cols[ok]] = vals[ok]
        return out

    def tissue_mask(self) -> np.ndarray:
        """Boolean stack: True where a pixel was measured."""
        out = np.zeros(self.stack_shape, dtype=bool)
        ok = self.rows >= 0
        out[self.slice_index[ok], self.rows[ok], self.cols[ok]] = True
        return out

    def reindex(self, base: MSIData, other: MSIData) -> Raster:
        """This canvas, indexed for ``other``'s pixels instead of ``base``'s.

        ``self`` must have been built from ``base``. Pixels of ``other`` are matched to
        ``base`` on ``(section, x, y)``, so a subset (e.g. after normalisation dropped empty
        pixels, or only some samples were clustered) lands exactly where it was in ``base``
        and every layer overlays. Pixels not in ``base`` are left out (index -1).
        """
        keys = ["section", "x", "y"]
        left = other.pixels[keys].reset_index(drop=True)
        right = base.pixels[keys].copy()
        right["_i"] = np.arange(base.n_pixels)
        idx = left.merge(right, on=keys, how="left")["_i"].to_numpy()
        found = ~np.isnan(idx.astype(np.float64))
        src = np.where(found, idx, 0).astype(np.int64)

        def pick(arr: np.ndarray) -> np.ndarray:
            return np.where(found, arr[src], -1).astype(np.int32)

        return Raster(
            sections=self.sections,
            shape=self.shape,
            slice_index=np.where(found, self.slice_index[src], 0).astype(np.int32),
            rows=pick(self.rows),
            cols=pick(self.cols),
            step=self.step,
        )

    def stack_feature(self, data: MSIData, feature: str) -> np.ndarray:
        return self.stack(data.column(feature))


def build_raster(data: MSIData, *, margin: float = 1.1) -> Raster:
    """Compute the canvas and per-pixel stack indices for ``data``.

    Sections are ordered naturally (``"2"`` before ``"10"``), which fixes upstream sorting
    string IDs lexically.
    """
    sections = data.sections
    sec_col = data.pixels["section"].to_numpy()
    x = data.pixels["x"].to_numpy(dtype=np.float64)
    y = data.pixels["y"].to_numpy(dtype=np.float64)

    n = data.n_pixels
    slice_index = np.empty(n, dtype=np.int32)
    local_r = np.empty(n, dtype=np.int64)
    local_c = np.empty(n, dtype=np.int64)
    extents: list[tuple[int, int]] = []
    steps: list[float] = []

    for i, sec in enumerate(sections):
        m = sec_col == sec
        xs, ys = x[m], y[m]
        sx, sy = estimate_step(xs), estimate_step(ys)
        steps += [sx, sy]
        r = np.rint((xs - xs.min()) / sx).astype(np.int64)
        c = np.rint((ys - ys.min()) / sy).astype(np.int64)
        slice_index[m] = i
        local_r[m], local_c[m] = r, c
        extents.append((int(r.max()) + 1, int(c.max()) + 1))

    def canvas(size: int) -> int:
        return int(np.ceil(((size * margin + 9) // 10) * 10))

    height = max(canvas(h) for h, _ in extents)
    width = max(canvas(w) for _, w in extents)

    rows = np.empty(n, dtype=np.int32)
    cols = np.empty(n, dtype=np.int32)
    for i, (h, w) in enumerate(extents):
        m = slice_index == i
        rows[m] = local_r[m] + (height - h) // 2
        cols[m] = local_c[m] + (width - w) // 2

    return Raster(
        sections=tuple(sections),
        shape=(height, width),
        slice_index=slice_index,
        rows=rows,
        cols=cols,
        step=float(np.median(steps)) if steps else 1.0,
    )
