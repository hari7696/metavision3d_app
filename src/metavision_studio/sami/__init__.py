"""SAMI: spatial multi-omics analysis of MALDI imaging.

Port of https://github.com/XinBiostats/SAMI (Xin Ma et al.; © 2023 University of Florida
Research Foundation, Inc.; CC BY-NC-SA 4.0). See NOTICE.md.

Typical use::

    from metavision_studio import io, sami

    layers = [io.read_table(f)[0] for f in ("brain_lipidomics.csv", "brain_metabolomics.csv")]
    data = sami.normalize(io.merge_omics(layers))  # sum normalisation + log2(x + 1)
    adata = sami.cluster(data, resolution=1.0)
    markers = sami.find_markers(adata, ["3"])  # cluster 3 vs the rest
    pathways = sami.enrich_pathways(markers)  # needs R + prepared libraries
"""

from metavision_studio.sami.annotate import annotate_features
from metavision_studio.sami.cluster import cluster, transfer_clusters
from metavision_studio.sami.libraries import library_dir, prepare_libraries
from metavision_studio.sami.markers import (
    MARKER_COLUMNS,
    filter_abundance_prevalence,
    find_all_markers,
    find_markers,
)
from metavision_studio.sami.methods import CITATION, describe
from metavision_studio.sami.norm import normalize
from metavision_studio.sami.pathways import PATHWAY_COLUMNS, enrich_pathways, library_for_omics

__all__ = [
    "CITATION",
    "MARKER_COLUMNS",
    "PATHWAY_COLUMNS",
    "annotate_features",
    "cluster",
    "describe",
    "enrich_pathways",
    "filter_abundance_prevalence",
    "find_all_markers",
    "find_markers",
    "library_dir",
    "library_for_omics",
    "normalize",
    "prepare_libraries",
    "transfer_clusters",
]
