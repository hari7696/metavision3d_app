"""Widget-test setup: headless Qt, isolated config, and the workflow fakes."""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest

# Headless Qt. Windows' offscreen platform has no OpenGL, so napari's canvas can't start
# there. On Windows we use the native platform instead; widgets are never shown, so no
# windows appear.
os.environ.setdefault("QT_QPA_PLATFORM", "windows" if sys.platform == "win32" else "offscreen")

_spec = importlib.util.spec_from_file_location(
    "_workflow_fixtures", Path(__file__).parent.parent / "workflows" / "conftest.py"
)
wf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(wf)

make_csv = wf.make_csv
fake_mv3d = wf.fake_mv3d
fake_sami = wf.fake_sami


@pytest.fixture(autouse=True)
def _isolated_config(tmp_path, monkeypatch):
    monkeypatch.setenv("METAVISION_CONFIG_DIR", str(tmp_path / "config"))


@pytest.fixture(autouse=True)
def clipboard(monkeypatch):
    """Capture copies instead of touching the real system clipboard."""
    from metavision_studio.widgets import clipboard as cb

    copied: list[str] = []
    monkeypatch.setattr(cb, "copy_text", copied.append)
    return copied


@pytest.fixture
def fakes(monkeypatch):
    from metavision_studio.workflows import runners

    mods = {"mv3d": fake_mv3d(), "sami": fake_sami()}
    monkeypatch.setattr(runners, "_core", lambda name: mods[name])
    return mods


@pytest.fixture
def tiny_csv(tmp_path):
    return make_csv(tmp_path / "sections_lipidomics.csv")


@pytest.fixture
def mv3d_project(tmp_path, tiny_csv):
    from metavision_studio.project import Project

    return Project.create(
        tmp_path / "proj",
        analysis="mv3d",
        inputs=[{"path": str(tiny_csv), "omics": "lipidomics"}],
        settings={"pixel_size_um": 50.0},
    )


@pytest.fixture
def viewer(make_napari_viewer):
    """A napari viewer, or skip when this machine can't create an OpenGL canvas."""
    try:
        return make_napari_viewer()
    except Exception as exc:
        pytest.skip(f"napari viewer unavailable here: {exc}")
