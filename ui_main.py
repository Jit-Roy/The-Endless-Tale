# -*- coding: utf-8 -*-
"""
ui_main.py — PyQt5 GUI entry point for The Endless Tale.

Run this instead of main.py to launch the graphical interface:
    python ui_main.py
"""

import sys
import os
import io

# ── Force UTF-8 on Windows (prevents charmap errors from emoji in backend code) ──
if sys.platform == "win32":
    # Reconfigure stdout/stderr to UTF-8, escaping unencodable characters
    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer, encoding="utf-8", errors="backslashreplace"
    )
    sys.stderr = io.TextIOWrapper(
        sys.stderr.buffer, encoding="utf-8", errors="backslashreplace"
    )
    os.environ["PYTHONIOENCODING"] = "utf-8"

# Ensure the project root is on the path
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

from ui.main_window import MainWindow


def main():
    # ── High-DPI support ──────────────────────────────────────────────────
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("The Endless Tale")
    app.setOrganizationName("The Endless Tale")

    # ── Global font ───────────────────────────────────────────────────────
    font = QFont("Segoe UI", 11)
    app.setFont(font)

    # ── Global stylesheet override (scrollbars, tooltips, etc.) ──────────
    app.setStyleSheet("""
        QToolTip {
            background-color: #1a1a1a;
            color: #cccccc;
            border: 1px solid #333333;
            padding: 4px 8px;
            font-size: 11px;
        }
        QMessageBox {
            background-color: #111111;
            color: #e0e0e0;
        }
        QMessageBox QPushButton {
            background-color: #1e1e1e;
            color: #d0d0d0;
            border: 1px solid #333333;
            border-radius: 4px;
            padding: 6px 18px;
            font-size: 11px;
        }
        QMessageBox QPushButton:hover {
            background-color: #2e2e2e;
        }
    """)

    # ── Launch main window ────────────────────────────────────────────────
    window = MainWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
