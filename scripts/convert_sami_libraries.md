# Pathway libraries for SAMI enrichment

SAMI's pathway enrichment matches marker names to MetaboAnalyst's compound database and
tests them against SMPDB pathways (metabolites and glycans) or lipid sub-classes (lipids). Six
tables are needed:

| Table | What |
|---|---|
| `compound_db` | compound names and IDs (HMDB, KEGG, …) |
| `syn_nms` | synonyms per compound (by row of `compound_db`) |
| `smpdb_pathway` | SMPDB pathways: name and members |
| `lipid_compound_db`, `lipid_syn_nms` | the lipid equivalents |
| `sub_class` | lipid sub-classes: name and members |

They are distributed as `.qs` files. MetaVision Studio converts them **once** to Parquet with
`src/metavision_studio/R/convert_libraries.R`, and enrichment (`R/ora.R`) reads only the Parquet
tables. Converted libraries live in `<cache>/sami-lib-parquet/<source>/` (on Windows,
`%LOCALAPPDATA%\metavision-studio\metavision-studio\Cache\sami-lib-parquet\`), and
`sami.libraries.library_dir()` finds them. Zenodo versions are preferred when both exist.

## Option 1: current MetaboAnalyst libraries (automatic)

```bash
metavision-studio install-r-deps          # jsonlite, nanoparquet (+ qs2, see below)
python scripts/convert_sami_libraries.py metaboanalyst
# or from Python:  metavision_studio.sami.prepare_libraries("metaboanalyst")
```

This downloads the six files from `https://www.metaboanalyst.ca/resources/libs/`, the same
location SAMI's R code downloads missing sets from. They are in the `qs2` format, which any
recent R reads with the CRAN package `qs2`. The libraries are newer than the ones used in the SAMI
paper (for example, 50,273 versus 23,168 compounds), so results can differ slightly.

## Option 2: the exact SAMI (Zenodo) libraries

`lib.zip` from Ma X., Zenodo, doi:[10.5281/zenodo.15224641](https://doi.org/10.5281/zenodo.15224641)
(CC BY 4.0) holds the versions used by SAMI. They are in the **legacy `qs` format**. The `qs`
package has been archived on CRAN, and its compiled code does not load in R ≥ 4.5. To convert:

1. Install R 4.4.x (Windows: `R-4.4.3-win.exe /CURRENTUSER` from
   <https://cloud.r-project.org/bin/windows/base/old/4.4.3/>; it can live alongside R 4.6).
2. Run

   ```bash
   python scripts/convert_sami_libraries.py zenodo --rscript "C:/path/to/R-4.4.3/bin/Rscript.exe"
   ```

   This downloads `lib.zip` with checksum verification, installs `qs`, `nanoparquet` and
   `jsonlite` into a private library from the Posit Package Manager snapshot of 2024-10-01 (which
   still has `qs` binaries), and converts.

Note: in the Zenodo set, `syn_nms` covers 19,837 compounds while `compound_db` has 23,168 rows. As
in SAMI, a synonym match at position *i* resolves to `compound_db` row *i*. About 96% of
compounds have their own name among their synonyms at the same position, so a few synonym-only
matches may resolve to a neighbouring compound. This is SAMI's own behaviour with these files;
exact-name matches are unaffected.

## Redistribution

The Zenodo libraries are CC BY 4.0, so converted copies may be redistributed with attribution
to Ma X. and the DOI above. The MetaboAnalyst downloads are MetaboAnalyst resources. They are
fetched from metaboanalyst.ca at conversion time and not redistributed by this project.
