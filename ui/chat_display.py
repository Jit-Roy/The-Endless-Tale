"""
Chat display — premium widget-based message cards matching the RoleRealm reference design.
Each message type is rendered as its own styled QFrame card inside a QScrollArea.
"""

from datetime import datetime
from PyQt5.QtWidgets import (
    QScrollArea, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFrame, QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer

# ── Palette ─────────────────────────────────────────────────────────────────
MAIN_BG      = "#161616"
CARD_BG      = "#1c1c1c"
CARD_SCENE   = "#181818"
BORDER       = "#252525"
TEXT_PRIMARY = "#f0f0f0"
TEXT_ACTION  = "#777777"
TEXT_MUTED   = "#4a4a4a"
TEXT_TS      = "#444444"


# ── Helpers ──────────────────────────────────────────────────────────────────

def _fmt_ts(ts_str: str) -> str:
    if not ts_str:
        return datetime.now().strftime("%H:%M")
    try:
        return datetime.fromisoformat(ts_str).strftime("%H:%M")
    except Exception:
        return ""


def _badge(symbol: str, size: int = 30, bg: str = "#222222",
           fg: str = "#666666", font_size: int = 11) -> QLabel:
    """Circular icon badge."""
    lbl = QLabel(symbol)
    lbl.setFixedSize(size, size)
    lbl.setAlignment(Qt.AlignCenter)
    lbl.setStyleSheet(f"""
        QLabel {{
            background-color: {bg};
            color: {fg};
            border-radius: {size // 2}px;
            font-size: {font_size}px;
        }}
    """)
    return lbl


def _avatar(name: str, size: int = 34) -> QLabel:
    """Circular avatar with initials."""
    parts = name.split()
    initials = (parts[0][0] + (parts[1][0] if len(parts) > 1 else "")).upper()
    lbl = QLabel(initials)
    lbl.setFixedSize(size, size)
    lbl.setAlignment(Qt.AlignCenter)
    lbl.setStyleSheet(f"""
        QLabel {{
            background-color: #262626;
            color: #b0b0b0;
            border-radius: {size // 2}px;
            font-size: {max(9, size // 3)}px;
            font-weight: bold;
            font-family: 'Segoe UI', sans-serif;
            border: 1px solid #303030;
        }}
    """)
    return lbl


def _ts_label(ts: str) -> QLabel:
    lbl = QLabel(ts)
    lbl.setStyleSheet(
        f"color: {TEXT_TS}; font-size: 10px; font-family: 'Segoe UI', sans-serif;"
        f"color: {TEXT_TS}; font-size: 11px; font-family: 'Segoe UI', sans-serif;"
    )
    lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
    return lbl


def _tag_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(f"""
        color: {TEXT_MUTED};
        font-size: 11px;
        font-weight: bold;
        letter-spacing: 1.2px;
        font-family: 'Segoe UI', sans-serif;
    """)
    return lbl


def _text(content: str, color: str = TEXT_PRIMARY,
          size: int = 14, italic: bool = False,
          bold: bool = False) -> QLabel:
    weight = "bold" if bold else "normal"
    style_flag = "italic" if italic else "normal"
    lbl = QLabel(content)
    lbl.setWordWrap(True)
    lbl.setAlignment(Qt.AlignLeft | Qt.AlignTop)
    lbl.setStyleSheet(f"""
        color: {color};
        font-size: {size}px;
        font-style: {style_flag};
        font-weight: {weight};
        font-family: 'Segoe UI', sans-serif;
        line-height: 1.5;
    """)
    return lbl


# ── Card base ─────────────────────────────────────────────────────────────────

class _Card(QFrame):
    def __init__(self, bg: str = CARD_BG, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.setStyleSheet(f"""
            _Card {{
                background-color: {bg};
                border: 1px solid {BORDER};
                border-radius: 8px;
            }}
        """)


# ── Message card types ────────────────────────────────────────────────────────

class SceneCard(_Card):
    def __init__(self, event: dict, parent=None):
        super().__init__(CARD_SCENE, parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        scene_type = event.get("scene_type", "environmental").upper()
        location   = event.get("location", "")
        desc       = event.get("description", "")
        ts         = _fmt_ts(event.get("timestamp", ""))

        # Header
        hdr = QHBoxLayout()
        hdr.setSpacing(10)
        hdr.addWidget(_badge("⛰", 28, "#1e1e1e", "#555555", 11))

        tag_col = QVBoxLayout()
        tag_col.setSpacing(0)
        tag_col.addWidget(_tag_label(f"SCENE  ·  {scene_type}"))
        if location:
            loc_lbl = QLabel(location)
            loc_lbl.setStyleSheet(
                f"color: #666666; font-size: 11px; font-family: 'Segoe UI', sans-serif;"
            )
            tag_col.addWidget(loc_lbl)
        hdr.addLayout(tag_col)
        hdr.addStretch()
        hdr.addWidget(_ts_label(ts))
        layout.addLayout(hdr)

        # Description
        layout.addWidget(_text(desc, "#888888", 13, italic=True))


class PlayerCard(_Card):
    def __init__(self, event: dict, player_name: str, parent=None):
        super().__init__(CARD_BG, parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        dialogue = event.get("dialouge", "")
        ts       = _fmt_ts(event.get("timestamp", ""))

        # Header
        hdr = QHBoxLayout()
        hdr.setSpacing(10)
        hdr.addWidget(_badge("◎", 28, "#222222", "#888888", 13))

        you_lbl = QLabel("YOU")
        you_lbl.setStyleSheet(
            f"color: {TEXT_PRIMARY}; font-size: 12px; font-weight: bold; "
            "letter-spacing: 1px; font-family: 'Segoe UI', sans-serif;"
        )
        hdr.addWidget(you_lbl)
        hdr.addStretch()
        hdr.addWidget(_ts_label(ts))
        layout.addLayout(hdr)

        layout.addWidget(_text(dialogue, TEXT_PRIMARY, 14))


class CharacterCard(_Card):
    def __init__(self, event: dict, parent=None):
        super().__init__(CARD_BG, parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(0)

        character = event.get("character", "?")
        dialogue  = event.get("dialouge", "")
        action    = event.get("action_description", "")
        ts        = _fmt_ts(event.get("timestamp", ""))

        # Top row: avatar + name/ts
        top_row = QHBoxLayout()
        top_row.setSpacing(10)
        top_row.setAlignment(Qt.AlignTop)

        av = _avatar(character, 34)
        top_row.addWidget(av, 0, Qt.AlignTop)

        info_col = QVBoxLayout()
        info_col.setSpacing(3)

        # Name + timestamp
        name_row = QHBoxLayout()
        name_row.setSpacing(0)
        name_lbl = QLabel(character.upper())
        name_lbl.setStyleSheet(
            f"color: {TEXT_PRIMARY}; font-size: 12px; font-weight: bold; "
            "letter-spacing: 0.8px; font-family: 'Segoe UI', sans-serif;"
        )
        name_row.addWidget(name_lbl)
        name_row.addStretch()
        name_row.addWidget(_ts_label(ts))
        info_col.addLayout(name_row)

        # Action (italic gray)
        if action and action.lower() not in ("speaks", ""):
            info_col.addSpacing(2)
            info_col.addWidget(_text(action, TEXT_ACTION, 12, italic=True))

        # Dialogue
        if dialogue:
            info_col.addSpacing(5)
            info_col.addWidget(_text(dialogue, TEXT_PRIMARY, 14))

        top_row.addLayout(info_col, stretch=1)
        layout.addLayout(top_row)


class ActionCard(_Card):
    def __init__(self, event: dict, parent=None):
        super().__init__(CARD_SCENE, parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(6)

        character = event.get("character", "?")
        desc      = event.get("description", "")
        ts        = _fmt_ts(event.get("timestamp", ""))

        hdr = QHBoxLayout()
        hdr.setSpacing(10)
        hdr.addWidget(_badge("⬡", 28, "#1e1e1e", "#4a4a4a", 11))
        hdr.addWidget(_tag_label("ACTION  ·  SYSTEM"))
        hdr.addStretch()
        hdr.addWidget(_ts_label(ts))
        layout.addLayout(hdr)

        layout.addWidget(_text(f"{character} {desc}", "#777777", 13, italic=True))


class MovementCard(_Card):
    def __init__(self, event: dict, parent=None):
        super().__init__("#141414", parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(10)

        is_entry  = event.get("type") == "character_entry"
        character = event.get("character", "?")
        desc      = event.get("description", "")
        ts        = _fmt_ts(event.get("timestamp", ""))

        arrow = "→" if is_entry else "←"
        layout.addWidget(_badge(arrow, 24, "#1a1a1a", "#444444", 10))

        verb = "entered" if is_entry else "left"
        txt  = QLabel(f"{character} {verb}: {desc}")
        txt.setWordWrap(True)
        txt.setStyleSheet(
            f"color: #4a4a4a; font-size: 11px; font-style: italic; font-family: 'Segoe UI', sans-serif;"
        )
        layout.addWidget(txt, stretch=1)
        layout.addWidget(_ts_label(ts))


class SystemMsg(QWidget):
    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 3, 14, 3)
        lbl = QLabel(text)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 10px; font-style: italic; font-family: 'Segoe UI', sans-serif;"
        )
        layout.addWidget(lbl)


# ── Main scroll container ─────────────────────────────────────────────────────

class ChatDisplay(QScrollArea):
    def __init__(self, player_name: str = "Player", parent=None):
        super().__init__(parent)
        self.player_name = player_name

        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setStyleSheet(f"""
            QScrollArea {{
                background-color: {MAIN_BG};
                border: none;
            }}
            QScrollBar:vertical {{
                background: #141414;
                width: 4px;
                border: none;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: #2e2e2e;
                border-radius: 2px;
                min-height: 30px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
        """)

        self._content = QWidget()
        self._content.setStyleSheet(f"background-color: {MAIN_BG};")
        self._layout = QVBoxLayout(self._content)
        self._layout.setContentsMargins(12, 14, 12, 14)
        self._layout.setSpacing(6)
        self._layout.addStretch()

        self.setWidget(self._content)

    # ── Public API ───────────────────────────────────────────────────────

    def append_event(self, event: dict):
        t    = event.get("type", "")
        char = event.get("character", "")

        if t == "message":
            card = PlayerCard(event, self.player_name) if char == self.player_name \
                   else CharacterCard(event)
        elif t == "scene":
            card = SceneCard(event)
        elif t == "action":
            card = ActionCard(event)
        elif t in ("character_entry", "character_exit"):
            card = MovementCard(event)
        else:
            return

        self._insert(card)

    def append_system(self, text: str):
        self._insert(SystemMsg(text))

    def clear_display(self):
        while self._layout.count() > 1:
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    # ── Private ──────────────────────────────────────────────────────────

    def _insert(self, widget: QWidget):
        self._layout.insertWidget(self._layout.count() - 1, widget)
        QTimer.singleShot(40, self._scroll_bottom)

    def _scroll_bottom(self):
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())
