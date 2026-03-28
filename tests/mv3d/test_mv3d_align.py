"""MetaAlign3D: recovery of known rigid misalignment, empty/failed sections, persistence."""

import numpy as np
import pytest

from metavision_studio import mv3d
from metavision_studio._progress import Cancelled
from metavision_studio.io import build_raster


def _centroid(img):
    yy, xx = np.nonzero(img > 0)
    return np.array([yy.mean(), xx.mean()])


def _mean_adjacent_corr(stack):
    return np.nanmean(mv3d.adjacent_similarity(stack)["corr"])


def test_alignment_recovers_rigid_shifts(phantom_data, shifts):
    data = phantom_data.data
    raster = build_raster(data)
    aln = mv3d.compute_alignment(data, raster, reference="ref")
    raw = raster.stack_feature(data, "ref")
    aligned = mv3d.apply_alignment(raw, aln)

    assert aln.warps.shape == (len(shifts), 2, 3)
    assert np.allclose(aln.warps[0], np.eye(2, 3))
    assert aln.failed == []
    c0 = _centroid(aligned[0])
    for i in range(1, len(shifts)):
        assert np.linalg.norm(_centroid(aligned[i]) - c0) < 1.0, f"section {i} not aligned"
    assert np.isnan(aln.scores[0]) and np.all(aln.scores[1:] > 0.9)
    assert _mean_adjacent_corr(aligned) > _mean_adjacent_corr(raw) + 0.1


def test_warps_apply_to_other_features(phantom_data, shifts):
    data = phantom_data.data
    raster = build_raster(data)
    aln = mv3d.compute_alignment(data, raster, reference="ref")
    other = mv3d.apply_alignment(raster.stack_feature(data, "other"), aln)
    masks = other > 0
    c0 = _centroid(masks[0])
    assert all(np.linalg.norm(_centroid(masks[i]) - c0) < 1.0 for i in range(1, len(shifts)))


def test_default_reference_is_most_prevalent(phantom_data):
    data = phantom_data.data
    aln = mv3d.compute_alignment(data, build_raster(data))
    assert aln.reference in {"ref", "other"}  # equal prevalence; never the sparse feature
    assert aln.reference != "sparse"


def test_empty_section_is_skipped_and_chain_continues(shifts, phantom_factory):
    ph = phantom_factory(shifts, empty=(3,))
    raster = build_raster(ph.data)
    aln = mv3d.compute_alignment(ph.data, raster, reference="ref")
    aligned = mv3d.apply_alignment(raster.stack_feature(ph.data, "ref"), aln)
    assert np.allclose(aln.warps[3], np.eye(2, 3))
    assert np.isnan(aln.scores[3])
    assert not aligned[3].any()
    c0 = _centroid(aligned[0])
    assert np.linalg.norm(_centroid(aligned[4]) - c0) < 1.0  # section after the gap still aligned


def test_ecc_failure_keeps_identity_and_raw_image(phantom_data, monkeypatch):
    from metavision_studio.mv3d import align as align_mod

    real = align_mod._ecc
    calls = {"n": 0}

    def flaky(template, moving, max_iter, eps):
        calls["n"] += 1
        return None if calls["n"] == 2 else real(template, moving, max_iter, eps)

    monkeypatch.setattr(align_mod, "_ecc", flaky)
    data = phantom_data.data
    raster = build_raster(data)
    aln = mv3d.compute_alignment(data, raster, reference="ref")
    assert aln.failed == [2]
    assert np.allclose(aln.warps[2], np.eye(2, 3))
    aligned = mv3d.apply_alignment(raster.stack_feature(data, "ref"), aln)
    assert aligned.dtype == np.float32 and aligned[2].max() > 1  # not a uint8-rescaled image


def test_all_zero_input_does_not_crash(shifts, phantom_factory):
    ph = phantom_factory(shifts[:3], empty=(0, 1, 2))
    aln = mv3d.compute_alignment(ph.data, build_raster(ph.data), reference="ref")
    assert np.allclose(aln.warps, np.eye(2, 3)) and np.all(np.isnan(aln.scores))


def test_progress_and_cancel(phantom_data, shifts):
    data = phantom_data.data
    raster = build_raster(data)
    seen = []
    mv3d.compute_alignment(data, raster, progress=lambda d, t, m: seen.append((d, t)))
    assert seen[-1] == (len(shifts), len(shifts))

    def cancel(done, total, msg):
        if done == 2:
            raise Cancelled

    with pytest.raises(Cancelled):
        mv3d.compute_alignment(data, raster, progress=cancel)


def test_save_load_roundtrip(phantom_data, tmp_path):
    data = phantom_data.data
    aln = mv3d.compute_alignment(data, build_raster(data), reference="ref")
    path = tmp_path / "alignment.npz"
    mv3d.save_alignment(aln, path)
    back = mv3d.load_alignment(path)
    assert back.reference == "ref"
    assert np.array_equal(back.warps, aln.warps)
    assert np.array_equal(back.scores, aln.scores, equal_nan=True)
    assert back.failed == aln.failed and back.sections == aln.sections


def test_apply_alignment_checks_section_count(phantom_data):
    data = phantom_data.data
    raster = build_raster(data)
    aln = mv3d.compute_alignment(data, raster, reference="ref")
    with pytest.raises(ValueError, match="sections"):
        mv3d.apply_alignment(raster.stack_feature(data, "ref")[:3], aln)


def test_natural_section_order_in_alignment(shifts, phantom_factory):
    names = ["1", "2", "3", "4", "5", "6", "10"]
    ph = phantom_factory(shifts, section_names=names)
    aln = mv3d.compute_alignment(ph.data, build_raster(ph.data), reference="ref")
    assert aln.sections == tuple(names)
