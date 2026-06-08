"""
Chat display — premium widget-based message cards.
Each message type is rendered as its own styled QFrame card inside a QScrollArea.
"""

from datetime import datetime
from PyQt5.QtWidgets import (
    QScrollArea, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFrame, QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer
from pathlib import Path
import time, traceback, json

# Debug log for UI insert events
_ui_log_path = Path(__file__).parent.parent / "ui_debug.log"
def _ui_log(msg: str):
    try:
        with open(_ui_log_path, "a", encoding="utf-8") as f:
            f.write(f"{time.time()} {msg}\n")
    except Exception:
        pass

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
           fg: str = "#666666", font_size: int = 11, parent=None) -> QLabel:
    """Circular icon badge."""
    lbl = QLabel(symbol, parent)
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


def _avatar(name: str, size: int = 34, parent=None) -> QLabel:
    """Circular avatar with initials."""
    parts = name.split()
    initials = (parts[0][0] + (parts[1][0] if len(parts) > 1 else "")).upper()
    lbl = QLabel(initials, parent)
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


def _ts_label(ts: str, parent=None) -> QLabel:
    lbl = QLabel(ts, parent)
    lbl.setStyleSheet(
        f"color: {TEXT_TS}; font-size: 10px; font-family: 'Segoe UI', sans-serif;"
        f"color: {TEXT_TS}; font-size: 11px; font-family: 'Segoe UI', sans-serif;"
    )
    lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
    return lbl


def _tag_label(text: str, parent=None) -> QLabel:
    lbl = QLabel(text, parent)
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
          bold: bool = False, parent=None) -> QLabel:
    weight = "bold" if bold else "normal"
    style_flag = "italic" if italic else "normal"
    lbl = QLabel(content, parent)
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
        hdr.addWidget(_badge("⛰", 28, "#1e1e1e", "#555555", 11, self))

        tag_col = QVBoxLayout()
        tag_col.setSpacing(0)
        tag_col.addWidget(_tag_label(f"SCENE  ·  {scene_type}", self))
        if location:
            loc_lbl = QLabel(location, self)
            loc_lbl.setStyleSheet(
                f"color: #666666; font-size: 11px; font-family: 'Segoe UI', sans-serif;"
            )
            tag_col.addWidget(loc_lbl)
        hdr.addLayout(tag_col)
        hdr.addStretch()
        hdr.addWidget(_ts_label(ts, self))
        layout.addLayout(hdr)

        # Description
        layout.addWidget(_text(desc, "#888888", 13, italic=True, parent=self))


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
        hdr.addWidget(_badge("◎", 28, "#222222", "#888888", 13, self))

        you_lbl = QLabel("YOU", self)
        you_lbl.setStyleSheet(
            f"color: {TEXT_PRIMARY}; font-size: 12px; font-weight: bold; "
            "letter-spacing: 1px; font-family: 'Segoe UI', sans-serif;"
        )
        hdr.addWidget(you_lbl)
        hdr.addStretch()
        hdr.addWidget(_ts_label(ts, self))
        layout.addLayout(hdr)

        layout.addWidget(_text(dialogue, TEXT_PRIMARY, 14, parent=self))


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

        av = _avatar(character, 34, self)
        top_row.addWidget(av, 0, Qt.AlignTop)

        info_col = QVBoxLayout()
        info_col.setSpacing(3)

        # Name + timestamp
        name_row = QHBoxLayout()
        name_row.setSpacing(0)
        name_lbl = QLabel(character.upper(), self)
        name_lbl.setStyleSheet(
            f"color: {TEXT_PRIMARY}; font-size: 12px; font-weight: bold; "
            "letter-spacing: 0.8px; font-family: 'Segoe UI', sans-serif;"
        )
        name_row.addWidget(name_lbl)
        name_row.addStretch()
        name_row.addWidget(_ts_label(ts, self))
        info_col.addLayout(name_row)

        # Action (italic gray)
        if action and action.lower() not in ("speaks", ""):
            info_col.addSpacing(2)
            info_col.addWidget(_text(action, TEXT_ACTION, 12, italic=True, parent=self))

        # Dialogue
        if dialogue:
            info_col.addSpacing(5)
            info_col.addWidget(_text(dialogue, TEXT_PRIMARY, 14, parent=self))

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
        hdr.addWidget(_badge("⬡", 28, "#1e1e1e", "#4a4a4a", 11, self))
        hdr.addWidget(_tag_label("ACTION  ·  SYSTEM", self))
        hdr.addStretch()
        hdr.addWidget(_ts_label(ts, self))
        layout.addLayout(hdr)

        layout.addWidget(_text(f"{character} {desc}", "#777777", 13, italic=True, parent=self))


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
        layout.addWidget(_badge(arrow, 24, "#1a1a1a", "#444444", 10, self))

        verb = "entered" if is_entry else "left"
        txt  = QLabel(f"{character} {verb}: {desc}", self)
        txt.setWordWrap(True)
        txt.setStyleSheet(
            f"color: #4a4a4a; font-size: 11px; font-style: italic; font-family: 'Segoe UI', sans-serif;"
        )
        layout.addWidget(txt, stretch=1)
        layout.addWidget(_ts_label(ts, self))


class SystemMsg(QWidget):
    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 3, 14, 3)
        lbl = QLabel(text, self)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 10px; font-style: italic; font-family: 'Segoe UI', sans-serif;"
        )
        layout.addWidget(lbl)


class ObjectiveCard(QFrame):
    def __init__(self, character_name: str, objective: str, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {CARD_BG};
                border: 1px solid {BORDER};
                border-radius: 10px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        name_lbl = QLabel(character_name, self)
        name_lbl.setStyleSheet(
            "color: #e8e8e8; font-size: 12px; font-weight: bold; font-family: 'Segoe UI', sans-serif;"
        )
        layout.addWidget(name_lbl)

        objective_lbl = QLabel(objective, self)
        objective_lbl.setWordWrap(True)
        objective_lbl.setStyleSheet(
            "color: #bfc0c2; font-size: 13px; font-family: 'Segoe UI', sans-serif; line-height: 1.4;"
        )
        layout.addWidget(objective_lbl)


class ObjectiveView(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
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
        self._layout.setContentsMargins(14, 14, 14, 14)
        self._layout.setSpacing(12)

        self._title = QLabel("Current Objectives")
        self._title.setStyleSheet(
            "color: #e8e8e8; font-size: 17px; font-weight: bold; font-family: 'Segoe UI', sans-serif;"
        )
        self._layout.addWidget(self._title)

        self._story_objective = QLabel("No story objective available.")
        self._story_objective.setWordWrap(True)
        self._story_objective.setStyleSheet(
            "color: #b0b0b0; font-size: 13px; font-family: 'Segoe UI', sans-serif;"
        )
        self._layout.addWidget(self._story_objective)

        # Removed extra divider to avoid visual clutter in ObjectiveView

        self._objectives_list = QWidget()
        self._list_layout = QVBoxLayout(self._objectives_list)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(10)
        self._layout.addWidget(self._objectives_list)
        self._layout.addStretch()

        self.setWidget(self._content)

    def update_story(self, data: dict):
        story_text = data.get("current_objective", "No current story objective.")
        self._story_objective.setText(f"Story objective: {story_text}")

    def update_objectives(self, characters: list):
        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not characters:
            self._list_layout.addWidget(_text("No character objectives available yet.", TEXT_MUTED, 12))
            return

        for char in characters:
            name = char.get("name", "Unknown")
            objective = char.get("objective", "—")
            self._list_layout.addWidget(ObjectiveCard(name, objective, self._objectives_list))


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
        # temporary thinking widgets keyed by character name
        self._thinking_widgets = {}

        self.setWidget(self._content)

    # ── Public API ───────────────────────────────────────────────────────

    def append_event(self, event: dict):
        t    = event.get("type", "")
        char = event.get("character", "")
        try:
            _ui_log(f"append_event: type={t} char={char} keys={list(event.keys())} dialouge_len={len(event.get('dialouge',''))}")
        except Exception:
            pass

        if t == "message":
            card = PlayerCard(event, self.player_name, self._content) if char == self.player_name \
                   else CharacterCard(event, self._content)
        elif t == "scene":
            card = SceneCard(event, self._content)
        elif t == "action":
            card = ActionCard(event, self._content)
        elif t in ("character_entry", "character_exit"):
            card = MovementCard(event, self._content)
        else:
            return

        self._insert(card)

    def append_system(self, text: str):
        self._insert(SystemMsg(text, self._content))

    def clear_display(self):
        while self._layout.count() > 1:
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    # ── Private ──────────────────────────────────────────────────────────

    def _insert(self, widget: QWidget):
        # Insert the widget before the stretch at the end
        try:
            _ui_log(f"_insert: widget={widget.__class__.__name__} layout_count={self._layout.count()}")
        except Exception:
            pass
        self._layout.insertWidget(self._layout.count() - 1, widget)
        # Auto-scroll only if the user is already at (or near) the bottom.
        sb = self.verticalScrollBar()
        at_bottom = sb.value() >= (sb.maximum() - 80)
        if at_bottom:
            QTimer.singleShot(40, self._scroll_bottom)
        try:
            _ui_log(f"_insert: scheduled scroll at_bottom={at_bottom} sb={sb.value()}/{sb.maximum()}")
        except Exception:
            pass

    def _scroll_bottom(self):
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())

    def scroll_to_bottom(self):
        QTimer.singleShot(40, self._scroll_bottom)

    # Thinking helpers
    def append_thinking(self, name: str, text: str):
        # Deprecated: thinking is now displayed in ThinkingPanel.
        # Kept for backward compatibility but does nothing.
        return

    def clear_thinking(self, name: str):
        # Deprecated: thinking display moved to ThinkingPanel
        return
