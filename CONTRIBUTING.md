# Contributing to MetaVision Studio

Thanks for helping. Bug reports, method questions and pull requests are all welcome.

## Development setup

You need Python 3.12+ (3.14 recommended), [Hatch](https://hatch.pypa.io) and, for the R-backed
features, R 4.3+.

```bash
git clone https://github.com/hari7696/metavision3d_app.git
cd metavision3d_app
hatch env create            # .venv with the package (editable) + dev tools
hatch run r-deps            # R packages for the bundled R scripts
hatch run doctor            # verify everything is found
hatch run pre-commit install
```

VS Code picks up `.venv` automatically. Use `hatch shell` to activate it in a terminal.

## Everyday commands

| Command              | What it does                                  |
|----------------------|-----------------------------------------------|
| `hatch run test`     | run the test suite                            |
| `hatch run cov`      | tests with a coverage report                  |
| `hatch run lint`     | ruff lint                                     |
| `hatch run fmt`      | format and autofix                            |
| `hatch run gui`      | open napari with the plugin installed         |

Tests that need R are marked `@pytest.mark.r` and skip automatically when R is missing.
GUI tests are marked `@pytest.mark.gui`.

## Project layout

```
src/metavision_studio/
  io/        loading pixel tables (CSV, Parquet, imzML)
  mv3d/      MetaVision3D: norm, align, impute, interp, atlas
  sami/      SAMI: norm, pooling, clustering, markers, pathways
  R/         R scripts shipped with the package (run via rbridge)
  rbridge.py locating and running Rscript
  cli.py     `metavision-studio` command
tests/       pytest suite; small fixtures in tests/data/
docs/        roadmap and design notes
legacy/      the 2024 desktop app, kept as a porting reference (not packaged)
```

## Guidelines

- **No data, secrets or binaries in git.** Imaging data belongs on Zenodo or similar. Test fixtures
  must be small (kilobytes) and synthetic or openly licensed. The pre-commit hook rejects files over 1 MB.
- **Science code stays headless.** `io`, `mv3d` and `sami` must not import napari or Qt, so they
  work in notebooks, scripts and on HPC. GUI code wraps them.
- **Every scientific change needs a test**, ideally against a small known-answer example.
- **Stay faithful to the published methods.** If you change how something works (for example,
  fixing a bug that is also in upstream), say so in the PR and in `CHANGELOG.md`.
- Keep the code `ruff`-clean and add type hints to public functions.

## Licence of contributions

By contributing, you agree that your contributions are licensed under the project's
[CC BY-NC-SA 4.0](LICENSE) licence.
