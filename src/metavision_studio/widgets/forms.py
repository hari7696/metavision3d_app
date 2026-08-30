"""Build a step's settings form from its params dataclass.

Essential fields are shown directly. Fields marked ``advanced`` sit under an *Advanced*
disclosure. Adding a parameter to a dataclass in ``workflows.params`` adds it to the GUI, so
the notebook API and the GUI can't drift apart.
"""

from __future__ import annotations

from typing import Any

from qtpy.QtCore import Qt, Signal
from qtpy.QtGui import QDoubleValidator
from qtpy.QtWidgets import (
    QCheckBox,
    QComboBox,
    QCompleter,
    QDoubleSpinBox,
    QFormLayout,
    QLineEdit,
    QSpinBox,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from metavision_studio.workflows.params import param_fields

__all__ = ["ParamsForm"]


def _combo(parent: QWidget) -> QComboBox:
    """A combo box that shrinks to fit a narrow dock instead of forcing a scrollbar."""
    w = QComboBox(parent)
    w.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
    w.setMinimumContentsLength(8)
    return w


# field -> (controlling field, value that enables it)
_ENABLED_WHEN = {
    "n_insert": ("interpolate", True),
    "radius": ("impute", True),
    "chosen": ("features", "chosen"),
}


class ParamsForm(QWidget):
    changed = Signal()

    def __init__(self, params_cls: type, parent: QWidget | None = None):
        super().__init__(parent)
        self._cls = params_cls
        self._widgets: dict[str, QWidget] = {}
        self._rows: dict[str, tuple[QFormLayout, QWidget]] = {}
        self._meta: dict[str, dict[str, Any]] = {}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(2)
        self._basic = QFormLayout()
        self._basic.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        self._basic.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        outer.addLayout(self._basic)

        self._adv_toggle = QToolButton(self)
        self._adv_toggle.setText("▸ Advanced")
        self._adv_toggle.setCheckable(True)
        self._adv_toggle.setAutoRaise(True)
        self._adv_toggle.setObjectName("advancedToggle")
        self._adv_box = QWidget(self)
        self._adv = QFormLayout(self._adv_box)
        self._adv.setContentsMargins(12, 0, 0, 0)
        self._adv.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        self._adv.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        self._adv_box.setVisible(False)
        self._adv_toggle.toggled.connect(self._toggle_advanced)

        n_adv = 0
        for name, default, meta in param_fields(params_cls):
            self._meta[name] = meta
            widget = self._make(name, default, meta)
            widget.setToolTip(meta.get("help", ""))
            widget.setMinimumWidth(60)
            self._widgets[name] = widget
            layout = self._adv if meta.get("advanced") else self._basic
            n_adv += bool(meta.get("advanced"))
            layout.addRow(meta.get("label", name), widget)
            self._rows[name] = (layout, widget)
        if n_adv:
            outer.addWidget(self._adv_toggle, 0, Qt.AlignmentFlag.AlignLeft)
            outer.addWidget(self._adv_box)
        else:
            self._adv_toggle.hide()
        self.changed.connect(self._apply_dependencies)
        self._apply_dependencies()

    # ------------------------------------------------------------------ construction
    def _make(self, name: str, default: Any, meta: dict[str, Any]) -> QWidget:
        choices = meta.get("choices")
        kind = meta.get("kind")
        if choices:
            w = _combo(self)
            for value, label in choices:
                w.addItem(label, value)
            w.setCurrentIndex(max(0, w.findData(default)))
            w.currentIndexChanged.connect(self.changed)
            return w
        if isinstance(default, bool):
            w = QCheckBox(self)
            w.setChecked(default)
            w.toggled.connect(self.changed)
            return w
        if isinstance(default, int):
            w = QSpinBox(self)
            w.setRange(int(meta.get("min") or 0), int(meta.get("max") or 1_000_000))
            w.setValue(default)
            w.valueChanged.connect(self.changed)
            return w
        if isinstance(default, float):
            lo = meta.get("min")
            if lo is not None and 0 < lo < 1e-4:  # tiny tolerances: scientific notation text box
                w = QLineEdit(f"{default:g}", self)
                w.setValidator(QDoubleValidator(lo, meta.get("max") or 1.0, 16, w))
                w.textChanged.connect(self.changed)
                return w
            w = QDoubleSpinBox(self)
            step = meta.get("step") or 0.1
            w.setDecimals(3 if step < 0.1 else 2)
            w.setRange(float(lo if lo is not None else 0.0), float(meta.get("max") or 1e9))
            w.setSingleStep(step)
            w.setValue(default)
            w.valueChanged.connect(self.changed)
            return w
        if kind == "feature" and name != "chosen":
            w = _combo(self)
            w.setEditable(True)
            w.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
            w.addItem("auto (most prevalent)" if default == "auto" else "(none)", default)
            w.currentIndexChanged.connect(self.changed)
            return w
        w = QLineEdit(str(default), self)
        if kind == "sections":
            w.setPlaceholderText("all")
        elif kind == "clusters":
            w.setPlaceholderText("e.g. 3, 5")
        elif kind == "feature":
            w.setPlaceholderText("molecule names, comma-separated")
        w.textChanged.connect(self.changed)
        return w

    def _toggle_advanced(self, on: bool) -> None:
        self._adv_box.setVisible(on)
        self._adv_toggle.setText("▾ Advanced" if on else "▸ Advanced")

    def _apply_dependencies(self) -> None:
        values = self.values()
        for name, (controller, wanted) in _ENABLED_WHEN.items():
            if name in self._widgets and controller in values:
                self._widgets[name].setEnabled(values[controller] == wanted)

    # ------------------------------------------------------------------ values
    def values(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for name, w in self._widgets.items():
            if isinstance(w, QComboBox):
                data = w.currentData()
                if w.isEditable() and (
                    data is None or w.currentText() != w.itemText(w.currentIndex())
                ):
                    data = w.currentText().strip()
                out[name] = data
            elif isinstance(w, QCheckBox):
                out[name] = w.isChecked()
            elif isinstance(w, QSpinBox | QDoubleSpinBox):
                out[name] = w.value()
            elif isinstance(w, QLineEdit):
                text = w.text().strip()
                if isinstance(self._default(name), float):
                    try:
                        out[name] = float(text)
                    except ValueError:
                        out[name] = self._default(name)
                else:
                    out[name] = text
        return out

    def _default(self, name: str) -> Any:
        for n, default, _meta in param_fields(self._cls):
            if n == name:
                return default
        return None

    def params(self) -> Any:
        return self._cls(**self.values())

    def set_values(self, values: dict[str, Any]) -> None:
        for name, value in values.items():
            w = self._widgets.get(name)
            if w is None:
                continue
            w.blockSignals(True)
            if isinstance(w, QComboBox):
                idx = w.findData(value)
                if idx >= 0:
                    w.setCurrentIndex(idx)
                elif w.isEditable():
                    w.setEditText(str(value))
            elif isinstance(w, QCheckBox):
                w.setChecked(bool(value))
            elif isinstance(w, QSpinBox):
                w.setValue(int(value))
            elif isinstance(w, QDoubleSpinBox):
                w.setValue(float(value))
            elif isinstance(w, QLineEdit):
                w.setText(f"{value:g}" if isinstance(value, float) else str(value))
            w.blockSignals(False)
        self._apply_dependencies()

    def set_value(self, name: str, value: Any) -> None:
        self.set_values({name: value})
        self.changed.emit()

    def has_field(self, name: str) -> bool:
        return name in self._widgets

    def set_row_visible(self, name: str, visible: bool) -> None:
        if name in self._rows:
            layout, widget = self._rows[name]
            layout.setRowVisible(widget, visible)

    def set_choices(self, kind: str, items: list[tuple[str, str]]) -> None:
        """Fill dynamic pickers: ``kind`` is ``feature``, ``sections`` or ``clusters``."""
        labels = [label for _value, label in items]
        for name, w in self._widgets.items():
            if self._meta[name].get("kind") != kind:
                continue
            if isinstance(w, QComboBox):
                current = w.currentData()
                w.blockSignals(True)
                first = (w.itemText(0), w.itemData(0))
                w.clear()
                w.addItem(*first)
                for value, label in items:
                    w.addItem(label, value)
                completer = QCompleter(labels, w)
                completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
                completer.setFilterMode(Qt.MatchFlag.MatchContains)
                w.setCompleter(completer)
                idx = w.findData(current)
                w.setCurrentIndex(max(0, idx))
                w.blockSignals(False)
            elif isinstance(w, QLineEdit):
                values = [value for value, _label in items]
                completer = QCompleter(values, w)
                completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
                completer.setFilterMode(Qt.MatchFlag.MatchContains)
                w.setCompleter(completer)
                if kind in ("sections", "clusters") and values:
                    preview = ", ".join(values[:4]) + ("…" if len(values) > 4 else "")
                    hint = "all" if kind == "sections" else "e.g."
                    w.setPlaceholderText(
                        f"{hint} · {preview}" if kind == "sections" else f"e.g. {preview}"
                    )
