"""The Insights panel: the one chart that matters for the open step, linked to the canvas."""

from __future__ import annotations

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from qtpy.QtCore import Signal
from qtpy.QtWidgets import QLabel, QVBoxLayout, QWidget

from metavision_studio.workflows.display import Insight

__all__ = ["InsightsPanel"]

_FG = "#d7dae0"
_MUTED = "#8b919c"
_ACCENT = "#5aa9ff"
_WARN = "#f0b232"


class InsightsPanel(QWidget):
    section_clicked = Signal(int)
    cluster_clicked = Signal(str)
    feature_clicked = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(2)
        self.title = QLabel(self)
        self.title.setObjectName("insightTitle")
        layout.addWidget(self.title)
        self.figure = Figure(figsize=(6, 1.8), facecolor="none", layout="constrained")
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.setStyleSheet("background: transparent;")
        self.canvas.setMinimumHeight(140)
        layout.addWidget(self.canvas, 1)
        self.note = QLabel(self)
        self.note.setObjectName("insightNote")
        self.note.setWordWrap(True)
        layout.addWidget(self.note)
        self.insight = Insight("none", "")
        self._pick_cid = None
        self._click_cid = None

    # ------------------------------------------------------------------ drawing
    def _axes(self):
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.set_facecolor("none")
        for spine in ("top", "right"):
            ax.spines[spine].set_visible(False)
        for spine in ("left", "bottom"):
            ax.spines[spine].set_color(_MUTED)
        ax.tick_params(colors=_MUTED, labelsize=8)
        ax.xaxis.label.set_color(_FG)
        ax.yaxis.label.set_color(_FG)
        return ax

    def show_insight(self, insight: Insight) -> None:
        self.insight = insight
        self.title.setText(insight.title)
        self.note.setText("")
        for cid in (self._pick_cid, self._click_cid):
            if cid is not None:
                self.canvas.mpl_disconnect(cid)
        self._pick_cid = self._click_cid = None
        draw = getattr(self, f"_draw_{insight.kind}", None)
        if draw is None:
            self.figure.clear()
        else:
            draw(insight)
        self.canvas.draw_idle()

    def _draw_boxplot(self, ins: Insight) -> None:
        ax = self._axes()
        before, after = ins.data["before"], ins.data["after"]
        sections = list(after)
        pos = np.arange(len(sections))
        kw = dict(widths=0.35, showfliers=False, patch_artist=True, manage_ticks=False)
        b1 = ax.boxplot(
            [before.get(s, np.array([0.0])) for s in sections], positions=pos - 0.2, **kw
        )
        b2 = ax.boxplot([after[s] for s in sections], positions=pos + 0.2, **kw)
        for parts, colour in ((b1, _MUTED), (b2, _ACCENT)):
            for patch in parts["boxes"]:
                patch.set(facecolor=colour, alpha=0.55, edgecolor=colour)
            for key in ("whiskers", "caps", "medians"):
                for line in parts[key]:
                    line.set(color=colour, linewidth=0.8)
        step = max(1, len(sections) // 20)
        ax.set_xticks(pos[::step], [sections[i] for i in range(0, len(sections), step)])
        ax.set_xlabel("section")
        ax.legend(
            [b1["boxes"][0], b2["boxes"][0]],
            ["before", "after"],
            frameon=False,
            labelcolor=_FG,
            fontsize=8,
            loc="upper right",
        )
        self._click_cid = self.canvas.mpl_connect("button_press_event", self._section_click)

    def _draw_scores(self, ins: Insight) -> None:
        ax = self._axes()
        df = ins.data
        scores = df["score"].to_numpy(dtype=float)
        x = np.arange(len(scores))
        finite = scores[np.isfinite(scores)]
        cut = float(np.median(finite) - 2 * np.std(finite)) if finite.size > 2 else -np.inf
        low = [i for i in x if np.isfinite(scores[i]) and scores[i] < cut] + list(
            ins.meta.get("failed", [])
        )
        colours = [_WARN if i in low else _ACCENT for i in x]
        ax.bar(x, np.nan_to_num(scores), color=colours, width=0.8)
        ax.set_ylim(min(0.0, float(np.nanmin(scores)) if finite.size else 0.0), 1.0)
        ax.set_xlabel("section")
        ax.set_ylabel("similarity")
        sections = df["section"].astype(str).tolist()
        step = max(1, len(x) // 20)
        ax.set_xticks(x[::step], sections[::step])
        flagged = sorted({sections[i] for i in low if i < len(sections)})
        self.note.setText(
            f"Low alignment: section{'s' if len(flagged) > 1 else ''} {', '.join(flagged)}. "
            "Click a bar to view it."
            if flagged
            else "Click a bar to view that section."
        )
        self._click_cid = self.canvas.mpl_connect("button_press_event", self._section_click)

    def _section_click(self, event) -> None:
        if event.inaxes is not None and event.xdata is not None:
            self.section_clicked.emit(round(event.xdata))

    def _draw_umap(self, ins: Insight) -> None:
        import matplotlib as mpl

        ax = self._axes()
        df = ins.data
        cats = ins.meta.get("categories") or sorted(df["cluster"].unique())
        cmap = mpl.colormaps["tab20"]
        colour_of = {c: cmap(i % 20) for i, c in enumerate(cats)}
        ax.scatter(
            df["u1"],
            df["u2"],
            s=1.5,
            c=[colour_of[c] for c in df["cluster"]],
            linewidths=0,
            rasterized=True,
        )
        for c in cats:
            pts = df.loc[df["cluster"] == c, ["u1", "u2"]]
            if len(pts):
                ax.text(
                    *pts.median().to_numpy(),
                    str(c),
                    color=_FG,
                    fontsize=7,
                    ha="center",
                    va="center",
                )
        ax.set_xticks([])
        ax.set_yticks([])
        self.note.setText("Click a cluster to highlight it in the canvas.")
        self._click_cid = self.canvas.mpl_connect("button_press_event", self._umap_click)

    def _umap_click(self, event) -> None:
        if event.inaxes is None or event.xdata is None:
            return
        df = self.insight.data
        d = (df["u1"] - event.xdata) ** 2 + (df["u2"] - event.ydata) ** 2
        self.cluster_clicked.emit(str(df["cluster"].iloc[int(np.argmin(d.to_numpy()))]))

    def _draw_volcano(self, ins: Insight) -> None:
        ax = self._axes()
        df = ins.data.copy()
        if df.empty or "log2fc" not in df:
            self.note.setText("No markers found with these settings.")
            return
        p = (df["padj"] if "padj" in df else df["pvalue"]).to_numpy(dtype=float)
        positive = p[p > 0]
        # p = 0 (underflow) would sit at an arbitrary wall; put it just above the smallest p
        floor = positive.min() / 10 if positive.size else 1e-300
        y = -np.log10(np.clip(p, floor, 1.0))
        x = df["log2fc"].to_numpy(dtype=float)
        sig = df["significant"].astype(bool).to_numpy() if "significant" in df else y > 1.3
        ax.scatter(x[~sig], y[~sig], s=8, color=_MUTED, linewidths=0)
        ax.scatter(x[sig], y[sig], s=12, color=_ACCENT, linewidths=0)
        names = (df["name"] if "name" in df else df["feature"]).astype(str).to_numpy()
        candidates = np.flatnonzero(sig) if sig.any() else np.arange(len(x))
        top = candidates[np.argsort(-np.abs(x[candidates]))][:5]
        for k, i in enumerate(top):
            ax.annotate(
                names[i],
                (x[i], y[i]),
                fontsize=7,
                color=_FG,
                xytext=(4, -10 * k + 4),
                textcoords="offset points",
            )
        ax.axvline(0, color=_MUTED, linewidth=0.5)
        ax.set_xlabel("log2 fold change")
        ax.set_ylabel("-log10 adj. p")
        self.note.setText(f"{int(sig.sum())} significant markers. Click a point to view it.")
        self._xy = np.column_stack([x, y])
        self._click_cid = self.canvas.mpl_connect("button_press_event", self._volcano_click)

    def _volcano_click(self, event) -> None:
        if event.inaxes is None or event.xdata is None:
            return
        xy = self._xy
        span = np.ptp(xy, axis=0) + 1e-9
        d = (((xy - [event.xdata, event.ydata]) / span) ** 2).sum(axis=1)
        i = int(np.argmin(d))
        col = "feature" if "feature" in self.insight.data else "name"
        self.feature_clicked.emit(str(self.insight.data[col].iloc[i]))

    def _draw_pathways(self, ins: Insight) -> None:
        ax = self._axes()
        df = ins.data
        if df.empty:
            self.note.setText("No enriched pathways at this FDR.")
            return
        df = df.sort_values("padj" if "padj" in df else "pvalue").head(12).iloc[::-1]
        p = df["padj"] if "padj" in df else df["pvalue"]
        y = np.arange(len(df))
        size = (df["hits"] if "hits" in df else np.ones(len(df))) * 12
        ax.scatter(-np.log10(p.clip(lower=1e-300)), y, s=size, color=_ACCENT)
        ax.set_yticks(y, df["pathway"].astype(str).str.slice(0, 40))
        ax.set_xlabel("-log10 adj. p")
        self._pathways = df.reset_index(drop=True)
        self.note.setText("Click a pathway to list its member molecules.")
        self._click_cid = self.canvas.mpl_connect("button_press_event", self._pathway_click)

    def _pathway_click(self, event) -> None:
        if event.inaxes is None or event.ydata is None:
            return
        i = round(event.ydata)
        if 0 <= i < len(self._pathways):
            row = self._pathways.iloc[i]
            members = row.get("members", "")
            self.note.setText(f"<b>{row['pathway']}</b>: {members}")
