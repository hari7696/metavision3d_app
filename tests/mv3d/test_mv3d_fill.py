"""MetaImpute3D / MetaInterp3D: vectorised versions match direct ports of upstream loops."""

import cv2
import numpy as np
import pytest
from scipy import interpolate as sp_interp

from metavision_studio import mv3d

# ---------------------------------------------------------------- upstream reference ports
# Verbatim logic of MetaVision3D modules/MetaImpute3D.py and MetaInterp3D.py (commit a108fe8),
# © 2023 University of Florida Research Foundation, Inc., CC BY-NC-SA 4.0. Used only as oracles.


def _up_find_neighbors(imgs, target_img, radius):
    target = imgs[target_img].copy()
    start_index = max(0, target_img - radius)
    end_index = min(len(imgs), target_img + radius + 1)
    before = imgs[start_index:target_img, :, :].copy()
    after = imgs[target_img + 1 : end_index, :, :].copy()
    neighbors = np.concatenate((before, after), axis=0)
    return target, neighbors, before, after


def _up_find_impute_mask(target, neighbors, before, after):
    if len(after) > 0:
        mask1 = ((np.sum(after > 0, axis=0) >= 1) & (target == 0)).astype(np.uint8)
    else:
        mask1 = ((np.sum(before > 0, axis=0) >= 1) & (target == 0)).astype(np.uint8)
    binary_img = (target > 0).astype(np.uint8)
    contours, _ = cv2.findContours(binary_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    mask2 = np.zeros_like(binary_img)
    for contour in contours:
        cv2.drawContours(mask2, [contour], -1, 255, thickness=3)
    mask2 = cv2.bitwise_and(binary_img, mask2)
    return (mask1 | mask2).astype(bool)


def _up_impute(neighbors):
    mask = neighbors != 0
    s = np.sum(neighbors * mask, axis=0)
    c = np.sum(mask, axis=0)
    out = np.zeros_like(s)
    nz = c != 0
    out[nz] = np.divide(s[nz], c[nz])
    return out


def upstream_seq_impute(matrix, radius):
    m = matrix.copy()
    for t in range(len(matrix)):
        target, neighbors, before, after = _up_find_neighbors(m, t, radius)
        mask = _up_find_impute_mask(target, neighbors, before, after)
        imputation = _up_impute(neighbors)
        m[t][mask] = imputation[mask]
    return m


def upstream_interp(matrix, insert):
    out = np.zeros((insert * (matrix.shape[0] - 1) + matrix.shape[0], *matrix.shape[1:]))
    x = np.linspace(1, matrix.shape[0], matrix.shape[0])
    x_new = np.linspace(1, matrix.shape[0], out.shape[0])
    for ii in range(out.shape[1]):
        for ij in range(out.shape[2]):
            out[:, ii, ij] = sp_interp.interp1d(x, matrix[:, ii, ij])(x_new)
    return out


# ---------------------------------------------------------------- tests


def _random_tissue_stack(seed=0, n=6, h=24, w=28):
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:h, 0:w]
    stack = np.zeros((n, h, w), dtype=np.float32)
    for i in range(n):
        blob = ((yy - h / 2) / (h * 0.35)) ** 2 + ((xx - w / 2 - i % 3) / (w * 0.35)) ** 2 < 1
        vals = rng.gamma(2.0, 10.0, size=(h, w)).astype(np.float32)
        holes = rng.random((h, w)) < 0.15  # missing pixels inside tissue
        stack[i] = np.where(blob & ~holes, vals, 0)
    stack[2, 5:12, 6:14] = 0  # a torn region
    return stack


@pytest.mark.parametrize("radius", [1, 2])
@pytest.mark.parametrize("seed", [0, 1, 2])
def test_impute_matches_upstream(radius, seed):
    stack = _random_tissue_stack(seed)
    ours = mv3d.impute(stack, radius=radius)
    ref = upstream_seq_impute(stack.copy(), radius)
    np.testing.assert_allclose(ours, ref, rtol=1e-5, atol=1e-4)


def test_impute_fills_hole_and_does_not_mutate_input():
    stack = _random_tissue_stack()
    before = stack.copy()
    out = mv3d.impute(stack, radius=1)
    assert np.array_equal(stack, before)
    assert not stack[2, 5:12, 6:14].any()
    assert (out[2, 5:12, 6:14] > 0).mean() > 0.6  # the torn region is mostly filled
    assert out.dtype == np.float32


def test_impute_rejects_bad_radius():
    with pytest.raises(ValueError):
        mv3d.impute(_random_tissue_stack(), radius=0)


@pytest.mark.parametrize("n_insert", [1, 2, 3])
def test_interpolate_matches_upstream(n_insert):
    stack = _random_tissue_stack(n=5, h=10, w=12)
    ours = mv3d.interpolate(stack, n_insert=n_insert)
    ref = upstream_interp(stack.astype(np.float64), n_insert)
    assert ours.shape == ref.shape == (5 + n_insert * 4, 10, 12)
    np.testing.assert_allclose(ours, ref, rtol=1e-5, atol=1e-3)


def test_interpolate_keeps_originals_and_edge_cases():
    stack = _random_tissue_stack(n=4, h=8, w=8)
    out = mv3d.interpolate(stack, n_insert=2)
    assert np.allclose(out[::3], stack)
    assert np.array_equal(mv3d.interpolate(stack, n_insert=0), stack)
    assert mv3d.interpolate(stack[:1], n_insert=3).shape == (1, 8, 8)
    with pytest.raises(ValueError):
        mv3d.interpolate(stack, n_insert=-1)
