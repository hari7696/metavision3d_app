"""GUI tests for the MetaVision Studio dock widget (pytest-qt)."""

from __future__ import annotations

import time

import pytest

from metavision_studio._progress import Cancelled
from metavision_studio.widgets import StudioWidget
from metavision_studio.widgets.new_project import NewProjectDialog
from metavision_studio.widgets.recent import recent_projects

pytestmark = pytest.mark.gui


def _studio(qtbot, viewer=None) -> StudioWidget:
    w = StudioWidget(viewer)
    qtbot.addWidget(w)
    return w


def _wait_idle(qtbot, w: StudioWidget, timeout=15_000):
    qtbot.waitUntil(lambda: not w.jobs.busy, timeout=timeout)
    qtbot.waitUntil(lambda: not w.view_jobs.busy and not w.insight_jobs.busy, timeout=timeout)


def test_widget_constructs_on_start_page(qtbot):
    w = _studio(qtbot)
    assert w.stack.currentWidget() is w.start
    assert len(w.start.example_btn.menu().actions()) == 2
    assert not w.status.isVisible()


def test_new_project_dialog_creates_project_and_loads(qtbot, tmp_path, tiny_csv, fakes):
    w = _studio(qtbot)
    dlg = NewProjectDialog(w, files=[str(tiny_csv)])
    qtbot.addWidget(dlg)
    assert "3 features" in dlg.columns.text() and "tissue_id" in dlg.columns.text()
    assert dlg.pixel.value() == pytest.approx(50.0)
    assert not dlg.create_btn.isEnabled()  # no analysis chosen yet
    dlg.set_analysis("mv3d")
    dlg.root.setText(str(tmp_path / "new_proj"))
    dlg._root_edited = True
    dlg._validate()
    assert dlg.create_btn.isEnabled()

    project = w._create_from_dialog(dlg)
    assert (tmp_path / "new_proj" / "project.json").exists()
    assert project.inputs[0]["omics"] == "lipidomics"
    _wait_idle(qtbot, w)  # Load runs automatically
    assert project.status("load") == "done"
    assert w.view.steps.card("load").status == "done"
    assert recent_projects()[0]["name"] == "new_proj"
    assert "4 sections" in w.view.summary.text()


def test_step_states_and_locked_hint(qtbot, mv3d_project, fakes):
    w = _studio(qtbot)
    w.open_project(mv3d_project)
    _wait_idle(qtbot, w)
    cards = w.view.steps.cards
    assert cards["load"].status == "done"
    assert cards["normalise"].status == "ready"
    assert cards["align"].status == "locked"
    assert "Normalise" in cards["align"].hint.text()
    assert not cards["align"].run.isEnabled()
    # the section-quality suggestion (fake flags the last section)
    assert "Exclude them" in cards["load"].banner.text()
    assert w.view.steps.open_step == "normalise"  # opened the next step to do


def test_run_completes_via_worker_and_updates_status(qtbot, mv3d_project, fakes):
    w = _studio(qtbot)
    w.open_project(mv3d_project)
    _wait_idle(qtbot, w)
    assert w.run("normalise")
    assert w.view.steps.card("normalise").status == "running"
    _wait_idle(qtbot, w)
    assert w.view.steps.card("normalise").status == "done"
    assert w.view.steps.card("align").status == "ready"
    assert w.view.steps.open_step == "align"
    assert w.view.picker.combo.count() == 3


def test_cancel_stops_a_running_step(qtbot, mv3d_project, fakes):
    def slow_alignment(data, raster, *, progress=None, **_):
        for i in range(400):
            progress(i, 400, f"Aligning {i}")
            time.sleep(0.01)
        raise AssertionError("should have been cancelled")

    fakes["mv3d"].compute_alignment = slow_alignment
    w = _studio(qtbot)
    w.open_project(mv3d_project)
    _wait_idle(qtbot, w)
    w.run("normalise")
    _wait_idle(qtbot, w)
    w.run("align")
    qtbot.waitUntil(lambda: "Aligning" in w.status_text.text(), timeout=5000)
    assert w.cancel_btn.isVisible() or not w.cancel_btn.isHidden()
    w.cancel()
    _wait_idle(qtbot, w)
    assert mv3d_project.record("align") is None
    assert w.view.steps.card("align").status == "ready"
    assert "Cancelled" in w.status_text.text()


def test_error_shows_inline_with_report(qtbot, mv3d_project, fakes, clipboard):
    def broken(*a, **k):
        raise ValueError("The reference molecule has no signal in section 3.")

    fakes["mv3d"].compute_alignment = broken
    w = _studio(qtbot)
    w.open_project(mv3d_project)
    _wait_idle(qtbot, w)
    w.run("normalise")
    _wait_idle(qtbot, w)
    w.run("align")
    _wait_idle(qtbot, w)
    card = w.view.steps.card("align")
    assert card.status == "failed"
    assert not card.error_box.isHidden()
    assert "no signal in section 3" in card.error_label.text()
    assert "ValueError" in card._error.details
    card.copy_btn.click()
    assert "Step: align" in clipboard[-1]


def test_exclude_flagged_sections_action(qtbot, mv3d_project, fakes):
    w = _studio(qtbot)
    w.open_project(mv3d_project)
    _wait_idle(qtbot, w)
    w._on_action("load", "exclude")
    _wait_idle(qtbot, w)
    assert mv3d_project.record("load")["params"]["exclude_sections"] == "4"
    assert w.view.steps.card("load").banner.isHidden()


def test_copy_methods_and_switch_analysis(qtbot, mv3d_project, fakes, clipboard):
    w = _studio(qtbot)
    w.open_project(mv3d_project)
    _wait_idle(qtbot, w)
    w.copy_methods()
    assert "MetaVision3D" in clipboard[-1]
    w.switch_analysis("sami")
    _wait_idle(qtbot, w)
    assert list(w.view.steps.cards) == ["load", "normalise", "cluster", "markers", "pathways"]
    assert w.view.steps.card("load").status == "done"


def test_jobs_cancel_raises_in_worker(qtbot):
    from metavision_studio.widgets.jobs import JobRunner

    runner = JobRunner()
    seen = {}

    def work(progress):
        for i in range(1000):
            progress(i, 1000, "")
            time.sleep(0.005)

    runner.start(
        work,
        on_done=lambda r: seen.setdefault("done", r),
        on_error=lambda e: seen.setdefault("error", e),
        on_cancel=lambda: seen.setdefault("cancelled", True),
    )
    runner.cancel()
    qtbot.waitUntil(lambda: not runner.busy, timeout=5000)
    assert seen == {"cancelled": True}
    assert issubclass(Cancelled, Exception)


# ---------------------------------------------------------------------------- with napari
def test_plugin_in_viewer_shows_layers_insights_and_3d(qtbot, viewer, mv3d_project, fakes):
    w = _studio(qtbot, viewer)
    viewer.window.add_dock_widget(w, name="MetaVision Studio")
    w.open_project(mv3d_project)
    _wait_idle(qtbot, w)
    for step in ("normalise", "align", "fill", "atlas"):
        w.view.steps.open(step)
        w.run(step)
        _wait_idle(qtbot, w)
        assert mv3d_project.status(step) == "done", step
    names = [layer.name for layer in viewer.layers]
    assert {"Raw", "Normalised", "Aligned", "Filled", "3D atlas"} <= set(names)
    w.view.steps.open("atlas")
    _wait_idle(qtbot, w)
    assert viewer.dims.ndisplay == 3
    assert [lyr.name for lyr in viewer.layers if lyr.visible] == ["3D atlas"]
    w.view.steps.open("align")
    _wait_idle(qtbot, w)
    assert viewer.dims.ndisplay == 2
    assert w.insights.insight.kind == "scores"
    assert w._insights_dock is not None and not w._insights_dock.isHidden()
    w._goto_section(2)
    assert viewer.dims.point[0] == pytest.approx(viewer.layers["Aligned"].scale[0] * 2, abs=1e-6)
    # molecule change updates layers in place
    before = viewer.layers["Aligned"].data.copy()
    w.view.picker.set_feature(w.view.picker.combo.itemData(2))
    _wait_idle(qtbot, w)
    assert not (viewer.layers["Aligned"].data == before).all()
    w.close_project()
    assert not [lyr for lyr in viewer.layers if lyr.metadata.get("metavision")]


def test_manifest_registers_dock_widget():
    import npe2

    manifest = npe2.PluginManifest.from_distribution("metavision-studio")
    assert [wd.display_name for wd in manifest.contributions.widgets] == ["MetaVision Studio"]
    cmd = manifest.contributions.commands[0]
    assert cmd.python_name == "metavision_studio.widgets:StudioWidget"
