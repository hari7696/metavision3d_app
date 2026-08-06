"""The runners against the real MetaVision3D and SAMI cores, on tiny synthetic data."""

from __future__ import annotations

import importlib.util

import numpy as np
import pytest

from metavision_studio.methods import methods_text
from metavision_studio.workflows import feature_items, params_for, run_step
from metavision_studio.workflows.display import insight_for, layer_for

pytestmark = pytest.mark.slow


def test_mv3d_real_core(mv3d_project):
    pytest.importorskip("metavision_studio.mv3d.align")
    p = mv3d_project
    for step in p.steps:
        run_step(p, step, params_for(p, step))
        assert p.status(step) == "done", step
    feat = feature_items(p)[0][0]
    spec = layer_for(p, "atlas", feat)
    assert spec.data.shape[0] == 7
    assert np.isfinite(spec.data).all()
    assert insight_for(p, "align", feat).data["score"].size == 4
    assert "ECC" in methods_text(p)


@pytest.mark.skipif(importlib.util.find_spec("leidenalg") is None, reason="needs leidenalg")
def test_sami_real_core_until_markers(sami_project):
    pytest.importorskip("metavision_studio.sami.cluster")
    p = sami_project
    run_step(p, "load")
    run_step(p, "normalise")
    run_step(p, "cluster", params_for(p, "cluster", resolution=0.5))
    clusters = p.record("cluster")["summary"]["clusters"]
    run_step(p, "markers", params_for(p, "markers", group_a=clusters[0]))
    assert p.status("markers") == "done"
    assert insight_for(p, "markers", None).kind == "volcano"
