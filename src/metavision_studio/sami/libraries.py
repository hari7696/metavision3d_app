"""Pathway-enrichment libraries: compound names and synonyms, SMPDB pathways, lipid classes.

SAMI's enrichment uses MetaboAnalyst's libraries (``compound_db``, ``syn_nms``,
``lipid_compound_db``, ``lipid_syn_nms``, ``smpdb_pathway``, ``sub_class``), distributed as
``.qs`` files. MetaVision Studio converts them once to Parquet (``R/convert_libraries.R``)
and uses only the Parquet tables afterwards.

Two sources:

``"zenodo"``
    The exact versions used by SAMI: Ma X., Zenodo, doi:10.5281/zenodo.15224641 (``lib.zip``,
    CC BY 4.0). These are in the legacy ``qs`` format, which needs the archived ``qs`` R package
    (R ≤ 4.4) to convert. See ``scripts/convert_sami_libraries.md``. Preferred when present.
``"metaboanalyst"``
    The current libraries served by MetaboAnalyst (https://www.metaboanalyst.ca), the same
    URLs SAMI's R code downloads missing sets from. They are in the ``qs2`` format, which R 4.6
    converts with CRAN packages. This is the automatic route: :func:`prepare_libraries` downloads
    and converts them on the user's machine.

Converted tables are cached in ``<cache>/sami-lib-parquet/<source>/`` (see
:func:`metavision_studio.datasets.cache_dir`).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from metavision_studio._progress import ProgressFn, report

__all__ = [
    "LIBRARY_TABLES",
    "Source",
    "library_dir",
    "library_info",
    "prepare_libraries",
]

Source = Literal["auto", "zenodo", "metaboanalyst"]

LIBRARY_TABLES = (
    "compound_db",
    "syn_nms",
    "smpdb_pathway",
    "lipid_compound_db",
    "lipid_syn_nms",
    "sub_class",
)
_METABOANALYST_URLS = {
    "compound_db": "https://www.metaboanalyst.ca/resources/libs/compound_db.qs",
    "syn_nms": "https://www.metaboanalyst.ca/resources/libs/syn_nms.qs",
    "lipid_compound_db": "https://www.metaboanalyst.ca/resources/libs/lipid_compound_db.qs",
    "lipid_syn_nms": "https://www.metaboanalyst.ca/resources/libs/lipid_syn_nms.qs",
    "smpdb_pathway": "https://www.metaboanalyst.ca/resources/libs/msets/smpdb_pathway.qs",
    "sub_class": "https://www.metaboanalyst.ca/resources/libs/msets/sub_class.qs",
}


def _root() -> Path:
    from metavision_studio.datasets import cache_dir

    return cache_dir() / "sami-lib-parquet"


def _is_complete(path: Path) -> bool:
    return (path / "manifest.json").is_file() and all(
        (path / f"{t}.parquet").is_file() for t in LIBRARY_TABLES
    )


def library_dir(source: Source = "auto") -> Path | None:
    """Directory of converted Parquet libraries, or None if not prepared yet.

    ``"auto"`` prefers SAMI's Zenodo versions and falls back to MetaboAnalyst's.
    """
    order = ("zenodo", "metaboanalyst") if source == "auto" else (source,)
    for s in order:
        path = _root() / s
        if _is_complete(path):
            return path
    return None


def library_info(path: Path) -> dict:
    """The conversion manifest (source files, row counts, R version) of a library directory."""
    return json.loads((Path(path) / "manifest.json").read_text(encoding="utf-8"))


def prepare_libraries(
    source: Literal["metaboanalyst", "zenodo"] = "metaboanalyst",
    *,
    force: bool = False,
    progress: ProgressFn | None = None,
) -> Path:
    """Download and convert the pathway libraries; return the Parquet directory.

    Needs R with ``qs2``, ``nanoparquet`` and ``jsonlite`` for ``"metaboanalyst"``
    (``metavision-studio install-r-deps``). ``"zenodo"`` needs R ≤ 4.4 with the archived ``qs``
    package; see ``scripts/convert_sami_libraries.md``.
    """
    import pooch

    from metavision_studio import rbridge
    from metavision_studio.datasets import cache_dir, fetch

    out = _root() / source
    if _is_complete(out) and not force:
        return out

    if source == "metaboanalyst":
        raw = cache_dir() / "metaboanalyst-libs"
        for i, (table, url) in enumerate(_METABOANALYST_URLS.items()):
            report(progress, i, len(_METABOANALYST_URLS) + 1, f"Downloading {table}")
            pooch.retrieve(url, known_hash=None, fname=f"{table}.qs", path=raw, progressbar=False)
    elif source == "zenodo":
        report(progress, 0, 2, "Downloading SAMI libraries (Zenodo)")
        raw = fetch("sami-lib", progress=False) / "lib"
    else:
        raise ValueError(f"Unknown library source {source!r}")

    report(progress, 6, 7, "Converting libraries to Parquet")
    try:
        rbridge.run_script("convert_libraries.R", str(raw), str(out), timeout=1800)
    except rbridge.RScriptError as exc:
        if "legacy qs format" in exc.stderr:
            raise RuntimeError(
                "SAMI's Zenodo libraries use the legacy 'qs' format, which current R can't read. "
                "Use source='metaboanalyst', or convert them once as described in "
                "scripts/convert_sami_libraries.md."
            ) from exc
        raise
    report(progress, 7, 7, "Libraries ready")
    return out
