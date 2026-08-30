"""The accordion step list: one card per step, one open at a time."""

from __future__ import annotations

from typing import Any

from qtpy.QtCore import Qt, Signal
from qtpy.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from metavision_studio.widgets import clipboard
from metavision_studio.widgets.forms import ParamsForm
from metavision_studio.workflows.errors import StepError
from metavision_studio.workflows.params import PARAMS, STEP_TITLES

__all__ = ["STATUS_ICONS", "StepCard", "StepList"]

STATUS_ICONS = {
    "locked": ("○", "#7f8590"),
    "ready": ("○", "#c8ccd4"),
    "running": ("◐", "#5aa9ff"),
    "done": ("✓", "#4cc38a"),
    "stale": ("⚠", "#f0b232"),
    "failed": ("✕", "#ef5b5b"),
}
STATUS_TEXT = {
    "locked": "",
    "ready": "ready",
    "running": "running…",
    "done": "",
    "stale": "out of date",
    "failed": "failed",
}
RUN_LABELS = {
    "load": "Load",
    "normalise": "Normalise",
    "align": "Align",
    "fill": "Fill gaps",
    "atlas": "Export",
    "cluster": "Cluster",
    "markers": "Find markers",
    "pathways": "Find pathways",
}


class _Header(QFrame):
    clicked = Signal()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class StepCard(QFrame):
    """Header (status · title · short result) plus a collapsible body with the form."""

    toggled = Signal(str)
    run_requested = Signal(str)
    action_requested = Signal(str, str)  # step, action id

    def __init__(self, analysis: str, step: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.step = step
        self.status = "locked"
        self.setObjectName("stepCard")
        self.setFrameShape(QFrame.Shape.NoFrame)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.header = _Header(self)
        self.header.setObjectName("stepHeader")
        self.header.setCursor(Qt.CursorShape.PointingHandCursor)
        h = QHBoxLayout(self.header)
        h.setContentsMargins(6, 5, 6, 5)
        self.icon = QLabel(self.header)
        self.icon.setFixedWidth(16)
        self.title = QLabel(STEP_TITLES[step], self.header)
        self.title.setObjectName("stepTitle")
        self.state = QLabel(self.header)
        self.state.setObjectName("stepState")
        self.state.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.state.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        h.addWidget(self.icon)
        h.addWidget(self.title)
        h.addWidget(self.state, 1)
        self.header.clicked.connect(lambda: self.toggled.emit(self.step))
        layout.addWidget(self.header)

        self.body = QWidget(self)
        b = QVBoxLayout(self.body)
        b.setContentsMargins(22, 2, 6, 8)
        b.setSpacing(6)

        self.hint = QLabel(self.body)
        self.hint.setObjectName("stepHint")
        self.hint.setWordWrap(True)
        b.addWidget(self.hint)

        self.banner = QLabel(self.body)  # e.g. section-QC suggestion on Load
        self.banner.setObjectName("stepBanner")
        self.banner.setWordWrap(True)
        self.banner.setTextFormat(Qt.TextFormat.RichText)
        self.banner.linkActivated.connect(lambda a: self.action_requested.emit(self.step, a))
        self.banner.hide()
        b.addWidget(self.banner)

        self.form = ParamsForm(PARAMS[analysis][step], self.body)
        b.addWidget(self.form)

        row = QHBoxLayout()
        row.addStretch(1)
        self.extra = QToolButton(self.body)  # optional secondary action (e.g. transfer)
        self.extra.setAutoRaise(True)
        self.extra.hide()
        self.extra.clicked.connect(
            lambda: self.action_requested.emit(self.step, self.extra.property("action"))
        )
        row.addWidget(self.extra)
        self.run = QPushButton(RUN_LABELS.get(step, "Run"), self.body)
        self.run.setObjectName("runButton")
        self.run.setDefault(True)
        self.run.clicked.connect(lambda: self.run_requested.emit(self.step))
        row.addWidget(self.run)
        b.addLayout(row)

        self.result = QLabel(self.body)
        self.result.setObjectName("stepResult")
        self.result.setWordWrap(True)
        self.result.hide()
        b.addWidget(self.result)

        self.error_box = QFrame(self.body)
        self.error_box.setObjectName("errorBox")
        e = QVBoxLayout(self.error_box)
        e.setContentsMargins(8, 6, 8, 6)
        self.error_label = QLabel(self.error_box)
        self.error_label.setWordWrap(True)
        self.error_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        e.addWidget(self.error_label)
        er = QHBoxLayout()
        self.details_btn = QToolButton(self.error_box)
        self.details_btn.setText("Details")
        self.details_btn.setCheckable(True)
        self.details_btn.setAutoRaise(True)
        self.copy_btn = QToolButton(self.error_box)
        self.copy_btn.setText("Copy report")
        self.copy_btn.setAutoRaise(True)
        er.addWidget(self.details_btn)
        er.addWidget(self.copy_btn)
        er.addStretch(1)
        e.addLayout(er)
        self.details = QLabel(self.error_box)
        self.details.setObjectName("errorDetails")
        self.details.setWordWrap(True)
        self.details.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.details.hide()
        e.addWidget(self.details)
        self.details_btn.toggled.connect(self.details.setVisible)
        self.copy_btn.clicked.connect(self._copy_report)
        self.error_box.hide()
        b.addWidget(self.error_box)
        self._error: StepError | None = None

        layout.addWidget(self.body)
        self.body.hide()
        self.set_status("locked")

    # ------------------------------------------------------------------ state
    @property
    def expanded(self) -> bool:
        return not self.body.isHidden()

    def set_expanded(self, on: bool) -> None:
        self.body.setVisible(on)
        self.setProperty("open", on)
        self.style().unpolish(self)
        self.style().polish(self)

    def set_status(self, status: str, *, blocker: str | None = None, text: str = "") -> None:
        self.status = status
        glyph, colour = STATUS_ICONS[status]
        self.icon.setText(glyph)
        self.icon.setStyleSheet(f"color: {colour}; font-weight: bold;")
        self.state.setText(text or STATUS_TEXT[status])
        locked = status == "locked"
        self.form.setEnabled(not locked and status != "running")
        self.run.setEnabled(not locked and status != "running")
        if locked and blocker:
            self.hint.setText(f"Run <b>{STEP_TITLES[blocker]}</b> first.")
            self.hint.show()
        elif status == "stale":
            self.hint.setText("An earlier step changed. Run again to update.")
            self.hint.show()
        else:
            self.hint.hide()
        self.run.setText(
            "Run again" if status in ("done", "stale") else RUN_LABELS.get(self.step, "Run")
        )

    def set_result(self, text: str) -> None:
        self.result.setText(text)
        self.result.setVisible(bool(text))

    def set_banner(self, html: str) -> None:
        self.banner.setText(html)
        self.banner.setVisible(bool(html))

    def set_extra_action(self, label: str, action: str) -> None:
        self.extra.setText(label)
        self.extra.setProperty("action", action)
        self.extra.setVisible(bool(label))

    def show_error(self, err: StepError | None) -> None:
        self._error = err
        if err is None:
            self.error_box.hide()
            return
        text = err.message + (f"<br><span style='opacity:.8'>{err.hint}</span>" if err.hint else "")
        self.error_label.setText(text)
        self.details.setText(f"<pre style='white-space:pre-wrap'>{_escape(err.details)}</pre>")
        self.details_btn.setChecked(False)
        self.error_box.show()

    def _copy_report(self) -> None:
        if self._error is not None:
            clipboard.copy_text(self._error.report())


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class StepList(QWidget):
    """Vertical accordion of :class:`StepCard`."""

    opened = Signal(str)
    run_requested = Signal(str)
    action_requested = Signal(str, str)

    def __init__(self, analysis: str, steps: list[str], parent: QWidget | None = None):
        super().__init__(parent)
        self.analysis = analysis
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)
        self.cards: dict[str, StepCard] = {}
        for step in steps:
            card = StepCard(analysis, step, self)
            card.toggled.connect(self.toggle)
            card.run_requested.connect(self.run_requested)
            card.action_requested.connect(self.action_requested)
            layout.addWidget(card)
            self.cards[step] = card
        layout.addStretch(1)

    @property
    def open_step(self) -> str | None:
        return next((s for s, c in self.cards.items() if c.expanded), None)

    def toggle(self, step: str) -> None:
        self.open(None if self.cards[step].expanded else step)

    def open(self, step: str | None) -> None:
        for s, card in self.cards.items():
            card.set_expanded(s == step)
        if step is not None:
            self.opened.emit(step)

    def card(self, step: str) -> StepCard:
        return self.cards[step]

    def set_choices(self, kind: str, items: list[tuple[str, str]]) -> None:
        for card in self.cards.values():
            card.form.set_choices(kind, items)

    def values(self, step: str) -> dict[str, Any]:
        return self.cards[step].form.values()
