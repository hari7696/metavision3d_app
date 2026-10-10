# Roadmap

This is the plan for rebuilding the 2024 desktop app (`legacy/`) into the `metavision-studio`
napari plugin. Each phase ends with tests passing on Windows, macOS and Linux.

## Phase 0: Foundation ✅

- [x] Purge the committed SCiLS licence key and junk from git history
- [x] `src/` package, Hatch env on Python 3.14, ruff, pytest, pre-commit, CI
- [x] R via `Rscript` subprocess (`rbridge`), `doctor` command
- [x] README with credits and citations, `CITATION.cff`, contributor docs

## Phase 1: Data loading (`io`) ✅

- [x] One validated pixel-table model: `x`, `y`, section ID, features, with explicit column mapping
      (replaces the hardcoded metadata column list and "everything after `region`" convention)
- [x] CSV and Parquet readers with encoding detection
- [x] imzML reader (optional `pyimzml`)
- [x] Natural sort of section IDs (`"2" < "10"`)
- [x] Rasterise with vectorised indexing in float32 (no float16 overflow above 65 504)
- [x] Synthetic fixtures generated in tests; example datasets fetched from Zenodo

## Phase 2: MetaVision3D core (`mv3d`) ✅

Port from `legacy/visionApp/MetaVision3D/` and upstream HEAD (a108fe8, 2025-03-14), fixing:

- [x] Normalisation must not mutate the input DataFrame (`MetaNorm3D.totalsum_norm` did)
- [x] Compute warp matrices from **normalised** data. Cache them keyed on a hash of the data and
      parameters, in the project folder (not next to the input CSV, keyed by filename)
- [x] Use one centring rule for the reference and the applied warp (`ceil` vs `int` gave a 1-px offset)
- [x] When ECC fails, keep the previous transform (identity), not the uint8-rescaled image. Guard against all-zero slices
- [x] Vectorise interpolation (`np.interp` / `scipy` along z) and imputation
- [x] NIfTI: write the voxel size **in the affine** (x/y = pixel size in µm,
      z = (thickness + gap) / (1 + inserted sections)). The 2024 files have pixdim 1,1,1
- [x] Expose upstream preprocessing the app lacked: shell removal, low-prevalence filtering,
      inferior-tissue removal, and evaluation metrics (ECC/SSIM/MSE)
- [x] Batch over all compounds. Export aligned, imputed or interpolated stacks (NIfTI, TIFF, CSV with coordinates)

## Phase 3: SAMI core (`sami`) ✅

Port from `legacy/visionApp/SAMI/` and upstream (2025-03 re-upload, which is newer), fixing:

- [x] **Benjamini–Hochberg**: `adj_pvalue` computes `p·n/rank` with no monotonicity and no cap at 1.
      Use `scipy.stats.false_discovery_control`. This is also in upstream, so report it to Xin
- [x] Pooling: fix the blind-merge no-op (`==` instead of `=`). Build `obs` from all files, not just the last one
- [x] Clustering: restore `ax=axs` in `plot_cluster` (region labels went to an empty figure)
- [x] Integration: subset to shared `var_names` before `sc.tl.ingest`
- [x] Normalisation: implement or remove `GroupMedianPQN` (undefined globals) and `ParetoNorm` (undefined)
- [x] Markers: adopt upstream `mean_a`/`mean_b`. Revisit log2FC on already-logged data. Replace the O(n²) concat
- [x] Pathways: adopt upstream's newer direction method (`log2(Σmean_a/Σmean_b)` with a neutral band).
      Fix the lipid branch (`GetFinalNameMap` without `lib_folder`, so lipid ORA is likely always empty)
- [x] Replace filename parsing (`region_modality_res.h5ad`) with a project manifest

## Phase 4: R integration ✅ (SCiLS export pending)

- [x] Port `MetabAnalystR.R` (MetaboAnalystR-derived, MIT) to run under `rbridge`, exchanging
      Parquet/JSON. No `sink()` leaks, no stray `.rda`/`.rds` files written to the working directory
- [x] The pathway libraries (`compound_db`, `syn_nms`, `lipid_*`, `smpdb_pathway`, `sub_class`)
      are `.qs` files from Zenodo 10.5281/zenodo.15224641. **`qs` has been removed from CRAN**, so
      convert them once to Parquet and host or cache the converted copies
- [ ] SCiLS Lab export as an optional feature: licence key from an environment variable or the OS
      keyring (never on disk), R code passed as arguments not f-strings, and errors propagated
      instead of reported as success

## Phase 5: napari plugin ✅

- [x] Project folder + manifest (`project.json`): inputs, parameters, outputs, versions, so runs
      are reproducible and resumable
- [x] Background workers (`napari.qt.threading`) with progress, cancel and real error messages.
      No blocking UI and no Tk-style cross-thread widget calls
- [x] MetaVision3D widget: load → normalise → align → impute/interpolate → 3D view in napari's
      own canvas (replaces the detached vedo window) → export
- [x] SAMI widgets: normalise, pool, group, cluster (UMAP + spatial), integrate, markers, pathways
- [x] Steps enable only when their inputs exist (the old app crashed when steps ran out of order)

## Phase 5½: Polish (next)

- [ ] SCiLS Lab `.slx` import (optional; needs Bruker's SCiLSLabClient R package and a licence)
- [ ] Markers: choose clusters from dropdowns and click-to-fill from the canvas; show a p-value
      floor line on the volcano plot when values underflow
- [ ] Leiden via the `igraph` flavour (about 5× faster; agrees with `leidenalg` at ARI 0.72, so it
      needs validating first)
- [ ] Glycan IDs (`G00014`) in the AD/WT data need annotation before pathway matching
- [ ] Host the converted SAMI pathway libraries (CC BY 4.0) as a release asset, so users get the
      exact published versions without an old R

## Phase 6: Release

- [ ] Docs site with a tutorial on the public example dataset
- [ ] PyPI release, napari-hub listing, Zenodo DOI for MetaVision Studio
- [ ] Remove `legacy/`
