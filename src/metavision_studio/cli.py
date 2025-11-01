"""Command-line entry point: ``metavision-studio``.

Commands:
    gui                 Open napari with the MetaVision Studio panel docked.
    doctor              Check the Python packages, optional extras and R setup.
    datasets            List the public example datasets.
    fetch KEY           Download (and cache) an example dataset.
    install-r-deps      Install the CRAN packages the bundled R scripts need.
    prepare-libraries   Download and convert the pathway-enrichment libraries.
"""

from __future__ import annotations

import argparse
import importlib
import platform
import sys
from importlib.metadata import PackageNotFoundError, version

from metavision_studio import __version__, rbridge

# (import name, distribution name)
_CORE = [
    ("numpy", "numpy"),
    ("scipy", "scipy"),
    ("pandas", "pandas"),
    ("pyarrow", "pyarrow"),
    ("anndata", "anndata"),
    ("scanpy", "scanpy"),
    ("leidenalg", "leidenalg"),
    ("igraph", "igraph"),
    ("cv2", "opencv-python-headless"),
    ("skimage", "scikit-image"),
    ("nibabel", "nibabel"),
    ("matplotlib", "matplotlib"),
]
_EXTRAS = [
    ("napari", "napari", "napari"),
    ("harmonypy", "harmonypy", "harmony"),
    ("pyimzml", "pyimzml", "imzml"),
]


def _probe(module: str, dist: str) -> str | None:
    """Import ``module``; return its version, or None if it is missing or broken."""
    try:
        importlib.import_module(module)
    except Exception:
        return None
    try:
        return version(dist)
    except PackageNotFoundError:
        return "installed"


def _doctor() -> int:
    ok = True
    print(f"metavision-studio {__version__}")
    print(f"Python {platform.python_version()} ({sys.executable})")
    print(f"Platform {platform.platform()}\n")

    print("Core packages:")
    for module, dist in _CORE:
        ver = _probe(module, dist)
        ok &= ver is not None
        print(f"  {'ok ' if ver else 'MISSING'}  {dist:<24} {ver or ''}")

    print("\nOptional extras:")
    for module, dist, extra in _EXTRAS:
        ver = _probe(module, dist)
        hint = "" if ver else f"(pip install 'metavision-studio[{extra}]')"
        print(f"  {'ok ' if ver else '-- '}  {dist:<24} {ver or hint}")

    print("\nR (pathway enrichment, SCiLS export):")
    try:
        status = rbridge.check_r()
    except rbridge.RNotFoundError as exc:
        print(f"  --   {exc}")
    except (rbridge.RScriptError, OSError) as exc:
        print(f"  ERROR  R was found but failed to run: {exc}")
    else:
        print(f"  ok   {status.version}")
        print(f"       {status.rscript}")
        if status.missing_packages:
            print(f"  --   missing R packages: {', '.join(status.missing_packages)}")
            print("       run: metavision-studio install-r-deps")
        else:
            print(f"  ok   R packages: {', '.join(rbridge.REQUIRED_R_PACKAGES)}")

    print("\nAll core packages OK." if ok else "\nSome core packages are missing.")
    return 0 if ok else 1


def _install_r_deps() -> int:
    try:
        proc = rbridge.run_script("install_deps.R", *rbridge.REQUIRED_R_PACKAGES)
    except (rbridge.RNotFoundError, rbridge.RScriptError) as exc:
        print(exc, file=sys.stderr)
        return 1
    print(proc.stdout, end="")
    return 0


def _gui(path: str | None) -> int:
    try:
        import napari
    except ImportError:
        print('The GUI needs napari: pip install "metavision-studio[napari]"', file=sys.stderr)
        return 1
    viewer = napari.Viewer(title="MetaVision Studio")
    _dock, widget = viewer.window.add_plugin_dock_widget("metavision-studio", "MetaVision Studio")
    if path:
        widget.open_project(path)
    napari.run()
    return 0


def _datasets() -> int:
    from metavision_studio import datasets

    for key, ds in datasets.DATASETS.items():
        mark = "cached" if datasets.is_cached(key) else f"{ds.size_mb:,.0f} MB"
        print(f"  {key:<15} {mark:>9}  {ds.description}")
    print()
    print(f"Cache: {datasets.cache_dir()}   (data: CC BY 4.0, Ma X. et al., Zenodo)")
    return 0


def _fetch(key: str) -> int:
    from metavision_studio import datasets

    try:
        path = datasets.fetch(key)
    except KeyError as exc:
        print(exc.args[0], file=sys.stderr)
        return 1
    print(path)
    print(f"Please cite: {datasets.DATASETS[key].citation}")
    return 0


def _prepare_libraries() -> int:
    from metavision_studio import sami

    def progress(done: int, total: int, message: str) -> None:
        print(f"  {message}", flush=True)

    try:
        path = sami.prepare_libraries(progress=progress)
    except Exception as exc:  # surfaced to the user as-is: network, R or conversion errors
        print(f"Couldn't prepare the pathway libraries: {exc}", file=sys.stderr)
        return 1
    print(path)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="metavision-studio", description=__doc__.splitlines()[0])
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    gui = sub.add_parser("gui", help="open napari with the MetaVision Studio panel")
    gui.add_argument("project", nargs="?", help="project folder to open")
    sub.add_parser("doctor", help="check the Python packages, optional extras and R setup")
    sub.add_parser("datasets", help="list the public example datasets")
    fetch = sub.add_parser("fetch", help="download an example dataset")
    fetch.add_argument("key", help="dataset key, see `metavision-studio datasets`")
    sub.add_parser("install-r-deps", help="install the CRAN packages the R scripts need")
    sub.add_parser("prepare-libraries", help="download and convert the pathway libraries")
    args = parser.parse_args(argv)

    match args.command:
        case "gui":
            return _gui(args.project)
        case "doctor":
            return _doctor()
        case "datasets":
            return _datasets()
        case "fetch":
            return _fetch(args.key)
        case "prepare-libraries":
            return _prepare_libraries()
        case _:
            return _install_r_deps()


if __name__ == "__main__":
    raise SystemExit(main())
