# Convert SAMI / MetaboAnalyst pathway-enrichment libraries from .qs to Parquet.
#
# Adapted from SAMI (https://github.com/XinBiostats/SAMI, commit 80da10b).
# © 2023 University of Florida Research Foundation, Inc. Licensed under CC BY-NC-SA 4.0
# (https://creativecommons.org/licenses/by-nc-sa/4.0/).
# Portions © Xia Lab (MetaboAnalystR), MIT licence: the library layout (compound_db,
# syn_nms, msets) follows MetaboAnalystR.
# Changes: a stand-alone converter. SAMI read the .qs files on every enrichment run (needing
# the `qs` package, which has been removed from CRAN). Here they are converted once to Parquet,
# so enrichment needs only base R + nanoparquet.
#
# Usage:  Rscript convert_libraries.R <input_dir> <output_dir>
#
# Each input file is read with qs2 (current MetaboAnalyst downloads, magic 0b0e0ac1) or with
# the legacy qs package (SAMI's Zenodo lib.zip, magic 0b0e0a0c; needs R <= 4.4 because qs is
# archived). Outputs:
#   compound_db.parquet, lipid_compound_db.parquet   (idx, name, hmdb_id, kegg_id, ...)
#   syn_nms.parquet, lipid_syn_nms.parquet           (idx, synonym), idx = compound row (1-based)
#   smpdb_pathway.parquet, sub_class.parquet         (id, name, member, reference)
#   manifest.json

args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 2) {
  message("Usage: Rscript convert_libraries.R <input_dir> <output_dir>")
  quit(status = 2)
}
in_dir <- normalizePath(args[1], mustWork = TRUE)
out_dir <- args[2]
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
out_dir <- normalizePath(out_dir, mustWork = TRUE)

suppressPackageStartupMessages(library(nanoparquet))

read_any_qs <- function(path) {
  magic <- readBin(path, "raw", n = 4)
  if (identical(magic, as.raw(c(0x0b, 0x0e, 0x0a, 0xc1)))) {
    if (!requireNamespace("qs2", quietly = TRUE)) stop("qs2 is needed to read ", basename(path))
    return(qs2::qs_read(path))
  }
  if (identical(magic, as.raw(c(0x0b, 0x0e, 0x0a, 0x0c)))) {
    if (!requireNamespace("qs", quietly = TRUE)) {
      stop(basename(path), " is in the legacy qs format; it needs the archived 'qs' package ",
           "(R <= 4.4). See scripts/convert_sami_libraries.md.")
    }
    return(qs::qread(path))
  }
  stop(basename(path), " is not a qs/qs2 file")
}

as_chr_df <- function(df) {
  df <- as.data.frame(df, stringsAsFactors = FALSE)
  for (col in names(df)) {
    if (is.factor(df[[col]]) || is.list(df[[col]])) df[[col]] <- as.character(df[[col]])
  }
  rownames(df) <- NULL
  df
}

files <- list()
convert_compounds <- function(stem) {
  path <- file.path(in_dir, paste0(stem, ".qs"))
  if (!file.exists(path)) return(invisible(NULL))
  db <- as_chr_df(read_any_qs(path))
  db <- cbind(idx = seq_len(nrow(db)), db)
  write_parquet(db, file.path(out_dir, paste0(stem, ".parquet")))
  files[[stem]] <<- list(rows = nrow(db), source = basename(path),
                         md5 = unname(tools::md5sum(path)))
  cat(stem, ":", nrow(db), "compounds\n")
}

convert_synonyms <- function(stem) {
  path <- file.path(in_dir, paste0(stem, ".qs"))
  if (!file.exists(path)) return(invisible(NULL))
  syn <- read_any_qs(path)
  syns <- syn$syns.list
  lens <- lengths(syns)
  long <- data.frame(idx = rep.int(seq_along(syns), lens),
                     synonym = as.character(unlist(syns, use.names = FALSE)),
                     stringsAsFactors = FALSE)
  long <- long[!is.na(long$synonym) & nzchar(long$synonym), ]
  write_parquet(long, file.path(out_dir, paste0(stem, ".parquet")))
  files[[stem]] <<- list(rows = nrow(long), compounds = length(syns), source = basename(path),
                         md5 = unname(tools::md5sum(path)))
  cat(stem, ":", length(syns), "compounds,", nrow(long), "synonyms\n")
}

convert_sets <- function(stem) {
  path <- file.path(in_dir, paste0(stem, ".qs"))
  if (!file.exists(path)) return(invisible(NULL))
  sets <- as_chr_df(read_any_qs(path))
  keep <- intersect(c("id", "name", "member", "reference"), names(sets))
  sets <- sets[, keep, drop = FALSE]
  sets$member <- iconv(sets$member, from = "UTF-8", to = "UTF-8", sub = "")
  write_parquet(sets, file.path(out_dir, paste0(stem, ".parquet")))
  files[[stem]] <<- list(rows = nrow(sets), source = basename(path),
                         md5 = unname(tools::md5sum(path)))
  cat(stem, ":", nrow(sets), "sets\n")
}

for (s in c("compound_db", "lipid_compound_db")) convert_compounds(s)
for (s in c("syn_nms", "lipid_syn_nms")) convert_synonyms(s)
for (s in c("smpdb_pathway", "sub_class")) convert_sets(s)

required <- c("compound_db", "syn_nms", "smpdb_pathway")
missing <- setdiff(required, names(files))
if (length(missing) > 0) {
  message("Missing required libraries in ", in_dir, ": ", paste(missing, collapse = ", "))
  quit(status = 1)
}

manifest <- list(
  format = 1L,
  converted = format(Sys.time(), "%Y-%m-%dT%H:%M:%S%z"),
  r_version = R.version.string,
  input_dir = in_dir,
  files = files
)
writeLines(jsonlite::toJSON(manifest, auto_unbox = TRUE, pretty = TRUE),
           file.path(out_dir, "manifest.json"), useBytes = TRUE)
cat("Wrote", length(files), "tables to", out_dir, "\n")
