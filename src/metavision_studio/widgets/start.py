"""Start page: new project, open project, try an example, recent projects."""

from __future__ import annotations

from qtpy.QtCore import Qt, Signal
from qtpy.QtWidgets import (
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from metavision_studio.widgets.recent import recent_projects, relative_time
from metavision_studio.workflows.examples import EXAMPLES

__all__ = ["StartPage"]


class StartPage(QWidget):
    new_requested = Signal()
    open_requested = Signal()
    open_path = Signal(str)
    example_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)

        title = QLabel("MetaVision Studio", self)
        title.setObjectName("appTitle")
        sub = QLabel("3D atlases and spatial multi-omics from MALDI imaging", self)
        sub.setObjectName("appSubtitle")
        sub.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(sub)
        layout.addSpacing(8)

        self.new_btn = QPushButton("New project from data…", self)
        self.new_btn.setObjectName("primaryButton")
        self.open_btn = QPushButton("Open project…", self)
        self.example_btn = QPushButton("Try an example dataset", self)
        menu = QMenu(self.example_btn)
        for ex in EXAMPLES.values():
            act = menu.addAction(f"{ex.title}  ·  {ex.description}")
            act.triggered.connect(lambda _=False, k=ex.key: self.example_requested.emit(k))
        self.example_btn.setMenu(menu)
        for w in (self.new_btn, self.open_btn, self.example_btn):
            w.setMinimumHeight(28)
            layout.addWidget(w)
        self.new_btn.clicked.connect(self.new_requested)
        self.open_btn.clicked.connect(self.open_requested)

        layout.addSpacing(12)
        self.recent_label = QLabel("Recent", self)
        self.recent_label.setObjectName("sectionLabel")
        layout.addWidget(self.recent_label)
        self.recent = QListWidget(self)
        self.recent.setObjectName("recentList")
        self.recent.setFrameShape(QListWidget.Shape.NoFrame)
        self.recent.itemActivated.connect(self._open_item)
        self.recent.itemClicked.connect(self._open_item)
        self.recent.setMaximumHeight(170)
        layout.addWidget(self.recent)
        layout.addStretch(1)

        credit = QLabel(
            "Methods by Xin Ma et al. · "
            "<a href='https://github.com/XinBiostats/MetaVision3D'>MetaVision3D</a> · "
            "<a href='https://github.com/XinBiostats/SAMI'>SAMI</a>",
            self,
        )
        credit.setObjectName("credit")
        credit.setOpenExternalLinks(True)
        credit.setWordWrap(True)
        layout.addWidget(credit)
        self.refresh()

    def refresh(self) -> None:
        self.recent.clear()
        items = recent_projects()
        for item in items:
            row = QListWidgetItem(f"{item['name']}    {relative_time(item.get('opened', ''))}")
            row.setData(Qt.ItemDataRole.UserRole, item["path"])
            row.setToolTip(item["path"])
            self.recent.addItem(row)
        self.recent_label.setVisible(bool(items))
        self.recent.setVisible(bool(items))

    def _open_item(self, item: QListWidgetItem) -> None:
        self.open_path.emit(item.data(Qt.ItemDataRole.UserRole))
