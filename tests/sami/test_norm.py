import numpy as np
import pytest

from metavision_studio import sami
from metavision_studio.io import MSIData


def test_default_is_per_omics_sum_then_log2(two_domain):
    data, _ = two_domain
    out = sami.normalize(data)
    raw = 2 ** out.values.astype(np.float64) - 1  # undo log2(x + 1)
    for om in ("lipidomics", "metabolomics", "glycomics"):
        cols = np.flatnonzero(out.features["omics"].to_numpy() == om)
        np.testing.assert_allclose(raw[:, cols].sum(axis=1), 1.0, rtol=1e-4)
    assert out.meta["normalisation"]["row"] == "sum"


def test_input_is_not_modified(two_domain):
    data, _ = two_domain
    before = data.values.copy()
    sami.normalize(data, row="median", transform="sqrt", scale="auto")
    np.testing.assert_array_equal(data.values, before)


def test_zero_sum_pixels_are_dropped():
    vals = np.array([[1.0, 2.0], [0.0, 0.0], [3.0, 1.0]])
    data = MSIData.from_arrays([0, 1, 2], [0, 0, 0], ["a"] * 3, vals, ["f1", "f2"])
    out = sami.normalize(data)
    assert out.n_pixels == 2
    assert out.meta["dropped_pixels"] == 1


def test_zero_in_any_omics_block_drops_pixel():
    vals = np.array([[1.0, 2.0], [1.0, 0.0], [3.0, 1.0]])
    data = MSIData.from_arrays(
        [0, 1, 2], [0, 0, 0], ["a"] * 3, vals, ["L", "M"], omics=["lipidomics", "metabolomics"]
    )
    assert sami.normalize(data).n_pixels == 2
    assert sami.normalize(data, per_omics=False).n_pixels == 3


def test_comp_norm_removes_reference(two_domain):
    data, _ = two_domain
    out = sami.normalize(data, row="comp", reference="Glycogen", transform="none")
    assert "Glycogen" not in out.feature_ids
    assert out.n_features == data.n_features - 1


def test_comp_norm_needs_reference(two_domain):
    with pytest.raises(ValueError, match="reference"):
        sami.normalize(two_domain[0], row="comp")


def test_scaling_handles_zero_variance():
    vals = np.array([[1.0, 5.0], [2.0, 5.0], [3.0, 5.0]])
    data = MSIData.from_arrays([0, 1, 2], [0, 0, 0], ["a"] * 3, vals, ["f1", "const"])
    for scale in ("auto", "pareto", "range"):
        out = sami.normalize(data, row="none", transform="none", scale=scale)
        assert np.isfinite(out.values).all()
        np.testing.assert_allclose(out.values[:, 1], 0.0)
    auto = sami.normalize(data, row="none", transform="none", scale="auto").values[:, 0]
    np.testing.assert_allclose(auto, (vals[:, 0] - 2) / np.std(vals[:, 0]), rtol=1e-6)
    pareto = sami.normalize(data, row="none", transform="none", scale="pareto").values[:, 0]
    np.testing.assert_allclose(pareto, (vals[:, 0] - 2) / np.sqrt(np.std(vals[:, 0])), rtol=1e-6)


def test_section_median_pqn_equalises_sections():
    rng = np.random.default_rng(1)
    a = rng.gamma(5, 10, size=(50, 4))
    vals = np.vstack([a, a * 3])  # section b is 3x brighter
    data = MSIData.from_arrays(
        np.arange(100), np.zeros(100), ["a"] * 50 + ["b"] * 50, vals, ["f1", "f2", "f3", "f4"]
    )
    out = sami.normalize(data, row="section_median_pqn", transform="none").values
    np.testing.assert_allclose(np.median(out[:50], axis=0), np.median(out[50:], axis=0), rtol=1e-5)


def test_median_zero_denominator_warns_and_drops():
    vals = np.array([[0.0, 0.0, 1.0], [1.0, 2.0, 3.0]])
    data = MSIData.from_arrays([0, 1], [0, 0], ["a"] * 2, vals, ["f1", "f2", "f3"])
    with pytest.warns(UserWarning, match="zero median"):
        out = sami.normalize(data, row="median")
    assert out.n_pixels == 1


@pytest.mark.parametrize("transform", ["log2", "log10", "glog2", "glog10", "sqrt", "cbrt", "none"])
def test_transforms_are_finite(two_domain, transform):
    out = sami.normalize(two_domain[0], transform=transform)
    assert np.isfinite(out.values).all()


def test_rejects_unknown_methods(two_domain):
    with pytest.raises(ValueError):
        sami.normalize(two_domain[0], row="nope")
    with pytest.raises(ValueError):
        sami.normalize(two_domain[0], transform="nope")
    with pytest.raises(ValueError):
        sami.normalize(two_domain[0], scale="nope")


@pytest.mark.parametrize("transform", ["sqrt", "glog2"])
def test_shifted_transforms_are_per_omics_block(transform):
    """Regression: the glog/sqrt/cbrt shift was taken over all omics at once, unlike upstream,
    which normalised each omics file separately."""
    from metavision_studio.io import MSIData, merge_omics

    rng = np.random.default_rng(1)
    xs, ys = np.arange(20) % 5, np.arange(20) // 5
    lip = rng.gamma(2, 100, (20, 3))
    met = rng.gamma(2, 1, (20, 2)) * 1e-3  # very different scale
    lip[0, 0] = met[0, 0] = 0
    a = MSIData.from_arrays(xs, ys, ["s"] * 20, lip, ["l1", "l2", "l3"], omics="lipidomics")
    b = MSIData.from_arrays(xs, ys, ["s"] * 20, met, ["m1", "m2"], omics="metabolomics")
    pooled = sami.normalize(merge_omics([a, b]), row="none", transform=transform)
    separate = sami.normalize(b, row="none", transform=transform)
    np.testing.assert_allclose(pooled.values[:, 3:], separate.values, rtol=1e-6)
