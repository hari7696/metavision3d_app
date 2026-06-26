"""What the canvas and the insights panel show for each step (Qt-free).

The GUI asks two questions:

* :func:`layer_for`: for step S and molecule M, which array goes in the canvas, as an image
  or labels layer, and at what physical scale?
* :func:`insight_for`: which one chart summarises step S?

Answers are plain data (numpy / pandas), so they are cheap to test and computed in worker
threads.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

import numpy as np
import pandas as pd

from metavision_studio.io import MSIData, build_raster
from metavision_studio.project import Project
from metavision_studio.workflows.params import STEP_TITLES
from metavision_studio.workflows.runners import load_step_data, mv3d_feature_stack
from metavision_studio.workflows.storage import read_result_table

__all__ = ["Insight", "LayerSpec", "insight_for", "layer_for"]

#: Layer shown in the canvas for each step, and its display name.
LAYER_NAMES = {
    "load": "Raw",
    "normalise": "Normalised",
    "align": "Aligned",
    "fill": "Filled",
    "atlas": "3D atlas",
    "cluster": "Clusters",
    "markers": "Normalised",
}


@dataclass
class LayerSpec:
    name: str
    kind: Literal["image", "labels"]
    data: np.ndarray
    scale: tuple[float, float, float]
    title: str = ""
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class Insight:
    kind: Literal["boxplot", "scores", "umap", "volcano", "pathways", "none"]
    title: str
    data: Any = None
    meta: dict[str, Any] = field(default_factory=dict)


def _pixel(project: Project) -> float:
    rec = project.record("load") or {}
    return float((rec.get("summary") or {}).get("pixel_size_um") or 1.0)


def _z_scale(project: Project, step: str) -> float:
    """z spacing (µm) of the canvas layer, matching ``mv3d.voxel_size`` and the export.

    Uses the 3D atlas settings when recorded, else their defaults (10 µm sections, 50 µm
    gap). Sections inserted by Fill shrink the spacing.
    """
    pixel = _pixel(project)
    if project.analysis != "mv3d":
        return pixel
    try:
        from metavision_studio import mv3d
        from metavision_studio.workflows.params import AtlasParams

        atlas = {**vars(AtlasParams()), **(project.record("atlas") or {}).get("params", {})}
        fill = (project.record("fill") or {}).get("params", {})
        n_insert = (
            int(fill.get("n_insert", 1))
            if step in ("fill", "atlas") and fill.get("interpolate", True)
            else 0
        )
        dz, _dx, _dy = mv3d.voxel_size(
            pixel_size_um=pixel,
            thickness_um=float(atlas["thickness_um"]),
            gap_um=float(atlas["gap_um"]),
            n_insert=n_insert,
        )
        return float(dz)
    except Exception:
        return pixel


def layer_for(project: Project, step: str, feature: str) -> LayerSpec | None:
    """Canvas layer for ``step`` showing ``feature``. None when the step has no image."""
    analysis = project.analysis
    if project.status(step) not in ("done", "stale") or step == "pathways":
        return None
    pixel = _pixel(project)
    name = LAYER_NAMES.get(step, STEP_TITLES[step])

    if analysis == "mv3d":
        upto = {"atlas": "fill"}.get(step, step)
        stack = mv3d_feature_stack(project, feature, upto)
        scale = (_z_scale(project, step), pixel, pixel)
        return LayerSpec(name, "image", stack, scale, title=f"{name} · {feature}")

    # SAMI: sections stacked along the first axis, one plane per sample
    if step == "cluster":
        import anndata as ad

        adata = ad.read_h5ad(project.output("cluster", "clusters"))
        return LayerSpec(
            "Clusters",
            "labels",
            cluster_label_stack(adata, project),
            (pixel, pixel, pixel),
            meta={"categories": _categories(adata)},
        )
    src = "load" if step == "load" else "normalise"
    data = load_step_data(project, src)
    stack = load_canvas(project, data).stack(data.column(feature))
    return LayerSpec(name, "image", stack, (pixel, pixel, pixel), title=f"{name} · {feature}")


def _categories(adata) -> list[str]:
    cats = adata.obs["cluster"].astype("category").cat.categories
    return [str(c) for c in cats]


def load_canvas(project: Project, data: MSIData):
    """Raster of the Load data, indexed for ``data``'s pixels.

    Every SAMI layer (Raw, Normalised, Clusters, transferred clusters) is placed on the same
    canvas, so they overlay even when normalisation dropped empty pixels or only some samples
    were clustered.
    """
    base = load_step_data(project, "load")
    raster = build_raster(base)
    return raster if data is base else raster.reindex(base, data)


def cluster_label_stack(adata, project: Project | None = None) -> np.ndarray:
    """Labels stack: 0 = background, cluster category *i* → label *i + 1*.

    With ``project``, labels are placed on the Load canvas so they line up with the image
    layers. Without it, they get a canvas of their own.
    """
    obs = adata.obs
    codes = obs["cluster"].astype("category").cat.codes.to_numpy().astype(np.float32) + 1
    data = MSIData.from_arrays(
        x=obs["x"].to_numpy(),
        y=obs["y"].to_numpy(),
        section=obs["section"].astype(str).to_numpy(),
        values=codes[:, None],
        feature_ids=["cluster"],
    )
    raster = load_canvas(project, data) if project is not None else build_raster(data)
    return raster.stack(codes).astype(np.int32)


def label_to_cluster(adata_categories: list[str], label: int) -> str | None:
    if label <= 0 or label > len(adata_categories):
        return None
    return adata_categories[label - 1]


# ----------------------------------------------------------------------- insights
def _per_section_values(project: Project, step: str, feature: str, max_per: int = 4000):
    data = load_step_data(project, step)
    col = data.column(feature)
    out = {}
    rng = np.random.default_rng(0)
    for sec in data.sections:
        vals = col[data.section_mask(sec)]
        vals = vals[np.isfinite(vals)]
        if len(vals) > max_per:
            vals = rng.choice(vals, max_per, replace=False)
        out[sec] = vals
    return out


def insight_for(project: Project, step: str, feature: str | None) -> Insight:
    """The one chart that matters for ``step`` (``kind == "none"`` hides the panel)."""
    status = project.status(step)
    if status not in ("done", "stale"):
        return Insight("none", "")
    rec = project.record(step) or {}

    if step == "normalise" and feature:
        before = _per_section_values(project, "load", feature)
        after = _per_section_values(project, "normalise", feature)
        return Insight(
            "boxplot",
            f"{feature}: per-section intensity before and after normalisation",
            {"before": before, "after": after},
        )

    if step == "align":
        from metavision_studio import mv3d

        alignment = mv3d.load_alignment(project.output("align", "alignment"))
        sections = [str(x) for x in getattr(alignment, "sections", [])] or (
            (project.record("load") or {}).get("summary", {}).get("sections", [])
        )
        scores = np.asarray(alignment.scores, dtype=float)
        return Insight(
            "scores",
            f"Alignment quality per section (reference: {alignment.reference})",
            pd.DataFrame(
                {"section": sections[: len(scores)] or list(range(len(scores))), "score": scores}
            ),
            {"failed": [int(i) for i in alignment.failed]},
        )

    if step == "cluster":
        import anndata as ad

        adata = ad.read_h5ad(project.output("cluster", "clusters"))
        umap = np.asarray(adata.obsm["X_umap"])
        n = len(umap)
        idx = np.random.default_rng(0).choice(n, min(n, 20_000), replace=False) if n else []
        frame = pd.DataFrame(
            {
                "u1": umap[idx, 0],
                "u2": umap[idx, 1],
                "cluster": adata.obs["cluster"].astype(str).to_numpy()[idx],
            }
        )
        return Insight(
            "umap",
            f"UMAP · {rec.get('summary', {}).get('n_clusters', '?')} clusters",
            frame,
            {"categories": _categories(adata)},
        )

    if step == "markers":
        df = read_result_table(project.output("markers", "markers"))
        return Insight("volcano", "Markers: click a point to show that molecule", df)

    if step == "pathways":
        df = read_result_table(project.output("pathways", "pathways"))
        return Insight("pathways", "Enriched pathways", df)

    return Insight("none", "")
