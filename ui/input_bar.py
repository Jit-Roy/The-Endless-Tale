"""
Premium input bar — multiline text area with toolbar icons and SEND button.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QPushButton, QLabel, QSizePolicy, QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QKeyEvent, QFont, QTextOption

# ── Palette ──────────────────────────────────────────────────────────────────
BG_INPUT    = "#141414"
BG_AREA     = "#1a1a1a"
BORDER      = "#222222"
BORDER_FOCUS= "#333333"
TEXT_MAIN   = "#e0e0e0"
TEXT_PLACE  = "#3a3a3a"
TEXT_HINT   = "#333333"
BTN_MUTED   = "#3a3a3a"
BTN_PRIMARY = "#e8e8e8"
BTN_BG      = "#1e1e1e"
BTN_HOVER   = "#2a2a2a"
BTN_BORDER  = "#2e2e2e"
ICON_CLR    = "#555555"
ICON_HOVER  = "#888888"
ACTION_BG   = "#1a1a1a"
ACTION_HV   = "#222222"
ACTION_TEXT = "#888888"
ACTION_BRD  = "#252525"


def _icon_btn(symbol: str, tooltip: str = "") -> QLabel:
    btn = QLabel(symbol)
    btn.setAlignment(Qt.AlignCenter)
    btn.setFixedSize(28, 28)
    btn.setToolTip(tooltip)
    btn.setStyleSheet(f"""
        QLabel {{
            color: {ICON_CLR};
            font-size: 14px;
            border-radius: 4px;
        }}
        QLabel:hover {{
            color: {ICON_HOVER};
            background-color: #222222;
        }}
    """)
    return btn


def _action_btn(text: str) -> QPushButton:
    btn = QPushButton(text)
    btn.setFixedHeight(28)
    btn.setStyleSheet(f"""
        QPushButton {{
            background-color: {ACTION_BG};
            color: {ACTION_TEXT};
            border: 1px solid {ACTION_BRD};
            border-radius: 5px;
            padding: 0px 12px;
            font-size: 12px;
            font-family: 'Segoe UI', sans-serif;
        }}
        QPushButton:hover {{
            background-color: {ACTION_HV};
            border-color: #333333;
            color: #aaaaaa;
        }}
        QPushButton:pressed {{
            background-color: #2a2a2a;
        }}
        QPushButton:disabled {{
            color: #2a2a2a;
            border-color: #1a1a1a;
        }}
    """)
    return btn


class _InputEdit(QTextEdit):
    """TextEdit that submits on Enter and grows up to 3 lines."""

    enter_pressed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(44)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
        self.setAcceptRichText(False)
        self.setStyleSheet(f"""
            QTextEdit {{
                background-color: transparent;
                color: {TEXT_MAIN};
                border: none;
                font-size: 14px;
                font-family: 'Segoe UI', sans-serif;
                padding: 0px 4px;
            }}
        """)
        self.document().contentsChanged.connect(self._on_contents_changed)

    def keyPressEvent(self, e: QKeyEvent):
        if e.key() in (Qt.Key_Return, Qt.Key_Enter) and not (e.modifiers() & Qt.ShiftModifier):
            self.enter_pressed.emit()
        else:
            super().keyPressEvent(e)

    def _on_contents_changed(self):
        doc_h = int(self.document().size().height())
        clamped = max(44, min(doc_h + 16, 96))
        self.setFixedHeight(clamped)

    def get_text(self) -> str:
        return self.toPlainText().strip()

    def clear_text(self):
        self.clear()


class InputBar(QWidget):
    """Bottom input widget."""

    message_submitted = pyqtSignal(str)
    listen_clicked    = pyqtSignal()
    skip_clicked      = pyqtSignal()
    progress_clicked  = pyqtSignal()
    info_clicked      = pyqtSignal()
    reset_clicked     = pyqtSignal()

    def __init__(self, player_name: str = "Player", parent=None):
        super().__init__(parent)
        self.player_name = player_name
        self.setStyleSheet(f"""
            InputBar {{
                background-color: {BG_INPUT};
                border-top: 1px solid {BORDER};
            }}
        """)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 10, 14, 12)
        outer.setSpacing(0)

        # ── Action buttons row ───────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        btn_row.setContentsMargins(0, 0, 0, 8)

        self._btn_listen   = _action_btn("Listen")
        self._btn_skip     = _action_btn("Skip")
        self._btn_progress = _action_btn("Progress")
        self._btn_info     = _action_btn("Info")
        self._btn_reset    = _action_btn("Reset")

        for btn in (self._btn_listen, self._btn_skip,
                    self._btn_progress, self._btn_info, self._btn_reset):
            btn_row.addWidget(btn)

        btn_row.addStretch()
        outer.addLayout(btn_row)

        # ── Text input box ───────────────────────────────────────────────
        input_box = QFrame()
        input_box.setObjectName("InputBox")
        input_box.setStyleSheet(f"""
            QFrame#InputBox {{
                background-color: {BG_AREA};
                border: 1px solid {BORDER};
                border-radius: 8px;
            }}
            QFrame#InputBox:focus-within {{
                border-color: {BORDER_FOCUS};
            }}
        """)
        box_layout = QVBoxLayout(input_box)
        box_layout.setContentsMargins(12, 10, 12, 8)
        box_layout.setSpacing(6)

        # Placeholder + edit
        self._placeholder = QLabel(f"What do you do or say?")
        self._placeholder.setStyleSheet(f"""
            color: {TEXT_PLACE};
            font-size: 14px;
            font-family: 'Segoe UI', sans-serif;
        """)
        self._placeholder.setVisible(True)

        self._edit = _InputEdit()
        self._edit.setVisible(False)   # swap with placeholder

        # Stack them in same space using a layout that shows one at a time
        content_area = QWidget()
        content_area.setStyleSheet("background: transparent;")
        ca_layout = QVBoxLayout(content_area)
        ca_layout.setContentsMargins(0, 0, 0, 0)
        ca_layout.setSpacing(0)
        ca_layout.addWidget(self._placeholder)
        ca_layout.addWidget(self._edit)
        box_layout.addWidget(content_area)

        # ── Bottom toolbar: icons + SEND ─────────────────────────────────
        toolbar = QHBoxLayout()
        toolbar.setSpacing(4)

        self._icon_cmd   = _icon_btn(">_",  "Command")
        self._icon_emoji = _icon_btn("☺",   "Emoji")
        self._icon_img   = _icon_btn("⊞",   "Attach")
        toolbar.addWidget(self._icon_cmd)
        toolbar.addWidget(self._icon_emoji)
        toolbar.addWidget(self._icon_img)
        toolbar.addStretch()

        # Enter hint
        hint = QLabel("Enter to send")
        hint.setStyleSheet(f"""
            color: {TEXT_HINT};
            font-size: 11px;
            font-family: 'Segoe UI', sans-serif;
        """)
        toolbar.addWidget(hint)
        toolbar.addSpacing(8)

        # SEND button
        self._btn_send = QPushButton("  ➤  SEND")
        self._btn_send.setFixedSize(90, 30)
        self._btn_send.setStyleSheet(f"""
            QPushButton {{
                background-color: #1e1e1e;
                color: {BTN_PRIMARY};
                border: 1px solid {BTN_BORDER};
                border-radius: 6px;
                font-size: 12px;
                font-weight: bold;
                font-family: 'Segoe UI', sans-serif;
                letter-spacing: 0.5px;
            }}
            QPushButton:hover {{
                background-color: #282828;
                border-color: #3a3a3a;
            }}
            QPushButton:pressed {{
                background-color: #303030;
            }}
            QPushButton:disabled {{
                color: #2a2a2a;
                border-color: #1a1a1a;
            }}
        """)
        toolbar.addWidget(self._btn_send)

        box_layout.addLayout(toolbar)
        outer.addWidget(input_box)

        # ── Wire up ──────────────────────────────────────────────────────
        self._placeholder.mousePressEvent = lambda _: self._focus_input()
        self._edit.enter_pressed.connect(self._submit)
        self._edit.textChanged.connect(self._on_text_changed)
        self._btn_send.clicked.connect(self._submit)

        self._btn_listen.clicked.connect(self.listen_clicked)
        self._btn_skip.clicked.connect(self.skip_clicked)
        self._btn_progress.clicked.connect(self.progress_clicked)
        self._btn_info.clicked.connect(self.info_clicked)
        self._btn_reset.clicked.connect(self.reset_clicked)

    # ── Public API ───────────────────────────────────────────────────────

    def set_enabled(self, enabled: bool):
        self._edit.setEnabled(enabled)
        self._btn_send.setEnabled(enabled)
        self._btn_listen.setEnabled(enabled)
        self._btn_skip.setEnabled(enabled)
        self._btn_progress.setEnabled(enabled)
        self._btn_info.setEnabled(enabled)
        self._btn_reset.setEnabled(enabled)
        if enabled:
            self._focus_input()

    # ── Private ──────────────────────────────────────────────────────────

    def _focus_input(self):
        self._placeholder.setVisible(False)
        self._edit.setVisible(True)
        self._edit.setFocus()

    def _on_text_changed(self):
        has_text = bool(self._edit.get_text())
        if not has_text and not self._edit.hasFocus():
            self._placeholder.setVisible(True)
            self._edit.setVisible(False)

    def _submit(self):
        text = self._edit.get_text()
        if text:
            self.message_submitted.emit(text)
            self._edit.clear_text()
            self._edit.setFixedHeight(44)
