"""Recently opened projects, stored in a small JSON file in the user config directory."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

__all__ = ["add_recent", "config_dir", "recent_projects", "relative_time"]

_MAX = 8


def config_dir() -> Path:
    if env := os.environ.get("METAVISION_CONFIG_DIR"):
        return Path(env)
    import platformdirs

    return Path(platformdirs.user_config_dir("metavision-studio", appauthor=False))


def _file() -> Path:
    return config_dir() / "recent.json"


def recent_projects() -> list[dict[str, str]]:
    """``[{"path", "name", "opened"}]``, newest first, only projects that still exist."""
    try:
        items = json.loads(_file().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [i for i in items if (Path(i.get("path", "")) / "project.json").exists()][:_MAX]


def add_recent(path: str | Path, name: str) -> None:
    path = str(Path(path).resolve())
    items = [i for i in recent_projects() if i["path"] != path]
    items.insert(0, {"path": path, "name": name, "opened": datetime.now(UTC).isoformat()})
    _file().parent.mkdir(parents=True, exist_ok=True)
    _file().write_text(json.dumps(items[:_MAX], indent=2), encoding="utf-8")


def relative_time(iso: str) -> str:
    try:
        then = datetime.fromisoformat(iso)
    except ValueError:
        return ""
    secs = (datetime.now(UTC) - then).total_seconds()
    if secs < 3600:
        return "just now" if secs < 120 else f"{int(secs // 60)} min ago"
    if secs < 86400:
        return f"{int(secs // 3600)} h ago"
    days = int(secs // 86400)
    if days < 7:
        return "yesterday" if days == 1 else f"{days} days ago"
    return "last week" if days < 14 else then.strftime("%d %b %Y")
