"""
Left sidebar — Logo, Story info, Objectives list with status icons, Location.
"""

from datetime import datetime
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QProgressBar, QScrollArea, QSizePolicy
)
from PyQt5.QtCore import Qt

# ── Palette ──────────────────────────────────────────────────────────────────
DARK_BG      = "#111111"
BORDER       = "#1e1e1e"
TEXT_PRIMARY = "#e8e8e8"
TEXT_SEC     = "#888888"
TEXT_MUTED   = "#444444"
TEXT_LABEL   = "#3a3a3a"
OBJ_COMPLETE = "#555555"
OBJ_ACTIVE   = "#e8e8e8"
OBJ_FUTURE   = "#404040"
BAR_BG       = "#1e1e1e"
BAR_FILL     = "#555555"


def _section_lbl(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(f"""
        color: {TEXT_LABEL};
        font-size: 10px;
        font-weight: bold;
        letter-spacing: 2px;
        font-family: 'Segoe UI', sans-serif;
    """)
    return lbl


def _divider() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.HLine)
    f.setStyleSheet(f"color: {BORDER}; margin: 0px;")
    f.setFixedHeight(1)
    return f


class ObjectiveItem(QWidget):
    """Single objective row: icon + text."""

    def __init__(self, text: str, status: str, parent=None):
        """status: 'completed' | 'active' | 'future'"""
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 3, 0, 3)
        layout.setSpacing(9)

        if status == "completed":
            icon_txt   = "✓"
            icon_color = "#555555"
            text_color = OBJ_COMPLETE
            bold       = False
            font_sz    = 12
        elif status == "active":
            icon_txt   = "●"
            icon_color = "#aaaaaa"
            text_color = OBJ_ACTIVE
            bold       = True
            font_sz    = 13
        else:
            icon_txt   = "○"
            icon_color = "#303030"
            text_color = OBJ_FUTURE
            bold       = False
            font_sz    = 12

        icon = QLabel(icon_txt, self)
        icon.setFixedWidth(14)
        icon.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        icon.setStyleSheet(
            f"color: {icon_color}; font-size: 10px; padding-top: 1px;"
        )
        layout.addWidget(icon)

        weight = "bold" if bold else "normal"
        txt = QLabel(text, self)
        txt.setWordWrap(True)
        txt.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        txt.setStyleSheet(f"""
            color: {text_color};
            font-size: {font_sz}px;
            font-weight: {weight};
            font-family: 'Segoe UI', sans-serif;
            line-height: 1.4;
        """)
        layout.addWidget(txt, stretch=1)


class StoryPanel(QWidget):
    """Left sidebar panel."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(255)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.setStyleSheet(f"background-color: {DARK_BG};")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Logo ─────────────────────────────────────────────────────────
        logo = QWidget()
        logo.setFixedHeight(56)
        logo.setStyleSheet(f"background-color: {DARK_BG};")
        ll = QHBoxLayout(logo)
        ll.setContentsMargins(16, 0, 16, 0)
        ll.setSpacing(10)

        shield = QLabel("⬡")
        shield.setStyleSheet("color: #666666; font-size: 16px;")
        ll.addWidget(shield)

        brand = QLabel("The Endless Tale")
        brand.setStyleSheet(f"""
            color: {TEXT_PRIMARY};
            font-size: 17px;
            font-weight: bold;
            font-family: 'Segoe UI', sans-serif;
            letter-spacing: 1px;
        """)
        ll.addWidget(brand)
        ll.addStretch()

        outer.addWidget(logo)
        outer.addWidget(_divider())

        # ── Scrollable content ───────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setStyleSheet(f"""
            QScrollArea {{ border: none; background: {DARK_BG}; }}
            QScrollBar:vertical {{
                background: {DARK_BG}; width: 3px; border: none;
            }}
            QScrollBar::handle:vertical {{
                background: #252525; border-radius: 1px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        """)

        body = QWidget()
        body.setStyleSheet(f"background-color: {DARK_BG};")
        bl = QVBoxLayout(body)
        bl.setContentsMargins(16, 18, 16, 18)
        bl.setSpacing(0)

        # ── STORY ───────────────────────────────────────────────────────
        bl.addWidget(_section_lbl("STORY"))
        bl.addSpacing(8)

        self._story_title = QLabel("—")
        self._story_title.setWordWrap(True)
        self._story_title.setStyleSheet(f"""
            color: {TEXT_PRIMARY};
            font-size: 16px;
            font-weight: bold;
            font-family: 'Segoe UI', sans-serif;
            line-height: 1.3;
        """)
        bl.addWidget(self._story_title)
        bl.addSpacing(7)

        self._story_desc = QLabel("")
        self._story_desc.setWordWrap(True)
        self._story_desc.setStyleSheet(f"""
            color: {TEXT_SEC};
            font-size: 12px;
            font-family: 'Segoe UI', sans-serif;
            line-height: 1.4;
        """)
        bl.addWidget(self._story_desc)

        bl.addSpacing(22)

        # ── OBJECTIVES ──────────────────────────────────────────────────
        bl.addWidget(_section_lbl("OBJECTIVES"))
        bl.addSpacing(8)

        # Chapter + counter row
        ch_row = QHBoxLayout()
        ch_row.setSpacing(4)
        self._chapter_lbl = QLabel("—")
        self._chapter_lbl.setWordWrap(True)
        self._chapter_lbl.setStyleSheet(f"""
            color: {TEXT_PRIMARY};
            font-size: 13px;
            font-weight: bold;
            font-family: 'Segoe UI', sans-serif;
        """)
        ch_row.addWidget(self._chapter_lbl, stretch=1)

        self._counter_lbl = QLabel("")
        self._counter_lbl.setStyleSheet(f"""
            color: {TEXT_MUTED};
            font-size: 12px;
            font-family: 'Segoe UI', sans-serif;
        """)
        ch_row.addWidget(self._counter_lbl)
        bl.addLayout(ch_row)

        bl.addSpacing(7)

        self._progress_bar = QProgressBar()
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setFixedHeight(3)
        self._progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {BAR_BG};
                border: none;
                border-radius: 1px;
            }}
            QProgressBar::chunk {{
                background-color: {BAR_FILL};
                border-radius: 1px;
            }}
        """)
        bl.addWidget(self._progress_bar)
        bl.addSpacing(12)

        self._obj_layout = QVBoxLayout()
        self._obj_layout.setSpacing(1)
        bl.addLayout(self._obj_layout)

        bl.addSpacing(22)

        # ── LOCATION ────────────────────────────────────────────────────
        bl.addWidget(_section_lbl("LOCATION"))
        bl.addSpacing(8)

        loc_row = QHBoxLayout()
        loc_row.setSpacing(7)
        pin = QLabel("○")
        pin.setFixedWidth(14)
        pin.setStyleSheet("color: #444444; font-size: 11px;")
        loc_row.addWidget(pin)

        self._loc_lbl = QLabel("—")
        self._loc_lbl.setWordWrap(True)
        self._loc_lbl.setStyleSheet(f"""
            color: {TEXT_PRIMARY};
            font-size: 13px;
            font-family: 'Segoe UI', sans-serif;
        """)
        loc_row.addWidget(self._loc_lbl, stretch=1)
        bl.addLayout(loc_row)

        bl.addSpacing(3)

        self._tod_lbl = QLabel("")
        self._tod_lbl.setStyleSheet(f"""
            color: {TEXT_SEC};
            font-size: 12px;
            font-family: 'Segoe UI', sans-serif;
            padding-left: 21px;
        """)
        bl.addWidget(self._tod_lbl)

        bl.addStretch()

        scroll.setWidget(body)
        outer.addWidget(scroll, stretch=1)

        # Bottom nav removed (icons were decorative and unused)

    # ── Public API ───────────────────────────────────────────────────────

    def update_story(self, data: dict):
        """
        data: {title, description, objectives: list[str],
               current_objective_index, beat_index, total_beats, complete}
        """
        self._story_title.setText(data.get("title", "—"))
        desc = data.get("description", "")
        # Truncate description to ~120 chars for sidebar
        if len(desc) > 120:
            desc = desc[:117] + "…"
        self._story_desc.setText(desc)

        objectives = data.get("objectives", [])
        cur_idx    = data.get("current_objective_index", 0)
        total      = data.get("total_beats", len(objectives))
        beat_idx   = data.get("beat_index", cur_idx + 1)

        # Chapter label
        self._chapter_lbl.setText(f"Chapter {beat_idx}: Into the Unknown")
        self._counter_lbl.setText(f"{cur_idx} / {total}")

        if total > 0:
            self._progress_bar.setMaximum(total)
            self._progress_bar.setValue(cur_idx)

        # Rebuild objectives list
        while self._obj_layout.count():
            item = self._obj_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for i, obj_text in enumerate(objectives):
            if i < cur_idx:
                status = "completed"
            elif i == cur_idx:
                status = "active"
            else:
                status = "future"
            self._obj_layout.addWidget(ObjectiveItem(obj_text, status, self._obj_layout.parentWidget()))

    def update_location(self, location: str, time_of_day: str = ""):
        self._loc_lbl.setText(location or "—")
        self._tod_lbl.setText(time_of_day or "")
