"""MetaVision Studio: 3D spatial metabolomics and multi-omics MALDI imaging in napari.

Builds on two published methods by Xin Ma and colleagues:

* MetaVision3D: 3D reconstruction of serial-section MALDI imaging
  (https://github.com/XinBiostats/MetaVision3D)
* SAMI: spatial multi-omics analysis from a single tissue section
  (https://github.com/XinBiostats/SAMI)

Subpackages
-----------
io       Load pixel tables (CSV / Parquet / imzML) into a common representation.
mv3d     MetaVision3D: normalisation, alignment, imputation, interpolation, 3D atlas.
sami     SAMI: normalisation, pooling, clustering, markers, pathway enrichment.
rbridge  Run the bundled R scripts through ``Rscript`` (no rpy2 required).
"""

__version__ = "0.1.0.dev0"

__all__ = ["__version__"]
