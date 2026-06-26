"""Create ready-to-run example projects from the public Zenodo datasets."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from metavision_studio import datasets
from metavision_studio.io import guess_omics
from metavision_studio.project import Project

__all__ = ["EXAMPLES", "Example", "create_example_project", "examples_dir"]


@dataclass(frozen=True)
class Example:
    key: str
    title: str
    description: str
    analysis: str
    dataset: str
    files: tuple[str, ...]  # relative to the unpacked dataset
    pixel_size_um: float


EXAMPLES: dict[str, Example] = {
    e.key: e
    for e in [
        Example(
            key="mv3d",
            title="3D atlas: mouse brain lipids",
            description="59 serial sections, 21 lipids (115 MB download)",
            analysis="mv3d",
            dataset="mv3d-wt2",
            files=("wt2/3d_brain_wt2_pbp_lipid_preprocessed.csv",),
            pixel_size_um=50.0,
        ),
        Example(
            key="sami",
            title="Multi-omics: mouse brain",
            description="2 sections, lipids + metabolites + glycans (124 MB download)",
            analysis="sami",
            dataset="sami-datasets",
            files=(
                "datasets/one_condition/brain_lipidomics.csv",
                "datasets/one_condition/brain_metabolomics.csv",
                "datasets/one_condition/brain_glycomics.csv",
            ),
            pixel_size_um=50.0,
        ),
    ]
}


def examples_dir() -> Path:
    import platformdirs

    return Path(platformdirs.user_documents_dir()) / "MetaVision Studio" / "examples"


def create_example_project(key: str, root: str | Path | None = None) -> Project:
    """Download the example data (once) and create, or reopen, its project."""
    ex = EXAMPLES[key]
    root = Path(root) if root else examples_dir() / ex.key
    if (root / "project.json").exists():
        return Project.open(root)
    data_dir = datasets.fetch(ex.dataset, progress=False)
    inputs = [{"path": str(data_dir / f), "omics": guess_omics(f)} for f in ex.files]
    missing = [i["path"] for i in inputs if not Path(i["path"]).exists()]
    if missing:
        raise FileNotFoundError(f"Example files missing after download: {missing}")
    return Project.create(
        root,
        analysis=ex.analysis,
        inputs=inputs,
        settings={"pixel_size_um": ex.pixel_size_um},
        name=ex.title,
    )
