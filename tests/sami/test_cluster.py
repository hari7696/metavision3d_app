import sys

import pytest
from sklearn.metrics import adjusted_rand_score

from metavision_studio import sami


@pytest.fixture(scope="module")
def clustered(make_data):
    data, truth = make_data(n_side=16)
    norm = sami.normalize(data)
    return sami.cluster(norm, resolution=0.3), truth, norm


def test_cluster_recovers_planted_domains(clustered):
    adata, truth, _ = clustered
    assert "X_umap" in adata.obsm and "spatial" in adata.obsm
    assert adata.obs["cluster"].dtype.name == "category"
    assert adjusted_rand_score(truth, adata.obs["cluster"]) > 0.5
    info = adata.uns["metavision"]["cluster"]
    assert info["n_clusters"] == adata.obs["cluster"].nunique()
    assert info["harmony"] is False


def test_cluster_is_reproducible(clustered):
    adata, _, norm = clustered
    again = sami.cluster(norm, resolution=0.3)
    assert (again.obs["cluster"].to_numpy() == adata.obs["cluster"].to_numpy()).all()


def test_cluster_categories_are_numerically_ordered(clustered):
    cats = list(clustered[0].obs["cluster"].cat.categories)
    assert cats == sorted(cats, key=int)


def test_harmony_without_package_gives_clear_error(monkeypatch, make_data):
    data, _ = make_data(n_side=6, sections=("a", "b"))
    monkeypatch.setitem(sys.modules, "harmonypy", None)
    with pytest.raises(ImportError, match=r"metavision-studio\[harmony\]"):
        sami.cluster(sami.normalize(data), harmony=True)


def test_harmony_ignored_for_single_section(monkeypatch, make_data):
    data, _ = make_data(n_side=6)
    monkeypatch.setitem(sys.modules, "harmonypy", None)
    adata = sami.cluster(sami.normalize(data), harmony=True)
    assert adata.uns["metavision"]["cluster"]["harmony"] is False


def test_invalid_resolution(two_domain):
    with pytest.raises(ValueError):
        sami.cluster(two_domain[0], resolution=0)


def test_transfer_clusters_uses_shared_features(clustered, make_data):
    adata, _, _ = clustered
    target_data, truth = make_data(n_side=12, seed=5)
    target = sami.normalize(target_data)
    target = target.subset(features=[f for f in target.feature_ids if f != "Glycogen"])
    out = sami.transfer_clusters(adata, target)
    assert out.n_vars == target.n_features
    assert set(out.obs["cluster"].dropna().unique()) <= set(adata.obs["cluster"].cat.categories)
    assert adjusted_rand_score(truth, out.obs["cluster"]) > 0.5
    assert out.uns["metavision"]["transfer"]["shared_features"] == target.n_features


def test_transfer_needs_clusters(clustered):
    adata, _, norm = clustered
    bare = adata.copy()
    del bare.obs["cluster"]
    with pytest.raises(ValueError, match="no clusters"):
        sami.transfer_clusters(bare, norm)
