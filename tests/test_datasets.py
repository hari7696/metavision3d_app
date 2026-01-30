"""Tests for the dataset registry (offline: no downloads)."""

import pytest

from metavision_studio import datasets


def test_registry_entries_are_complete():
    for key, ds in datasets.DATASETS.items():
        assert ds.key == key
        assert len(ds.md5) == 32
        assert ds.url.startswith("https://zenodo.org/api/records/")
        assert ds.doi in ds.citation
        assert ds.license == "CC-BY-4.0"


def test_cache_dir_override(monkeypatch, tmp_path):
    monkeypatch.setenv("METAVISION_DATA_DIR", str(tmp_path))
    assert datasets.cache_dir() == tmp_path
    assert not datasets.is_cached("mv3d-wt2")
    (tmp_path / "mv3d-wt2").mkdir()
    (tmp_path / "mv3d-wt2" / "f.csv").write_text("x")
    assert datasets.is_cached("mv3d-wt2")


def test_unknown_dataset():
    with pytest.raises(KeyError, match="Available"):
        datasets.fetch("nope")
