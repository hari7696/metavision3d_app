# Adapted from MetaVision3D (https://github.com/XinBiostats/MetaVision3D, commit a108fe8).
# © 2023 University of Florida Research Foundation, Inc. Licensed under CC BY-NC-SA 4.0
# (https://creativecommons.org/licenses/by-nc-sa/4.0/).
# Changes: pure functions on MSIData (no in-place mutation), natural section order,
# zero scale factors guarded.
"""MetaNorm3D: total-ion-current (TIC) and section-median normalisation.

Default ``method="tic+section"``. The MetaVision3D paper (Ma et al., bioRxiv 2023, Results:
"Normalization, imputation, interpolation…") normalises to TIC and then, per metabolite, to
the tissue-section median to remove between-section variability. Upstream's ``main.py`` demo
runs TIC only, with the section step commented out. Choose ``method="tic"`` to reproduce it.

Deviations from upstream ``MetaNorm3D``:

* **No mutation.** Upstream ``totalsum_norm`` overwrote the caller's DataFrame. Here a new
  :class:`MSIData` is returned and the input is left untouched.
* **Zero scale factors.** Upstream replaced only NaN/inf scale factors with 1. When a feature's
  median across sections is 0 (sparse features), the factor ``0 / median_s`` became 0 and wiped
  that feature from every section with a non-zero median. Such factors are now 1 (left unscaled).
* **NaN** intensities are treated as 0 (undetected), the usual MALDI export convention.
"""

from __future__ import annotations

from typing import Literal

import numpy as np

from metavision_studio.io.data import MSIData

__all__ = ["NormMethod", "normalize", "section_median_factors"]

NormMethod = Literal["tic+section", "tic", "section", "none"]


def _tic(values: np.ndarray) -> np.ndarray:
    row_sum = values.sum(axis=1, dtype=np.float64)
    out = values.astype(np.float32, copy=True)
    nz = row_sum != 0
    out[nz] = (values[nz] / row_sum[nz, None]).astype(np.float32)
    return out


def section_median_factors(data: MSIData) -> np.ndarray:
    """Per-section, per-feature scale factors, ``(n_sections, n_features)``.

    Rows follow ``data.sections`` (natural order).

    Each factor is ``median over sections of the per-section medians`` divided by
    ``this section's median``, so every section's median is brought to the common value.
    """
    values = np.nan_to_num(data.values, nan=0.0)
    sec = data.pixels["section"].to_numpy()
    sections = data.sections
    medians = np.stack([np.median(values[sec == s], axis=0) for s in sections]).astype(np.float64)
    target = np.median(medians, axis=0)
    with np.errstate(divide="ignore", invalid="ignore"):
        factors = target[None, :] / medians
    bad = ~np.isfinite(factors) | (factors == 0)
    factors[bad] = 1.0
    return factors.astype(np.float32)


def normalize(data: MSIData, method: NormMethod = "tic+section") -> MSIData:
    """Normalise intensities; returns a new :class:`MSIData`.

    Args:
        data: pixel intensities.
        method: ``"tic+section"`` (paper default), ``"tic"`` (total ion current only,
            upstream demo), ``"section"`` (section median only) or ``"none"``.
    """
    if method not in ("tic+section", "tic", "section", "none"):
        raise ValueError(f"Unknown normalisation method {method!r}")
    values = np.nan_to_num(data.values, nan=0.0)
    if method in ("tic", "tic+section"):
        values = _tic(values)
    out = data.with_values(values, normalisation=method)
    if method in ("section", "tic+section"):
        factors = section_median_factors(out)
        index = {s: i for i, s in enumerate(out.sections)}
        rows = out.pixels["section"].map(index).to_numpy()
        values = (out.values * factors[rows]).astype(np.float32)
        out = out.with_values(values, normalisation=method)
    return out
