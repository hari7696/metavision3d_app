"""MetaNorm3D and preprocessing utilities."""

import numpy as np
import pytest

from metavision_studio import mv3d
from metavision_studio.io import MSIData, build_raster


def _data(values, sections, features=("a", "b", "c")):
    n = len(sections)
    return MSIData.from_arrays(
        x=np.arange(n),
        y=np.zeros(n),
        section=sections,
        values=np.asarray(values, np.float32),
        feature_ids=list(features),
    )


def test_tic_rows_sum_to_one_and_zero_rows_untouched():
    d = _data([[1, 1, 2], [0, 0, 0], [3, 0, 1]], ["1", "1", "2"])
    out = mv3d.normalize(d, method="tic")
    sums = out.values.sum(axis=1)
    assert np.allclose(sums, [1, 0, 1])
    assert out.meta["normalisation"] == "tic"


def test_normalize_does_not_mutate_input(phantom_data):
    d = phantom_data.data
    before = d.values.copy()
    mv3d.normalize(d)
    assert np.array_equal(d.values, before)


def test_section_norm_equalises_section_medians():
    rng = np.random.default_rng(0)
    vals = np.vstack([rng.uniform(1, 2, (50, 2)) * 1.0, rng.uniform(1, 2, (50, 2)) * 5.0])
    d = _data(vals, ["1"] * 50 + ["2"] * 50, features=("a", "b"))
    out = mv3d.normalize(d, method="section")
    med1 = np.median(out.values[:50], axis=0)
    med2 = np.median(out.values[50:], axis=0)
    assert np.allclose(med1, med2, rtol=1e-5)


def test_section_norm_zero_median_factor_is_one():
    # Feature 'a' is detected only in section 1: median across sections is 0.
    vals = [[5, 1], [5, 1], [0, 2], [0, 2], [0, 3], [0, 3]]
    d = _data(vals, ["1", "1", "2", "2", "3", "3"], features=("a", "b"))
    out = mv3d.normalize(d, method="section")
    assert np.allclose(out.values[:2, 0], 5)  # upstream would have zeroed these


def test_section_factors_follow_natural_order():
    d = _data([[1], [2], [4]], ["10", "2", "1"], features=("a",))
    f = mv3d.section_median_factors(d)
    assert d.sections == ["1", "2", "10"]
    assert np.allclose(f[:, 0], [2 / 4, 2 / 2, 2 / 1])


def test_default_method_is_tic_plus_section(phantom_data):
    assert mv3d.normalize(phantom_data.data).meta["normalisation"] == "tic+section"
    with pytest.raises(ValueError):
        mv3d.normalize(phantom_data.data, method="bogus")


def test_prevalence_reference_and_filter(phantom_data):
    d = phantom_data.data
    prev = mv3d.prevalence(d)
    assert prev["sparse"] < prev["ref"]
    assert mv3d.reference_feature(d) in {"ref", "other"}
    kept, removed = mv3d.remove_low_prevalence(d, 0.1)
    assert removed == ["sparse"] and kept.feature_ids == ["ref", "other"]


def test_nan_counts_as_not_detected():
    d = _data([[np.nan, 1, 1], [np.nan, 0, 1]], ["1", "1"])
    assert mv3d.prevalence(d)["a"] == 0


def test_blank_sections_keeps_pixels(phantom_data):
    d = phantom_data.data
    out = mv3d.blank_sections(d, ["3"])
    assert out.n_pixels == d.n_pixels
    assert not out.values[out.section_mask("3")].any()
    assert out.values[out.section_mask("2")].any()


def test_section_quality_flags_bad_sections(phantom_factory, shifts):
    ph = phantom_factory(shifts, empty=(4,))
    d = ph.data.subset(
        pixel_mask=~(ph.data.section_mask("6") & (np.arange(ph.data.n_pixels) % 10 != 0))
    )
    q = mv3d.section_quality(d)
    assert list(q["section"]) == d.sections
    flagged = dict(zip(q["section"], q["reason"], strict=True))
    assert flagged["5"] == "no signal"
    assert flagged["6"].startswith("only")
    assert q["flagged"].sum() == 2


def test_shell_mask_and_drop(phantom_data):
    d = phantom_data.data
    raster = build_raster(d)
    stack = raster.stack_feature(d, "ref")
    mask = mv3d.shell_mask(stack)
    assert mask.shape == stack.shape and mask.dtype == bool
    assert not (mask & ~(stack > 0)).any()  # shell only on measured pixels
    out = mv3d.drop_masked_pixels(d, raster, mask)
    assert out.n_pixels == d.n_pixels - int(
        mask[raster.slice_index, raster.rows, raster.cols].sum()
    )
