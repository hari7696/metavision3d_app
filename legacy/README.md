# Legacy: the 2024 "Vision" desktop app

This folder holds the original customtkinter desktop app (2024 – May 2025). It is kept only as
a reference while its features are ported into the `metavision_studio` package. It is **not**
packaged, linted or tested, and it will be removed once the new package reaches feature parity.

| Path                        | What it was                                                  |
|-----------------------------|--------------------------------------------------------------|
| `visionApp/app.py`          | entry point: switches between the MetaVision3D and SAMI UIs  |
| `visionApp/Metavision_tk/`  | MetaVision3D UI                                              |
| `visionApp/MetaVision3D/`   | vendored MetaVision3D modules (from XinBiostats/MetaVision3D, 2024) |
| `visionApp/sami_tk/`        | SAMI step-by-step UI                                         |
| `visionApp/SAMI/`           | vendored SAMI modules (from XinBiostats/SAMI, Aug–Sep 2024)   |
| `visionApp/SCILS/`          | SCiLS Lab `.slx` → CSV export through R                      |
| `visionApp/praveen_app.py`, `MetaVision3D/MetaAlign3Dold.py` | earlier prototypes (broken, unused) |
| `packaging/`                | PyInstaller spec/commands, the conda `environment.yml` (Python 3.10, Windows) and old `setup.py` |
| `notebooks/`                | scratch analysis notebook                                    |
| `sample_outputs/`           | two example NIfTI outputs                                    |
| `README_2024.md`            | the original README                                          |

Known problems with this code are listed in [../docs/roadmap.md](../docs/roadmap.md).
