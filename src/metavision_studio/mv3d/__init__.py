"""MetaVision3D: 3D reconstruction of serial-section MALDI imaging.

Port of https://github.com/XinBiostats/MetaVision3D (Xin Ma et al.; © 2023 University of
Florida Research Foundation, Inc.; CC BY-NC-SA 4.0). See NOTICE.md.

Typical use::

    from metavision_studio import io, mv3d

    data, _ = io.read_table("sections.csv")
    norm = mv3d.normalize(data)  # TIC + section median
    raster = io.build_raster(norm)
    alignment = mv3d.compute_alignment(norm, raster)  # ECC on the most prevalent feature
    stack = mv3d.apply_alignment(raster.stack_feature(norm, "PI(38:4)"), alignment)
    stack = mv3d.interpolate(mv3d.impute(stack, radius=1), n_insert=1)
    img = mv3d.to_nifti(stack, pixel_size_um=50, thickness_um=10, gap_um=50, n_insert=1)
"""

from metavision_studio.mv3d.align import (
    Alignment,
    apply_alignment,
    compute_alignment,
    load_alignment,
    save_alignment,
)
from metavision_studio.mv3d.atlas import to_nifti, voxel_size
from metavision_studio.mv3d.evaluate import adjacent_similarity, paired_similarity
from metavision_studio.mv3d.fill import impute, interpolate
from metavision_studio.mv3d.methods import CITATION, describe
from metavision_studio.mv3d.norm import NormMethod, normalize, section_median_factors
from metavision_studio.mv3d.preprocess import (
    blank_sections,
    drop_masked_pixels,
    prevalence,
    reference_feature,
    remove_low_prevalence,
    section_quality,
    shell_mask,
)

__all__ = [
    "CITATION",
    "Alignment",
    "NormMethod",
    "adjacent_similarity",
    "apply_alignment",
    "blank_sections",
    "compute_alignment",
    "describe",
    "drop_masked_pixels",
    "impute",
    "interpolate",
    "load_alignment",
    "normalize",
    "paired_similarity",
    "prevalence",
    "reference_feature",
    "remove_low_prevalence",
    "save_alignment",
    "section_median_factors",
    "section_quality",
    "shell_mask",
    "to_nifti",
    "voxel_size",
]
