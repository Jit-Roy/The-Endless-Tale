"""
Loading screen — modal dialog shown while the backend loads characters and story.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont


# ── Palette ─────────────────────────────────────────────────────────────────
BG       = "#0e0e0e"
TEXT     = "#d0d0d0"
MUTED    = "#555555"
BORDER   = "#2a2a2a"


class LoadingScreen(QDialog):
    """Frameless modal loading dialog with animated dots."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setModal(True)
        self.setFixedSize(380, 200)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {BG};
                border: 1px solid {BORDER};
                border-radius: 10px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 32, 36, 32)
        layout.setSpacing(16)

        # Title
        title = QLabel("The Endless Tale")
        title.setStyleSheet(f"""
            color: {TEXT};
            font-size: 22px;
            font-weight: bold;
            font-family: 'Segoe UI', sans-serif;
            letter-spacing: 2px;
        """)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Status label
        self._status = QLabel("Initialising…")
        self._status.setStyleSheet(f"""
            color: {MUTED};
            font-size: 12px;
            font-family: 'Segoe UI', sans-serif;
        """)
        self._status.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._status)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_status(self, text: str):
        self._status.setText(text)
        self._status.repaint()
