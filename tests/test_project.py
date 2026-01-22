"""Tests for the project manifest, step status and staleness."""

import json

import pytest

from metavision_studio.project import PIPELINES, Project


@pytest.fixture
def project(tmp_path):
    return Project.create(
        tmp_path / "study",
        analysis="mv3d",
        inputs=[{"path": "brain.csv", "omics": "lipidomics"}],
        settings={"pixel_size_um": 50},
    )


def test_create_writes_manifest(project):
    manifest = json.loads((project.root / "project.json").read_text())
    assert manifest["analysis"] == "mv3d"
    assert manifest["name"] == "study"
    assert manifest["steps"] == {}


def test_create_refuses_existing_project(project):
    with pytest.raises(FileExistsError):
        Project.create(project.root, analysis="mv3d", inputs=[])


def test_open_roundtrip(project):
    again = Project.open(project.root)
    assert again.inputs == project.inputs
    assert Project.open(project.root / "project.json").name == "study"


def test_initial_status(project):
    assert project.status("load") == "ready"
    assert project.status("normalise") == "locked"
    assert project.blocking_step("align") == "load"


def test_done_unlocks_next_and_records_outputs(project):
    out = project.results_dir("load") / "data.parquet"
    project.mark_done("load", {}, {"data": out}, summary={"sections": 59})
    assert project.status("load") == "done"
    assert project.status("normalise") == "ready"
    assert project.output("load", "data") == out
    rec = project.record("load")
    assert rec["outputs"]["data"].replace("\\", "/") == "results/mv3d/load/data.parquet"
    assert "numpy" in rec["versions"]


def test_rerun_with_new_params_marks_downstream_stale(project):
    project.mark_done("load", {}, {})
    project.mark_done("normalise", {"method": "tic"}, {})
    project.mark_done("align", {"reference": "auto"}, {})
    assert project.status("align") == "done"

    project.mark_done("normalise", {"method": "tic+section"}, {})
    assert project.status("normalise") == "done"
    assert project.status("align") == "stale"
    assert project.blocking_step("fill") == "align"

    project.mark_done("align", {"reference": "auto"}, {})
    assert project.status("align") == "done"


def test_settings_change_marks_everything_stale(project):
    project.mark_done("load", {}, {})
    project.mark_done("normalise", {}, {})
    project.update_settings(flip_x=True)
    assert project.status("load") == "stale"
    assert project.status("normalise") == "stale"


def test_failed_step(project):
    project.mark_done("load", {}, {})
    project.mark_failed("normalise", {"method": "x"}, "boom")
    assert project.status("normalise") == "failed"
    assert project.record("normalise")["error"] == "boom"


def test_switch_analysis(project):
    project.analysis = "sami"
    assert list(project.steps) == list(PIPELINES["sami"])
    with pytest.raises(ValueError):
        project.analysis = "nope"


def test_refuses_newer_format(project):
    path = project.root / "project.json"
    manifest = json.loads(path.read_text())
    manifest["format"] = 999
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="newer"):
        Project.open(project.root)
