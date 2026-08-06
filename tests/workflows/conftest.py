"""Shared fixtures: a tiny synthetic dataset and fake core modules."""

from __future__ import annotations

import itertools
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from metavision_studio.project import Project
from metavision_studio.workflows import runners


def make_csv(
    path,
    *,
    n_sections=4,
    shape=(10, 12),
    features=("PC(34:1)", "LPA(16:0)", "m.z.760.585"),
    section_col="tissue_id",
    seed=0,
):
    rng = np.random.default_rng(seed)
    rows = []
    for s in range(1, n_sections + 1):
        for i in range(shape[0]):
            for j in range(shape[1]):
                # an offset per section, like real slides; 50 µm grid
                rows.append({"x": 1000 * s + 50 * i, "y": 50 * j, section_col: s})
    df = pd.DataFrame(rows)
    blob = np.exp(-(((df["x"] % 1000) / 50 - 5) ** 2 + (df["y"] / 50 - 6) ** 2) / 10)
    for k, f in enumerate(features):
        df[f] = (blob * (k + 1) * 100 + rng.random(len(df))).astype(float)
    df["spotId"] = np.arange(len(df))
    df.to_csv(path, index=False)
    return path


@pytest.fixture
def tiny_csv(tmp_path):
    return make_csv(tmp_path / "sections_lipidomics.csv")


@pytest.fixture
def mv3d_project(tmp_path, tiny_csv):
    return Project.create(
        tmp_path / "proj",
        analysis="mv3d",
        inputs=[{"path": str(tiny_csv), "omics": "lipidomics"}],
        settings={"pixel_size_um": 50.0},
    )


@pytest.fixture
def sami_project(tmp_path):
    a = make_csv(
        tmp_path / "brain_lipidomics.csv",
        n_sections=2,
        section_col="region",
        features=("LPA(16:0)", "PC(34:1)"),
    )
    b = make_csv(
        tmp_path / "brain_metabolomics.csv",
        n_sections=2,
        section_col="region",
        features=("Pyruvic acid", "Taurine"),
        seed=1,
    )
    return Project.create(
        tmp_path / "sproj",
        analysis="sami",
        inputs=[{"path": str(a), "omics": "lipidomics"}, {"path": str(b), "omics": "metabolomics"}],
    )


# ----------------------------------------------------------------------------- fakes
class FakeAlignment(SimpleNamespace):
    pass


def fake_mv3d(calls: list | None = None):
    calls = calls if calls is not None else []

    def normalize(data, method="tic+section"):
        calls.append(("normalize", method))
        v = np.asarray(data.values)
        return data.with_values(v / (v.sum(axis=1, keepdims=True) + 1))

    def compute_alignment(data, raster, *, reference=None, max_iter=5000, eps=1e-10, progress=None):
        calls.append(("compute_alignment", reference, max_iter))
        n = len(raster.sections)
        for i in range(n):
            if progress:
                progress(i, n, f"Aligning {i + 1}/{n}")
        return FakeAlignment(
            reference=reference or data.feature_ids[0],
            warps=np.tile(np.eye(2, 3), (n, 1, 1)),
            scores=np.linspace(0.5, 1.0, n),
            failed=[],
            sections=list(raster.sections),
        )

    def save_alignment(a, path):
        np.savez(
            path,
            reference=a.reference,
            warps=a.warps,
            scores=a.scores,
            failed=np.array(a.failed, dtype=int),
            sections=np.array(a.sections),
        )

    def load_alignment(path):
        z = np.load(path, allow_pickle=False)
        return FakeAlignment(
            reference=str(z["reference"]),
            warps=z["warps"],
            scores=z["scores"],
            failed=z["failed"].tolist(),
            sections=z["sections"].tolist(),
        )

    def section_quality(data):
        secs = data.sections
        return pd.DataFrame(
            {
                "section": secs,
                "n_pixels": 1,
                "total": 1.0,
                "flagged": [s == secs[-1] for s in secs],
                "reason": ["small" if s == secs[-1] else "" for s in secs],
            }
        )

    def interpolate(stack, *, n_insert=1, progress=None):
        out = [stack[0]]
        for a, b in itertools.pairwise(stack):
            for k in range(1, n_insert + 1):
                out.append(a + (b - a) * k / (n_insert + 1))
            out.append(b)
        return np.stack(out)

    def voxel_size(*, pixel_size_um, thickness_um, gap_um=0.0, n_insert=0):
        return ((thickness_um + gap_um) / (1 + n_insert), pixel_size_um, pixel_size_um)

    def to_nifti(stack, *, pixel_size_um, thickness_um, gap_um=0.0, n_insert=0):
        import nibabel as nib

        return nib.Nifti1Image(np.transpose(stack, (1, 2, 0)), np.eye(4))

    return SimpleNamespace(
        normalize=normalize,
        remove_low_prevalence=lambda data, min_prevalence=0.1: (data, []),
        section_quality=section_quality,
        blank_sections=lambda data, sections: data.with_values(
            np.where(data.pixels["section"].isin(sections).to_numpy()[:, None], 0, data.values)
        ),
        compute_alignment=compute_alignment,
        apply_alignment=lambda stack, a: stack,
        save_alignment=save_alignment,
        load_alignment=load_alignment,
        impute=lambda stack, *, radius=1, progress=None: stack,
        interpolate=interpolate,
        voxel_size=voxel_size,
        to_nifti=to_nifti,
        describe=lambda step, params: f"[{step}]",
        calls=calls,
    )


def fake_sami():
    import anndata as ad

    def cluster(data, *, resolution=1.0, harmony=False, random_state=7, progress=None):
        adata = data.to_anndata()
        labels = (data.pixels["x"].to_numpy() % 1000 > 200).astype(int)
        adata.obs["cluster"] = pd.Categorical(labels.astype(str))
        adata.obsm["X_umap"] = np.column_stack([labels + 0.1 * np.arange(len(labels)) % 1, labels])
        return adata

    def find_markers(
        adata, group_a, group_b=None, *, min_abundance=0.1, min_prevalence=0.1, fdr=0.05, top=None
    ):
        feats = list(adata.var_names)
        return pd.DataFrame(
            {
                "feature": feats,
                "name": feats,
                "omics": "lipidomics",
                "mean_a": 1.0,
                "mean_b": 0.5,
                "log2fc": np.linspace(-1, 1, len(feats)),
                "pvalue": 0.001,
                "padj": 0.01,
                "significant": True,
            }
        )

    def enrich_pathways(markers, *, libraries=None, fdr=0.05, progress=None):
        return pd.DataFrame(
            {
                "pathway": ["Glycolysis"],
                "library": ["smpdb"],
                "omics": ["metabolomics"],
                "hits": [2],
                "size": [10],
                "pvalue": [0.001],
                "padj": [0.01],
                "significant": [True],
                "direction": ["up"],
                "members": ["a; b"],
            }
        )

    def transfer_clusters(reference, target, *, progress=None):
        adata = target.to_anndata()
        adata.obs["cluster"] = pd.Categorical(["0"] * adata.n_obs)
        return adata

    return SimpleNamespace(
        normalize=lambda data, *, row="sum", transform="log2", scale="none", reference=None: (
            data.with_values(np.log2(np.asarray(data.values) + 1))
        ),
        cluster=cluster,
        find_markers=find_markers,
        enrich_pathways=enrich_pathways,
        transfer_clusters=transfer_clusters,
        library_dir=lambda: "libs",
        prepare_libraries=lambda progress=None: "libs",
        describe=lambda step, params: f"[{step}]",
        ad=ad,
    )


@pytest.fixture
def fakes(monkeypatch):
    mods = {"mv3d": fake_mv3d(), "sami": fake_sami()}
    monkeypatch.setattr(runners, "_core", lambda name: mods[name])
    return mods
