import json
import subprocess

import numpy as np
import pandas as pd
import pytest
from scipy.stats import hypergeom

from metavision_studio import rbridge, sami
from metavision_studio.sami import libraries


def _r_available() -> bool:
    try:
        return rbridge.check_r(("jsonlite", "nanoparquet")).ok
    except (rbridge.RNotFoundError, rbridge.RScriptError, OSError, subprocess.SubprocessError):
        return False


requires_r = pytest.mark.skipif(not _r_available(), reason="R with jsonlite + nanoparquet needed")


def _markers():
    rows = [
        # name, omics, significant, mean_a, mean_b
        ("Taurine", "metabolomics", True, 2.0, 1.0),
        ("L-Glutamine", "metabolomics", True, 1.5, 1.0),
        ("Citrate", "metabolomics", True, 0.5, 1.0),  # matches "Citric acid" via synonym
        ("Unknownium", "metabolomics", True, 1.0, 1.0),
        ("Succinic acid", "metabolomics", False, 0.25, 1.0),  # measured, not a marker
        ("Glycogen [1]", "glycomics", False, 1.0, 1.0),
        ("PC(34:1)", "lipidomics", True, 3.0, 1.0),
        ("PE(38:4)", "lipidomics", False, 1.0, 1.0),
        ("Mystery", "other", True, 1.0, 1.0),
    ]
    df = pd.DataFrame(rows, columns=["name", "omics", "significant", "mean_a", "mean_b"])
    df["feature"] = df["name"]
    df["log2fc"] = np.log2(df["mean_a"] / df["mean_b"])
    df["pvalue"] = 0.01
    df["padj"] = 0.02
    return df


def test_library_for_omics():
    assert sami.library_for_omics("metabolomics") == "smpdb_pathway"
    assert sami.library_for_omics("glycomics") == "smpdb_pathway"
    assert sami.library_for_omics("lipidomics") == "sub_class"
    assert sami.library_for_omics("other") is None


def test_missing_libraries_explain_how_to_prepare(tmp_path, monkeypatch):
    monkeypatch.setenv("METAVISION_DATA_DIR", str(tmp_path))
    assert libraries.library_dir() is None
    with pytest.raises(FileNotFoundError, match="prepare_libraries"):
        sami.enrich_pathways(_markers())


def test_library_dir_prefers_zenodo(tmp_path, monkeypatch, library_writer):
    write_mini_library = library_writer
    monkeypatch.setenv("METAVISION_DATA_DIR", str(tmp_path))
    write_mini_library(tmp_path / "sami-lib-parquet" / "metaboanalyst")
    assert libraries.library_dir().name == "metaboanalyst"
    write_mini_library(tmp_path / "sami-lib-parquet" / "zenodo")
    assert libraries.library_dir().name == "zenodo"
    assert libraries.library_dir("metaboanalyst").name == "metaboanalyst"


def test_no_testable_markers(mini_library):
    df = _markers()
    df = df[df["omics"] == "other"]
    out = sami.enrich_pathways(df, libraries=mini_library)
    assert out.empty and out.attrs["messages"]


@pytest.mark.r
@requires_r
def test_enrichment_matches_hypergeometric(mini_library):
    out = sami.enrich_pathways(_markers(), libraries=mini_library)
    assert list(out.columns) == sami.PATHWAY_COLUMNS
    metab = out[out["library"] == "smpdb_pathway"].set_index("pathway")
    # Universe: sets with >= 2 members -> {Taurine, Hypotaurine, L-Glutamine, Citric acid,
    # Succinic acid, Glycogen} = 6. Query (matched, in universe): Taurine, L-Glutamine,
    # Citric acid = 3.
    tau = metab.loc["Taurine and Hypotaurine Metabolism"]
    assert tau["hits"] == 2 and tau["size"] == 3
    assert tau["pvalue"] == pytest.approx(hypergeom.sf(2 - 1, 6, 3, 3))
    tca = metab.loc["Citric Acid Cycle"]
    assert tca["hits"] == 1
    assert "Citrate" in tca["members"]  # reported under the user's own name
    assert "Singleton" not in metab.index  # < 2 members excluded
    assert "Starch Metabolism" not in metab.index  # no hits


@pytest.mark.r
@requires_r
def test_direction_uses_all_measured_molecules(mini_library):
    out = sami.enrich_pathways(_markers(), libraries=mini_library).set_index("pathway")
    tca = out.loc["Citric Acid Cycle"]
    # measured: Citrate (0.5/1) and Succinic acid (0.25/1, not a marker): log2(0.75 / 2)
    assert set(tca["measured"].split(";")) == {"Citrate", "Succinic acid"}
    assert tca["log2fc"] == pytest.approx(np.log2(0.75 / 2))
    assert tca["direction"] == "down"
    assert out.loc["Taurine and Hypotaurine Metabolism", "direction"] == "up"


@pytest.mark.r
@requires_r
def test_lipid_branch_returns_results(mini_library):
    out = sami.enrich_pathways(_markers(), libraries=mini_library)
    lip = out[out["library"] == "sub_class"]
    assert not lip.empty
    assert set(lip["pathway"]) == {"PC"}
    assert lip.iloc[0]["omics"] == "lipidomics"


@pytest.mark.r
@requires_r
def test_unmatched_markers_are_reported(mini_library):
    out = sami.enrich_pathways(_markers(), libraries=mini_library)
    assert any("Unknownium" in m for m in out.attrs["messages"])


@pytest.mark.r
@requires_r
def test_multiple_comparisons(mini_library):
    a = _markers().assign(comparison="1")
    b = _markers().assign(comparison="2")
    out = sami.enrich_pathways(pd.concat([a, b]), libraries=mini_library)
    assert set(out["comparison"]) == {"1", "2"}


@pytest.mark.r
@requires_r
def test_ora_script_writes_nothing_to_cwd(mini_library, tmp_path, monkeypatch):
    work = tmp_path / "cwd"
    work.mkdir()
    monkeypatch.chdir(work)
    sami.enrich_pathways(_markers(), libraries=mini_library)
    assert list(work.iterdir()) == []


@pytest.mark.r
@requires_r
def test_ora_script_fails_loudly_on_missing_library(tmp_path):
    req = {
        "library_dir": str(tmp_path / "nope"),
        "comparisons": [{"id": "1", "lipid": False, "queries": ["Taurine"], "background": []}],
    }
    (tmp_path / "req.json").write_text(json.dumps(req), encoding="utf-8")
    with pytest.raises(rbridge.RScriptError, match="not found"):
        rbridge.run_script("ora.R", str(tmp_path / "req.json"), str(tmp_path / "out"))


def _has_r_pkgs(*pkgs) -> bool:
    try:
        return rbridge.check_r(pkgs).ok
    except (rbridge.RNotFoundError, rbridge.RScriptError, OSError):
        return False


@pytest.mark.r
@pytest.mark.skipif(not _has_r_pkgs("qs2", "nanoparquet", "jsonlite"), reason="needs R qs2")
def test_convert_libraries_roundtrip(tmp_path):
    src = tmp_path / "qs"
    src.mkdir()
    code = f"""
    d <- "{src.as_posix()}"
    cdb <- data.frame(hmdb_id = c("H1", "H2"), name = c("Taurine", "Citric acid"),
                      kegg_id = c("C1", "C2"), stringsAsFactors = FALSE)
    qs2::qs_save(cdb, file.path(d, "compound_db.qs"))
    qs2::qs_save(list(syns.vec = NULL, syns.list = list(c("Taurine"), c("Citrate", "Citric acid"))),
                 file.path(d, "syn_nms.qs"))
    sets <- data.frame(id = "S1", name = "TCA", member = "Taurine; Citric acid",
                       reference = "", image = NA, stringsAsFactors = FALSE)
    qs2::qs_save(sets, file.path(d, "smpdb_pathway.qs"))
    """
    script = tmp_path / "make_qs.R"  # multi-line `Rscript -e` is unreliable on Windows
    script.write_text(code, encoding="utf-8")
    rbridge.run_r([str(script)])
    out = tmp_path / "parquet"
    rbridge.run_script("convert_libraries.R", str(src), str(out))
    cdb = pd.read_parquet(out / "compound_db.parquet")
    assert list(cdb["name"]) == ["Taurine", "Citric acid"] and list(cdb["idx"]) == [1, 2]
    syn = pd.read_parquet(out / "syn_nms.parquet")
    assert syn[syn["synonym"] == "Citrate"]["idx"].item() == 2
    sets = pd.read_parquet(out / "smpdb_pathway.parquet")
    assert list(sets.columns) == ["id", "name", "member", "reference"]
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert set(manifest["files"]) == {"compound_db", "syn_nms", "smpdb_pathway"}
