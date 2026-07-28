"""Generate a ready-to-paste methods paragraph from a project's record of what was run.

Every completed step contributes one or more sentences, written by the pipeline module that
implements it (``mv3d.describe`` / ``sami.describe``) from the exact parameters stored in
``project.json``. Software versions and the method citations are added at the end.
"""

from __future__ import annotations

import importlib
from typing import Any

from metavision_studio.project import Project

__all__ = ["CITATIONS", "methods_text"]

CITATIONS = {
    "mv3d": (
        "Ma X, et al. MetaVision3D: Automated Framework for the Generation of Spatial "
        "Metabolome Atlas in 3D. bioRxiv (2023). doi:10.1101/2023.11.27.568931"
    ),
    "sami": ("Ma X. XinBiostats/SAMI (v1.0.0). Zenodo (2025). doi:10.5281/zenodo.15022514"),
}

_FALLBACK = {
    "load": "Pixel tables were imported{files}.",
    "normalise": "Intensities were normalised ({params}).",
    "align": "Serial sections were aligned by rigid ECC registration ({params}).",
    "fill": "Missing pixels were imputed and intermediate sections interpolated ({params}).",
    "atlas": "A 3D volume was assembled and exported ({params}).",
    "cluster": "Pixels were clustered with the Leiden algorithm ({params}).",
    "markers": "Marker features were identified with Wilcoxon rank-sum tests ({params}).",
    "pathways": "Pathway over-representation analysis was performed ({params}).",
}


def _fmt_params(params: dict[str, Any]) -> str:
    return ", ".join(
        f"{k.replace('_', ' ')} = {v}" for k, v in params.items() if v not in ("", None)
    )


def _sentence(analysis: str, step: str, rec: dict[str, Any], project: Project) -> str:
    params = dict(rec.get("params", {}))
    summary = rec.get("summary") or {}
    # Report what was actually used, not the "auto" placeholder the user left selected.
    if params.get("reference") in ("auto", "") and summary.get("reference"):
        params["reference"] = summary["reference"]
    if params.get("reference"):
        from metavision_studio.io import pretty_name

        params["reference"] = pretty_name(str(params["reference"]))  # LPE.22.6._1 → LPE(22:6)
    try:
        module = importlib.import_module(f"metavision_studio.{analysis}")
        text = module.describe(step, params)
        if text:
            text = str(text).strip()
            lib = summary.get("library") or {}
            if step == "pathways" and lib.get("source"):
                origin = {
                    "zenodo": "the SAMI release (Zenodo, doi:10.5281/zenodo.15224641)",
                    "metaboanalyst": "MetaboAnalyst (www.metaboanalyst.ca)",
                }.get(lib["source"], lib["source"])
                when = f", retrieved {lib['converted'][:10]}" if lib.get("converted") else ""
                text += f" Compound and pathway libraries were from {origin}{when}."
            return text
    except Exception:
        pass
    files = ""
    if step == "load":
        n = len(project.inputs)
        summary = rec.get("summary", {})
        files = f" from {n} file{'s' if n != 1 else ''}"
        if summary.get("text"):
            files += f" ({summary['text'].replace(' · ', ', ')})"
    return _FALLBACK.get(step, f"{step}: {{params}}.").format(
        params=_fmt_params(params), files=files
    )


def methods_text(project: Project) -> str:
    """Methods paragraph covering every completed step, then versions and citations."""
    analysis = project.analysis
    sentences = []
    versions: dict[str, str] = {}
    for step in project.steps:
        rec = project.record(step)
        if not rec or rec.get("status") != "done":
            continue
        sentences.append(_sentence(analysis, step, rec, project))
        versions.update(rec.get("versions", {}))

    if not sentences:
        return "No steps have been run yet."
    soft = versions.get("metavision-studio", "")
    deps = ", ".join(
        f"{k} {v}" for k, v in versions.items() if k not in ("metavision-studio", "python")
    )
    tail = (
        f"Analyses were performed in MetaVision Studio {soft} (Python {versions.get('python', '')}"
        f"{'; ' + deps if deps else ''}), which implements the "
        f"{'MetaVision3D' if analysis == 'mv3d' else 'SAMI'} method [1]."
    )
    return " ".join([*sentences, tail]) + f"\n\n[1] {CITATIONS[analysis]}"
