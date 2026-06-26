"""Workflows: run pipeline steps against a :class:`~metavision_studio.project.Project`.

This layer joins the headless core (``io``, ``mv3d``, ``sami``) to project persistence. It
has no Qt dependency, so it works from the GUI, the CLI and notebooks::

    from metavision_studio.project import Project
    from metavision_studio.workflows import run_step, params_for

    project = Project.open("my_study")
    run_step(project, "load")
    run_step(project, "normalise", params_for(project, "normalise", method="tic"))
"""

from typing import Any

from metavision_studio.project import Project
from metavision_studio.workflows.errors import StepError, StepLocked, explain
from metavision_studio.workflows.params import (
    PARAMS,
    STEP_TITLES,
    default_params,
    param_fields,
    params_from_dict,
    params_to_dict,
    split_list,
)
from metavision_studio.workflows.runners import (
    StepResult,
    feature_items,
    feature_list,
    load_step_data,
    mv3d_feature_stack,
    pathway_libraries,
    run_step,
    run_transfer,
    switch_analysis,
)
from metavision_studio.workflows.storage import load_msidata, save_msidata


def params_for(project: Project, step: str, **overrides: Any) -> Any:
    """Params for ``step``: the last-used values from the project, then ``overrides``."""
    rec = project.record(step) or {}
    values = {**rec.get("params", {}), **overrides}
    return params_from_dict(project.analysis, step, values)


__all__ = [
    "PARAMS",
    "STEP_TITLES",
    "StepError",
    "StepLocked",
    "StepResult",
    "default_params",
    "explain",
    "feature_items",
    "feature_list",
    "load_msidata",
    "load_step_data",
    "mv3d_feature_stack",
    "param_fields",
    "params_for",
    "params_from_dict",
    "params_to_dict",
    "pathway_libraries",
    "run_step",
    "run_transfer",
    "save_msidata",
    "split_list",
    "switch_analysis",
]
