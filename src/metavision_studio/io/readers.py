"""Read pixel tables (CSV, Parquet, imzML) into :class:`MSIData`.

Columns are detected automatically and shown to the user for confirmation:

* ``x`` and ``y``: pixel coordinates
* section: the first of ``section``, ``tissue_id``, ``region``, ``roi_named``, ``slice``, ``roi``
* features: every remaining **numeric** column that isn't known acquisition metadata

This replaces the 2024 app's two conventions, a hardcoded list of metadata columns and
"every column after ``region`` is a molecule". Both broke on new exports (for example the
``slide_id`` column in the MetaVision3D data).
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from metavision_studio.io.data import MSIData
from metavision_studio.io.raster import estimate_step

__all__ = [
    "ColumnMapping",
    "detect_columns",
    "guess_omics",
    "pretty_name",
    "read_imzml",
    "read_table",
]

SECTION_CANDIDATES = ("section", "tissue_id", "region", "roi_named", "slice", "roi", "sample")
METADATA_COLUMNS = {
    "unnamed: 0",
    "unnamed: 0.1",
    "index",
    "spotid",
    "spot_id",
    "raster",
    "z",
    "date",
    "slide_id",
    "slide",
    "tic",
    "roi_id",
}

_OMICS_HINTS = {
    "lipidomics": ("lipid",),
    "metabolomics": ("metab", "metabolite"),
    "glycomics": ("glycan", "glyco"),
}


def guess_omics(filename: str | Path) -> str:
    """Guess the omics type from a file name (``brain_lipidomics.csv`` → ``lipidomics``)."""
    stem = Path(filename).stem.lower()
    for omics, hints in _OMICS_HINTS.items():
        if any(h in stem for h in hints):
            return omics
    return "other"


@dataclass
class ColumnMapping:
    """Which columns hold coordinates, section IDs and features."""

    x: str
    y: str
    section: str | None
    features: list[str]
    ignored: list[str] = field(default_factory=list)

    def describe(self) -> str:
        sec = self.section or "(single section)"
        return f"x: {self.x}  y: {self.y}  section: {sec}  · {len(self.features):,} features"


def _find(columns: Sequence[str], candidates: Sequence[str]) -> str | None:
    lower = {c.lower(): c for c in columns}
    for cand in candidates:
        if cand in lower:
            return lower[cand]
    return None


def detect_columns(df: pd.DataFrame) -> ColumnMapping:
    """Work out the column roles of a wide pixel table.

    Raises:
        ValueError: if x/y coordinates or feature columns can't be found.
    """
    cols = [str(c) for c in df.columns]
    x = _find(cols, ("x", "pos_x", "x_coord"))
    y = _find(cols, ("y", "pos_y", "y_coord"))
    if x is None or y is None:
        raise ValueError(
            "Couldn't find the x/y coordinate columns. Expected columns named 'x' and 'y'; "
            f"found: {', '.join(cols[:12])}{'…' if len(cols) > 12 else ''}"
        )
    section = _find(cols, SECTION_CANDIDATES)
    roles = {x, y, section}
    features, ignored = [], []
    for c in cols:
        if c in roles:
            continue
        if c.lower() in METADATA_COLUMNS or c.lower().startswith("unnamed:"):
            ignored.append(c)
        elif pd.api.types.is_numeric_dtype(df[c]) and not df[c].isna().all():
            features.append(c)
        else:
            ignored.append(c)
    if not features:
        raise ValueError("No numeric feature (m/z intensity) columns were found.")
    return ColumnMapping(x=x, y=y, section=section, features=features, ignored=ignored)


def _dedupe(names: Sequence[str]) -> list[str]:
    seen: dict[str, int] = {}
    out = []
    for n in names:
        if n in seen:
            seen[n] += 1
            out.append(f"{n} [{seen[n]}]")
        else:
            seen[n] = 0
            out.append(n)
    return out


def _undo_pandas_dupes(names: Sequence[str]) -> list[str]:
    """pandas renames repeated headers to ``Glycogen.1``; restore ``Glycogen``.

    Only strips the suffix when the base name is itself a column, so ``m.z.760.585`` stays.
    """
    present = set(names)
    out = []
    for n in names:
        m = re.match(r"^(.*)\.(\d+)$", n)
        out.append(m.group(1) if m and m.group(1) in present else n)
    return out


_R_LIPID = re.compile(
    r"^(?P<cls>[A-Za-z][A-Za-z0-9]*)\.{1,2}(?:(?P<link>[OP])\.)?(?P<c>\d+)\.(?P<d>\d+)\.?(?:_\d+)?$"
)


def pretty_name(name: str) -> str:
    """Undo R's ``make.names`` mangling of lipid names: ``LPA.18.1._1`` → ``LPA(18:1)``.

    Names that don't look like mangled lipid shorthand are returned unchanged.
    """
    m = _R_LIPID.match(name)
    if not m:
        return name
    link = f"{m['link']}-" if m["link"] else ""
    return f"{m['cls']}({link}{m['c']}:{m['d']})"


def _display_names(ids: Sequence[str]) -> list[str]:
    pretty = [pretty_name(i) for i in ids]
    counts: dict[str, int] = {}
    for p in pretty:
        counts[p] = counts.get(p, 0) + 1
    return [p if counts[p] == 1 else i for p, i in zip(pretty, ids, strict=True)]


def _read_raw(path: Path) -> pd.DataFrame:
    suffix = "".join(path.suffixes[-2:]).lower()
    if suffix.endswith((".parquet", ".pq")):
        return pd.read_parquet(path)
    if suffix.endswith((".csv", ".csv.gz", ".tsv", ".txt")):
        sep = "\t" if ".tsv" in suffix else ","
        for encoding in ("utf-8", "utf-8-sig", "latin-1"):
            try:
                return pd.read_csv(path, sep=sep, encoding=encoding, low_memory=False)
            except UnicodeDecodeError:
                continue
        raise ValueError(f"Couldn't decode {path.name} as UTF-8 or Latin-1 text.")
    raise ValueError(f"Unsupported file type: {path.name} (use CSV, Parquet or imzML)")


def read_table(
    path: str | Path,
    *,
    mapping: ColumnMapping | None = None,
    omics: str | None = None,
    pixel_size_um: float | None = None,
    section: str | None = None,
) -> tuple[MSIData, ColumnMapping]:
    """Read a CSV/Parquet pixel table.

    Args:
        path: file to read.
        mapping: column roles. Detected automatically if omitted.
        omics: omics label for every feature. Guessed from the file name if omitted.
        pixel_size_um: physical pixel size. Estimated from the coordinate grid if omitted
            (this assumes coordinates are in µm, as in MALDI exports).
        section: section ID to use when the file has no section column. Defaults to the file stem.

    Returns:
        The data and the column mapping that was used.
    """
    path = Path(path)
    df = _read_raw(path)
    mapping = mapping or detect_columns(df)
    omics = omics or guess_omics(path)

    x = df[mapping.x].to_numpy(dtype=np.float64)
    y = df[mapping.y].to_numpy(dtype=np.float64)
    if mapping.section:
        sec = df[mapping.section]
        if pd.api.types.is_float_dtype(sec) and np.allclose(sec.dropna() % 1, 0):
            sec = sec.astype("Int64")
        sec = sec.astype(str).to_numpy()
    else:
        sec = np.full(len(df), section or path.stem)

    names = _dedupe(_undo_pandas_dupes(mapping.features))
    values = df[mapping.features].to_numpy(dtype=np.float32, na_value=np.nan)
    if pixel_size_um is None:
        pixel_size_um = estimate_step(x[sec == sec[0]]) if len(df) else None

    data = MSIData.from_arrays(
        x=x,
        y=y,
        section=sec,
        values=values,
        feature_ids=names,
        names=_display_names(names),
        omics=omics,
        pixel_size_um=pixel_size_um,
        sources=(str(path),),
    )
    return data, mapping


def read_imzml(
    path: str | Path,
    *,
    mz: Sequence[float],
    tolerance_ppm: float = 10.0,
    omics: str | None = None,
    section: str | None = None,
    names: Sequence[str] | None = None,
) -> MSIData:
    """Read an imzML file, extracting the intensity of each target m/z.

    imzML stores full spectra, so you choose which peaks to extract (``mz``). Each pixel's
    value is the summed intensity within ``±tolerance_ppm`` of the target. Needs the optional
    ``pyimzml`` dependency (``pip install "metavision-studio[imzml]"``).
    """
    try:
        from pyimzml.ImzMLParser import ImzMLParser
    except ImportError as exc:  # pragma: no cover - exercised only without the extra
        raise ImportError(
            'Reading imzML needs pyimzml: pip install "metavision-studio[imzml]"'
        ) from exc

    path = Path(path)
    targets = np.asarray(mz, dtype=np.float64)
    tol = targets * tolerance_ppm * 1e-6
    lo, hi = targets - tol, targets + tol
    parser = ImzMLParser(str(path))
    n = len(parser.coordinates)
    values = np.zeros((n, len(targets)), dtype=np.float32)
    xs = np.empty(n)
    ys = np.empty(n)
    for i, (cx, cy, *_rest) in enumerate(parser.coordinates):
        spec_mz, spec_int = parser.getspectrum(i)
        order = np.argsort(spec_mz)
        spec_mz, spec_int = np.asarray(spec_mz)[order], np.asarray(spec_int)[order]
        csum = np.concatenate([[0.0], np.cumsum(spec_int, dtype=np.float64)])
        a = np.searchsorted(spec_mz, lo, side="left")
        b = np.searchsorted(spec_mz, hi, side="right")
        values[i] = csum[b] - csum[a]
        xs[i], ys[i] = cx, cy

    pixel_size = None
    try:
        pixel_size = float(parser.imzmldict.get("pixel size x"))  # µm, when present
    except (TypeError, ValueError, AttributeError):
        pixel_size = None

    ids = [f"m/z {m:.4f}" for m in targets]
    return MSIData.from_arrays(
        x=xs,
        y=ys,
        section=np.full(n, section or path.stem),
        values=values,
        feature_ids=ids,
        names=list(names) if names is not None else ids,
        omics=omics or guess_omics(path),
        pixel_size_um=pixel_size,
        sources=(str(path),),
    )
