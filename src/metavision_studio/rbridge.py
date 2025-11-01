"""Run the R scripts bundled with MetaVision Studio through ``Rscript``.

The 2024 app embedded R in-process with rpy2. That tied every install to one R
build, one rpy2 ABI and a hardcoded ``C:\\Program Files\\R\\R-4.3.3``. Here R runs as
a subprocess and data is exchanged through files (Parquet/CSV/JSON), so any recent R
on Windows, macOS or Linux works.

Locating R, in order:

1. ``METAVISION_RSCRIPT``: full path to an ``Rscript`` executable
2. ``R_HOME``: ``$R_HOME/bin/Rscript``
3. ``Rscript`` on ``PATH``
4. Standard install locations (Windows per-user and system installs, the macOS framework,
   Homebrew), newest version first
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

from natsort import natsorted

#: CRAN packages the bundled R scripts need. Keep in sync with ``R/install_deps.R``.
#: ``qs2`` reads the pathway libraries MetaboAnalyst currently serves (converted once to Parquet).
REQUIRED_R_PACKAGES: tuple[str, ...] = ("jsonlite", "nanoparquet", "qs2")

_EXE = "Rscript.exe" if sys.platform == "win32" else "Rscript"


class RNotFoundError(RuntimeError):
    """No usable ``Rscript`` executable was found."""


class RScriptError(RuntimeError):
    """An R script exited with a non-zero status."""

    def __init__(self, returncode: int, stderr: str):
        super().__init__(f"R exited with status {returncode}:\n{stderr.strip()}")
        self.returncode = returncode
        self.stderr = stderr


def _candidate_install_dirs() -> list[Path]:
    """R home directories in conventional locations, newest version first."""
    dirs: list[Path] = []
    if sys.platform == "win32":
        roots = [
            Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "R",
            Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "R",
        ]
        for root in roots:
            if root.is_dir():
                dirs += natsorted(root.glob("R-*"), reverse=True)
    elif sys.platform == "darwin":
        dirs.append(Path("/Library/Frameworks/R.framework/Resources"))
        dirs += [Path("/opt/homebrew"), Path("/usr/local")]
    else:
        dirs += [Path("/usr/lib/R"), Path("/usr/local/lib/R"), Path("/usr")]
    return dirs


def find_rscript() -> Path:
    """Return the path to a usable ``Rscript`` executable.

    Raises:
        RNotFoundError: if R cannot be found. The message explains how to fix it.
    """
    explicit = os.environ.get("METAVISION_RSCRIPT")
    if explicit:
        path = Path(explicit)
        if path.is_file():
            return path
        raise RNotFoundError(f"METAVISION_RSCRIPT points to a missing file: {path}")

    if r_home := os.environ.get("R_HOME"):
        path = Path(r_home) / "bin" / _EXE
        if path.is_file():
            return path

    if on_path := shutil.which("Rscript"):
        return Path(on_path)

    for home in _candidate_install_dirs():
        path = home / "bin" / _EXE
        if path.is_file():
            return path

    raise RNotFoundError(
        "R was not found. Install R 4.3 or newer from https://cran.r-project.org/ "
        "(Windows: `winget install RProject.R`), or set METAVISION_RSCRIPT to the full "
        "path of Rscript."
    )


def script_path(name: str) -> Path:
    """Path to an R script shipped inside the package (``metavision_studio/R/<name>``)."""
    ref = resources.files("metavision_studio") / "R" / name
    path = Path(str(ref))
    if not path.is_file():
        raise FileNotFoundError(f"Bundled R script not found: {name}")
    return path


def run_r(
    args: list[str],
    *,
    timeout: float | None = None,
    cwd: str | os.PathLike[str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run ``Rscript <args>`` and return the completed process.

    Raises:
        RNotFoundError: if R is not installed.
        RScriptError: if R exits with a non-zero status (stderr is included).
    """
    cmd = [str(find_rscript()), "--no-save", "--no-restore", *args]
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        cwd=cwd,
        check=False,
    )
    if proc.returncode != 0:
        raise RScriptError(proc.returncode, proc.stderr)
    return proc


def run_script(
    name: str, *args: str, timeout: float | None = None
) -> subprocess.CompletedProcess[str]:
    """Run a bundled R script by file name, passing ``args`` as ``commandArgs()``."""
    return run_r([str(script_path(name)), *args], timeout=timeout)


@dataclass(frozen=True)
class RStatus:
    """What :func:`check_r` found: where R is, its version, and missing packages."""

    rscript: Path
    version: str
    missing_packages: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.missing_packages


def check_r(packages: tuple[str, ...] = REQUIRED_R_PACKAGES, timeout: float = 60) -> RStatus:
    """Locate R, report its version and which required packages are not installed."""
    rscript = find_rscript()
    pkg_vec = ", ".join(f'"{p}"' for p in packages)
    code = (
        'cat(R.version.string, "\\n", sep = "");'
        f"pk <- c({pkg_vec});"
        'cat(pk[!vapply(pk, requireNamespace, logical(1), quietly = TRUE)], sep = "\\n")'
    )
    out = run_r(["-e", code], timeout=timeout).stdout.splitlines()
    version = out[0].strip() if out else "unknown"
    missing = tuple(line.strip() for line in out[1:] if line.strip())
    return RStatus(rscript=rscript, version=version, missing_packages=missing)
