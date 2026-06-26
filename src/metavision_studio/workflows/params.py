"""Parameters for every step, as dataclasses whose field metadata drives the GUI form.

Each field is declared with :func:`param`. Its metadata tells the form builder how to show it:

* ``label`` / ``help``: text shown next to the control and as a tooltip
* ``advanced``: hidden under the step's *Advanced* disclosure
* ``choices``: a fixed list of ``(value, label)`` pairs, shown as a dropdown
* ``kind``: a dynamic picker filled from the project: ``"feature"`` (molecule), ``"sections"``
  (comma list of sections) or ``"clusters"`` (comma list of cluster IDs)
* ``min`` / ``max`` / ``step``: numeric bounds

Defaults follow the MetaVision3D and SAMI papers and reference code.
"""

from __future__ import annotations

from dataclasses import MISSING, asdict, dataclass, field, fields
from typing import Any

__all__ = [
    "PARAMS",
    "AtlasParams",
    "ClusterParams",
    "FillParams",
    "LoadParams",
    "MarkersParams",
    "Mv3dAlignParams",
    "Mv3dNormaliseParams",
    "PathwaysParams",
    "SamiNormaliseParams",
    "default_params",
    "param",
    "param_fields",
    "params_from_dict",
    "params_to_dict",
]


def param(
    default: Any,
    label: str,
    help: str = "",
    *,
    advanced: bool = False,
    choices: list[tuple[Any, str]] | None = None,
    kind: str | None = None,
    min: float | None = None,
    max: float | None = None,
    step: float | None = None,
) -> Any:
    meta = {
        "label": label,
        "help": help,
        "advanced": advanced,
        "choices": choices,
        "kind": kind,
        "min": min,
        "max": max,
        "step": step,
    }
    return field(default=default, metadata=meta)


# --------------------------------------------------------------------- shared
@dataclass
class LoadParams:
    pixel_size_um: float = param(
        0.0,
        "Pixel size (µm)",
        "Physical size of one pixel. 0 = estimate from the coordinate grid.",
        min=0.0,
        max=10_000.0,
        step=5.0,
    )
    flip_x: bool = param(False, "Flip X", "Mirror every section along x.", advanced=True)
    flip_y: bool = param(False, "Flip Y", "Mirror every section along y.", advanced=True)
    exclude_sections: str = param(
        "",
        "Exclude sections",
        "Comma-separated section IDs to leave out (e.g. empty or damaged sections).",
        advanced=True,
        kind="sections",
    )


# --------------------------------------------------------------------- MetaVision3D
@dataclass
class Mv3dNormaliseParams:
    method: str = param(
        "tic+section",
        "Method",
        "Total-ion-count (TIC) normalisation per pixel, then scaling so each section's "
        "median matches the median across sections (MetaVision3D).",
        choices=[
            ("tic+section", "TIC + section median"),
            ("tic", "TIC only"),
            ("section", "Section median only"),
            ("none", "None"),
        ],
    )
    min_prevalence: float = param(
        0.0,
        "Drop rare features",
        "Remove features detected in fewer than this fraction of pixels (0 = keep all; "
        "MetaVision3D's example uses 0.1).",
        advanced=True,
        min=0.0,
        max=1.0,
        step=0.05,
    )


@dataclass
class Mv3dAlignParams:
    reference: str = param(
        "auto",
        "Reference",
        "Molecule used to compute the alignment. Auto = the most prevalent one.",
        kind="feature",
    )
    max_iter: int = param(
        5000, "Max iterations", "ECC optimiser iteration limit.", advanced=True, min=10, max=100_000
    )
    eps: float = param(
        1e-10, "Tolerance", "ECC convergence threshold.", advanced=True, min=1e-14, max=1e-2
    )


@dataclass
class FillParams:
    impute: bool = param(True, "Impute missing pixels", "Fill holes from neighbouring sections.")
    interpolate: bool = param(True, "Add sections between", "Interpolate new sections in z.")
    n_insert: int = param(1, "Sections to add", "New sections between each pair.", min=1, max=10)
    radius: int = param(
        1,
        "Imputation radius",
        "How many sections on each side are used to fill a missing pixel.",
        advanced=True,
        min=1,
        max=5,
    )


@dataclass
class AtlasParams:
    thickness_um: float = param(
        10.0, "Thickness (µm)", "Thickness of each cut section.", min=0.1, max=1000.0
    )
    gap_um: float = param(
        50.0,
        "Gap (µm)",
        "Tissue discarded between kept sections.",
        min=0.0,
        max=10_000.0,
    )
    export_format: str = param(
        "nifti",
        "Export as",
        "",
        choices=[("nifti", "NIfTI (.nii.gz)"), ("tiff", "TIFF stack"), ("csv", "CSV (voxels)")],
    )
    features: str = param(
        "current",
        "Molecules",
        "",
        choices=[("current", "Current molecule"), ("all", "All molecules"), ("chosen", "Chosen…")],
    )
    chosen: str = param(
        "",
        "Chosen molecules",
        "Comma-separated molecules, used when 'Molecules' is 'Chosen…'.",
        advanced=True,
        kind="feature",
    )


# --------------------------------------------------------------------- SAMI
@dataclass
class SamiNormaliseParams:
    row: str = param(
        "sum",
        "Row",
        "Per-pixel normalisation.",
        choices=[
            ("sum", "Sum"),
            ("median", "Median"),
            ("comp", "Reference compound"),
            ("pqn", "PQN"),
            ("none", "None"),
        ],
    )
    transform: str = param(
        "log2",
        "Transform",
        "",
        choices=[
            ("log2", "log2"),
            ("log10", "log10"),
            ("sqrt", "Square root"),
            ("cbrt", "Cube root"),
            ("none", "None"),
        ],
    )
    scale: str = param(
        "none",
        "Scaling",
        "Per-feature scaling.",
        advanced=True,
        choices=[("none", "None"), ("auto", "Auto"), ("pareto", "Pareto"), ("range", "Range")],
    )
    reference: str = param(
        "",
        "Reference compound",
        "Only for Row = Reference compound.",
        advanced=True,
        kind="feature",
    )


@dataclass
class ClusterParams:
    resolution: float = param(
        1.0, "Resolution", "Higher → more, smaller clusters.", min=0.05, max=5.0, step=0.1
    )
    samples: str = param(
        "",
        "Samples",
        "Sections to cluster together (empty = all). Choosing samples replaces the old "
        "Grouping step.",
        kind="sections",
    )
    harmony: bool = param(
        False,
        "Correct batch effects",
        "Harmony integration across samples (needs the 'harmony' extra).",
    )
    random_state: int = param(7, "Random seed", "", advanced=True, min=0, max=2**31 - 1)


@dataclass
class MarkersParams:
    group_a: str = param(
        "",
        "Compare",
        "Cluster IDs (comma-separated). Tip: click a cluster in the canvas.",
        kind="clusters",
    )
    group_b: str = param(
        "rest",
        "Against",
        "Cluster IDs, or 'rest' for all other clusters.",
        kind="clusters",
    )
    fdr: float = param(
        0.05,
        "FDR",
        "Benjamini-Hochberg adjusted p-value cutoff.",
        advanced=True,
        min=0.0,
        max=1.0,
        step=0.01,
    )
    min_abundance: float = param(
        0.1, "Min pixel abundance", "", advanced=True, min=0.0, max=1.0, step=0.05
    )
    min_prevalence: float = param(
        0.1, "Min feature prevalence", "", advanced=True, min=0.0, max=1.0, step=0.05
    )
    top: int = param(0, "Top N markers", "0 = all significant.", advanced=True, min=0, max=10_000)


@dataclass
class PathwaysParams:
    fdr: float = param(
        0.05,
        "FDR",
        "Adjusted p-value cutoff for enriched pathways.",
        advanced=True,
        min=0.0,
        max=1.0,
        step=0.01,
    )


PARAMS: dict[str, dict[str, type]] = {
    "mv3d": {
        "load": LoadParams,
        "normalise": Mv3dNormaliseParams,
        "align": Mv3dAlignParams,
        "fill": FillParams,
        "atlas": AtlasParams,
    },
    "sami": {
        "load": LoadParams,
        "normalise": SamiNormaliseParams,
        "cluster": ClusterParams,
        "markers": MarkersParams,
        "pathways": PathwaysParams,
    },
}

STEP_TITLES: dict[str, str] = {
    "load": "Load data",
    "normalise": "Normalise",
    "align": "Align sections",
    "fill": "Fill gaps",
    "atlas": "3D atlas & export",
    "cluster": "Cluster",
    "markers": "Markers",
    "pathways": "Pathways",
}


def default_params(analysis: str, step: str) -> Any:
    return PARAMS[analysis][step]()


def param_fields(cls_or_obj: Any) -> list[tuple[str, Any, dict[str, Any]]]:
    """``(name, default, metadata)`` for each field, in declaration order."""
    out = []
    for f in fields(cls_or_obj):
        default = f.default if f.default is not MISSING else None
        out.append((f.name, default, dict(f.metadata)))
    return out


def params_to_dict(params: Any) -> dict[str, Any]:
    return asdict(params)


def params_from_dict(analysis: str, step: str, values: dict[str, Any] | None) -> Any:
    """Rebuild a params object, ignoring unknown keys (e.g. from an older project file)."""
    cls = PARAMS[analysis][step]
    names = {f.name for f in fields(cls)}
    return cls(**{k: v for k, v in (values or {}).items() if k in names})


def split_list(text: str) -> list[str]:
    """``"3, 5 ,7"`` → ``["3", "5", "7"]``."""
    return [t.strip() for t in str(text or "").split(",") if t.strip()]
