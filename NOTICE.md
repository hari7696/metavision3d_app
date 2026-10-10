# Notices and attribution

MetaVision Studio is licensed under the
[Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International](LICENSE) licence
(CC BY-NC-SA 4.0). It contains material adapted from the works below. As the licence
requires, each is credited here with its copyright notice and licence, and the changes we
made are described. Ported source files repeat this information in their headers.

## MetaVision3D

- **Source:** <https://github.com/XinBiostats/MetaVision3D>, commit
  [`a108fe8`](https://github.com/XinBiostats/MetaVision3D/commit/a108fe823641bde1f4730c2ed0442031f30cd32c)
  (2025-03-14)
- **Author:** Xin Ma
- **Copyright:** © 2023 University of Florida Research Foundation, Inc. All Rights Reserved.
- **Licence:** CC BY-NC-SA 4.0, <https://creativecommons.org/licenses/by-nc-sa/4.0/>
- **Used in:** `src/metavision_studio/mv3d/`
- **Changes:** restructured into pure functions without file side effects; vectorised
  rasterisation, imputation and interpolation; bug fixes listed in
  [docs/roadmap.md](docs/roadmap.md) (natural section ordering, consistent centring,
  alignment from normalised data, NIfTI voxel size in the affine, ECC-failure handling); added
  progress reporting and cancellation.

## SAMI (Spatial Augmented Multiomics Interface)

- **Source:** <https://github.com/XinBiostats/SAMI>, commit
  [`80da10b`](https://github.com/XinBiostats/SAMI/commit/80da10bc7002910d52e53ca33e52c2bf7c92bde4)
  (2025-04-15)
- **Author:** Xin Ma
- **Copyright:** © 2023 University of Florida Research Foundation, Inc. All Rights Reserved.
- **Licence:** CC BY-NC-SA 4.0, <https://creativecommons.org/licenses/by-nc-sa/4.0/>
- **Used in:** `src/metavision_studio/sami/`, `src/metavision_studio/R/`
- **Changes:** restructured into pure functions without file side effects; correct
  Benjamini–Hochberg adjustment; arbitrary cluster-group marker comparisons; R invoked
  through `Rscript` instead of rpy2; bug fixes listed in [docs/roadmap.md](docs/roadmap.md).

## MetaboAnalystR

- **Source:** <https://github.com/xia-lab/MetaboAnalystR>
- **Copyright:** © Xia Lab
- **Licence:** MIT
- **Used in:** pathway over-representation functions in `src/metavision_studio/R/`, by way of SAMI.

## Pathway libraries (downloaded on demand)

On first use, the pathway step downloads the compound and pathway tables (HMDB/SMPDB-derived
compound database, synonyms, lipid classes) and converts them to Parquet in the user cache.
By default they come from MetaboAnalyst (<https://www.metaboanalyst.ca>, Xia Lab), the same
URLs SAMI's R code downloads from; they are fetched by the user's installation and not
redistributed by this project. The exact library versions published with SAMI (Zenodo,
CC BY 4.0, below) can be converted instead with `scripts/convert_sami_libraries.py`, and
are used in preference when present.

## Datasets (downloaded on demand, not redistributed in this repository)

- MetaVision3D MALDI data: Ma X., Zenodo, <https://doi.org/10.5281/zenodo.14212427>, CC BY 4.0
- SAMI datasets and pathway libraries: Ma X., Zenodo,
  <https://doi.org/10.5281/zenodo.15224641>, CC BY 4.0

## The 2024 desktop app (`legacy/`)

The `legacy/` folder holds the original app, which contains verbatim copies of MetaVision3D
and SAMI under the same licence and copyright. It is kept only as a porting reference.
