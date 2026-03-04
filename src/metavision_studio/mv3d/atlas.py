# Adapted from MetaVision3D (https://github.com/XinBiostats/MetaVision3D, commit a108fe8).
# © 2023 University of Florida Research Foundation, Inc. Licensed under CC BY-NC-SA 4.0
# (https://creativecommons.org/licenses/by-nc-sa/4.0/).
# Changes: physical voxel size written into the affine (mm), so it survives saving.
"""MetaAtlas3D: build a NIfTI volume from a section stack.

Voxel size:

* in-plane: the MALDI pixel size (``pixel_size_um``)
* through-plane: ``(thickness_um + gap_um) / (1 + n_insert)``, i.e. section pitch divided by
  the number of slices per section after interpolation

Deviation from upstream ``MetaAtlas3D.create_nii``: upstream used an identity affine and set
only ``header['pixdim'][3] = (thickness + gap) / ((1 + insert) * resolution)``, a z spacing
relative to the pixel size. nibabel rewrites ``pixdim`` from the affine when saving, so saved
files had voxel size 1 x 1 x 1 (the 2024 sample outputs confirm this). Here the voxel size goes
into the affine **in millimetres**, the NIfTI convention, with ``xyzt_units`` set to mm, so
viewers such as napari, ITK-SNAP and 3D Slicer show true physical proportions.

The array layout matches upstream: the ``(sections, x, y)`` stack is transposed to
``(y, x, section)``, so existing MetaVision3D atlases and these files have the same orientation.
"""

from __future__ import annotations

import nibabel as nib
import numpy as np

__all__ = ["to_nifti", "voxel_size"]


def voxel_size(
    *, pixel_size_um: float, thickness_um: float, gap_um: float = 0.0, n_insert: int = 0
) -> tuple[float, float, float]:
    """Voxel size in µm as ``(z, x, y)``, matching the ``(sections, rows, cols)`` stack axes."""
    if pixel_size_um <= 0 or thickness_um <= 0 or gap_um < 0 or n_insert < 0:
        raise ValueError("pixel size and thickness must be > 0; gap and n_insert >= 0")
    z = (thickness_um + gap_um) / (1 + n_insert)
    return (float(z), float(pixel_size_um), float(pixel_size_um))


def to_nifti(
    stack: np.ndarray,
    *,
    pixel_size_um: float,
    thickness_um: float,
    gap_um: float = 0.0,
    n_insert: int = 0,
) -> nib.Nifti1Image:
    """NIfTI-1 image of a ``(sections, rows, cols)`` stack with physical voxel size (mm).

    Args:
        stack: intensities (after alignment, imputation and interpolation as desired).
        pixel_size_um: MALDI pixel size (e.g. 50).
        thickness_um: section thickness (e.g. 10).
        gap_um: distance skipped between consecutive sections (e.g. 50).
        n_insert: interpolated sections inserted between each original pair.
    """
    dz, dx, dy = voxel_size(
        pixel_size_um=pixel_size_um, thickness_um=thickness_um, gap_um=gap_um, n_insert=n_insert
    )
    volume = np.ascontiguousarray(np.transpose(np.asarray(stack, dtype=np.float32), (2, 1, 0)))
    affine = np.diag([dy / 1000.0, dx / 1000.0, dz / 1000.0, 1.0])
    img = nib.Nifti1Image(volume, affine)
    img.header.set_xyzt_units(xyz="mm")
    img.header.set_data_dtype(np.float32)
    return img
