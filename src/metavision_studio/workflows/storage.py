"""Save and load :class:`MSIData` inside a project.

Layout of a saved dataset directory::

    <dir>/pixels.parquet     x, y, section
    <dir>/values.npy         float32 matrix, pixels x features (memory-mappable)
    <dir>/features.parquet   feature id (index), name, mz, omics
    <dir>/meta.json          pixel size, sources, meta
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from metavision_studio.io.data import MSIData

__all__ = ["load_msidata", "read_result_table", "save_msidata"]


def save_msidata(data: MSIData, directory: str | Path) -> Path:
    d = Path(directory)
    d.mkdir(parents=True, exist_ok=True)
    data.pixels.to_parquet(d / "pixels.parquet", index=False)
    np.save(d / "values.npy", np.ascontiguousarray(data.values, dtype=np.float32))
    feats = data.features.copy()
    feats.index = feats.index.astype(str)
    feats.index.name = "feature"
    feats.to_parquet(d / "features.parquet")
    meta = {
        "pixel_size_um": data.pixel_size_um,
        "sources": list(data.sources),
        "meta": data.meta,
    }
    (d / "meta.json").write_text(json.dumps(meta, indent=2, default=str), encoding="utf-8")
    return d


def load_msidata(directory: str | Path, *, mmap: bool = False) -> MSIData:
    d = Path(directory)
    if not (d / "values.npy").exists():
        raise FileNotFoundError(f"No saved dataset in {d}")
    pixels = pd.read_parquet(d / "pixels.parquet")
    pixels["section"] = pixels["section"].astype(str)
    values = np.load(d / "values.npy", mmap_mode="r" if mmap else None)
    features = pd.read_parquet(d / "features.parquet")
    meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
    return MSIData(
        pixels=pixels,
        values=values if mmap else np.ascontiguousarray(values, dtype=np.float32),
        features=features,
        pixel_size_um=meta.get("pixel_size_um"),
        sources=tuple(meta.get("sources", ())),
        meta=meta.get("meta", {}),
    )


#: Text columns of result tables. Read back as strings so ``760.580`` stays an ID (not the
#: float 760.58) and a molecule named "NA" isn't turned into a missing value.
_TEXT_COLUMNS = (
    "feature",
    "name",
    "omics",
    "comparison",
    "pathway",
    "set_id",
    "library",
    "members",
    "measured",
    "direction",
    "cluster",
)


def read_result_table(path):
    """Read a markers/pathways CSV written by a runner, keeping ID and name columns as text."""
    import pandas as pd

    header = pd.read_csv(path, nrows=0).columns
    text = [c for c in _TEXT_COLUMNS if c in header]
    df = pd.read_csv(path, dtype=dict.fromkeys(text, str), keep_default_na=False, na_values=[""])
    for c in text:
        df[c] = df[c].fillna("")
    return df
