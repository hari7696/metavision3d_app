"""One place that writes to the system clipboard (tests replace it)."""

from __future__ import annotations

from qtpy.QtGui import QGuiApplication

__all__ = ["copy_text"]


def copy_text(text: str) -> None:
    QGuiApplication.clipboard().setText(text)
