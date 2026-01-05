"""Tests for MSIData, readers, merging and rasterisation."""

import numpy as np
import pandas as pd
import pytest

from metavision_studio.io import (
    MSIData,
    build_raster,
    detect_columns,
    estimate_step,
    guess_omics,
    merge_omics,
    parse_mz,
    read_table,
)


def _grid_table(sections=("1", "2", "10"), step=50.0, shape=(4, 5), offset=(1000.0, -300.0)):
    rows = []
    for k, sec in enumerate(sections):
        for i in range(shape[0]):
            for j in range(shape[1]):
                rows.append(
                    {
                        "spotId": len(rows),
                        "tissue_id": int(sec),
                        "x": offset[0] * k + i * step,
                        "y": offset[1] * k + j * step,
                        "slide_id": 1,
                        "LPA.18.1._1": float(i + j + k),
                        "m.z.760.585": float(10 * k + i),
                    }
                )
    return pd.DataFrame(rows)


@pytest.fixture
def csv_file(tmp_path):
    path = tmp_path / "brain_lipid_preprocessed.csv"
    _grid_table().to_csv(path)  # writes an unnamed index column, like real exports
    return path


def test_parse_mz():
    assert parse_mz("m.z.760.585") == pytest.approx(760.585)
    assert parse_mz("m/z 87.0080") == pytest.approx(87.008)
    assert np.isnan(parse_mz("Glycogen"))


def test_guess_omics():
    assert guess_omics("brain_lipidomics.csv") == "lipidomics"
    assert guess_omics("3d_brain_wt2_pbp_lipid_preprocessed.csv") == "lipidomics"
    assert guess_omics("brain_metabolomics.csv") == "metabolomics"
    assert guess_omics("brain_glycomics.parquet") == "glycomics"
    assert guess_omics("export.csv") == "other"


def test_detect_columns_ignores_metadata():
    m = detect_columns(_grid_table())
    assert (m.x, m.y, m.section) == ("x", "y", "tissue_id")
    assert m.features == ["LPA.18.1._1", "m.z.760.585"]
    assert {"spotId", "slide_id"} <= set(m.ignored)


def test_detect_columns_errors_are_actionable():
    with pytest.raises(ValueError, match="x/y"):
        detect_columns(pd.DataFrame({"a": [1.0], "b": [2.0]}))
    with pytest.raises(ValueError, match="feature"):
        detect_columns(pd.DataFrame({"x": [1.0], "y": [2.0], "region": ["a"]}))


def test_read_table_roundtrip(csv_file):
    data, mapping = read_table(csv_file)
    assert data.sections == ["1", "2", "10"]  # natural order, ints become clean strings
    assert data.n_features == 2
    assert data.features["omics"].unique().tolist() == ["lipidomics"]
    assert data.pixel_size_um == pytest.approx(50.0)
    assert data.values.dtype == np.float32
    assert data.features.loc["m.z.760.585", "mz"] == pytest.approx(760.585)
    assert mapping.section == "tissue_id"


def test_read_table_restores_duplicate_headers(tmp_path):
    path = tmp_path / "brain_glycomics.csv"
    path.write_text("x,y,region,Glycogen,G1,Glycogen\n0,0,a,1,2,3\n50,0,a,4,5,6\n")
    data, _ = read_table(path)
    assert data.feature_ids == ["Glycogen", "G1", "Glycogen [1]"]
    assert data.column("Glycogen [1]").tolist() == [3.0, 6.0]


def test_read_table_without_section_column(tmp_path):
    path = tmp_path / "single.csv"
    path.write_text("x,y,m.z.100.1\n0,0,1\n0,1,2\n")
    data, mapping = read_table(path)
    assert mapping.section is None
    assert data.sections == ["single"]


def test_msidata_validates_shapes():
    with pytest.raises(ValueError, match="does not match"):
        MSIData.from_arrays([0, 1], [0, 0], ["a", "a"], np.zeros((3, 1)), ["f"])
    with pytest.raises(ValueError, match="unique"):
        MSIData.from_arrays([0], [0], ["a"], np.zeros((1, 2)), ["f", "f"])


def test_subset_and_with_values_do_not_mutate(csv_file):
    data, _ = read_table(csv_file)
    before = data.values.copy()
    sub = data.subset(sections=["2"], features=["m.z.760.585"])
    assert sub.sections == ["2"] and sub.n_features == 1
    doubled = data.with_values(data.values * 2, step="test")
    assert doubled.meta["step"] == "test"
    np.testing.assert_array_equal(data.values, before)


def test_feature_lookup_by_name():
    d = MSIData.from_arrays([0], [0], ["a"], np.ones((1, 1)), ["m.z.760.585"], names=["PC(34:1)"])
    assert d.feature_index("PC(34:1)") == 0
    assert d.label("m.z.760.585") == "PC(34:1) (m/z 760.5850)"
    with pytest.raises(KeyError):
        d.feature_index("nope")


def test_flipped():
    d = MSIData.from_arrays([1, 2], [3, 4], ["a", "a"], np.ones((2, 1)), ["f"])
    f = d.flipped(flip_x=True)
    assert f.pixels["x"].tolist() == [-1, -2] and d.pixels["x"].tolist() == [1, 2]


def test_merge_omics_matches_pixels_and_suffixes_collisions():
    a = MSIData.from_arrays(
        [0, 1, 2], [0, 0, 0], ["s"] * 3, np.arange(3)[:, None], ["Glc"], omics="metabolomics"
    )
    b = MSIData.from_arrays(
        [2, 1], [0, 0], ["s"] * 2, np.array([[20.0], [10.0]]), ["Glc"], omics="glycomics"
    )
    m = merge_omics([a, b])
    assert m.n_pixels == 2
    assert m.feature_ids == ["Glc", "Glc@glycomics"]
    by_x = dict(zip(m.pixels["x"], m.values[:, 1], strict=True))
    assert by_x == {1: 10.0, 2: 20.0}


def test_merge_omics_without_shared_pixels_explains():
    a = MSIData.from_arrays([0], [0], ["s"], np.ones((1, 1)), ["a"])
    b = MSIData.from_arrays([9], [9], ["s"], np.ones((1, 1)), ["b"])
    with pytest.raises(ValueError, match="share no pixels"):
        merge_omics([a, b])


def test_to_anndata():
    d = MSIData.from_arrays([0, 1], [0, 0], ["2", "10"], np.ones((2, 1)), ["f"])
    ad = d.to_anndata()
    assert ad.shape == (2, 1)
    assert list(ad.obs["section"].cat.categories) == ["2", "10"]
    assert ad.obsm["spatial"].shape == (2, 2)


def test_estimate_step_ignores_missing_rows():
    coords = np.array([0, 50, 100, 200, 250, 300, 400])  # gaps at 150 and 350
    assert estimate_step(coords) == pytest.approx(50.0)


def test_raster_places_pixels_and_centres_sections(csv_file):
    data, _ = read_table(csv_file)
    r = build_raster(data)
    # 4x5 sections -> canvas ((n*1.1+9)//10)*10 = 10 x 10
    assert r.stack_shape == (3, 10, 10)
    stack = r.stack(data.column("LPA.18.1._1"))
    assert stack.dtype == np.float32
    # every section occupies the same centred 4x5 block despite different physical offsets
    occupied = r.tissue_mask()
    assert occupied.sum(axis=(1, 2)).tolist() == [20, 20, 20]
    rows, cols = np.nonzero(occupied[0])
    assert (rows.min(), cols.min()) == ((10 - 4) // 2, (10 - 5) // 2)
    np.testing.assert_array_equal(occupied[0], occupied[2])
    # value at local (i=3, j=4) of section index 2 ("10" -> k=2): i + j + k = 9
    assert stack[2, rows.min() + 3, cols.min() + 4] == 9.0


def test_raster_handles_large_intensities_without_overflow():
    d = MSIData.from_arrays([0, 1], [0, 0], ["a", "a"], np.array([[1e6], [70000.0]]), ["f"])
    stack = build_raster(d).stack(d.column("f"))
    assert np.isfinite(stack).all() and stack.max() == 1e6


@pytest.mark.parametrize(
    ("raw", "pretty"),
    [
        ("LPA.18.1._1", "LPA(18:1)"),
        ("LPA..20.4._1", "LPA(20:4)"),
        ("PE.P.38.4.", "PE(P-38:4)"),
        ("PC.34.1.", "PC(34:1)"),
        ("m.z.760.585", "m.z.760.585"),
        ("Glycogen", "Glycogen"),
    ],
)
def test_pretty_name(raw, pretty):
    from metavision_studio.io import pretty_name

    assert pretty_name(raw) == pretty


def test_read_table_uses_pretty_names_but_keeps_ids(csv_file):
    data, _ = read_table(csv_file)
    assert "LPA.18.1._1" in data.feature_ids
    assert data.features.loc["LPA.18.1._1", "name"] == "LPA(18:1)"
    assert data.feature_index("LPA(18:1)") == data.feature_index("LPA.18.1._1")


def test_read_imzml_extracts_target_peaks(tmp_path):
    writer_mod = pytest.importorskip("pyimzml.ImzMLWriter")
    path = tmp_path / "brain_lipidomics.imzML"
    mzs = np.array([100.0, 200.0, 200.001, 300.0])
    with writer_mod.ImzMLWriter(str(path), mode="processed") as w:
        for x in (1, 2):
            for y in (1, 2, 3):
                w.addSpectrum(mzs, np.array([1.0, x, y, 7.0]), (x, y, 1))
    from metavision_studio.io import read_imzml

    data = read_imzml(path, mz=[200.0, 300.0], tolerance_ppm=10, names=["A", "B"])
    assert data.n_pixels == 6 and data.feature_ids == ["m/z 200.0000", "m/z 300.0000"]
    assert data.features["omics"].iloc[0] == "lipidomics"
    # 200.0 and 200.001 (5 ppm) are summed; 300.0 is constant
    by_xy = {
        (int(a), int(b)): v
        for a, b, v in zip(data.pixels.x, data.pixels.y, data.values[:, 0], strict=True)
    }
    assert by_xy[(2, 3)] == pytest.approx(2 + 3)
    np.testing.assert_allclose(data.values[:, 1], 7.0)


def test_reindex_places_a_subset_on_the_base_canvas(csv_file):
    """Regression: a subset got its own canvas, so its layer did not overlay the others."""
    base, _ = read_table(csv_file)
    raster = build_raster(base)
    keep = (base.pixels["section"] == "10").to_numpy() & (base.pixels["x"] > base.pixels["x"].min())
    sub = base.subset(pixel_mask=keep)
    own = build_raster(sub)
    shared = raster.reindex(base, sub)
    assert own.stack_shape != raster.stack_shape  # the bug: a subset gets its own canvas
    full = raster.stack(base.column("LPA.18.1._1"))
    part = shared.stack(sub.column("LPA.18.1._1"))
    assert part.shape == full.shape
    np.testing.assert_array_equal(part[part != 0], full[part != 0])
    assert part[0].sum() == 0 and part[1].sum() == 0  # only section "10" (plane 2) is present


def test_reindex_skips_pixels_missing_from_base(csv_file):
    base, _ = read_table(csv_file)
    extra = MSIData.from_arrays([1e9], [1e9], ["1"], np.ones((1, 2)), base.feature_ids)
    shared = build_raster(base).reindex(base, extra)
    assert shared.rows.tolist() == [-1]
    assert shared.stack(extra.column(base.feature_ids[0])).sum() == 0
