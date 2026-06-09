"""Small synthetic SAMI datasets with known structure."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from metavision_studio.io import MSIData


def make_two_domain(
    *, n_side: int = 14, sections: tuple[str, ...] = ("s1",), seed: int = 0, extra_offset: float = 0
) -> tuple[MSIData, np.ndarray]:
    """Square sections split into a left and right domain.

    Features: 4 lipids, 3 metabolites, 1 glycan. ``Taurine`` and ``PC(34:1)`` are 4x higher
    on the right; the rest are noise. Returns the data and the true domain label per pixel.
    """
    rng = np.random.default_rng(seed)
    xs, ys, secs, truth = [], [], [], []
    for s in sections:
        gx, gy = np.meshgrid(np.arange(n_side), np.arange(n_side), indexing="ij")
        xs.append(gx.ravel() * 50.0 + extra_offset)
        ys.append(gy.ravel() * 50.0)
        secs += [s] * gx.size
        truth.append((gy.ravel() >= n_side // 2).astype(int))
    x, y, truth = np.concatenate(xs), np.concatenate(ys), np.concatenate(truth)
    names = [
        "PC(34:1)",
        "PE(38:4)",
        "LPA(16:0)",
        "PI(38:4)",
        "Taurine",
        "L-Glutamine",
        "Citric acid",
        "Glycogen",
    ]
    omics = ["lipidomics"] * 4 + ["metabolomics"] * 3 + ["glycomics"]
    base = rng.gamma(shape=5, scale=200, size=(len(x), len(names)))
    base[truth == 1, 0] *= 4  # PC(34:1)
    base[truth == 1, 4] *= 4  # Taurine
    base[rng.random(base.shape) < 0.05] = 0  # sparse zeros like real MALDI
    base[:, 7] += 1  # the only glycan stays non-zero, so normalisation keeps every pixel
    data = MSIData.from_arrays(x, y, secs, base, names, omics=omics, pixel_size_um=50.0)
    return data, truth


@pytest.fixture
def two_domain():
    return make_two_domain()


def write_mini_library(path) -> None:
    """A tiny Parquet library in the converter's layout (see R/convert_libraries.R)."""
    path.mkdir(parents=True, exist_ok=True)
    compounds = pd.DataFrame(
        {
            "idx": [1, 2, 3, 4, 5, 6],
            "hmdb_id": [f"HMDB{i:07d}" for i in range(1, 7)],
            "name": [
                "Taurine",
                "L-Glutamine",
                "Citric acid",
                "Glycogen",
                "Hypotaurine",
                "Succinic acid",
            ],
            "kegg_id": ["C00245", "C00064", "C00158", "C00182", "C00519", "C00042"],
        }
    )
    compounds.to_parquet(path / "compound_db.parquet")
    pd.DataFrame(
        {"idx": [3, 3, 5], "synonym": ["Citrate", "Citric acid", "2-Aminoethanesulfinic acid"]}
    ).to_parquet(path / "syn_nms.parquet")
    pd.DataFrame(
        {
            "id": ["SMP1", "SMP2", "SMP3", "SMP4"],
            "name": [
                "Taurine and Hypotaurine Metabolism",
                "Citric Acid Cycle",
                "Starch Metabolism",
                "Singleton",
            ],
            "member": [
                "Taurine; Hypotaurine; L-Glutamine",
                "Citric acid; Succinic acid",
                "Glycogen; Succinic acid",
                "Taurine",
            ],
            "reference": ["", "", "", ""],
        }
    ).to_parquet(path / "smpdb_pathway.parquet")
    lipids = pd.DataFrame(
        {
            "idx": [1, 2, 3, 4],
            "hmdb_id": ["L1", "L2", "L3", "L4"],
            "name": ["PC(34:1)", "PE(38:4)", "LPA(16:0)", "PI(38:4)"],
            "kegg_id": [None, None, None, None],
        }
    )
    lipids.to_parquet(path / "lipid_compound_db.parquet")
    pd.DataFrame({"idx": [1], "synonym": ["PC 34:1"]}).to_parquet(path / "lipid_syn_nms.parquet")
    pd.DataFrame(
        {
            "id": ["sc1", "sc2"],
            "name": ["PC", "Glycerophosphates"],
            "member": ["PC(34:1); PC(36:2)", "LPA(16:0); PE(38:4); PI(38:4)"],
            "reference": ["", ""],
        }
    ).to_parquet(path / "sub_class.parquet")
    (path / "manifest.json").write_text('{"format": 1, "files": {}}', encoding="utf-8")


@pytest.fixture
def mini_library(tmp_path):
    lib = tmp_path / "lib"
    write_mini_library(lib)
    return lib


@pytest.fixture(scope="session")
def make_data():
    """Factory for synthetic two-domain data (see make_two_domain)."""
    return make_two_domain


@pytest.fixture(scope="session")
def library_writer():
    return write_mini_library
