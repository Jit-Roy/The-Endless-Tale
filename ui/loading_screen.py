"""
Loading screen — modal dialog shown while the backend loads characters and story.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QProgressBar, QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont


# ── Palette ─────────────────────────────────────────────────────────────────
BG       = "#0e0e0e"
TEXT     = "#d0d0d0"
MUTED    = "#555555"
BAR_BG   = "#1e1e1e"
BAR_FILL = "#888888"
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
        title = QLabel("RoleRealm")
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

        # Indeterminate progress bar
        self._bar = QProgressBar()
        self._bar.setRange(0, 0)   # indeterminate
        self._bar.setTextVisible(False)
        self._bar.setFixedHeight(3)
        self._bar.setStyleSheet(f"""
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
        layout.addWidget(self._bar)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_status(self, text: str):
        self._status.setText(text)
        self._status.repaint()
