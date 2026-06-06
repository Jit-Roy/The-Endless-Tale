"""
Right sidebar — character list only, anchored to the bottom.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QSizePolicy
)
from PyQt5.QtCore import Qt

# ── Palette ──────────────────────────────────────────────────────────────────
DARK_BG      = "#111111"
CARD_BG      = "#181818"
BORDER       = "#1e1e1e"
BORDER_BTN   = "#2a2a2a"
TEXT_PRIMARY = "#e8e8e8"
TEXT_SEC     = "#888888"
TEXT_MUTED   = "#444444"
TEXT_LABEL   = "#3a3a3a"
PRESENT_DOT  = "#888888"
ABSENT_DOT   = "#333333"


def _divider() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.HLine)
    f.setStyleSheet(f"color: {BORDER};")
    f.setFixedHeight(1)
    return f


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


def _avatar_circle(name: str, size: int = 38) -> QLabel:
    parts    = name.split()
    initials = (parts[0][0] + (parts[1][0] if len(parts) > 1 else "")).upper()
    lbl = QLabel(initials)
    lbl.setFixedSize(size, size)
    lbl.setAlignment(Qt.AlignCenter)
    lbl.setStyleSheet(f"""
        QLabel {{
            background-color: #222222;
            color: #b0b0b0;
            border-radius: {size // 2}px;
            font-size: {max(10, size // 3)}px;
            font-weight: bold;
            font-family: 'Segoe UI', sans-serif;
            border: 1px solid #2e2e2e;
        }}
    """)
    return lbl


class CharacterCard(QFrame):
    """Single character card in right panel."""

    def __init__(self, data: dict, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            CharacterCard {{
                background-color: {CARD_BG};
                border: 1px solid {BORDER};
                border-radius: 6px;
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Avatar
        layout.addWidget(_avatar_circle(data.get("name", "?")))

        # Info column
        info = QVBoxLayout()
        info.setSpacing(2)

        name_lbl = QLabel(data.get("name", "—"))
        name_lbl.setStyleSheet(f"""
            color: {TEXT_PRIMARY};
            font-size: 13px;
            font-weight: bold;
            font-family: 'Segoe UI', sans-serif;
        """)
        info.addWidget(name_lbl)

        # Traits / role
        traits = data.get("traits", [])
        role_txt = "  ·  ".join(traits[:2]) if traits else "Character"
        role_lbl = QLabel(role_txt)
        role_lbl.setStyleSheet(f"""
            color: {TEXT_SEC};
            font-size: 11px;
            font-family: 'Segoe UI', sans-serif;
        """)
        info.addWidget(role_lbl)

        # Status dot + label
        in_scene = data.get("in_scene", True)
        status_row = QHBoxLayout()
        status_row.setSpacing(5)
        dot = QLabel("●")
        dot.setStyleSheet(
            f"color: {PRESENT_DOT if in_scene else ABSENT_DOT}; font-size: 7px;"
        )
        status_row.addWidget(dot)
        stat_lbl = QLabel("Present" if in_scene else "Away")
        stat_lbl.setStyleSheet(f"""
            color: {TEXT_MUTED};
            font-size: 11px;
            font-family: 'Segoe UI', sans-serif;
        """)
        status_row.addWidget(stat_lbl)
        status_row.addStretch()
        info.addLayout(status_row)

        layout.addLayout(info, stretch=1)


class SectionHeader(QWidget):
    """Collapsible section header (PRESENT / ABSENT)."""

    def __init__(self, title: str, count: int = 0, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 6, 0, 6)
        layout.setSpacing(6)

        lbl = QLabel(f"{title}  ({count})")
        lbl.setStyleSheet(f"""
            color: {TEXT_MUTED};
            font-size: 11px;
            font-weight: bold;
            letter-spacing: 0.5px;
            font-family: 'Segoe UI', sans-serif;
        """)
        layout.addWidget(lbl)
        layout.addStretch()

        arrow = QLabel("∨")
        arrow.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 10px;")
        layout.addWidget(arrow)


class StatusPanel(QWidget):
    """Right sidebar panel."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(270)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.setStyleSheet(f"background-color: {DARK_BG};")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Header ───────────────────────────────────────────────────────
        hdr_widget = QWidget()
        hdr_widget.setFixedHeight(56)
        hdr_widget.setStyleSheet(f"background-color: {DARK_BG};")
        hl = QHBoxLayout(hdr_widget)
        hl.setContentsMargins(14, 0, 14, 0)
        hl.setSpacing(8)

        people_icon = QLabel("👥")
        people_icon.setStyleSheet("font-size: 13px; color: #555555;")
        hl.addWidget(people_icon)

        hdr_lbl = QLabel("CHARACTERS")
        hdr_lbl.setStyleSheet(f"""
            color: {TEXT_PRIMARY};
            font-size: 13px;
            font-weight: bold;
            letter-spacing: 1.5px;
            font-family: 'Segoe UI', sans-serif;
        """)
        hl.addWidget(hdr_lbl)
        hl.addStretch()

        outer.addWidget(hdr_widget)
        outer.addWidget(_divider())

        # ── Scrollable character list ────────────────────────────────────
        char_scroll = QScrollArea()
        char_scroll.setWidgetResizable(True)
        char_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        char_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        char_scroll.setStyleSheet(f"""
            QScrollArea {{ border: none; background: {DARK_BG}; }}
            QScrollBar:vertical {{
                background: {DARK_BG}; width: 3px; border: none;
            }}
            QScrollBar::handle:vertical {{
                background: #252525; border-radius: 1px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        """)

        char_body = QWidget()
        char_body.setStyleSheet(f"background-color: {DARK_BG};")
        self._char_layout = QVBoxLayout(char_body)
        self._char_layout.setContentsMargins(10, 10, 10, 10)
        self._char_layout.setSpacing(6)
        self._char_layout.addStretch()

        # Present section header
        self._present_header = SectionHeader("PRESENT", 0)
        self._char_layout.insertWidget(0, self._present_header)

        # Absent section (inserted after present cards)
        self._absent_header = SectionHeader("ABSENT", 0)

        char_scroll.setWidget(char_body)
        outer.addWidget(char_scroll, stretch=1)

        self._cards: dict[str, CharacterCard] = {}
        self._char_body_layout = self._char_layout

    # ── Public API ───────────────────────────────────────────────────────

    def update_characters(self, characters: list):
        """
        characters: list of {name, objective, in_scene, traits}
        Creates/updates cards, separating present from absent.
        """
        present = [c for c in characters if c.get("in_scene", True)]
        absent  = [c for c in characters if not c.get("in_scene", True)]

        # Remove old cards
        for name, card in list(self._cards.items()):
            card.setParent(None)
            card.deleteLater()
        self._cards.clear()

        # Remove absent header if present
        layout = self._char_body_layout
        # Clear layout except stretch
        while layout.count() > 1:
            item = layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

        # Rebuild
        insert_pos = 0

        # Present section
        self._present_header = SectionHeader("PRESENT", len(present))
        layout.insertWidget(insert_pos, self._present_header)
        insert_pos += 1

        for data in present:
            card = CharacterCard(data)
            layout.insertWidget(insert_pos, card)
            self._cards[data["name"]] = card
            insert_pos += 1

        # Absent section
        if absent:
            layout.insertSpacing(insert_pos, 6)
            insert_pos += 1
            self._absent_header = SectionHeader("ABSENT", len(absent))
            layout.insertWidget(insert_pos, self._absent_header)
            insert_pos += 1
            for data in absent:
                card = CharacterCard(data)
                layout.insertWidget(insert_pos, card)
                self._cards[data["name"]] = card
                insert_pos += 1
