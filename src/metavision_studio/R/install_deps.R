# Install the CRAN packages that MetaVision Studio's R scripts need.
#
# Usage:  metavision-studio install-r-deps
#    or:  Rscript install_deps.R [package ...]
#
# Installs into the user library (created if missing), so no admin rights are needed.
# Keep the default list in sync with REQUIRED_R_PACKAGES in metavision_studio/rbridge.py.

args <- commandArgs(trailingOnly = TRUE)
pkgs <- if (length(args) > 0) args else c("jsonlite", "nanoparquet", "qs2")

user_lib <- Sys.getenv("R_LIBS_USER")
if (nzchar(user_lib) && !dir.exists(user_lib)) {
  dir.create(user_lib, recursive = TRUE, showWarnings = FALSE)
}
if (nzchar(user_lib)) .libPaths(c(user_lib, .libPaths()))

missing <- pkgs[!vapply(pkgs, requireNamespace, logical(1), quietly = TRUE)]
if (length(missing) == 0) {
  cat("All R packages already installed:", paste(pkgs, collapse = ", "), "\n")
  quit(status = 0)
}

cat("Installing:", paste(missing, collapse = ", "), "\n")
install.packages(missing, lib = .libPaths()[1], repos = "https://cloud.r-project.org")

still_missing <- missing[!vapply(missing, requireNamespace, logical(1), quietly = TRUE)]
if (length(still_missing) > 0) {
  message("Failed to install: ", paste(still_missing, collapse = ", "))
  quit(status = 1)
}
cat("Done.\n")
