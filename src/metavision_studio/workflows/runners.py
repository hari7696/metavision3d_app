"""Step runners: read inputs from the project, call the core, save outputs, record the run.

``run_step(project, step, params)`` is the single entry point used by the GUI, the CLI and
notebooks. It never touches Qt and is safe to call from a worker thread.

Core modules (``mv3d``, ``sami``) are imported lazily inside each runner, so the plugin
still opens if an optional part of the science stack is missing.
"""

from __future__ import annotations

import importlib
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from metavision_studio._progress import Cancelled, ProgressFn, report
from metavision_studio.io import build_raster, merge_omics, read_table
from metavision_studio.io.data import MSIData
from metavision_studio.project import Project
from metavision_studio.workflows.errors import StepLocked, explain
from metavision_studio.workflows.params import (
    PARAMS,
    STEP_TITLES,
    params_to_dict,
    split_list,
)
from metavision_studio.workflows.storage import load_msidata, read_result_table, save_msidata

__all__ = [
    "StepResult",
    "feature_items",
    "feature_list",
    "load_step_data",
    "pathway_libraries",
    "run_step",
    "run_transfer",
    "switch_analysis",
]


@dataclass
class StepResult:
    step: str
    outputs: dict[str, str]
    summary: dict[str, Any] = field(default_factory=dict)


def _core(name: str):
    return importlib.import_module(f"metavision_studio.{name}")


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


# ======================================================================= shared helpers
def load_step_data(project: Project, step: str) -> MSIData:
    """The MSIData saved by ``load`` or ``normalise``."""
    path = project.output(step, "data")
    if path is None:
        raise StepLocked(f"Run {STEP_TITLES[step]} first.")
    return load_msidata(path)


def feature_list(project: Project) -> list[str]:
    """Feature ids of the most processed dataset available."""
    for step in ("normalise", "load"):
        path = project.output(step, "data")
        if path is not None and (path / "features.parquet").exists():
            return pd.read_parquet(path / "features.parquet").index.astype(str).tolist()
    return []


def feature_items(project: Project) -> list[tuple[str, str]]:
    """``(feature_id, label)`` for the molecule picker, e.g. ``LPA(16:0) (m/z 409.2349)``."""
    for step in ("normalise", "load"):
        path = project.output(step, "data")
        if path is None or not (path / "features.parquet").exists():
            continue
        feats = pd.read_parquet(path / "features.parquet")
        items = []
        for fid, name, mz in zip(
            feats.index.astype(str), feats["name"].astype(str), feats["mz"], strict=True
        ):
            label = f"{name} (m/z {mz:.4f})" if np.isfinite(mz) and name != fid else name
            items.append((fid, label))
        return items
    return []


def switch_analysis(project: Project, analysis: str) -> dict[str, Any] | None:
    """Switch between the 3D atlas and multi-omics analyses.

    Each analysis keeps its own step records and output folders (``results/<analysis>/``),
    set aside here and restored when you switch back. Load is per-analysis too, because
    excluded sections are blanked for 3D but removed for multi-omics.

    Returns:
        The previous analysis's Load parameters when the new analysis has no Load yet, so
        the caller can re-run Load with the same settings (it takes seconds). Otherwise None.
    """
    if analysis == project.analysis:
        return None
    manifest = project.manifest
    shelf = manifest.setdefault("shelved_steps", {})
    steps = manifest["steps"]
    previous_load = (steps.get("load") or {}).get("params")
    shelf[project.analysis] = dict(steps)
    restored = shelf.pop(analysis, {})
    manifest["steps"] = restored
    project.analysis = analysis  # saves
    return previous_load if "load" not in restored else None


def pathway_libraries(progress: ProgressFn | None = None) -> Path:
    """Directory of the converted (Parquet) pathway libraries, preparing them on first use."""
    sami = _core("sami")
    path = sami.library_dir()
    if path is None:
        report(progress, 0, 1, "Preparing pathway libraries (first run only)")
        path = sami.prepare_libraries(progress=progress)
    return Path(path)


def _resolve_feature(data: MSIData, feature: str | None) -> str | None:
    if not feature or feature == "auto":
        return None
    return data.feature_ids[data.feature_index(feature)]


# ======================================================================= load (both)
def _run_load(project: Project, p: Any, progress: ProgressFn | None, **_: Any) -> StepResult:
    inputs = project.inputs
    if not inputs:
        raise ValueError("This project has no input files. Add data with New project.")
    pixel = p.pixel_size_um or project.settings.get("pixel_size_um") or None
    datasets = []
    for i, inp in enumerate(inputs):
        report(progress, i, len(inputs) + 1, f"Reading {Path(inp['path']).name}")
        data, _mapping = read_table(inp["path"], omics=inp.get("omics"), pixel_size_um=pixel)
        datasets.append(data)
    report(progress, len(inputs), len(inputs) + 1, "Combining files")
    data = merge_omics(datasets)
    data = data.flipped(flip_x=p.flip_x, flip_y=p.flip_y)
    excluded = split_list(p.exclude_sections)
    if excluded:
        unknown = sorted(set(excluded) - set(data.sections))
        if unknown:
            raise KeyError(f"Unknown sections in 'Exclude sections': {', '.join(unknown)}")
        keep = [s for s in data.sections if s not in set(excluded)]
        if not keep:
            raise ValueError("Every section is excluded. Remove some from 'Exclude sections'.")
        if project.analysis == "mv3d":
            # Keep the section's place in the stack (blank it) so z-spacing stays right and
            # imputation can fill it from its neighbours.
            data = _core("mv3d").blank_sections(data, excluded)
        else:
            data = data.subset(sections=keep)

    out = project.results_dir("load")
    save_msidata(data, out / "data")
    outputs = {"data": str(out / "data")}
    summary: dict[str, Any] = {
        "text": data.summary(),
        "n_sections": data.n_sections,
        "n_features": data.n_features,
        "n_pixels": data.n_pixels,
        "pixel_size_um": data.pixel_size_um,
        "sections": data.sections,
        "flagged_sections": [],
    }
    try:
        qc = _core("mv3d").section_quality(data)
    except (AttributeError, ImportError, NotImplementedError):
        qc = None
    if qc is not None:
        qc.to_csv(out / "qc.csv", index=False)
        outputs["qc"] = str(out / "qc.csv")
        flagged = qc.loc[qc["flagged"].astype(bool)] if "flagged" in qc else qc.iloc[0:0]
        summary["flagged_sections"] = [str(s) for s in flagged["section"]]
        summary["flag_reasons"] = (
            {str(s): str(r) for s, r in zip(flagged["section"], flagged["reason"], strict=False)}
            if "reason" in flagged
            else {}
        )
    return StepResult("load", outputs, summary)


# ======================================================================= MetaVision3D
def _run_mv3d_normalise(project: Project, p: Any, progress: ProgressFn | None, **_: Any):
    mv3d = _core("mv3d")
    data = load_step_data(project, "load")
    dropped: list[str] = []
    if p.min_prevalence > 0:
        data, dropped = mv3d.remove_low_prevalence(data, min_prevalence=p.min_prevalence)
    report(progress, 0, 1, "Normalising")
    norm = mv3d.normalize(data, method=p.method)
    out = project.results_dir("normalise")
    save_msidata(norm, out / "data")
    return StepResult(
        "normalise",
        {"data": str(out / "data")},
        {"method": p.method, "dropped_features": list(dropped), "n_features": norm.n_features},
    )


def _run_mv3d_align(project: Project, p: Any, progress: ProgressFn | None, **_: Any):
    import hashlib
    import json
    import shutil

    mv3d = _core("mv3d")
    data = load_step_data(project, "normalise")  # alignment is computed from normalised data
    raster = build_raster(data)
    # Cache keyed on the normalised data (its step fingerprint) and the alignment settings,
    # so re-running with unchanged inputs is instant and a changed input never reuses a stale
    # warp matrix (the 2024 app keyed its cache on the CSV file name).
    norm_fp = (project.record("normalise") or {}).get("fingerprint", "")
    key = hashlib.sha256(
        json.dumps([norm_fp, p.reference, p.max_iter, p.eps]).encode()
    ).hexdigest()[:16]
    cached = project.cache_dir() / f"alignment_{key}.npz"
    if cached.exists():
        report(progress, 1, 1, "Using cached alignment")
        alignment = mv3d.load_alignment(cached)
    else:
        alignment = mv3d.compute_alignment(
            data,
            raster,
            reference=_resolve_feature(data, p.reference),
            max_iter=p.max_iter,
            eps=p.eps,
            progress=progress,
        )
        mv3d.save_alignment(alignment, cached)
    out = project.results_dir("align")
    path = out / "alignment.npz"
    shutil.copyfile(cached, path)
    scores = np.asarray(alignment.scores, dtype=float)
    failed = [int(i) for i in alignment.failed]
    return StepResult(
        "align",
        {"alignment": str(path)},
        {
            "reference": alignment.reference,
            "failed_sections": [
                str(alignment.sections[i]) for i in failed if i < len(alignment.sections)
            ],
            "mean_score": float(np.nanmean(scores)) if scores.size else None,
        },
    )


def mv3d_feature_stack(
    project: Project, feature: str, upto: str, progress: ProgressFn | None = None
) -> np.ndarray:
    """Stack ``(sections, rows, cols)`` of one feature after the given step.

    ``upto`` is one of ``load``, ``normalise``, ``align`` or ``fill``. Used by export and by the
    GUI, so what you see is exactly what gets exported.
    """
    mv3d = _core("mv3d")
    data = load_step_data(project, "load" if upto == "load" else "normalise")
    raster = build_raster(data)
    stack = raster.stack(data.column(feature))
    if upto in ("load", "normalise"):
        return stack
    stack = mv3d.apply_alignment(stack, mv3d.load_alignment(project.output("align", "alignment")))
    if upto == "align":
        return stack
    rec = project.record("fill") or {}
    fp = rec.get("params", {})
    if fp.get("impute", True):
        stack = mv3d.impute(stack, radius=int(fp.get("radius", 1)), progress=progress)
    if fp.get("interpolate", True):
        stack = mv3d.interpolate(stack, n_insert=int(fp.get("n_insert", 1)), progress=progress)
    return stack


def _run_mv3d_fill(
    project: Project, p: Any, progress: ProgressFn | None, feature: str | None = None, **_: Any
):
    # Fill is applied per molecule on demand; here we check it on one molecule and record
    # the settings that the canvas and the export will use.
    mv3d = _core("mv3d")
    data = load_step_data(project, "normalise")
    align = mv3d.load_alignment(project.output("align", "alignment"))
    feat = _resolve_feature(data, feature) or align.reference
    stack = build_raster(data).stack(data.column(feat))
    stack = mv3d.apply_alignment(stack, align)
    if p.impute:
        stack = mv3d.impute(stack, radius=p.radius, progress=progress)
    if p.interpolate:
        stack = mv3d.interpolate(stack, n_insert=p.n_insert, progress=progress)
    out = project.results_dir("fill")
    np.save(out / "preview.npy", stack.astype(np.float32))
    return StepResult(
        "fill",
        {"preview": str(out / "preview.npy")},
        {"preview_feature": feat, "shape": list(stack.shape)},
    )


def _export_features(project: Project, p: Any, data: MSIData, current: str | None) -> list[str]:
    if p.features == "all":
        return data.feature_ids
    if p.features == "chosen":
        chosen = [data.feature_ids[data.feature_index(f)] for f in split_list(p.chosen)]
        if not chosen:
            raise ValueError("Choose at least one molecule under 'Chosen molecules'.")
        return chosen
    feat = _resolve_feature(data, current)
    if feat is None:
        rec = project.record("align") or {}
        feat = (rec.get("summary") or {}).get("reference") or data.feature_ids[0]
    return [feat]


def _safe_name(text: str) -> str:
    return "".join(c if c.isalnum() or c in "-_." else "_" for c in text).strip("_")[:80]


def _run_mv3d_atlas(
    project: Project, p: Any, progress: ProgressFn | None, feature: str | None = None, **_: Any
):
    mv3d = _core("mv3d")
    data = load_step_data(project, "normalise")
    fill = (project.record("fill") or {}).get("params", {})
    n_insert = int(fill.get("n_insert", 1)) if fill.get("interpolate", True) else 0
    pixel = float(data.pixel_size_um or project.settings.get("pixel_size_um") or 1.0)
    feats = _export_features(project, p, data, feature)
    out = project.results_dir("atlas")
    files = []
    for i, feat in enumerate(feats):
        report(progress, i, len(feats), f"Building {data.label(feat)} ({i + 1}/{len(feats)})")
        stack = mv3d_feature_stack(project, feat, "fill")
        base = out / _safe_name(feat)
        if p.export_format == "nifti":
            img = mv3d.to_nifti(
                stack,
                pixel_size_um=pixel,
                thickness_um=p.thickness_um,
                gap_um=p.gap_um,
                n_insert=n_insert,
            )
            import nibabel as nib

            path = base.with_suffix(".nii.gz")
            nib.save(img, path)
        elif p.export_format == "tiff":
            import tifffile

            dz, dx, dy = mv3d.voxel_size(
                pixel_size_um=pixel,
                thickness_um=p.thickness_um,
                gap_um=p.gap_um,
                n_insert=n_insert,
            )
            path = base.with_suffix(".tif")
            tifffile.imwrite(
                path,
                stack.astype(np.float32),
                imagej=True,
                resolution=(1.0 / dx, 1.0 / dy),
                metadata={"spacing": dz, "unit": "um", "axes": "ZYX"},
            )
        else:
            z, r, c = np.nonzero(stack)
            path = base.with_suffix(".csv")
            pd.DataFrame({"z": z, "x": r, "y": c, "value": stack[z, r, c]}).to_csv(
                path, index=False
            )
        files.append(path)
    report(progress, len(feats), len(feats), "Done")
    voxel = mv3d.voxel_size(
        pixel_size_um=pixel, thickness_um=p.thickness_um, gap_um=p.gap_um, n_insert=n_insert
    )
    outputs = {"dir": str(out)}
    if len(files) == 1:
        outputs["file"] = str(files[0])
    return StepResult(
        "atlas",
        outputs,
        {"n_files": len(files), "format": p.export_format, "voxel_um": list(map(float, voxel))},
    )


# ======================================================================= SAMI
def _run_sami_normalise(project: Project, p: Any, progress: ProgressFn | None, **_: Any):
    sami = _core("sami")
    data = load_step_data(project, "load")
    if p.row == "comp" and not p.reference:
        raise ValueError("Choose a reference compound (Advanced) to use 'Reference compound'.")
    report(progress, 0, 1, "Normalising")
    norm = sami.normalize(
        data,
        row=p.row,
        transform=p.transform,
        scale=p.scale,
        reference=_resolve_feature(data, p.reference),
    )
    out = project.results_dir("normalise")
    save_msidata(norm, out / "data")
    return StepResult("normalise", {"data": str(out / "data")}, {"n_features": norm.n_features})


def _cluster_input(project: Project, samples: str) -> MSIData:
    data = load_step_data(project, "normalise")
    chosen = split_list(samples)
    if chosen:
        unknown = set(chosen) - set(data.sections)
        if unknown:
            raise KeyError(f"Unknown sections: {', '.join(sorted(unknown))}")
        data = data.subset(sections=chosen)
    return data


def _attach_counts(project: Project, adata) -> None:
    """Add the loaded (pre-transform) intensities as ``adata.layers["counts"]``.

    Markers use it to decide whether a molecule was *detected* in a pixel (non-zero). After
    sqrt/cbrt/glog transforms or scaling, zeros in ``X`` are no longer zero, so detection must
    come from the measured intensities. Pixels are matched on ``(section, x, y)``.
    """
    raw = load_step_data(project, "load")
    keys = ["section", "x", "y"]
    left = adata.obs[keys].astype({"section": str}).reset_index(drop=True)
    right = raw.pixels[keys].copy()
    right["_i"] = np.arange(raw.n_pixels)
    idx = left.merge(right, on=keys, how="left")["_i"]
    if idx.isna().any():
        return  # can't match every pixel; markers fall back to X
    try:
        cols = [raw.feature_index(f) for f in adata.var_names]
    except KeyError:
        return
    adata.layers["counts"] = raw.values[np.ix_(idx.to_numpy(dtype=np.int64), cols)]


def _run_sami_cluster(project: Project, p: Any, progress: ProgressFn | None, **_: Any):
    sami = _core("sami")
    data = _cluster_input(project, p.samples)
    harmony = bool(p.harmony and data.n_sections > 1)
    adata = sami.cluster(
        data,
        resolution=p.resolution,
        harmony=harmony,
        random_state=p.random_state,
        progress=progress,
    )
    _attach_counts(project, adata)
    out = project.results_dir("cluster")
    path = out / "clusters.h5ad"
    adata.write_h5ad(path)
    counts = adata.obs["cluster"].astype(str).value_counts()
    return StepResult(
        "cluster",
        {"clusters": str(path)},
        {
            "n_clusters": int(counts.size),
            "sections": [str(s) for s in pd.unique(adata.obs["section"].astype(str))],
            "harmony": harmony,
            "clusters": [str(c) for c in adata.obs["cluster"].astype("category").cat.categories],
        },
    )


def run_transfer(
    project: Project, target_sections: list[str], progress: ProgressFn | None = None
) -> Path:
    """Transfer the clusters found in Cluster onto other sections ("another sample")."""
    import anndata as ad

    sami = _core("sami")
    ref_path = project.output("cluster", "clusters")
    if ref_path is None:
        raise StepLocked("Run Cluster first.")
    reference = ad.read_h5ad(ref_path)
    target = load_step_data(project, "normalise").subset(sections=target_sections)
    result = sami.transfer_clusters(reference, target, progress=progress)
    _attach_counts(project, result)
    path = project.results_dir("cluster") / f"transfer_{_safe_name('_'.join(target_sections))}.h5ad"
    result.write_h5ad(path)
    rec = project.record("cluster")
    if rec is not None:
        rec.setdefault("outputs", {})["transfer"] = str(path.relative_to(project.root))
        rec.setdefault("summary", {})["transfer_sections"] = list(target_sections)
        project.save()
    return path


def _run_sami_markers(project: Project, p: Any, progress: ProgressFn | None, **_: Any):
    import anndata as ad

    sami = _core("sami")
    adata = ad.read_h5ad(project.output("cluster", "clusters"))
    group_a = split_list(p.group_a)
    if not group_a:
        raise ValueError("Choose at least one cluster to compare (click one in the canvas).")
    group_b = None if p.group_b.strip().lower() in ("", "rest") else split_list(p.group_b)
    known = set(adata.obs["cluster"].astype(str))
    unknown = (set(group_a) | set(group_b or [])) - known
    if unknown:
        raise KeyError(f"Unknown clusters: {', '.join(sorted(unknown))}")
    report(progress, 0, 1, "Testing features")
    markers = sami.find_markers(
        adata,
        group_a,
        group_b,
        min_abundance=p.min_abundance,
        min_prevalence=p.min_prevalence,
        fdr=p.fdr,
        top=p.top or None,
    )
    out = project.results_dir("markers")
    path = out / "markers.csv"
    markers.to_csv(path, index=False)
    n_sig = int(markers["significant"].sum()) if "significant" in markers else len(markers)
    return StepResult("markers", {"markers": str(path)}, {"n_significant": n_sig})


def _run_sami_pathways(project: Project, p: Any, progress: ProgressFn | None, **_: Any):
    sami = _core("sami")
    markers = read_result_table(project.output("markers", "markers"))
    libraries = pathway_libraries(progress)
    result = sami.enrich_pathways(markers, libraries=libraries, fdr=p.fdr, progress=progress)
    out = project.results_dir("pathways")
    path = out / "pathways.csv"
    result.to_csv(path, index=False)
    if "significant" in result:
        n_sig = int(result["significant"].astype(bool).sum())
    else:
        n_sig = int((result["padj"] <= p.fdr).sum()) if "padj" in result else len(result)
    return StepResult(
        "pathways",
        {"pathways": str(path)},
        {"n_enriched": n_sig, "library": _library_provenance(libraries)},
    )


def _library_provenance(directory: Path) -> dict[str, Any]:
    """Which pathway library produced the results (recorded in project.json and methods text).

    The Zenodo (SAMI) and MetaboAnalyst libraries differ, so results are only reproducible if
    the library is recorded with them.
    """
    import json

    info: dict[str, Any] = {"source": directory.name, "path": str(directory)}
    manifest = directory / "manifest.json"
    if manifest.exists():
        m = json.loads(manifest.read_text(encoding="utf-8"))
        info["converted"] = m.get("converted")
        info["md5"] = {k: v.get("md5") for k, v in (m.get("files") or {}).items()}
    return info


# ======================================================================= dispatcher
_RUNNERS: dict[tuple[str, str], Callable[..., StepResult]] = {
    ("mv3d", "load"): _run_load,
    ("mv3d", "normalise"): _run_mv3d_normalise,
    ("mv3d", "align"): _run_mv3d_align,
    ("mv3d", "fill"): _run_mv3d_fill,
    ("mv3d", "atlas"): _run_mv3d_atlas,
    ("sami", "load"): _run_load,
    ("sami", "normalise"): _run_sami_normalise,
    ("sami", "cluster"): _run_sami_cluster,
    ("sami", "markers"): _run_sami_markers,
    ("sami", "pathways"): _run_sami_pathways,
}


def run_step(
    project: Project,
    step: str,
    params: Any | None = None,
    *,
    progress: ProgressFn | None = None,
    feature: str | None = None,
) -> StepResult:
    """Run one step and record it in the project.

    Args:
        project: the open project.
        step: a step of ``project.analysis`` (see ``metavision_studio.project.PIPELINES``).
        params: the step's params dataclass. Defaults are used if omitted.
        progress: ``progress(done, total, message)``. Raise ``Cancelled`` from it to stop.
        feature: the molecule currently selected in the GUI (used by Fill and the export).

    Raises:
        StepError: the step failed. The failure is also recorded in ``project.json``.
        Cancelled: the user cancelled. Nothing is recorded.
    """
    analysis = project.analysis
    if (analysis, step) not in _RUNNERS:
        raise ValueError(f"{analysis} has no step {step!r}")
    if params is None:
        params = PARAMS[analysis][step]()
    if (blocker := project.blocking_step(step)) is not None:
        raise explain(step, StepLocked(f"Run {STEP_TITLES[blocker]} first."))
    started = _now()
    pdict = params_to_dict(params)
    try:
        result = _RUNNERS[(analysis, step)](project, params, progress, feature=feature)
        # Last cancellation point. Steps whose heavy part has no checkpoints (R, Wilcoxon,
        # file writes) can still be cancelled here, before the run is recorded.
        report(progress, 1, 1, "Saving")
    except Cancelled:
        raise
    except Exception as exc:
        err = explain(step, exc)
        project.mark_failed(step, pdict, f"{err.message} {err.hint}".strip())
        raise err from exc
    project.mark_done(step, pdict, result.outputs, summary=result.summary, started=started)
    return result
