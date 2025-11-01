"""Tests for locating and running R through ``Rscript``."""

from pathlib import Path

import pytest

from metavision_studio import rbridge


def _r_available() -> bool:
    try:
        rbridge.find_rscript()
    except rbridge.RNotFoundError:
        return False
    return True


requires_r = pytest.mark.skipif(not _r_available(), reason="R is not installed")


def test_explicit_rscript_must_exist(monkeypatch, tmp_path):
    monkeypatch.setenv("METAVISION_RSCRIPT", str(tmp_path / "nope" / "Rscript"))
    with pytest.raises(rbridge.RNotFoundError, match="missing file"):
        rbridge.find_rscript()


def test_not_found_message_is_actionable(monkeypatch):
    monkeypatch.delenv("METAVISION_RSCRIPT", raising=False)
    monkeypatch.delenv("R_HOME", raising=False)
    monkeypatch.setattr(rbridge.shutil, "which", lambda _name: None)
    monkeypatch.setattr(rbridge, "_candidate_install_dirs", list)
    with pytest.raises(rbridge.RNotFoundError, match=r"cran\.r-project\.org"):
        rbridge.find_rscript()


def test_bundled_install_script_is_packaged():
    assert rbridge.script_path("install_deps.R").name == "install_deps.R"


def test_missing_bundled_script_raises():
    with pytest.raises(FileNotFoundError):
        rbridge.script_path("does_not_exist.R")


@pytest.mark.r
@requires_r
def test_find_rscript_returns_executable():
    assert Path(rbridge.find_rscript()).is_file()


@pytest.mark.r
@requires_r
def test_run_r_captures_stdout():
    assert rbridge.run_r(["-e", "cat(1 + 1)"]).stdout == "2"


@pytest.mark.r
@requires_r
def test_run_r_raises_with_stderr_on_error():
    with pytest.raises(rbridge.RScriptError, match="boom"):
        rbridge.run_r(["-e", 'stop("boom")'])


@pytest.mark.r
@requires_r
def test_check_r_reports_version():
    status = rbridge.check_r(packages=("stats",))
    assert status.version.startswith("R version")
    assert status.ok
