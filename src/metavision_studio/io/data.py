"""The in-memory representation shared by every pipeline: :class:`MSIData`.

A mass spectrometry imaging experiment is a set of pixels, each belonging to a tissue
section and carrying an intensity for every feature (an m/z peak, usually annotated with a
molecule name). One or more sections make up a dataset: serial sections for a 3D atlas, or
regions or samples for multi-omics analysis.

``MSIData`` stores this as:

* ``pixels``: a DataFrame with columns ``x``, ``y`` (grid coordinates) and ``section`` (str)
* ``values``: a float32 matrix, ``n_pixels x n_features``
* ``features``: a DataFrame indexed by feature id, with columns ``name``, ``mz`` and ``omics``

It is immutable by convention. Operations return new objects (sharing arrays where
possible) instead of modifying inputs in place. The 2024 code modified the input table in
place, which made results depend on the order steps were run.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from typing import Any

import numpy as np
import pandas as pd
from natsort import natsorted

__all__ = ["OMICS_TYPES", "MSIData", "merge_omics", "parse_mz"]

#: Omics labels used for pathway-library selection and display.
OMICS_TYPES = ("lipidomics", "metabolomics", "glycomics", "other")

_MZ_RE = re.compile(r"(\d+\.\d+)")


def parse_mz(name: str) -> float:
    """Extract an m/z value from a feature name such as ``m.z.760.585``; NaN if none."""
    match = _MZ_RE.search(str(name).replace("m.z.", "").replace("m/z", ""))
    return float(match.group(1)) if match else float("nan")


@dataclass(frozen=True, eq=False)
class MSIData:
    pixels: pd.DataFrame
    values: np.ndarray
    features: pd.DataFrame
    pixel_size_um: float | None = None
    sources: tuple[str, ...] = ()
    meta: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        missing = {"x", "y", "section"} - set(self.pixels.columns)
        if missing:
            raise ValueError(f"pixels is missing columns: {sorted(missing)}")
        if self.values.ndim != 2:
            raise ValueError("values must be a 2-D array (pixels x features)")
        if self.values.shape != (len(self.pixels), len(self.features)):
            raise ValueError(
                f"values shape {self.values.shape} does not match "
                f"{len(self.pixels)} pixels x {len(self.features)} features"
            )
        for col in ("name", "mz", "omics"):
            if col not in self.features.columns:
                raise ValueError(f"features is missing column {col!r}")

    # ------------------------------------------------------------------ constructors
    @classmethod
    def from_arrays(
        cls,
        x: Sequence[float] | np.ndarray,
        y: Sequence[float] | np.ndarray,
        section: Sequence[Any] | np.ndarray,
        values: np.ndarray,
        feature_ids: Sequence[str],
        *,
        names: Sequence[str] | None = None,
        omics: str | Sequence[str] = "other",
        pixel_size_um: float | None = None,
        sources: Sequence[str] = (),
    ) -> MSIData:
        ids = [str(f) for f in feature_ids]
        if len(set(ids)) != len(ids):
            raise ValueError("feature ids must be unique")
        pixels = pd.DataFrame(
            {
                "x": np.asarray(x),
                "y": np.asarray(y),
                "section": pd.Series(np.asarray(section)).astype(str).to_numpy(),
            }
        )
        omics_col = [omics] * len(ids) if isinstance(omics, str) else list(omics)
        features = pd.DataFrame(
            {
                "name": list(names) if names is not None else ids,
                "mz": [parse_mz(f) for f in ids],
                "omics": omics_col,
            },
            index=pd.Index(ids, name="feature"),
        )
        return cls(
            pixels=pixels,
            values=np.ascontiguousarray(values, dtype=np.float32),
            features=features,
            pixel_size_um=pixel_size_um,
            sources=tuple(sources),
        )

    # ------------------------------------------------------------------ properties
    @property
    def n_pixels(self) -> int:
        return len(self.pixels)

    @property
    def n_features(self) -> int:
        return len(self.features)

    @property
    def feature_ids(self) -> list[str]:
        return self.features.index.tolist()

    @property
    def sections(self) -> list[str]:
        """Section IDs in natural order (``"2"`` before ``"10"``)."""
        return natsorted(self.pixels["section"].unique().tolist())

    @property
    def n_sections(self) -> int:
        return self.pixels["section"].nunique()

    def summary(self) -> str:
        """Short description such as ``"79 sections · 1,204 features · 2.1M pixels"``."""
        px = self.n_pixels
        px_s = f"{px / 1e6:.1f}M" if px >= 1e6 else f"{px / 1e3:.0f}k" if px >= 1e4 else str(px)
        return f"{self.n_sections} sections · {self.n_features:,} features · {px_s} pixels"

    # ------------------------------------------------------------------ access
    def feature_index(self, feature: str) -> int:
        """Column index of a feature, by id or by annotated name."""
        idx = self.features.index
        if feature in idx:
            return int(idx.get_loc(feature))
        hits = np.flatnonzero(self.features["name"].to_numpy() == feature)
        if len(hits) == 1:
            return int(hits[0])
        raise KeyError(f"Unknown feature {feature!r}")

    def column(self, feature: str) -> np.ndarray:
        """Intensities of one feature for every pixel (a view, do not modify)."""
        return self.values[:, self.feature_index(feature)]

    def label(self, feature: str) -> str:
        """Display label: ``name (m/z 760.585)`` when both are known."""
        row = self.features.iloc[self.feature_index(feature)]
        name, mz = str(row["name"]), row["mz"]
        fid = self.feature_ids[self.feature_index(feature)]
        if np.isfinite(mz) and name != fid:
            return f"{name} (m/z {mz:.4f})"
        return name

    def section_mask(self, section: str) -> np.ndarray:
        return (self.pixels["section"] == str(section)).to_numpy()

    # ------------------------------------------------------------------ derivation
    def with_values(self, values: np.ndarray, **meta: Any) -> MSIData:
        """Same pixels and features with new intensities (e.g. after normalisation)."""
        return replace(
            self,
            values=np.ascontiguousarray(values, dtype=np.float32),
            meta={**self.meta, **meta},
        )

    def subset(
        self,
        *,
        sections: Sequence[str] | None = None,
        features: Sequence[str] | None = None,
        pixel_mask: np.ndarray | None = None,
    ) -> MSIData:
        """Select sections, features and/or pixels. Returns a new object."""
        mask = np.ones(self.n_pixels, dtype=bool) if pixel_mask is None else pixel_mask.copy()
        if sections is not None:
            mask &= self.pixels["section"].isin([str(s) for s in sections]).to_numpy()
        cols = (
            np.arange(self.n_features)
            if features is None
            else np.array([self.feature_index(f) for f in features], dtype=int)
        )
        return replace(
            self,
            pixels=self.pixels.loc[mask].reset_index(drop=True),
            values=np.ascontiguousarray(self.values[np.ix_(mask, cols)]),
            features=self.features.iloc[cols].copy(),
        )

    def flipped(self, *, flip_x: bool = False, flip_y: bool = False) -> MSIData:
        """Mirror every section along x and/or y (the old app's Flip X / Flip Y)."""
        if not (flip_x or flip_y):
            return self
        px = self.pixels.copy()
        if flip_x:
            px["x"] = -px["x"]
        if flip_y:
            px["y"] = -px["y"]
        return replace(self, pixels=px)

    # ------------------------------------------------------------------ interop
    def to_frame(self) -> pd.DataFrame:
        """Wide table: ``x, y, section`` followed by one column per feature id."""
        vals = pd.DataFrame(self.values, columns=self.feature_ids)
        return pd.concat([self.pixels.reset_index(drop=True), vals], axis=1)

    def to_anndata(self):
        """AnnData with pixels as observations (``obs``: section, x, y; ``obsm['spatial']``)."""
        import anndata as ad

        obs = self.pixels.copy()
        obs.index = (
            obs["section"].astype(str) + ":" + obs["x"].astype(str) + "x" + obs["y"].astype(str)
        )
        obs["section"] = pd.Categorical(obs["section"], categories=self.sections)
        var = self.features.copy()
        var.index = var.index.astype(str)
        adata = ad.AnnData(X=self.values.copy(), obs=obs, var=var)
        adata.obsm["spatial"] = self.pixels[["x", "y"]].to_numpy(dtype=np.float32)
        adata.uns["metavision"] = {
            "pixel_size_um": self.pixel_size_um,
            "sources": list(self.sources),
        }
        return adata


def merge_omics(datasets: Sequence[MSIData], *, how: str = "inner") -> MSIData:
    """Combine datasets measured on the same pixels (e.g. lipids + metabolites + glycans).

    Pixels are matched on ``(section, x, y)``. Feature ids that collide across datasets get
    an ``@omics`` suffix. Replaces SAMI's separate *Pooling* step.

    Raises:
        ValueError: if no pixels are shared (the files are not from the same acquisition).
    """
    if len(datasets) == 1:
        return datasets[0]
    keys = ["section", "x", "y"]
    merged = datasets[0].pixels[keys].copy()
    merged["_i0"] = np.arange(datasets[0].n_pixels)
    for i, ds in enumerate(datasets[1:], start=1):
        right = ds.pixels[keys].copy()
        right[f"_i{i}"] = np.arange(ds.n_pixels)
        merged = merged.merge(right, on=keys, how=how)
    if merged.empty:
        raise ValueError(
            "These files share no pixels (same section, x and y), so they can't be combined. "
            "Check that they come from the same acquisition and use the same coordinates."
        )

    blocks, feats = [], []
    seen: set[str] = set()
    for i, ds in enumerate(datasets):
        idx = merged[f"_i{i}"].to_numpy()
        valid = ~pd.isna(idx)
        block = np.zeros((len(merged), ds.n_features), dtype=np.float32)
        block[valid] = ds.values[idx[valid].astype(int)]
        blocks.append(block)
        f = ds.features.copy()
        new_ids = []
        for fid, om in zip(f.index, f["omics"], strict=True):
            nid = fid if fid not in seen else f"{fid}@{om}"
            seen.add(nid)
            new_ids.append(nid)
        f.index = pd.Index(new_ids, name="feature")
        feats.append(f)

    pixel_size = next((d.pixel_size_um for d in datasets if d.pixel_size_um), None)
    return MSIData(
        pixels=merged[keys].reset_index(drop=True),
        values=np.hstack(blocks),
        features=pd.concat(feats),
        pixel_size_um=pixel_size,
        sources=tuple(s for d in datasets for s in d.sources),
        meta={"merged_from": len(datasets), "merge": how},
    )
