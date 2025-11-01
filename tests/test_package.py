"""Smoke tests: the package imports, is versioned, and its napari manifest is valid."""

from importlib.metadata import entry_points, version

import pytest

import metavision_studio
from metavision_studio import cli


def test_version_matches_metadata():
    assert metavision_studio.__version__ == version("metavision-studio")


def test_subpackages_import():
    from metavision_studio import io, mv3d, rbridge, sami  # noqa: F401


def test_napari_manifest_entry_point_registered():
    eps = entry_points(group="napari.manifest")
    assert any(ep.name == "metavision-studio" for ep in eps)


def test_napari_manifest_is_valid():
    npe2 = pytest.importorskip("npe2")
    manifest = npe2.PluginManifest.from_distribution("metavision-studio")
    assert manifest.name == "metavision-studio"


def test_cli_version(capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(["--version"])
    assert exc.value.code == 0
    assert metavision_studio.__version__ in capsys.readouterr().out


def test_cli_doctor_runs(capsys):
    # The core dependencies are installed in the test environment, so doctor passes.
    assert cli.main(["doctor"]) == 0
    out = capsys.readouterr().out
    assert "Core packages:" in out
    assert "R (pathway enrichment" in out


def test_cli_datasets_lists_registry(capsys):
    assert cli.main(["datasets"]) == 0
    out = capsys.readouterr().out
    assert "mv3d-wt2" in out and "CC BY 4.0" in out


def test_cli_fetch_unknown_dataset(capsys):
    assert cli.main(["fetch", "nope"]) == 1
    assert "Available" in capsys.readouterr().err
