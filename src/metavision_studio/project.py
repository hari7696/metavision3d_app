"""Projects: a folder holding inputs, settings, every step's parameters and outputs.

::

    my_study/
      project.json      ← the manifest (human-readable; the record of what was run)
      results/<step>/   ← outputs of each step (Parquet, .npy, .h5ad, .nii.gz, .csv, .png)
      cache/            ← reusable intermediates (e.g. alignment warp matrices)

Each step's record includes a **fingerprint**: a hash of its parameters plus the
fingerprints of the steps it depends on. When an earlier step is re-run with different
settings, the later steps' stored fingerprints no longer match, so they show as *out of
date* instead of silently mixing results from different settings.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
from collections.abc import Mapping
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from metavision_studio import __version__

__all__ = ["PIPELINES", "Project", "StepStatus"]

FORMAT_VERSION = 1
MANIFEST = "project.json"

StepStatus = Literal["locked", "ready", "done", "stale", "failed"]
Analysis = Literal["mv3d", "sami"]

#: Steps of each analysis and what each step depends on (in run order).
PIPELINES: dict[str, dict[str, tuple[str, ...]]] = {
    "mv3d": {
        "load": (),
        "normalise": ("load",),
        "align": ("normalise",),
        "fill": ("align",),
        "atlas": ("fill",),
    },
    "sami": {
        "load": (),
        "normalise": ("load",),
        "cluster": ("normalise",),
        "markers": ("cluster",),
        "pathways": ("markers",),
    },
}


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, default=str, separators=(",", ":"))


def _versions() -> dict[str, str]:
    from importlib.metadata import PackageNotFoundError, version

    out = {"metavision-studio": __version__, "python": platform.python_version()}
    for dist in ("numpy", "scipy", "pandas", "scanpy", "anndata", "opencv-python-headless"):
        with suppress(PackageNotFoundError):
            out[dist] = version(dist)
    return out


@dataclass
class Project:
    root: Path
    manifest: dict[str, Any]

    # ------------------------------------------------------------------ lifecycle
    @classmethod
    def create(
        cls,
        root: str | os.PathLike[str],
        *,
        analysis: Analysis,
        inputs: list[dict[str, Any]],
        settings: Mapping[str, Any] | None = None,
        name: str | None = None,
    ) -> Project:
        """Create a new project folder (it may exist but must not contain a project)."""
        root = Path(root)
        if (root / MANIFEST).exists():
            raise FileExistsError(f"{root} already contains a project; open it instead.")
        root.mkdir(parents=True, exist_ok=True)
        manifest = {
            "format": FORMAT_VERSION,
            "name": name or root.name,
            "created": _now(),
            "modified": _now(),
            "analysis": analysis,
            "inputs": inputs,
            "settings": dict(settings or {}),
            "steps": {},
        }
        project = cls(root=root, manifest=manifest)
        project.save()
        return project

    @classmethod
    def open(cls, root: str | os.PathLike[str]) -> Project:
        root = Path(root)
        path = root / MANIFEST if root.is_dir() else root
        manifest = json.loads(path.read_text(encoding="utf-8"))
        if manifest.get("format", 0) > FORMAT_VERSION:
            raise ValueError(
                f"{path} was written by a newer MetaVision Studio. Please update to open it."
            )
        return cls(root=path.parent, manifest=manifest)

    def save(self) -> None:
        self.manifest["modified"] = _now()
        tmp = self.root / (MANIFEST + ".tmp")
        tmp.write_text(json.dumps(self.manifest, indent=2, default=str), encoding="utf-8")
        tmp.replace(self.root / MANIFEST)  # atomic: a crash never leaves a half-written manifest

    # ------------------------------------------------------------------ properties
    @property
    def name(self) -> str:
        return self.manifest["name"]

    @property
    def analysis(self) -> Analysis:
        return self.manifest["analysis"]

    @analysis.setter
    def analysis(self, value: Analysis) -> None:
        if value not in PIPELINES:
            raise ValueError(f"Unknown analysis {value!r}")
        self.manifest["analysis"] = value
        self.save()

    @property
    def settings(self) -> dict[str, Any]:
        return self.manifest["settings"]

    @property
    def inputs(self) -> list[dict[str, Any]]:
        return self.manifest["inputs"]

    @property
    def steps(self) -> dict[str, tuple[str, ...]]:
        return PIPELINES[self.analysis]

    def results_dir(self, step: str) -> Path:
        """Output folder of ``step`` for the current analysis.

        Each analysis has its own folders (``results/mv3d/normalise`` vs
        ``results/sami/normalise``). They share step names but not outputs, and Load differs
        between them too (excluded sections are blanked for 3D and removed for multi-omics).
        """
        path = self.root / "results" / self.analysis / step
        path.mkdir(parents=True, exist_ok=True)
        return path

    def cache_dir(self) -> Path:
        path = self.root / "cache"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def output(self, step: str, key: str) -> Path | None:
        """Absolute path of a recorded output, or None."""
        rec = self.manifest["steps"].get(step)
        if not rec or key not in rec.get("outputs", {}):
            return None
        return self.root / rec["outputs"][key]

    def record(self, step: str) -> dict[str, Any] | None:
        return self.manifest["steps"].get(step)

    # ------------------------------------------------------------------ fingerprints/status
    def _expected_fingerprint(self, step: str, params: Mapping[str, Any]) -> str:
        deps = self.steps.get(step, ())
        parts = {
            "step": step,
            "params": params,
            "deps": {d: (self.record(d) or {}).get("fingerprint") for d in deps},
        }
        if step == "load":
            parts["analysis"] = self.analysis
            parts["inputs"] = [{**inp, "file": self._file_identity(inp)} for inp in self.inputs]
            parts["settings"] = self.settings
        return hashlib.sha256(_canonical(parts).encode()).hexdigest()[:16]

    def _file_identity(self, inp: Mapping[str, Any]) -> list[Any] | str:
        """Size and modification time of an input file, so edited or replaced files are detected."""
        path = Path(inp.get("path", ""))
        if not path.is_absolute():
            path = self.root / path
        try:
            st = path.stat()
        except OSError:
            return "missing"
        return [st.st_size, st.st_mtime_ns]

    def status(self, step: str) -> StepStatus:
        rec = self.record(step)
        deps = self.steps.get(step, ())
        deps_ok = all(self.status(d) == "done" for d in deps)
        if rec is None:
            return "ready" if deps_ok else "locked"
        if rec.get("status") == "failed":
            return "failed" if deps_ok else "locked"
        if not deps_ok:
            return "stale" if all(self.record(d) for d in deps) else "locked"
        expected = self._expected_fingerprint(step, rec.get("params", {}))
        return "done" if rec.get("fingerprint") == expected else "stale"

    def blocking_step(self, step: str) -> str | None:
        """The earliest dependency that must be (re)run before ``step``, if any."""
        for dep in self.steps.get(step, ()):
            if (blocker := self.blocking_step(dep)) is not None:
                return blocker
            if self.status(dep) != "done":
                return dep
        return None

    # ------------------------------------------------------------------ recording runs
    def mark_done(
        self,
        step: str,
        params: Mapping[str, Any],
        outputs: Mapping[str, str | os.PathLike[str]],
        *,
        summary: Mapping[str, Any] | None = None,
        started: str | None = None,
    ) -> None:
        """Record a successful run. Output paths are stored relative to the project root."""
        rel = {}
        for key, path in outputs.items():
            p = Path(path)
            rel[key] = str(p.relative_to(self.root)) if p.is_absolute() else str(p)
        self.manifest["steps"][step] = {
            "status": "done",
            "params": dict(params),
            "outputs": rel,
            "summary": dict(summary or {}),
            "started": started or _now(),
            "finished": _now(),
            "versions": _versions(),
            "fingerprint": self._expected_fingerprint(step, params),
        }
        self.save()

    def mark_failed(self, step: str, params: Mapping[str, Any], error: str) -> None:
        self.manifest["steps"][step] = {
            "status": "failed",
            "params": dict(params),
            "outputs": {},
            "error": error,
            "finished": _now(),
        }
        self.save()

    def update_settings(self, **settings: Any) -> None:
        """Change load-time settings (pixel size, flips, excluded sections).

        Changing settings makes the load step, and so every later step, out of date.
        """
        self.manifest["settings"].update(settings)
        self.save()
