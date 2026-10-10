# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

The 2024 desktop app has been rebuilt as the `metavision-studio` package: a tested core
library plus a napari plugin.

### Added
- **napari plugin** with the workflow from [docs/ux-design.md](docs/ux-design.md):
  - Start page with recent projects and a one-click example dataset, and a one-screen
    New Project dialog.
  - Project card, a single molecule picker, and an accordion of steps showing their status.
  - Insights panel with linked charts, background jobs with progress and Cancel, and inline
    errors with a "copy report" button.
- **MetaVision3D pipeline** (`metavision_studio.mv3d`): normalise (TIC + section median),
  section quality check, ECC alignment, imputation, interpolation, and NIfTI/TIFF/CSV export.
- **SAMI pipeline** (`metavision_studio.sami`):
  - Normalisation (Sum/Median/Comp/PQN, log/sqrt/cbrt transforms, scaling) and Leiden
    clustering, with optional Harmony.
  - Cluster transfer between samples.
  - Markers between any cluster groups, or case vs control.
  - Pathway over-representation through R.
- **Data loading** (`metavision_studio.io`): CSV, Parquet and imzML; automatic column
  detection; multi-omics merging by pixel; vectorised float32 rasterisation; readable lipid
  names (`LPA.18.1._1` → `LPA(18:1)`).
- **Projects** (`project.json`) recording parameters, outputs, software versions and
  fingerprints. Results go out of date when an earlier step's settings change or an input
  file is edited or replaced. Each analysis keeps its own results (`results/<analysis>/`).
  The pathway library used is recorded with the results. **Copy methods text** generates a
  methods paragraph from all of this.
- **Example datasets** from Zenodo (`metavision-studio datasets` / `fetch`), with checksums
  verified.
- **Pathway libraries** converted to Parquet on first use (`metavision-studio prepare-libraries`).
- **R through `Rscript`**: rpy2 and the hardcoded R install path are gone.
- **CLI:** `metavision-studio gui | doctor | datasets | fetch | install-r-deps | prepare-libraries`.
- **Tooling:** tests (pytest, pytest-qt), linting (ruff), pre-commit hooks, CI on Windows,
  macOS and Linux with R and a headless GUI job, `CITATION.cff`, `NOTICE.md` and contributor docs.

### Fixed (relative to the reference implementations)
- Marker p-values now use correct Benjamini–Hochberg adjustment. The old `p·n/rank` had no
  monotonicity and no cap at 1.
- Alignment is computed from **normalised** data and cached by content and settings, not by
  file name.
- When ECC fails, the section keeps its position. Previously a uint8-rescaled image was
  passed on as the next reference.
- Empty sections no longer break alignment, and the reference and the applied warps use one
  centring rule.
- Sections are ordered naturally (`2` before `10`).
- NIfTI files store the real voxel size in the affine; the old files had pixdim 1, 1, 1.
- No float16 overflow for intensities above 65,504.
- Normalisation no longer modifies the input table in place.
- Lipid pathway enrichment returns results, and pathway direction uses all measured
  compounds (upstream's newer method).
- Cluster transfer uses only the features both samples share.
- `GroupMedianPQN` is fixed and Pareto scaling is implemented.

### Changed
- The 2024 customtkinter app moved to `legacy/` as a porting reference.

### Removed
- GraphPad Prism (`.pzfx`) and Excel cluster-table export.
- The committed SCiLS Lab licence key (also purged from git history), debug pickles and
  notebooks, `.DS_Store` files, and duplicate cached warp matrices.
