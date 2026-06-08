from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton
from PyQt5.QtCore import Qt, QTimer

TEXT_MUTED = "#777777"
TEXT_PRIMARY = "#f0f0f0"
MAIN_BG = "#161616"
CARD_BG = "#1c1c1c"

class ThinkingPanel(QWidget):
    """Small panel that shows per-character ephemeral "thinking" text.

    Methods:
      - update_thinking(name, text): show or update thinking line
      - clear_thinking(name): remove thinking for character
      - clear_all(): clear all
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color: {MAIN_BG};")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(8, 8, 8, 8)
        self._layout.setSpacing(6)

        header = QLabel("Thinking", self)
        header.setStyleSheet(f"color: {TEXT_PRIMARY}; font-weight: bold; font-size: 12px;")
        self._layout.addWidget(header)

        self._entries = {}  # name -> (widget_label, timer)

    def update_thinking(self, name: str, text: str, timeout: int = 10000):
        """Show or update thinking text for `name`. Timeout in ms."""
        # Create or update label
        if name in self._entries:
            lbl, timer = self._entries[name]
            lbl.setText(f"{name}: {text}")
            # restart timer
            if timer:
                timer.stop()
                timer.start()
            return

        lbl = QLabel(f"{name}: {text}", self)
        lbl.setWordWrap(True)
        lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-style: italic; font-size: 12px;")
        self._layout.addWidget(lbl)

        # Setup timer to auto-clear
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(lambda n=name: self.clear_thinking(n))
        timer.start(timeout)

        self._entries[name] = (lbl, timer)

    def clear_thinking(self, name: str):
        if name not in self._entries:
            return
        lbl, timer = self._entries.pop(name)
        try:
            if timer:
                timer.stop()
        except Exception:
            pass
        # remove widget
        lbl.setParent(None)
        lbl.deleteLater()

    def clear_all(self):
        names = list(self._entries.keys())
        for n in names:
            self.clear_thinking(n)
