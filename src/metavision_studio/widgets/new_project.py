"""One-screen New Project dialog: files, column check, pixel size, analysis."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from qtpy.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QTableWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from metavision_studio.io import OMICS_TYPES, detect_columns, estimate_step, guess_omics

__all__ = ["NewProjectDialog", "inspect_file"]

_FILTER = "Pixel tables (*.csv *.csv.gz *.tsv *.parquet *.pq);;All files (*)"


def inspect_file(path: str | Path, nrows: int = 3000) -> dict[str, Any]:
    """Quickly read the start of a file: column mapping, feature count, pixel-size estimate."""
    path = Path(path)
    if path.suffix.lower() in (".parquet", ".pq"):
        df = pd.read_parquet(path).head(nrows)
    else:
        df = None
        for enc in ("utf-8", "utf-8-sig", "latin-1"):
            try:
                df = pd.read_csv(
                    path,
                    nrows=nrows,
                    encoding=enc,
                    sep="\t" if path.suffix.lower() == ".tsv" else ",",
                )
                break
            except UnicodeDecodeError:
                continue
        if df is None:
            raise ValueError("Couldn't decode the file as text.")
    mapping = detect_columns(df)
    xs = df[mapping.x].to_numpy(dtype=float)
    if mapping.section:
        xs = xs[(df[mapping.section] == df[mapping.section].iloc[0]).to_numpy()]
    return {
        "mapping": mapping,
        "n_features": len(mapping.features),
        "pixel_size_um": float(estimate_step(xs)) if len(xs) > 1 else 0.0,
    }


class NewProjectDialog(QDialog):
    """Collects everything needed for ``Project.create``. Read :meth:`result_spec` after accept."""

    def __init__(self, parent: QWidget | None = None, files: list[str] | None = None):
        super().__init__(parent)
        self.setWindowTitle("New project")
        self.setMinimumWidth(560)
        self.setAcceptDrops(True)
        self._info: dict[str, dict[str, Any]] = {}
        self._root_edited = False

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        files_row = QHBoxLayout()
        files_row.addWidget(QLabel("<b>Files</b>", self))
        self.drop_hint = QLabel("drop CSV / Parquet here, or", self)
        self.drop_hint.setObjectName("muted")
        files_row.addWidget(self.drop_hint)
        add = QPushButton("Add files…", self)
        add.clicked.connect(self._browse_files)
        files_row.addWidget(add)
        files_row.addStretch(1)
        layout.addLayout(files_row)

        self.table = QTableWidget(0, 4, self)
        self.table.setHorizontalHeaderLabels(["File", "Omics", "", ""])
        self.table.verticalHeader().hide()
        self.table.setShowGrid(False)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        hdr = self.table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for c in (1, 2, 3):
            hdr.setSectionResizeMode(c, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setMaximumHeight(130)
        layout.addWidget(self.table)

        form = QFormLayout()
        self.columns = QLabel("—", self)
        self.columns.setObjectName("muted")
        self.columns.setWordWrap(True)
        form.addRow("Columns", self.columns)
        self.pixel = QDoubleSpinBox(self)
        self.pixel.setRange(0.0, 10_000.0)
        self.pixel.setDecimals(1)
        self.pixel.setSuffix(" µm")
        self.pixel.setSpecialValueText("auto")
        form.addRow("Pixel size", self.pixel)
        layout.addLayout(form)

        layout.addWidget(QLabel("<b>What do you want to do?</b>", self))
        self.analysis = QButtonGroup(self)
        for key, title, desc in (
            ("mv3d", "Build a 3D atlas", "MetaVision3D: align serial sections into a volume"),
            ("sami", "Spatial multi-omics", "SAMI: clusters, markers and pathways"),
        ):
            rb = QRadioButton(title, self)
            rb.setProperty("analysis", key)
            self.analysis.addButton(rb)
            row = QHBoxLayout()
            row.addWidget(rb)
            d = QLabel(desc, self)
            d.setObjectName("muted")
            row.addWidget(d, 1)
            layout.addLayout(row)
        self.analysis.buttonToggled.connect(lambda *_: self._validate())

        root_row = QHBoxLayout()
        root_row.addWidget(QLabel("Project folder", self))
        self.root = QLineEdit(self)
        self.root.textEdited.connect(self._root_was_edited)
        root_row.addWidget(self.root, 1)
        browse = QToolButton(self)
        browse.setText("…")
        browse.clicked.connect(self._browse_root)
        root_row.addWidget(browse)
        layout.addLayout(root_row)

        self.error = QLabel(self)
        self.error.setObjectName("errorText")
        self.error.setWordWrap(True)
        self.error.hide()
        layout.addWidget(self.error)

        self.buttons = QDialogButtonBox(self)
        self.create_btn = self.buttons.addButton("Create", QDialogButtonBox.ButtonRole.AcceptRole)
        self.buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

        if files:
            self.add_files(files)
        self._validate()

    # ------------------------------------------------------------------ files
    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        self.add_files([u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()])

    def _browse_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(self, "Add data files", "", _FILTER)
        self.add_files(files)

    def add_files(self, files: list[str]) -> None:
        for f in files:
            if not f or f in self._info:
                continue
            try:
                info = inspect_file(f)
            except Exception as exc:
                info = {"error": str(exc)}
            self._info[f] = info
            self._add_row(f, info)
        self._refresh_summary()

    def _add_row(self, path: str, info: dict[str, Any]) -> None:
        r = self.table.rowCount()
        self.table.insertRow(r)
        name = QLabel(Path(path).name, self.table)
        name.setToolTip(path)
        self.table.setCellWidget(r, 0, name)
        omics = QComboBox(self.table)
        for o in OMICS_TYPES:
            omics.addItem(o.capitalize() if o != "other" else "Other", o)
        omics.setCurrentIndex(max(0, omics.findData(guess_omics(path))))
        omics.setProperty("path", path)
        self.table.setCellWidget(r, 1, omics)
        status = QLabel(
            f"✓ {info['n_features']:,} features" if "error" not in info else f"✕ {info['error']}",
            self.table,
        )
        status.setObjectName("muted" if "error" not in info else "errorText")
        self.table.setCellWidget(r, 2, status)
        remove = QToolButton(self.table)
        remove.setText("✕")
        remove.setAutoRaise(True)
        remove.setToolTip("Remove")
        remove.clicked.connect(lambda _=False, p=path: self._remove(p))
        self.table.setCellWidget(r, 3, remove)

    def _remove(self, path: str) -> None:
        for r in range(self.table.rowCount()):
            if self.table.cellWidget(r, 1).property("path") == path:
                self.table.removeRow(r)
                break
        self._info.pop(path, None)
        self._refresh_summary()

    def _refresh_summary(self) -> None:
        ok = [i for i in self._info.values() if "error" not in i]
        if ok:
            self.columns.setText(ok[0]["mapping"].describe())
            if self.pixel.value() == 0 and ok[0]["pixel_size_um"]:
                self.pixel.setValue(round(ok[0]["pixel_size_um"], 1))
        else:
            self.columns.setText("—")
        if self._info and not self._root_edited:
            first = Path(next(iter(self._info)))
            self.root.setText(str(first.parent / f"{first.stem}_project"))
        self.drop_hint.setVisible(not self._info)
        self._validate()

    # ------------------------------------------------------------------ root
    def _root_was_edited(self, _text: str) -> None:
        self._root_edited = True
        self._validate()

    def _browse_root(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "Project folder", self.root.text())
        if d:
            self.root.setText(d)
            self._root_edited = True
            self._validate()

    # ------------------------------------------------------------------ result
    def _validate(self) -> None:
        msg = ""
        ok_files = [f for f, i in self._info.items() if "error" not in i]
        if any("error" in i for i in self._info.values()):
            msg = "Remove the files that couldn't be read."
        elif self.root.text() and (Path(self.root.text()) / "project.json").exists():
            msg = "That folder already has a project. Open it instead, or pick another folder."
        self.error.setText(msg)
        self.error.setVisible(bool(msg))
        self.create_btn.setEnabled(
            bool(ok_files)
            and not msg
            and self.analysis.checkedButton() is not None
            and bool(self.root.text().strip())
        )

    def result_spec(self) -> dict[str, Any]:
        """Arguments for ``Project.create``."""
        inputs = []
        for r in range(self.table.rowCount()):
            combo = self.table.cellWidget(r, 1)
            inputs.append({"path": combo.property("path"), "omics": combo.currentData()})
        button = self.analysis.checkedButton()
        settings = {"pixel_size_um": float(self.pixel.value()) or None}
        return {
            "root": self.root.text().strip(),
            "analysis": button.property("analysis") if button else "mv3d",
            "inputs": inputs,
            "settings": settings,
        }

    def set_analysis(self, analysis: str) -> None:
        for b in self.analysis.buttons():
            b.setChecked(b.property("analysis") == analysis)
