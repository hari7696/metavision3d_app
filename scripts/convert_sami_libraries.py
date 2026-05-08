"""Convert SAMI's pathway libraries (.qs) to the Parquet tables MetaVision Studio uses.

See scripts/convert_sami_libraries.md for background. Two sources:

  metaboanalyst  current MetaboAnalyst libraries (qs2 format). Works with any recent R.
                   python scripts/convert_sami_libraries.py metaboanalyst

  zenodo         the exact versions used by SAMI (doi:10.5281/zenodo.15224641, legacy qs
                 format). Needs an R <= 4.4 (the archived `qs` package doesn't load in R >= 4.5):
                   python scripts/convert_sami_libraries.py zenodo --rscript <R-4.4 Rscript>

Packages for the legacy route are installed into a private library (no changes to your normal
R library) from a dated Posit Package Manager snapshot that still has `qs` binaries.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

SNAPSHOT = "https://packagemanager.posit.co/cran/2024-10-01"


def _run(cmd: list[str], env_lib: Path | None = None) -> None:
    import os

    env = dict(os.environ)
    if env_lib is not None:
        env["R_LIBS"] = str(env_lib)
    print("$", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, env=env)


def convert_zenodo(rscript: Path, lib: Path | None) -> Path:
    from metavision_studio import rbridge
    from metavision_studio.datasets import cache_dir, fetch

    raw = fetch("sami-lib") / "lib"
    out = cache_dir() / "sami-lib-parquet" / "zenodo"
    lib = lib or (cache_dir() / "r-legacy-qs-lib")
    lib.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile("w", suffix=".R", delete=False, encoding="utf-8") as fh:
        fh.write(
            f'lib <- "{lib.as_posix()}"\n'
            'need <- c("qs", "nanoparquet", "jsonlite")\n'
            "have <- rownames(installed.packages(lib.loc = lib))\n"
            "todo <- setdiff(need, have)\n"
            f'if (length(todo)) install.packages(todo, lib = lib, repos = "{SNAPSHOT}")\n'
        )
        setup = fh.name
    _run([str(rscript), setup])
    _run(
        [str(rscript), str(rbridge.script_path("convert_libraries.R")), str(raw), str(out)],
        env_lib=lib,
    )
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("source", choices=["metaboanalyst", "zenodo"])
    parser.add_argument("--rscript", type=Path, help="Rscript of an R <= 4.4 (zenodo only)")
    parser.add_argument("--lib", type=Path, help="private R library for the legacy packages")
    parser.add_argument("--force", action="store_true", help="re-convert even if present")
    args = parser.parse_args(argv)

    if args.source == "metaboanalyst":
        from metavision_studio.sami.libraries import prepare_libraries

        out = prepare_libraries("metaboanalyst", force=args.force)
    else:
        if args.rscript is None:
            parser.error("zenodo needs --rscript pointing to an R <= 4.4 Rscript executable")
        out = convert_zenodo(args.rscript, args.lib)
    print(f"Libraries ready in {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
