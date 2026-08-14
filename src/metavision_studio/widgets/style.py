"""A small stylesheet that sits quietly on top of napari's dark and light themes."""

STYLESHEET = """
#studio QLabel#appTitle { font-size: 17px; font-weight: 600; }
#studio QLabel#appSubtitle, #studio QLabel#muted, #studio QLabel#stepState,
#studio QLabel#credit, #studio QLabel#insightNote, #studio QLabel#stepHint {
    color: #9aa0a6;
}
#studio QLabel#muted, #studio QLabel#stepState, #studio QLabel#credit { font-size: 11px; }
#studio QLabel#sectionLabel { font-weight: 600; margin-top: 4px; }
#studio QFrame#projectCard {
    background: rgba(127, 127, 127, 0.10);
    border-radius: 6px;
}
#studio QLabel#projectName { font-weight: 600; font-size: 13px; }
#studio QToolButton#menuButton { font-size: 15px; padding: 0 6px; border: none; }
#studio QToolButton#menuButton::menu-indicator { image: none; width: 0; }
#studio QFrame#stepCard { border-bottom: 1px solid rgba(127, 127, 127, 0.18); }
#studio QFrame#stepCard[open="true"] { background: rgba(127, 127, 127, 0.07); }
#studio QLabel#stepTitle { font-weight: 600; }
#studio QLabel#stepResult { font-size: 11px; }
#studio QLabel#stepBanner {
    background: rgba(240, 178, 50, 0.14);
    border-radius: 4px;
    padding: 6px;
}
#studio QFrame#errorBox {
    background: rgba(239, 91, 91, 0.12);
    border: 1px solid rgba(239, 91, 91, 0.45);
    border-radius: 4px;
}
#studio QLabel#errorText { color: #ef5b5b; }
#studio QPushButton#runButton, #studio QPushButton#primaryButton { font-weight: 600; }
#studio QToolButton#advancedToggle { border: none; padding: 0; color: #9aa0a6; }
#studio QListWidget#recentList { background: transparent; }
#studio QProgressBar { border: none; border-radius: 3px; background: rgba(127,127,127,0.25); }
#studio QProgressBar::chunk { border-radius: 3px; background: #5aa9ff; }
"""
