"""MetaAtlas3D voxel sizes survive a NIfTI round-trip; evaluation metrics; methods text."""

import nibabel as nib
import numpy as np
import pytest

from metavision_studio import mv3d


def test_voxel_size():
    assert mv3d.voxel_size(pixel_size_um=50, thickness_um=10, gap_um=50, n_insert=2) == (20, 50, 50)
    with pytest.raises(ValueError):
        mv3d.voxel_size(pixel_size_um=0, thickness_um=10)


def test_nifti_roundtrip_keeps_physical_voxel_size(tmp_path):
    stack = np.random.default_rng(0).random((7, 12, 9)).astype(np.float32)
    img = mv3d.to_nifti(stack, pixel_size_um=50, thickness_um=10, gap_um=50, n_insert=2)
    path = tmp_path / "atlas.nii.gz"
    nib.save(img, path)
    back = nib.load(path)
    assert back.shape == (9, 12, 7)  # (y, x, section) as upstream
    assert np.allclose(back.header.get_zooms(), (0.05, 0.05, 0.02))  # mm
    assert back.header.get_xyzt_units()[0] == "mm"
    np.testing.assert_array_equal(np.asarray(back.dataobj), np.transpose(stack, (2, 1, 0)))


def test_adjacent_and_paired_similarity():
    rng = np.random.default_rng(1)
    a = rng.random((4, 16, 16)).astype(np.float32)
    stack = np.stack([a[0], a[0], a[1], np.zeros_like(a[0])])
    df = mv3d.adjacent_similarity(stack)
    assert list(df.columns) == ["section", "next", "corr", "ecc", "ssim", "mse"]
    assert df.loc[0, "corr"] == pytest.approx(1.0) and df.loc[0, "mse"] == pytest.approx(0)
    assert np.isnan(df.loc[2, "corr"])  # empty section → NaN, no crash
    paired = mv3d.paired_similarity(stack, stack)
    assert np.allclose(paired["ssim"].iloc[:3], 1.0)
    with pytest.raises(ValueError):
        mv3d.paired_similarity(stack, stack[:2])


@pytest.mark.parametrize(
    ("step", "params", "expect"),
    [
        ("normalise", {"method": "tic+section"}, "total ion current"),
        ("align", {"reference": "PI(38:4)"}, "ECC"),
        ("fill", {"impute": True, "radius": 1, "n_insert": 2}, "MetaImpute3D"),
        ("atlas", {"thickness_um": 10, "gap_um": 50, "voxel_size_um": (20, 50, 50)}, "NIfTI"),
    ],
)
def test_describe(step, params, expect):
    text = mv3d.describe(step, params)
    assert expect in text and "Ma et al." in text
    assert text[0].isupper()


def test_describe_unknown_step_is_empty():
    assert mv3d.describe("cluster", {}) == ""
