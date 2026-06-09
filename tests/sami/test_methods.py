import pandas as pd
import pytest

from metavision_studio import sami
from metavision_studio.io import MSIData


@pytest.mark.parametrize(
    ("step", "params", "expect"),
    [
        ("normalise", {"row": "sum", "transform": "log2"}, "log2(x + 1)"),
        ("normalise", {"row": "comp", "reference": "Taurine", "transform": "none"}, "Taurine"),
        ("cluster", {"resolution": 1.5, "harmony": True}, "Harmony"),
        ("transfer", {}, "ingest"),
        ("markers", {"fdr": 0.05, "top": 50}, "Benjamini"),
        ("pathways", {"fdr": 0.05}, "SMPDB"),
    ],
)
def test_describe(step, params, expect):
    text = sami.describe(step, params)
    assert expect in text
    assert text.endswith(".") or text.endswith(")")


def test_describe_cites_sami():
    assert "10.5281/zenodo.15022514" in sami.describe("markers", {})


def test_describe_unknown_step():
    with pytest.raises(KeyError):
        sami.describe("nope", {})


def test_annotate_features():
    data = MSIData.from_arrays([0], [0], ["a"], [[1.0, 2.0]], ["m.z.87.008", "m.z.1.0"])
    table = pd.DataFrame({"m.z. export": ["m.z.87.008"], "Name": ["pyruvate"]})
    out = sami.annotate_features(data, table)
    assert list(out.features["name"]) == ["pyruvate", "m.z.1.0"]
    assert list(data.features["name"]) == ["m.z.87.008", "m.z.1.0"]
