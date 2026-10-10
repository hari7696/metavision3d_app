# MetaVision Studio: UX design

**Status:** implemented (Phase 5 of the [roadmap](roadmap.md)); open polish items are listed there

## Who we're designing for

A lab scientist with MALDI imaging exports and a biological question, not a programmer. They run
the analysis a few times per study, so they won't remember settings between runs. They want three
things: to see their tissue, trust the result, and get figures plus a methods paragraph out the
other end.

## What made the 2024 app feel heavy

| 2024 app | Why it hurt |
|---|---|
| Algorithm dropdown → file-type dropdown → 8-button step bar | Three navigation systems before seeing any data |
| 8 SAMI steps (Visualization, Normalization, Pooling, Grouping, Clustering, Integration, Markers, Pathways) | Bookkeeping steps (Pooling, Grouping) were exposed as science steps |
| File picker inside every step | The user had to remember which output fed which step |
| A molecule dropdown and a colormap dropdown in every step | The same choice made over and over |
| Thumbnail grid, Slide tab, Animation tab, separate vedo 3D window | Four viewers for one stack of images |
| Stopwatch and fixed "takes 15+ min" labels | No real progress and no cancel |
| Modal error boxes saying "take a screenshot" | Errors interrupted work and couldn't be acted on |
| Steps crashed when opened out of order | Hidden dependencies |

## Principles

1. **The canvas is the viewer.** Every spatial result (sections, aligned stack, 3D volume, cluster
   map) is a napari layer. There are no thumbnail grids or image tabs. napari already provides
   colormaps, contrast, a section slider, a 2D/3D toggle and screenshots, so we don't rebuild them.
2. **One panel, one step open at a time.** A vertical list of steps, accordion-style. A step shows
   at most 3 essential settings, and everything else goes under *Advanced*. Defaults come from the papers.
3. **Choose things once.** The molecule, the data and physical units are chosen once and apply everywhere.
   Steps read their inputs from the project, never from a file picker.
4. **Never block, never lose work.** Jobs run in the background with real progress and a Cancel
   button. The project is saved automatically. Reopening it brings you back where you were.
5. **Explain, don't alarm.** Errors appear inline in the step that failed, in plain language, with
   a suggested fix and a "copy report" button. No modal pop-ups.

## Layout

```
┌──────────────────────────────────────────────────────┬────────────────────────────────┐
│                                                      │ MetaVision Studio           ⋯  │
│                                                      │ ┌────────────────────────────┐ │
│                                                      │ │ mouse_brain_3d             │ │
│               napari canvas                          │ │ 79 sections · 1,204 feats  │ │
│   (selected molecule, latest result)                 │ │ 20 µm pixels               │ │
│                                                      │ └────────────────────────────┘ │
│                                                      │ Molecule [🔍 PC(34:1) 760.58 ▾]│
│                                                      │                                │
│                                                      │ ✓ Load data                    │
│                                                      │ ✓ Normalise                    │
│                                                      │ ▼ Align sections        ready  │
│                                                      │   Reference  [auto (most   ▾]  │
│                                                      │               prevalent)       │
│                                                      │   ▸ Advanced                   │
│                                                      │              [ Align ]         │
│ section ━━━━━━━━━●━━━━━━━━━━━━ 14 / 79     [2D|3D]   │ ○ Fill gaps                    │
├──────────────────────────────────────────────────────┤ ○ 3D atlas & export            │
│ Insights: alignment quality per section     ▾ hide  │                                │
│  ▁▂▂▃▅▇▇▇▇▆▇▇▇▇▂▇▇▇▇  section 19 low, click to view │ ────────────────────────────── │
│                                                      │ Aligning 14/79 ▓▓▓▓░░░  Cancel │
└──────────────────────────────────────────────────────┴────────────────────────────────┘
```

- **Right: Workflow panel.** It has a project card, the global molecule picker, the step list and a
  status line at the bottom.
- **Bottom: Insights panel.** It shows the one chart that matters for the open step (box plots,
  alignment score, UMAP, volcano, pathway dots), and collapses when the step has no chart. Charts
  are **linked to the canvas**: click a section, cluster, marker or pathway and the canvas follows.
- **Step states:** `○` not run · `◐` running · `✓` done · `⚠` out of date (an earlier step changed)
  · `✕` failed. A locked step tells you what to run first ("Run *Normalise* first").

## Flow

### 1. Start

```
┌ MetaVision Studio ───────────────┐
│  New project from data…          │
│  Open project…                   │
│  Try the example dataset         │   ← downloads public data from Zenodo
│                                  │
│  Recent                          │
│   mouse_brain_3d     2 days ago  │
│   cerebellum_sami    last week   │
└──────────────────────────────────┘
```

### 2. Load data (one screen, not a wizard)

```
┌ New project ─────────────────────────────────────────────┐
│ Files   [ drop CSV / Parquet / imzML here ]              │
│   brain_lipids.csv      Lipids       ▾   ✓ 12 sections   │
│   brain_metab.csv       Metabolites  ▾   ✓ 12 sections   │  ← omics type guessed from name
│                                                          │
│ Columns  x: x   y: y   section: tissue_id   ✓ 1,204 features │
│          (shown for confirmation; edit only if wrong)    │
│ Pixel size  [ 20 ] µm                                    │
│                                                          │
│ What do you want to do?                                  │
│  ( ) Build a 3D atlas        MetaVision3D: align serial  │
│                              sections into a volume      │
│  ( ) Spatial multi-omics     SAMI: clusters, markers and │
│                              pathways                    │
│                                        [ Create ]        │
└──────────────────────────────────────────────────────────┘
```

When several files describe the same sections, they're matched up automatically. That replaces the
old *Pooling* step. Afterwards the data appears in the canvas straight away (replacing the old
*Visualization* step), and the Load card shows an automatic **section check**:

> ⚠ 3 sections look empty or low-signal (7, 31, 62). **Exclude them** · Review

Flip X/Y and manual section exclusion live under *Advanced* on the Load card. You can switch
between the 3D and multi-omics analyses later without reloading.

### 3a. Build a 3D atlas (MetaVision3D): 4 steps

| Step | Essential settings | Canvas shows | Insights |
|---|---|---|---|
| **Normalise** | Method: *TIC + section median* (paper default) | normalised stack | per-section box plots, before and after |
| **Align sections** | Reference molecule: *auto* | aligned stack | alignment score per section; low scores flagged |
| **Fill gaps** | ☑ Impute missing pixels · ☑ Add sections between (1) | filled stack | — |
| **3D atlas & export** | Section thickness, gap (µm) · Export: NIfTI / TIFF / CSV · molecules: current / all / chosen | 3D volume (napari 3D) | — |

### 3b. Spatial multi-omics (SAMI): 4 steps (was 7)

| Step | Essential settings | Canvas shows | Insights |
|---|---|---|---|
| **Normalise** | Row: *Sum* · Transform: *log2* | normalised sections | box plots, before and after |
| **Cluster** | Samples: ☑ all (choosing samples is the old *Grouping*). With more than one sample: ☑ Correct batch effects. Resolution slider | cluster map (Labels layer: click a region to select its cluster) | UMAP, linked to the map |
| **Markers** | Compare [Cluster 3] vs [all other clusters]. Clicking a cluster in the canvas fills it in | selected marker | volcano plot + table. Clicking a marker switches the global molecule picker |
| **Pathways** | none required (library chosen from the omics type) | — | pathway dot plot. Click a pathway to list its member markers |

The old *Clusters Integration* step becomes an action on the Cluster card: **"Transfer these
clusters to another sample…"**.

### 4. Finish

The `⋯` menu on the project card has:

- **Copy methods text.** A ready-to-paste methods paragraph listing every step that ran, with its
  parameters, software versions and the MetaVision3D and SAMI citations.
- **Open project folder.** Shows all outputs, with plain names and a `project.json` record of the run.

## What we deliberately leave out

- Colormap and contrast controls: napari's layer controls already do this.
- Thumbnail grids and animation tabs: the section slider, 2D/3D toggle and napari's grid mode cover them.
- Timers and "this takes N minutes" labels: real progress bars instead.
- Per-step file pickers and tracker CSVs: the project manifest replaces them.
- Separate Pooling, Grouping and Integration steps: folded into Load and Cluster.
- Prism export: removed.

## How this keeps the code lean too

Each step is a typed function in the headless core (`mv3d.align(stack, reference="auto", ...)`).
The GUI form is **generated** from that signature with magicgui. Parameters tagged *advanced*
collapse under *Advanced*. So the notebook API and the GUI can't drift apart, and adding a parameter
means changing one function, not a hand-built form.

## Open questions

- Do users run both analyses on the same data, so the project should hold both? The current design
  allows switching.
- Typical dataset size (sections × pixels × features) decides whether every feature is held in
  memory or loaded on demand.
- Should the Markers step also offer a case-vs-control mode (the old "dual" mode) on the first
  screen, or keep it under *Advanced*?
