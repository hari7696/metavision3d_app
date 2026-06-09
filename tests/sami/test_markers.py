import anndata as ad
import numpy as np
import pandas as pd
import pytest
from scipy.stats import false_discovery_control, ranksums

from metavision_studio import sami


def _adata(seed=0, n=200, shift=3.0):
    rng = np.random.default_rng(seed)
    x = rng.gamma(4, 1, size=(n, 5))
    labels = np.array(["0"] * (n // 2) + ["1"] * (n - n // 2))
    x[labels == "1", 0] *= shift  # feature A is a marker of cluster 1
    obs = pd.DataFrame(
        {"cluster": pd.Categorical(labels, categories=["0", "1"]), "section": "s"},
        index=[str(i) for i in range(n)],
    )
    var = pd.DataFrame(
        {"name": ["A", "B", "C", "D", "E"], "omics": ["metabolomics"] * 5},
        index=["A", "B", "C", "D", "E"],
    )
    return ad.AnnData(X=np.log2(1 + x / x.sum(axis=1, keepdims=True)), obs=obs, var=var)


def test_detects_planted_marker():
    df = sami.find_markers(_adata(), ["1"])
    assert list(df.columns) == sami.MARKER_COLUMNS
    top = df.iloc[0]
    assert top["feature"] == "A" and top["significant"] and top["log2fc"] > 0


def test_matches_scipy_ranksums_and_bh():
    adata = _adata()
    df = sami.find_markers(adata, ["1"], min_abundance=0, min_prevalence=0).set_index("feature")
    a = adata[adata.obs["cluster"] == "1"].X
    b = adata[adata.obs["cluster"] == "0"].X
    p = ranksums(a, b, axis=0).pvalue
    np.testing.assert_allclose(df.loc[list(adata.var_names), "pvalue"], p)
    np.testing.assert_allclose(df.loc[list(adata.var_names), "padj"], false_discovery_control(p))


def test_padj_is_monotone_and_capped():
    df = sami.find_markers(_adata(shift=1.0), ["1"]).sort_values("pvalue")
    assert (df["padj"] <= 1).all()
    assert (np.diff(df["padj"].to_numpy()) >= -1e-15).all()


def test_log2fc_and_delta():
    adata = _adata()
    df = sami.find_markers(adata, ["1"], min_abundance=0, min_prevalence=0).set_index("feature")
    ma = adata[adata.obs["cluster"] == "1"].X.mean(axis=0)
    mb = adata[adata.obs["cluster"] == "0"].X.mean(axis=0)
    np.testing.assert_allclose(df.loc[list(adata.var_names), "log2fc"], np.log2(ma / mb))
    np.testing.assert_allclose(df.loc[list(adata.var_names), "delta"], ma - mb)


def test_top_limits_significant():
    df = sami.find_markers(_adata(shift=5), ["1"], top=1, fdr=1.0)
    assert df["significant"].sum() == 1


def test_pct_filter_excludes_rare_features():
    adata = _adata()
    adata.X[:, 4] = 0
    adata.X[:3, 4] = 1  # E detected in 1.5% of pixels
    df = sami.find_markers(adata, ["1"], min_prevalence=0, min_abundance=0)
    assert "E" not in set(df["feature"])


def test_overlapping_groups_rejected():
    with pytest.raises(ValueError, match="overlap"):
        sami.find_markers(_adata(), ["1"], ["1", "0"])


def test_control_mode_compares_same_cluster():
    case, ctrl = _adata(seed=1, shift=4), _adata(seed=2, shift=1)
    df = sami.find_markers(case, ["1"], control=ctrl)
    assert df.attrs["comparison"]["control"] is True
    assert df.iloc[0]["feature"] == "A" and df.iloc[0]["log2fc"] > 0


def test_filter_abundance_prevalence():
    adata = _adata()
    adata.X[:, 3] = 0
    out = sami.filter_abundance_prevalence(adata, 0.1, 0.1)
    assert "D" not in out.var_names and "prevalence" in out.var
    assert adata.n_vars == 5  # input untouched


def test_find_all_markers_stacks_comparisons():
    df = sami.find_all_markers(_adata())
    assert list(df.columns) == ["comparison", *sami.MARKER_COLUMNS]
    assert set(df["comparison"]) == {"0", "1"}


def test_detection_uses_counts_after_scaling():
    """Regression: after auto-scaling every value is non-zero, so the prevalence filter passed
    a molecule seen in 3% of pixels, and log2fc was NaN for every feature."""
    import anndata as ad

    rng = np.random.default_rng(0)
    n = 400
    counts = rng.gamma(2.0, 10.0, size=(n, 3)).astype(np.float32)
    counts[:, 2] = 0
    counts[: int(0.03 * n), 2] = 50.0  # rare molecule: 3% of pixels
    counts[: n // 2, 0] *= 4  # feature 0 is higher in cluster "a"
    x = (counts - counts.mean(0)) / counts.std(0)  # auto-scaling: signed, no zeros
    adata = ad.AnnData(
        X=x,
        obs=pd.DataFrame(
            {"cluster": ["a"] * (n // 2) + ["b"] * (n // 2)}, index=map(str, range(n))
        ),
        var=pd.DataFrame(index=["f0", "f1", "rare"]),
    )
    adata.layers["counts"] = counts
    res = sami.find_markers(adata, ["a"], ["b"], min_prevalence=0.1, top=None)
    assert "rare" not in set(res["feature"])
    assert np.isfinite(res["log2fc"]).all()
    assert res.set_index("feature").loc["f0", "log2fc"] > 1

    # Without the counts layer the old behaviour remains (upstream used X).
    del adata.layers["counts"]
    res_x = sami.find_markers(adata, ["a"], ["b"], min_prevalence=0.1, top=None)
    assert "rare" in set(res_x["feature"])
