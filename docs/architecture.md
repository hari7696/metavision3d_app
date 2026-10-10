# Architecture

```
┌──────────────────────────── napari plugin (widgets/) ────────────────────────────┐
│ StudioWidget: start page · project card · molecule picker · step list ·         │
│ insights panel · status bar                                                      │
└───────────────┬──────────────────────────────────────────────────────────────────┘
                │ calls
┌───────────────▼───────────── workflows/ (no Qt) ─────────────────────────────────┐
│ One runner per step: load inputs from the Project, call core, save outputs,      │
│ record the run in project.json. Step parameter dataclasses live here.            │
└───────┬──────────────────────────┬──────────────────────────┬────────────────────┘
        │                          │                          │
┌───────▼──────┐  ┌────────────────▼─────────┐  ┌─────────────▼───────────────┐
│ io/          │  │ mv3d/                    │  │ sami/                       │
│ MSIData,     │  │ normalise, align, fill,  │  │ normalise, cluster,         │
│ readers,     │  │ atlas, evaluate          │  │ transfer, markers, pathways │
│ raster       │  │                          │  │ (pathways → rbridge → R)    │
└──────────────┘  └──────────────────────────┘  └─────────────────────────────┘
   project.py (manifest, fingerprints) · datasets.py (Zenodo) · _progress.py · methods.py
```

**Rules**

- `io`, `mv3d`, `sami`, `workflows`, `project` never import Qt or napari. They are usable in
  notebooks, scripts and on HPC.
- Core functions are **pure**: they take data, return new data, and never modify inputs or
  write files. Persistence happens in `workflows`.
- Long-running functions take `progress: ProgressFn | None = None`
  (`progress(done, total, message)`). Raising `Cancelled` from the callback stops them.

## Shared types

| Type | Module | What |
|---|---|---|
| `MSIData` | `io.data` | pixels (`x`, `y`, `section`), float32 `values` (pixels × features), `features` (`name`, `mz`, `omics`) |
| `Raster` | `io.raster` | maps pixels to a `(sections, rows, cols)` stack. `raster.stack(column)` returns a float32 stack |
| `Project` | `project` | folder + `project.json`: inputs, settings, per-step params/outputs/fingerprints, status |

## Core API contract

### `mv3d`

```python
normalize(data, method: Literal["tic+section", "tic", "section", "none"] = ...) -> MSIData
remove_low_prevalence(data, min_prevalence=0.1) -> tuple[MSIData, list[str]]
reference_feature(data) -> str                                  # most prevalent feature
section_quality(data) -> pd.DataFrame                           # section, n_pixels, total, flagged, reason

@dataclass Alignment: reference: str; warps: np.ndarray (n_sections, 2, 3);
                      scores: np.ndarray (n_sections,); failed: list[int]
compute_alignment(data, raster, *, reference=None, max_iter=5000, eps=1e-10,
                  progress=None) -> Alignment
apply_alignment(stack, alignment) -> np.ndarray
save_alignment(alignment, path) / load_alignment(path) -> Alignment

impute(stack, *, radius=1, progress=None) -> np.ndarray
interpolate(stack, *, n_insert=1, progress=None) -> np.ndarray
voxel_size(*, pixel_size_um, thickness_um, gap_um, n_insert) -> tuple[float, float, float]  # z, x, y (µm)
to_nifti(stack, *, pixel_size_um, thickness_um, gap_um, n_insert) -> nibabel.Nifti1Image
adjacent_similarity(stack) -> pd.DataFrame                      # per adjacent pair: corr, ssim, mse
describe(step, params) -> str                                   # methods-text sentence

# also: prevalence(data), section_median_factors(data), paired_similarity(a, b),
# blank_sections(data, sections)  ← "exclude section": keeps z-spacing, imputation fills it
# shell_mask(stack, ...) / drop_masked_pixels(data, raster, mask)  ← off-tissue removal
```

### `sami`

```python
normalize(data, *, row: Literal["sum", "median", "comp", "pqn", "none"] = "sum",
          transform: Literal["log2", "log10", "sqrt", "cbrt", "none"] = "log2",
          scale: Literal["none", "auto", "pareto", "range"] = "none",
          reference: str | None = None) -> MSIData
cluster(data, *, resolution=1.0, harmony=False, random_state=7, progress=None) -> AnnData
        # obs: section, x, y, cluster (categorical str); obsm: X_umap, spatial
transfer_clusters(reference: AnnData, target: MSIData, *, progress=None) -> AnnData
find_markers(adata, group_a, group_b=None, *, min_abundance=0.1, min_prevalence=0.1,
             fdr=0.05, top=50, control=None) -> pd.DataFrame
        # feature, name, omics, mean_a, mean_b, log2fc, pvalue, padj, significant
enrich_pathways(markers, *, libraries: Path | None = None, fdr=0.05, progress=None) -> pd.DataFrame
        # libraries default: library_dir(); prepare_libraries() downloads + converts on first use
        # pathway, library, omics, hits, size, pvalue, padj, direction, members
describe(step, params) -> str
```

## Project layout on disk

```
<project>/project.json
<project>/results/load/data/                   # MSIData: pixels.parquet, values.npy,
<project>/results/normalise/data/              #          features.parquet, meta.json
<project>/results/align/alignment.npz
<project>/results/atlas/<feature>.nii.gz
<project>/results/cluster/clusters.h5ad
<project>/results/markers/markers.csv
<project>/results/pathways/pathways.csv
```

## Licensing of ported code

Modules adapted from MetaVision3D or SAMI carry a header naming the source repository and
commit, the copyright holder, the licence (CC BY-NC-SA 4.0), and a summary of the changes. See
[NOTICE.md](../NOTICE.md).
