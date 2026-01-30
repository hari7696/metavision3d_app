"""Public example datasets and libraries, downloaded on demand from Zenodo.

Nothing here is bundled with the package. Files are downloaded once, checked against
Zenodo's MD5 checksum, unpacked, and cached in the user cache directory (override it with
``METAVISION_DATA_DIR``).

All datasets are by Xin Ma and colleagues and are licensed CC BY 4.0. Cite the record
DOI when you use them (see :attr:`Dataset.citation`).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

__all__ = ["DATASETS", "Dataset", "cache_dir", "fetch", "is_cached"]


@dataclass(frozen=True)
class Dataset:
    key: str
    title: str
    description: str
    record: str
    filename: str
    md5: str
    size_mb: float
    doi: str
    license: str = "CC-BY-4.0"

    @property
    def url(self) -> str:
        return f"https://zenodo.org/api/records/{self.record}/files/{self.filename}/content"

    @property
    def citation(self) -> str:
        return f"Ma X. {self.title}. Zenodo. https://doi.org/{self.doi} ({self.license})"


_MV3D = dict(
    record="14212427",
    doi="10.5281/zenodo.14212427",
    title="MetaVision3D: Automated Framework for the Generation of Spatial Metabolome Atlas "
    "in 3D | MALDI Data",
)
_SAMI = dict(
    record="15224641",
    doi="10.5281/zenodo.15224641",
    title="Spatial Mapping of the Brain Metabolome Lipidome and Glycome | SAMI datasets",
)

DATASETS: dict[str, Dataset] = {
    d.key: d
    for d in [
        Dataset(
            key="mv3d-wt2",
            description="MetaVision3D: wild-type mouse brain serial sections (smallest, "
            "recommended for trying the tool)",
            filename="wt2.zip",
            md5="e1f58a1df214453ecefa35efa74a66c5",
            size_mb=114.6,
            **_MV3D,
        ),
        Dataset(
            key="mv3d-wt",
            description="MetaVision3D: wild-type mouse brain serial sections (full)",
            filename="wt.zip",
            md5="30fc52f7e4e3a0180e8a5ca822833e6d",
            size_mb=1042.1,
            **_MV3D,
        ),
        Dataset(
            key="mv3d-5x",
            description="MetaVision3D: 5xFAD mouse brain serial sections",
            filename="5x.zip",
            md5="bf69f4935a8b275011ceeb3b61e3a449",
            size_mb=1118.0,
            **_MV3D,
        ),
        Dataset(
            key="mv3d-gaa",
            description="MetaVision3D: Gaa-knockout (Pompe) mouse brain serial sections",
            filename="gaa.zip",
            md5="024552d162d74c088b768e1a2c9f5429",
            size_mb=1139.0,
            **_MV3D,
        ),
        Dataset(
            key="sami-datasets",
            description="SAMI: triple-omics (lipids, metabolites, glycans) mouse brain sections, "
            "one condition and AD vs WT",
            filename="datasets.zip",
            md5="020026e245c3f4ebcbd17e955f5bcd9b",
            size_mb=123.6,
            **_SAMI,
        ),
        Dataset(
            key="sami-lib",
            description="SAMI: pathway-enrichment libraries (compound DB, SMPDB, lipid classes)",
            filename="lib.zip",
            md5="55e47e121a2588b9cda78f077632e784",
            size_mb=18.3,
            **_SAMI,
        ),
    ]
}


def cache_dir() -> Path:
    """Where downloads are stored (``METAVISION_DATA_DIR`` or the user cache)."""
    if env := os.environ.get("METAVISION_DATA_DIR"):
        return Path(env)
    import pooch

    return Path(pooch.os_cache("metavision-studio"))


def _extract_dir(ds: Dataset) -> Path:
    return cache_dir() / f"{ds.key}"


def is_cached(key: str) -> bool:
    """True if the dataset has already been downloaded and unpacked."""
    path = _extract_dir(DATASETS[key])
    return path.is_dir() and any(path.iterdir())


def fetch(key: str, *, progress: bool = True) -> Path:
    """Download (if needed) and unpack a dataset; return the directory with its files.

    >>> path = fetch("mv3d-wt2")  # doctest: +SKIP
    """
    import pooch

    try:
        ds = DATASETS[key]
    except KeyError:
        raise KeyError(f"Unknown dataset {key!r}. Available: {', '.join(DATASETS)}") from None

    target = _extract_dir(ds)
    pooch.retrieve(
        url=ds.url,
        known_hash=f"md5:{ds.md5}",
        fname=ds.filename,
        path=cache_dir() / "downloads",
        processor=pooch.Unzip(extract_dir=str(target)),
        progressbar=progress,
    )
    return target
