"""Synthetic serial-section phantoms for MetaVision3D tests (generated in code, no files)."""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np
import pytest

from metavision_studio.io import MSIData

H, W = 48, 56  # field of view per section, in pixels
STEP = 50.0  # µm


def phantom(h: int = H, w: int = W) -> np.ndarray:
    """An asymmetric 'brain-like' blob with internal structure (so rotation is identifiable)."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cy, cx = h / 2, w / 2
    body = ((yy - cy) / (h * 0.32)) ** 2 + ((xx - cx) / (w * 0.36)) ** 2 < 1
    img = np.where(body, 100.0, 0.0).astype(np.float32)
    img += 80.0 * np.exp(-(((yy - cy + 6) ** 2) + (xx - cx - 9) ** 2) / 18.0)  # off-centre hot spot
    img[(yy > cy + 3) & (yy < cy + 7) & (xx > cx - 14) & (xx < cx + 2) & body] += 60.0  # a bar
    return img * body


def rigid(img: np.ndarray, dx: float, dy: float, angle_deg: float) -> np.ndarray:
    h, w = img.shape
    m = cv2.getRotationMatrix2D((w / 2, h / 2), angle_deg, 1.0)
    m[:, 2] += (dx, dy)
    return cv2.warpAffine(img, m, (w, h), flags=cv2.INTER_LINEAR)


@dataclass
class Phantom:
    data: MSIData
    shifts: list[tuple[float, float, float]]  # (dx cols, dy rows, angle) per section
    images: np.ndarray  # (n, H, W) reference images as generated


def make_phantom(
    shifts: list[tuple[float, float, float]],
    *,
    empty: tuple[int, ...] = (),
    section_names: list[str] | None = None,
) -> Phantom:
    """Sections = rigidly transformed copies of :func:`phantom`; the full field of view is exported.

    Exporting every pixel of the field of view (zeros outside tissue) keeps each section's
    bounding box identical, so the raster preserves the simulated misalignment.
    """
    base = phantom()
    rng = np.random.default_rng(0)
    xs, ys, secs, vals = [], [], [], []
    imgs = []
    names = section_names or [str(i + 1) for i in range(len(shifts))]
    yy, xx = np.mgrid[0:H, 0:W]
    for i, (dx, dy, ang) in enumerate(shifts):
        img = rigid(base, dx, dy, ang)
        img[img < 1] = 0
        if i in empty:
            img = np.zeros_like(img)
        imgs.append(img)
        ref = img
        other = np.where(img > 0, 50.0 + 10 * rng.random(img.shape), 0.0)  # second feature
        sparse = np.where(rng.random(img.shape) < 0.03, img, 0.0)  # rarely detected feature
        # rows = x, cols = y (MetaVision3D convention); offset each section on the slide
        xs.append((yy.ravel() + 1000 * i) * STEP)
        ys.append((xx.ravel() - 300 * i) * STEP)
        secs.append(np.full(H * W, names[i]))
        vals.append(np.stack([ref.ravel(), other.ravel(), sparse.ravel()], axis=1))
    data = MSIData.from_arrays(
        x=np.concatenate(xs),
        y=np.concatenate(ys),
        section=np.concatenate(secs),
        values=np.concatenate(vals).astype(np.float32),
        feature_ids=["ref", "other", "sparse"],
        pixel_size_um=STEP,
    )
    return Phantom(data=data, shifts=shifts, images=np.stack(imgs))


SHIFTS = [(0, 0, 0), (2, -1, 3), (-3, 2, -4), (1, 3, 6), (-2, -3, -2), (3, 1, 4), (0, -2, -5)]


@pytest.fixture
def phantom_data() -> Phantom:
    return make_phantom(SHIFTS)


@pytest.fixture
def shifts() -> list[tuple[float, float, float]]:
    return list(SHIFTS)


@pytest.fixture
def phantom_factory():
    return make_phantom
