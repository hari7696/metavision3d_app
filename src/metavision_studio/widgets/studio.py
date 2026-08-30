"""MetaVision Studio's napari dock widget: the whole workflow in one lean panel."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from qtpy.QtCore import Qt, QUrl
from qtpy.QtGui import QDesktopServices
from qtpy.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMenu,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from metavision_studio._progress import Cancelled
from metavision_studio.methods import methods_text
from metavision_studio.project import Project
from metavision_studio.widgets import clipboard
from metavision_studio.widgets.insights import InsightsPanel
from metavision_studio.widgets.jobs import JobRunner
from metavision_studio.widgets.new_project import NewProjectDialog
from metavision_studio.widgets.picker import MoleculePicker
from metavision_studio.widgets.recent import add_recent
from metavision_studio.widgets.start import StartPage
from metavision_studio.widgets.steps import StepList
from metavision_studio.widgets.style import STYLESHEET
from metavision_studio.workflows import (
    STEP_TITLES,
    StepError,
    explain,
    feature_items,
    params_for,
    run_step,
    run_transfer,
    switch_analysis,
)
from metavision_studio.workflows.display import (
    LAYER_NAMES,
    Insight,
    LayerSpec,
    cluster_label_stack,
    insight_for,
    label_to_cluster,
    layer_for,
)
from metavision_studio.workflows.examples import create_example_project
from metavision_studio.workflows.params import params_from_dict

__all__ = ["StudioWidget"]

ANALYSIS_NAMES = {"mv3d": "3D atlas (MetaVision3D)", "sami": "Spatial multi-omics (SAMI)"}


def _short_status(step: str, rec: dict[str, Any] | None) -> str:
    s = (rec or {}).get("summary") or {}
    match step:
        case "load":
            n = s.get("n_sections")
            return f"{n} sections" if n else ""
        case "normalise":
            return {"tic+section": "TIC + section", "tic": "TIC", "section": "section median"}.get(
                s.get("method", ""), ""
            )
        case "align":
            failed = s.get("failed_sections") or []
            return f"{len(failed)} failed" if failed else "aligned"
        case "fill":
            shape = s.get("shape")
            return f"{shape[0]} sections" if shape else ""
        case "atlas":
            n = s.get("n_files", 0)
            return f"{n} file{'s' if n != 1 else ''}"
        case "cluster":
            return f"{s.get('n_clusters', '?')} clusters"
        case "markers":
            return f"{s.get('n_significant', 0)} markers"
        case "pathways":
            return f"{s.get('n_enriched', 0)} pathways"
    return ""


class ProjectView(QWidget):
    """Project card, molecule picker and step list for one open project."""

    def __init__(self, project: Project, parent: QWidget | None = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.card = QFrame(self)
        self.card.setObjectName("projectCard")
        c = QHBoxLayout(self.card)
        c.setContentsMargins(10, 8, 6, 8)
        text = QVBoxLayout()
        text.setSpacing(1)
        self.name = QLabel(project.name, self.card)
        self.name.setObjectName("projectName")
        self.summary = QLabel(self.card)
        self.summary.setObjectName("muted")
        self.summary.setWordWrap(True)
        self.analysis = QLabel(ANALYSIS_NAMES[project.analysis], self.card)
        self.analysis.setObjectName("muted")
        text.addWidget(self.name)
        text.addWidget(self.summary)
        text.addWidget(self.analysis)
        c.addLayout(text, 1)
        self.menu_btn = QToolButton(self.card)
        self.menu_btn.setText("⋯")
        self.menu_btn.setObjectName("menuButton")
        self.menu_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.menu = QMenu(self.menu_btn)
        self.menu_btn.setMenu(self.menu)
        c.addWidget(self.menu_btn, 0, Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self.card)

        self.picker = MoleculePicker(self)
        layout.addWidget(self.picker)

        self.steps = StepList(project.analysis, list(project.steps), self)
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(self.steps)
        layout.addWidget(scroll, 1)


class StudioWidget(QWidget):
    """The MetaVision Studio panel (registered as a napari dock widget)."""

    def __init__(self, napari_viewer=None, parent: QWidget | None = None):
        super().__init__(parent)
        self.viewer = napari_viewer
        self.project: Project | None = None
        self.view: ProjectView | None = None
        self.jobs = JobRunner(self)  # pipeline steps: one at a time, with progress + cancel
        self.view_jobs = JobRunner(self)  # canvas layers: latest request wins
        self.insight_jobs = JobRunner(self)
        self._running_step: str | None = None
        self._categories: list[str] = []
        self._insights_dock = None
        self.setObjectName("studio")
        self.setStyleSheet(STYLESHEET)
        self.setMinimumWidth(300)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 6)
        layout.setSpacing(6)
        self.stack = QStackedWidget(self)
        self.start = StartPage(self)
        self.start.new_requested.connect(self.new_project)
        self.start.open_requested.connect(self.browse_project)
        self.start.open_path.connect(self.open_project)
        self.start.example_requested.connect(self.open_example)
        self.stack.addWidget(self.start)
        layout.addWidget(self.stack, 1)

        # status line: message · progress · cancel (hidden when idle)
        self.status = QFrame(self)
        self.status.setObjectName("statusLine")
        s = QHBoxLayout(self.status)
        s.setContentsMargins(0, 4, 0, 0)
        self.status_text = QLabel(self.status)
        self.status_text.setObjectName("muted")
        self.progress = QProgressBar(self.status)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(6)
        self.progress.setMaximumWidth(110)
        self.cancel_btn = QPushButton("Cancel", self.status)
        self.cancel_btn.setObjectName("cancelButton")
        self.cancel_btn.clicked.connect(self.cancel)
        s.addWidget(self.status_text, 1)
        s.addWidget(self.progress)
        s.addWidget(self.cancel_btn)
        layout.addWidget(self.status)
        self._set_idle()

        self.jobs.started.connect(self._on_job_started)
        self.jobs.progressed.connect(self._on_job_progress)

        self.insights = InsightsPanel()
        self.insights.section_clicked.connect(self._goto_section)
        self.insights.cluster_clicked.connect(self._on_cluster_clicked)
        self.insights.feature_clicked.connect(self._select_feature)

    # ================================================================== status line
    def _set_idle(self, message: str = "") -> None:
        self.progress.hide()
        self.cancel_btn.hide()
        self.status_text.setText(message)
        self.status.setVisible(bool(message))

    def _on_job_started(self, label: str) -> None:
        self.status.show()
        self.status_text.setText(label)
        self.progress.setRange(0, 0)  # indeterminate until the first progress report
        self.progress.show()
        self.cancel_btn.show()
        self.cancel_btn.setEnabled(True)

    def _on_job_progress(self, done: int, total: int, message: str) -> None:
        if total > 0:
            self.progress.setRange(0, total)
            self.progress.setValue(min(done, total))
        if message:
            self.status_text.setText(message)

    def cancel(self) -> None:
        self.jobs.cancel()
        self.cancel_btn.setEnabled(False)
        self.status_text.setText("Cancelling…")

    def _flash(self, message: str) -> None:
        if not self.jobs.busy:
            self._set_idle(message)

    # ================================================================== projects
    def new_project(self, files: list[str] | None = None) -> NewProjectDialog:
        dlg = NewProjectDialog(self, files=files)
        dlg.accepted.connect(lambda: self._create_from_dialog(dlg))
        dlg.open()
        return dlg

    def _create_from_dialog(self, dlg: NewProjectDialog) -> Project:
        spec = dlg.result_spec()
        project = Project.create(
            spec["root"],
            analysis=spec["analysis"],
            inputs=spec["inputs"],
            settings=spec["settings"],
        )
        self.open_project(project)
        return project

    def browse_project(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open project", "", "MetaVision project (project.json)"
        )
        if path:
            self.open_project(str(Path(path).parent))

    def open_example(self, key: str) -> None:
        self.jobs.start(
            lambda _progress: create_example_project(key),
            label="Preparing example dataset (downloads once)…",
            on_done=lambda project: (self._set_idle(), self.open_project(project)),
            on_error=lambda exc: self._set_idle(f"Couldn't prepare the example: {exc}"),
            on_cancel=lambda: self._set_idle("Cancelled"),
        )

    def open_project(self, project: Project | str | Path) -> None:
        if not isinstance(project, Project):
            try:
                project = Project.open(project)
            except Exception as exc:
                self._set_idle(f"Couldn't open project: {exc}")
                return
        self.project = project
        add_recent(project.root, project.name)
        self.start.refresh()
        self._clear_layers()
        if self.view is not None:
            self.stack.removeWidget(self.view)
            self.view.deleteLater()
        self.view = ProjectView(project, self)
        self.stack.addWidget(self.view)
        self.stack.setCurrentWidget(self.view)
        self._build_menu()
        v = self.view
        v.picker.feature_changed.connect(self._on_feature_changed)
        v.steps.opened.connect(self._on_step_opened)
        v.steps.run_requested.connect(self.run)
        v.steps.action_requested.connect(self._on_action)
        for step in project.steps:
            v.steps.card(step).form.set_values(vars(params_for(project, step)))
        self.refresh()
        first_open = next(
            (s for s in project.steps if project.status(s) in ("ready", "stale", "failed")),
            list(project.steps)[-1],
        )
        v.steps.open(first_open)
        self._update_layers()
        if project.status("load") == "ready":
            self.run("load")  # the data appears in the canvas straight away

    def close_project(self) -> None:
        self.project = None
        self._clear_layers()
        self._hide_insights()
        self.start.refresh()
        self.stack.setCurrentWidget(self.start)

    def _build_menu(self) -> None:
        assert self.view is not None and self.project is not None
        m = self.view.menu
        m.clear()
        m.addAction("Copy methods text", self.copy_methods)
        m.addAction("Open project folder", self.open_folder)
        other = "sami" if self.project.analysis == "mv3d" else "mv3d"
        m.addAction(f"Switch to {ANALYSIS_NAMES[other]}", lambda: self.switch_analysis(other))
        m.addSeparator()
        m.addAction("Close project", self.close_project)

    def copy_methods(self) -> None:
        if self.project is not None:
            clipboard.copy_text(methods_text(self.project))
            self._flash("Methods text copied to the clipboard.")

    def open_folder(self) -> None:
        if self.project is not None:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.project.root)))

    def switch_analysis(self, analysis: str) -> None:
        if self.project is None or self.jobs.busy:
            return
        load_params = switch_analysis(self.project, analysis)
        self.open_project(self.project)
        if load_params is not None and self.project.status("load") == "ready":
            # Each analysis has its own Load; re-run it with the same settings (seconds).
            self.run("load", params=params_from_dict(analysis, "load", load_params))

    # ================================================================== refresh
    def refresh(self) -> None:
        """Re-read the project: statuses, summaries, dynamic choices."""
        p, v = self.project, self.view
        if p is None or v is None:
            return
        load = (p.record("load") or {}).get("summary") or {}
        v.summary.setText(load.get("text", "Data not loaded yet"))
        for step in p.steps:
            card = v.steps.card(step)
            status = "running" if step == self._running_step else p.status(step)
            rec = p.record(step)
            card.set_status(
                status,
                blocker=p.blocking_step(step) if status == "locked" else None,
                text=_short_status(step, rec) if status == "done" else "",
            )
            if rec and rec.get("status") == "failed" and status == "failed":
                card.show_error(card._error or StepError(step, rec.get("error", "Failed."), "", ""))
            elif status != "failed":
                card.show_error(None)

        items = feature_items(p)
        current = v.picker.current_feature()
        if items and v.picker.combo.count() != len(items):
            ref = ((p.record("align") or {}).get("summary") or {}).get("reference")
            v.picker.set_features(items, current or ref)
        v.steps.set_choices("feature", items)
        sections = [str(s) for s in load.get("sections", [])]
        v.steps.set_choices("sections", [(s, s) for s in sections])
        cl = ((p.record("cluster") or {}).get("summary") or {}).get("clusters", [])
        self._categories = [str(c) for c in cl]
        v.steps.set_choices("clusters", [(c, c) for c in self._categories])
        if "cluster" in v.steps.cards:
            v.steps.card("cluster").form.set_row_visible("harmony", len(sections) > 1)

        # Load: section-quality suggestion
        flagged = load.get("flagged_sections") or []
        excluded = set(v.steps.card("load").form.values().get("exclude_sections", "").split(","))
        flagged = [f for f in flagged if f not in {e.strip() for e in excluded}]
        if flagged and p.status("load") == "done":
            n = len(flagged)
            shown = ", ".join(flagged[:6]) + ("…" if n > 6 else "")
            v.steps.card("load").set_banner(
                f"⚠ {n} section{'s' if n > 1 else ''} look{'' if n > 1 else 's'} empty or "
                f"low-signal ({shown}). <a href='exclude'>Exclude them</a>"
            )
        else:
            v.steps.card("load").set_banner("")
        if "cluster" in v.steps.cards:
            rec = p.record("cluster") or {}
            clustered = set((rec.get("summary") or {}).get("sections", []))
            others = [s for s in sections if s not in clustered]
            v.steps.card("cluster").set_extra_action(
                "Transfer clusters to another sample…"
                if p.status("cluster") == "done" and others
                else "",
                "transfer",
            )

    # ================================================================== running steps
    def run(self, step: str, params: Any = None) -> bool:
        p, v = self.project, self.view
        if p is None or v is None:
            return False
        if self.jobs.busy:
            self._flash("Another step is running. Wait for it or cancel it.")
            return False
        card = v.steps.card(step)
        if params is None:
            try:
                params = card.form.params()
            except (TypeError, ValueError) as exc:
                card.show_error(explain(step, exc))
                return False
        feature = v.picker.current_feature()
        self._running_step = step
        card.show_error(None)
        self.refresh()

        def work(progress):
            return run_step(p, step, params, progress=progress, feature=feature)

        return self.jobs.start(
            work,
            label=f"{STEP_TITLES[step]}…",
            on_done=lambda result: self._step_done(step),
            on_error=lambda exc: self._step_failed(step, exc),
            on_cancel=lambda: self._step_cancelled(step),
        )

    def _step_done(self, step: str) -> None:
        self._running_step = None
        self._set_idle()
        self.refresh()
        v, p = self.view, self.project
        if v is None or p is None:
            return
        nxt = next((s for s in p.steps if p.status(s) == "ready"), None)
        if nxt is not None and step != "atlas":
            v.steps.open(nxt)
        else:
            self._on_step_opened(v.steps.open_step or step)
        self._update_layers()

    def _step_failed(self, step: str, exc: BaseException) -> None:
        self._running_step = None
        err = exc if isinstance(exc, StepError) else explain(step, exc)
        if self.view is not None:
            self.view.steps.card(step).show_error(err)
        self._set_idle()
        self.refresh()
        if self.view is not None:
            self.view.steps.card(step).show_error(err)

    def _step_cancelled(self, step: str) -> None:
        self._running_step = None
        self._set_idle("Cancelled.")
        self.refresh()

    def _on_action(self, step: str, action: str) -> None:
        v, p = self.view, self.project
        if v is None or p is None:
            return
        if step == "load" and action == "exclude":
            flagged = ((p.record("load") or {}).get("summary") or {}).get("flagged_sections", [])
            form = v.steps.card("load").form
            current = [s.strip() for s in form.values()["exclude_sections"].split(",") if s.strip()]
            form.set_value("exclude_sections", ", ".join(dict.fromkeys([*current, *flagged])))
            self.run("load")
        elif step == "cluster" and action == "transfer":
            self._transfer_dialog()

    def _transfer_dialog(self) -> None:
        p = self.project
        if p is None:
            return
        load = (p.record("load") or {}).get("summary") or {}
        clustered = set(((p.record("cluster") or {}).get("summary") or {}).get("sections", []))
        others = [s for s in load.get("sections", []) if s not in clustered]
        choice, ok = QInputDialog.getItem(
            self,
            "Transfer clusters",
            "Apply these clusters to:",
            ["All other sections", *others],
            0,
            False,
        )
        if not ok:
            return
        targets = others if choice == "All other sections" else [choice]
        self.jobs.start(
            lambda progress: run_transfer(p, targets, progress=progress),
            label="Transferring clusters…",
            on_done=lambda path: (
                self._set_idle("Clusters transferred."),
                self._show_transfer(path),
            ),
            on_error=lambda exc: self._step_failed("cluster", exc),
            on_cancel=lambda: self._set_idle("Cancelled."),
        )

    def _show_transfer(self, path: str | Path) -> None:
        if self.viewer is None:
            return
        import anndata as ad

        adata = ad.read_h5ad(path)
        pixel = float(
            ((self.project.record("load") or {}).get("summary") or {}).get("pixel_size_um") or 1.0
        )
        self._apply_layer(
            LayerSpec(
                "Clusters (transferred)",
                "labels",
                cluster_label_stack(adata, self.project),
                (pixel, pixel, pixel),
            )
        )

    # ================================================================== canvas
    def _on_feature_changed(self, _feature: str) -> None:
        self._update_layers()
        if self.view is not None and self.view.steps.open_step == "normalise":
            self._update_insight("normalise")

    def _select_feature(self, feature: str) -> None:
        if self.view is not None:
            self.view.picker.set_feature(feature)

    def _update_layers(self) -> None:
        p, v = self.project, self.view
        if p is None or v is None or self.viewer is None:
            return
        feature = v.picker.current_feature()
        if feature is None:
            return
        steps = [s for s in p.steps if p.status(s) in ("done", "stale")]

        def work(progress):
            specs = []
            for i, step in enumerate(steps):
                progress(i, len(steps), "")
                try:
                    spec = layer_for(p, step, feature)
                except Cancelled:
                    raise
                except Exception:
                    # One unavailable layer (e.g. a step made stale by a failed re-run) must not
                    # blank the others; the step card already explains what to re-run.
                    continue
                if spec is not None and all(x.name != spec.name for _s, x in specs):
                    specs.append((step, spec))
            return specs

        self.view_jobs.start(
            work,
            on_done=self._apply_layers,
            on_error=lambda e: self._flash(f"View: {e}"),
            exclusive=False,
        )

    def _apply_layers(self, specs: list[tuple[str, LayerSpec]]) -> None:
        for _step, spec in specs:
            self._apply_layer(spec)
        if self.viewer is not None and self.viewer.dims.ndim == 3 and self.project is not None:
            # napari labels axes "-3, -2, -1" by default, which reads like a bug on the slider
            first = "section" if self.project.analysis == "mv3d" else "sample"
            self.viewer.dims.axis_labels = (first, "x", "y")
        self._show_step_layer(self.view.steps.open_step if self.view else None)

    def _apply_layer(self, spec: LayerSpec) -> None:
        if self.viewer is None:
            return
        layers = self.viewer.layers
        existing = next((lyr for lyr in layers if lyr.name == spec.name), None)
        if existing is not None and existing._type_string != spec.kind:
            layers.remove(existing)
            existing = None
        if existing is None:
            if spec.kind == "labels":
                layer = self.viewer.add_labels(spec.data, name=spec.name, scale=spec.scale)
                layer.metadata["metavision"] = True
                layer.mouse_drag_callbacks.append(self._labels_click)
                self._categories = spec.meta.get("categories", self._categories)
            else:
                layer = self.viewer.add_image(
                    spec.data,
                    name=spec.name,
                    scale=spec.scale,
                    colormap="magma",
                    interpolation2d="nearest",
                )
                layer.metadata["metavision"] = True
        else:
            existing.data = spec.data
            existing.scale = spec.scale
            if spec.kind == "image":
                existing.reset_contrast_limits()
            else:
                self._categories = spec.meta.get("categories", self._categories)

    def _clear_layers(self) -> None:
        if self.viewer is None:
            return
        for layer in list(self.viewer.layers):
            if layer.metadata.get("metavision"):
                self.viewer.layers.remove(layer)

    def _layer_name_for(self, step: str | None) -> str | None:
        p = self.project
        if p is None or self.viewer is None:
            return None
        names = [lyr.name for lyr in self.viewer.layers]
        order = list(p.steps)
        if step in order:  # the open step's layer, else the latest earlier one
            idx = order.index(step)
            for s in reversed(order[: idx + 1]):
                name = LAYER_NAMES.get(s)
                if name in names and p.status(s) in ("done", "stale"):
                    return name
        for s in reversed(order):
            name = LAYER_NAMES.get(s)
            if name in names:
                return name
        return None

    def _show_step_layer(self, step: str | None) -> None:
        if self.viewer is None:
            return
        target = self._layer_name_for(step)
        for layer in self.viewer.layers:
            if layer.metadata.get("metavision"):
                layer.visible = layer.name == target
        if target is not None:
            self.viewer.layers.selection.active = self.viewer.layers[target]
        want_3d = target == LAYER_NAMES["atlas"]
        if (self.viewer.dims.ndisplay == 3) != want_3d:
            self.viewer.dims.ndisplay = 3 if want_3d else 2

    def _goto_section(self, index: int) -> None:
        """Move the slider to section ``index`` of the visible layer (in world coordinates)."""
        if self.viewer is None or self.viewer.dims.ndim < 3:
            return
        layer = next(
            (lyr for lyr in self.viewer.layers if lyr.visible and lyr.metadata.get("metavision")),
            None,
        )
        if layer is None:
            self.viewer.dims.set_current_step(0, max(0, index))
            return
        z = float(layer.translate[0]) + float(layer.scale[0]) * max(0, index)
        self.viewer.dims.set_point(0, z)

    def _labels_click(self, layer, event):
        value = layer.get_value(event.position, world=True)
        if isinstance(value, int | float) and value and value > 0:
            cluster = label_to_cluster(self._categories, int(value))
            if cluster is not None:
                self._on_cluster_clicked(cluster)

    def _on_cluster_clicked(self, cluster: str) -> None:
        if (
            cluster in self._categories
            and self.viewer is not None
            and "Clusters" in self.viewer.layers
        ):
            layer = self.viewer.layers["Clusters"]
            layer.selected_label = self._categories.index(cluster) + 1
            layer.show_selected_label = True
        v = self.view
        if v is not None and "markers" in v.steps.cards and v.steps.open_step == "markers":
            form = v.steps.card("markers").form
            current = [c.strip() for c in form.values()["group_a"].split(",") if c.strip()]
            if cluster not in current:
                form.set_value("group_a", ", ".join([*current, cluster]))
        self._flash(f"Cluster {cluster} selected.")

    # ================================================================== insights
    def _on_step_opened(self, step: str) -> None:
        self._show_step_layer(step)
        self._update_insight(step)

    def _update_insight(self, step: str) -> None:
        p = self.project
        if p is None:
            return
        feature = self.view.picker.current_feature() if self.view else None
        if p.status(step) not in ("done", "stale"):
            self._hide_insights()
            return
        self.insight_jobs.start(
            lambda _progress: insight_for(p, step, feature),
            on_done=self._show_insight,
            on_error=lambda e: self._hide_insights(),
            exclusive=False,
        )

    def _show_insight(self, insight: Insight) -> None:
        if insight.kind == "none":
            self._hide_insights()
            return
        self.insights.show_insight(insight)
        if self.viewer is not None and getattr(self.viewer, "window", None) is not None:
            if self._insights_dock is None:
                self._insights_dock = self.viewer.window.add_dock_widget(
                    self.insights, area="bottom", name="Insights"
                )
            self._insights_dock.setVisible(True)

    def _hide_insights(self) -> None:
        if self._insights_dock is not None:
            self._insights_dock.setVisible(False)
