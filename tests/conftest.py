"""Suite-wide test configuration."""

import importlib.util

# Widget tests need the optional GUI stack (`pip install -e ".[napari]"`). Without it, skip
# the whole folder instead of failing at import, so core-only installs can still run the suite.
collect_ignore = []
if importlib.util.find_spec("napari") is None or importlib.util.find_spec("qtpy") is None:
    collect_ignore.append("widgets")
