"""Rename m/z features to molecule names using a SAMI-style annotation table.

SAMI ships ``annotation/{lipidomics,metabolomics,glycomics}_annotation.csv`` with two columns,
``m.z. export`` (the exported column name, e.g. ``m.z.760.585``) and ``Name`` (e.g.
``PC(34:1)``). Pathway enrichment matches *names*, so data exported with m/z headers must be
annotated first.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from metavision_studio.io.data import MSIData

__all__ = ["annotate_features"]


def annotate_features(
    data: MSIData,
    annotation: pd.DataFrame | str | Path,
    *,
    key_column: str | None = None,
    name_column: str | None = None,
) -> MSIData:
    """Set ``features["name"]`` from an annotation table (unmatched features keep their name).

    Args:
        annotation: DataFrame or CSV path. By default the first column holds feature ids
            (as exported) and a ``Name`` column (or the second column) holds molecule names.
    """
    table = pd.read_csv(annotation) if isinstance(annotation, (str, Path)) else annotation
    key = key_column or table.columns[0]
    name = name_column or ("Name" if "Name" in table.columns else table.columns[1])
    lookup = dict(zip(table[key].astype(str), table[name].astype(str), strict=False))
    features = data.features.copy()
    features["name"] = [
        lookup.get(fid, current)
        for fid, current in zip(features.index, features["name"], strict=True)
    ]
    from dataclasses import replace

    return replace(data, features=features)
