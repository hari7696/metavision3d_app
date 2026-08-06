"""Workflow runners: persistence, status tracking, errors, cancellation (fake core)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from metavision_studio._progress import Cancelled
from metavision_studio.methods import methods_text
from metavision_studio.project import Project
from metavision_studio.workflows import (
    StepError,
    feature_items,
    load_msidata,
    params_for,
    run_step,
    run_transfer,
    save_msidata,
    switch_analysis,
)
from metavision_studio.workflows.display import insight_for, layer_for
from metavision_studio.workflows.params import PARAMS, param_fields, params_from_dict
from metavision_studio.workflows.runners import load_step_data


def test_msidata_round_trip(tmp_path, tiny_csv):
    from metavision_studio.io import read_table

    data, _ = read_table(tiny_csv)
    save_msidata(data, tmp_path / "d")
    back = load_msidata(tmp_path / "d")
    assert back.sections == data.sections
    assert back.feature_ids == data.feature_ids
    np.testing.assert_array_equal(back.values, data.values)
    assert back.pixel_size_um == data.pixel_size_um == 50.0
    pd.testing.assert_frame_equal(back.features, data.features)


def test_every_param_has_label_and_valid_default():
    for analysis, steps in PARAMS.items():
        for step, cls in steps.items():
            obj = cls()
            for name, default, meta in param_fields(cls):
                assert meta["label"], (analysis, step, name)
                if meta["choices"]:
                    assert default in [v for v, _ in meta["choices"]], (step, name)
            assert params_from_dict(analysis, step, {**vars(obj), "unknown": 1}) == obj


def test_mv3d_pipeline_end_to_end(mv3d_project, fakes):
    p = mv3d_project
    assert p.status("load") == "ready" and p.status("align") == "locked"
    progress = []
    for step in p.steps:
        run_step(p, step, params_for(p, step), progress=lambda *a: progress.append(a))
        assert p.status(step) == "done", step
    rec = json.loads((p.root / "project.json").read_text())
    assert set(rec["steps"]) == set(p.steps)
    assert rec["steps"]["load"]["summary"]["flagged_sections"] == ["4"]
    assert any("Aligning" in m for *_x, m in progress)
    assert (p.root / rec["steps"]["atlas"]["outputs"]["file"]).name.endswith(".nii.gz")
    # layers and insights
    feat = feature_items(p)[0][0]
    fill = layer_for(p, "fill", feat)
    assert fill.data.shape[0] == 4 + 3  # 1 interpolated section between each pair
    assert fill.scale[0] == pytest.approx(30.0)  # (10 + 50) / 2
    assert layer_for(p, "load", feat).scale == (60.0, 50.0, 50.0)
    assert insight_for(p, "align", feat).kind == "scores"
    assert insight_for(p, "normalise", feat).kind == "boxplot"
    text = methods_text(p)
    assert "aligned" in text and "MetaVision3D" in text and "doi:10.1101/2023.11.27.568931" in text


def test_rerun_earlier_step_marks_later_stale(mv3d_project, fakes):
    p = mv3d_project
    for step in ("load", "normalise", "align"):
        run_step(p, step)
    run_step(p, "normalise", params_for(p, "normalise", method="tic"))
    assert p.status("normalise") == "done"
    assert p.status("align") == "stale"
    assert p.blocking_step("fill") == "align"


def test_alignment_is_cached_on_normalised_fingerprint(mv3d_project, fakes):
    p = mv3d_project
    for step in ("load", "normalise", "align"):
        run_step(p, step)
    run_step(p, "align")
    assert sum(c[0] == "compute_alignment" for c in fakes["mv3d"].calls) == 1
    run_step(p, "normalise", params_for(p, "normalise", method="tic"))
    run_step(p, "align")
    assert sum(c[0] == "compute_alignment" for c in fakes["mv3d"].calls) == 2


def test_exclude_sections_blanks_them_in_mv3d(mv3d_project, fakes):
    p = mv3d_project
    run_step(p, "load", params_for(p, "load", exclude_sections="2"))
    data = load_msidata(p.output("load", "data"))
    assert "2" in data.sections  # kept in place for z-spacing
    assert np.all(data.values[data.section_mask("2")] == 0)


def test_unknown_excluded_section_is_a_friendly_error(mv3d_project, fakes):
    with pytest.raises(StepError) as exc:
        run_step(mv3d_project, "load", params_for(mv3d_project, "load", exclude_sections="99"))
    assert "99" in exc.value.message
    assert mv3d_project.status("load") == "failed"


def test_locked_step_raises(mv3d_project, fakes):
    with pytest.raises(StepError, match="Load data"):
        run_step(mv3d_project, "align")


def test_failure_is_recorded_with_user_message(mv3d_project, fakes, monkeypatch):
    run_step(mv3d_project, "load")
    run_step(mv3d_project, "normalise")

    def boom(*a, **k):
        raise MemoryError()

    monkeypatch.setattr(fakes["mv3d"], "compute_alignment", boom)
    with pytest.raises(StepError) as exc:
        run_step(mv3d_project, "align")
    assert "memory" in exc.value.message.lower()
    assert "MemoryError" in exc.value.details
    assert "Step: align" in exc.value.report()
    assert mv3d_project.status("align") == "failed"


def test_cancel_records_nothing(mv3d_project, fakes):
    run_step(mv3d_project, "load")
    run_step(mv3d_project, "normalise")

    def cancel(done, total, msg):
        if done >= 2:
            raise Cancelled()

    with pytest.raises(Cancelled):
        run_step(mv3d_project, "align", progress=cancel)
    assert mv3d_project.record("align") is None
    assert mv3d_project.status("align") == "ready"


def test_export_formats(mv3d_project, fakes):
    p = mv3d_project
    for step in ("load", "normalise", "align", "fill"):
        run_step(p, step)
    for fmt, suffix in (("tiff", ".tif"), ("csv", ".csv")):
        r = run_step(p, "atlas", params_for(p, "atlas", export_format=fmt, features="all"))
        assert r.summary["n_files"] == 3
        assert sorted(f.suffix for f in (p.root / "results" / "mv3d" / "atlas").glob(f"*{suffix}"))


def test_sami_pipeline_end_to_end(sami_project, fakes):
    p = sami_project
    run_step(p, "load")
    data = load_msidata(p.output("load", "data"))
    assert data.n_features == 4 and set(data.features["omics"]) == {"lipidomics", "metabolomics"}
    run_step(p, "normalise")
    run_step(p, "cluster")
    clusters = p.record("cluster")["summary"]["clusters"]
    assert clusters == ["0", "1"]
    with pytest.raises(StepError, match="Choose at least one cluster"):
        run_step(p, "markers")
    run_step(p, "markers", params_for(p, "markers", group_a="1"))
    run_step(p, "pathways")
    assert p.status("pathways") == "done"
    assert p.record("pathways")["summary"]["library"]["source"]  # provenance is recorded
    labels = layer_for(p, "cluster", data.feature_ids[0])
    assert labels.kind == "labels" and labels.data.max() == 2
    assert insight_for(p, "cluster", None).kind == "umap"
    assert insight_for(p, "markers", None).kind == "volcano"
    assert insight_for(p, "pathways", None).kind == "pathways"


def test_sami_transfer_clusters(sami_project, fakes):
    p = sami_project
    for step in ("load", "normalise"):
        run_step(p, step)
    run_step(p, "cluster", params_for(p, "cluster", samples="1"))
    path = run_transfer(p, ["2"])
    assert path.exists()
    assert p.record("cluster")["outputs"]["transfer"].endswith(".h5ad")
    assert p.status("cluster") == "done"


def test_switch_analysis_shelves_and_restores_steps(mv3d_project, fakes):
    p = mv3d_project
    run_step(p, "load", params_from_dict("mv3d", "load", {"flip_x": True}))
    run_step(p, "normalise")
    previous = switch_analysis(p, "sami")
    # Each analysis has its own Load; the old Load settings are handed back for a re-run.
    assert p.status("load") == "ready" and p.record("normalise") is None
    assert previous["flip_x"] is True
    assert switch_analysis(p, "mv3d") is None  # mv3d still has its Load
    assert p.status("normalise") == "done"
    assert Project.open(p.root).analysis == "mv3d"


def test_switching_analyses_never_shares_outputs(mv3d_project, fakes):
    """Regression: both analyses wrote results/normalise/data, so switching back silently
    pointed the 3D pipeline at the multi-omics normalisation."""
    p = mv3d_project
    run_step(p, "load")
    run_step(p, "normalise")
    mv3d_out = p.output("normalise", "data")
    switch_analysis(p, "sami")
    run_step(p, "load")
    run_step(p, "normalise")
    sami_out = p.output("normalise", "data")
    assert mv3d_out != sami_out
    switch_analysis(p, "mv3d")
    assert p.output("normalise", "data") == mv3d_out and mv3d_out.exists()
    assert p.status("normalise") == "done"


def test_exclusions_differ_per_analysis(mv3d_project, fakes):
    """Regression: a SAMI Load (sections removed) was reused by the 3D atlas (needs blanks)."""
    p = mv3d_project
    switch_analysis(p, "sami")
    run_step(p, "load", params_from_dict("sami", "load", {"exclude_sections": "1"}))
    assert "1" not in load_step_data(p, "load").sections
    previous = switch_analysis(p, "mv3d")
    run_step(p, "load", params_from_dict("mv3d", "load", previous))
    assert "1" in load_step_data(p, "load").sections  # blanked, keeps its z slot


def test_edited_input_file_makes_results_stale(mv3d_project, fakes):
    """Regression: fingerprints hashed only the path, so editing the CSV reused old results."""
    import os

    p = mv3d_project
    run_step(p, "load")
    run_step(p, "normalise")
    assert p.status("normalise") == "done"
    path = Path(p.inputs[0]["path"])
    path.write_text(path.read_text())  # same content, new mtime
    st = path.stat()
    os.utime(path, ns=(st.st_atime_ns, st.st_mtime_ns + 10**9))
    assert p.status("load") == "stale"
    assert p.status("normalise") == "stale"


def test_cluster_labels_overlay_images_when_one_sample_is_clustered(sami_project, fakes):
    """Regression: labels for a clustered subset were drawn on their own canvas, so sample 2's
    clusters landed on top of sample 1."""
    p = sami_project
    for step in ("load", "normalise"):
        run_step(p, step)
    run_step(p, "cluster", params_for(p, "cluster", samples="2"))
    feature = load_msidata(p.output("load", "data")).feature_ids[0]
    image = layer_for(p, "normalise", feature).data
    labels = layer_for(p, "cluster", feature).data
    assert labels.shape == image.shape
    assert labels[0].max() == 0 and labels[1].max() > 0  # sample "2" stays on plane 1


def test_result_tables_keep_ids_and_names_as_text(tmp_path):
    """Regression: read_csv turned id '760.580' into 760.58 and the name 'NA' into NaN."""
    from metavision_studio.workflows.storage import read_result_table

    path = tmp_path / "markers.csv"
    pd.DataFrame(
        {"feature": ["760.580", "NA"], "name": ["NA", "Taurine"], "pvalue": [0.01, 0.2]}
    ).to_csv(path, index=False)
    df = read_result_table(path)
    assert df["feature"].tolist() == ["760.580", "NA"]
    assert df["name"].tolist() == ["NA", "Taurine"]
    assert df["pvalue"].dtype.kind == "f"
