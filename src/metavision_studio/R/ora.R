# Over-representation analysis (ORA) of marker molecules against SMPDB pathways or lipid
# sub-classes.
#
# Adapted from SAMI (https://github.com/XinBiostats/SAMI, commit 80da10b), MetabAnalystR.R.
# © 2023 University of Florida Research Foundation, Inc. Licensed under CC BY-NC-SA 4.0
# (https://creativecommons.org/licenses/by-nc-sa/4.0/).
# Portions © Xia Lab (MetaboAnalystR), MIT licence: CrossReferencing /
# MetaboliteMappingExact (name + synonym matching), SetCurrentMsetLib and
# CalculateHyperScore (hypergeometric test, Holm and FDR adjustment).
#
# Changes: one self-contained function with no global state (no mSet / current.msetlib
# globals, no `<<-`). Libraries are read from Parquet (convert_libraries.R) instead of qs. The
# request and results are files passed on the command line. Nothing is written to the working
# directory (upstream wrote qvec__checking.rda, cmpd.db__checking.rda, tosend.rds and sink
# output). Per-comparison problems are returned as messages instead of being printed and
# swallowed. P-values are not rounded to 3 significant digits.
#
# Usage:  Rscript ora.R <request.json> <output_dir>
#
# request.json:
#   { "library_dir": "...", "min_set_size": 2,
#     "comparisons": [ { "id": "3", "lipid": false,
#                        "queries": ["Taurine", ...],        # marker names (ORA input)
#                        "background": ["Taurine", ...] } ]   # all measured names (mapping only)
#   }
# Outputs in <output_dir>:
#   results.parquet  comparison, set_id, pathway, total, expected, hits, raw_p, holm_p, fdr,
#                    all_compounds, overlap_compounds
#   mapping.parquet  comparison, role, query, matched, hmdb_id, kegg_id
#   messages.json    [{comparison, level, message}]

suppressPackageStartupMessages({
  library(jsonlite)
  library(nanoparquet)
})

args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 2) {
  message("Usage: Rscript ora.R <request.json> <output_dir>")
  quit(status = 2)
}
req <- fromJSON(args[1], simplifyVector = FALSE)
out_dir <- args[2]
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

lib_dir <- req$library_dir
min_set_size <- if (is.null(req$min_set_size)) 2L else as.integer(req$min_set_size)

read_lib <- function(stem) {
  path <- file.path(lib_dir, paste0(stem, ".parquet"))
  if (!file.exists(path)) stop("Pathway library table not found: ", path)
  as.data.frame(read_parquet(path), stringsAsFactors = FALSE)
}

# Cache tables per branch so each library is read once per run.
libs <- list()
get_branch <- function(lipid) {
  key <- if (lipid) "lipid" else "metab"
  if (!is.null(libs[[key]])) return(libs[[key]])
  cmpd <- read_lib(if (lipid) "lipid_compound_db" else "compound_db")
  syn <- read_lib(if (lipid) "lipid_syn_nms" else "syn_nms")
  syn <- syn[order(syn$idx), ]
  sets <- read_lib(if (lipid) "sub_class" else "smpdb_pathway")
  # SetCurrentMsetLib: split members on "; ", keep sets with >= excludeNum members
  members <- lapply(iconv(sets$member, from = "UTF-8", to = "UTF-8", sub = ""),
                    function(x) unique(unlist(strsplit(x, "; ", fixed = TRUE))))
  names(members) <- sets$name
  keep <- lengths(members) >= min_set_size
  branch <- list(
    cmpd = cmpd,
    cmpd_lower = tolower(cmpd$name),
    syn_idx = syn$idx,
    syn_lower = tolower(syn$synonym),
    set_ids = sets$id[keep],
    members = members[keep]
  )
  branch$universe <- unique(unlist(branch$members, use.names = FALSE))
  libs[[key]] <<- branch
  branch
}

# MetaboliteMappingExact(q.type = "name"): exact name match, then the first compound
# (in library order) whose synonyms contain the query.
map_names <- function(queries, branch) {
  q <- tolower(queries)
  hit <- match(q, branch$cmpd_lower)
  todo <- which(is.na(hit))
  if (length(todo) > 0) {
    s <- match(q[todo], branch$syn_lower)
    hit[todo] <- branch$syn_idx[s]
  }
  matched <- branch$cmpd$name[hit]
  get_col <- function(col) if (col %in% names(branch$cmpd)) branch$cmpd[[col]][hit] else NA
  data.frame(query = queries, matched = matched,
             hmdb_id = get_col("hmdb_id"), kegg_id = get_col("kegg_id"),
             stringsAsFactors = FALSE)
}

# CalculateHyperScore: hypergeometric test of each set against the library universe.
hyper_score <- function(matched_names, branch) {
  ora_vec <- unique(matched_names[!is.na(matched_names)])
  ora_vec <- ora_vec[ora_vec %in% branch$universe]
  q_size <- length(ora_vec)
  if (q_size == 0) return(NULL)
  uniq_count <- length(branch$universe)
  hits <- lapply(branch$members, function(x) x[x %in% ora_vec])
  hit_num <- lengths(hits)
  if (sum(hit_num > 0) == 0) return(NULL)
  set_num <- lengths(branch$members)
  raw_p <- phyper(hit_num - 1, set_num, uniq_count - set_num, q_size, lower.tail = FALSE)
  res <- data.frame(
    set_id = branch$set_ids,
    pathway = names(branch$members),
    total = set_num,
    expected = q_size * (set_num / uniq_count),
    hits = hit_num,
    raw_p = raw_p,
    holm_p = p.adjust(raw_p, "holm"),
    fdr = p.adjust(raw_p, "fdr"),
    all_compounds = vapply(branch$members, paste, character(1), collapse = ";"),
    overlap_compounds = vapply(hits, paste, character(1), collapse = ";"),
    stringsAsFactors = FALSE
  )
  res <- res[res$hits > 0, ]
  res[order(res$raw_p), ]
}

results <- list()
mappings <- list()
messages <- list()
note <- function(id, level, msg) {
  messages[[length(messages) + 1]] <<- list(comparison = id, level = level, message = msg)
}

for (cmp in req$comparisons) {
  id <- as.character(cmp$id)
  lipid <- isTRUE(cmp$lipid)
  queries <- unique(as.character(unlist(cmp$queries)))
  background <- unique(as.character(unlist(cmp$background)))
  outcome <- tryCatch({
    branch <- get_branch(lipid)
    if (length(queries) == 0) {
      note(id, "info", "No marker molecules to test.")
    } else {
      qmap <- map_names(queries, branch)
      n_unmatched <- sum(is.na(qmap$matched))
      if (n_unmatched == length(queries)) {
        note(id, "warning", "None of the marker names matched the compound library.")
      } else if (n_unmatched > 0) {
        note(id, "info", sprintf("%d of %d marker names did not match the compound library: %s",
                                 n_unmatched, length(queries),
                                 paste(head(qmap$query[is.na(qmap$matched)], 10), collapse = ", ")))
      }
      bmap <- map_names(setdiff(background, queries), branch)
      mappings[[length(mappings) + 1]] <- rbind(
        cbind(comparison = id, role = "query", qmap, stringsAsFactors = FALSE),
        if (nrow(bmap)) cbind(comparison = id, role = "background", bmap, stringsAsFactors = FALSE)
      )
      res <- hyper_score(qmap$matched, branch)
      if (is.null(res)) {
        note(id, "warning", "No marker matched any set in the selected library.")
      } else {
        # Report compounds by the user's own feature names where they were matched.
        ok <- !is.na(qmap$matched)
        lookup <- setNames(qmap$query[ok], qmap$matched[ok])
        back <- function(s) {
          v <- strsplit(s, ";", fixed = TRUE)[[1]]
          paste(ifelse(v %in% names(lookup), lookup[v], v), collapse = ";")
        }
        res$all_compounds <- vapply(res$all_compounds, back, character(1), USE.NAMES = FALSE)
        res$overlap_compounds <- vapply(res$overlap_compounds, back, character(1), USE.NAMES = FALSE)
        results[[length(results) + 1]] <- cbind(comparison = id, res, stringsAsFactors = FALSE)
      }
    }
    TRUE
  }, error = function(e) {
    note(id, "error", conditionMessage(e))
    FALSE
  })
}

empty_results <- data.frame(
  comparison = character(), set_id = character(), pathway = character(), total = integer(),
  expected = numeric(), hits = integer(), raw_p = numeric(), holm_p = numeric(), fdr = numeric(),
  all_compounds = character(), overlap_compounds = character(), stringsAsFactors = FALSE
)
empty_map <- data.frame(comparison = character(), role = character(), query = character(),
                        matched = character(), hmdb_id = character(), kegg_id = character(),
                        stringsAsFactors = FALSE)

res_df <- if (length(results)) do.call(rbind, results) else empty_results
map_df <- if (length(mappings)) do.call(rbind, mappings) else empty_map
rownames(res_df) <- NULL
rownames(map_df) <- NULL
for (col in c("matched", "hmdb_id", "kegg_id")) map_df[[col]] <- as.character(map_df[[col]])

write_parquet(res_df, file.path(out_dir, "results.parquet"))
write_parquet(map_df, file.path(out_dir, "mapping.parquet"))
writeLines(toJSON(messages, auto_unbox = TRUE, null = "null"), file.path(out_dir, "messages.json"),
           useBytes = TRUE)

if (any(vapply(messages, function(m) identical(m$level, "error"), logical(1))) &&
    length(results) == 0) {
  message("All comparisons failed: ",
          paste(vapply(messages, function(m) m$message, character(1)), collapse = "; "))
  quit(status = 1)
}
