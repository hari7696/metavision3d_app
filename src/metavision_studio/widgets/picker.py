"""Global molecule picker: one searchable choice that drives every step's canvas layer."""

from __future__ import annotations

from qtpy.QtCore import Qt, Signal
from qtpy.QtWidgets import QComboBox, QCompleter, QHBoxLayout, QLabel, QWidget

__all__ = ["MoleculePicker"]


class MoleculePicker(QWidget):
    feature_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        label = QLabel("Molecule", self)
        label.setObjectName("pickerLabel")
        self.combo = QComboBox(self)
        self.combo.setEditable(True)
        self.combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.combo.lineEdit().setPlaceholderText("🔍 Search by name or m/z")
        self.combo.setMinimumContentsLength(14)
        self.combo.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        layout.addWidget(label)
        layout.addWidget(self.combo, 1)
        self.combo.currentIndexChanged.connect(self._emit)
        self._silent = False

    def set_features(self, items: list[tuple[str, str]], current: str | None = None) -> None:
        """``items`` are ``(feature_id, label)`` pairs."""
        self._silent = True
        self.combo.clear()
        for fid, label in items:
            self.combo.addItem(label, fid)
        completer = QCompleter([label for _fid, label in items], self.combo)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.combo.setCompleter(completer)
        idx = self.combo.findData(current) if current else 0
        self.combo.setCurrentIndex(max(0, idx))
        self._silent = False

    def current_feature(self) -> str | None:
        data = self.combo.currentData()
        return str(data) if data is not None else None

    def set_feature(self, feature: str) -> bool:
        idx = self.combo.findData(feature)
        if idx < 0:
            idx = self.combo.findText(feature, Qt.MatchFlag.MatchContains)
        if idx < 0:
            return False
        self.combo.setCurrentIndex(idx)
        return True

    def _emit(self, _index: int) -> None:
        if not self._silent and (fid := self.current_feature()) is not None:
            self.feature_changed.emit(fid)
