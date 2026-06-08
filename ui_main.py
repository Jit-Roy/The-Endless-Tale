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
from PyQt5.QtCore import Qt, QObject, QEvent
from pathlib import Path
import time, traceback


class UIEventTracer(QObject):
    """Application-wide event filter that logs Show/Paint/Resize events."""
    def __init__(self, log_path: Path):
        super().__init__()
        self.log_path = log_path

    def _log(self, text: str):
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(f"{time.time()} {text}\n")
        except Exception:
            pass

    def eventFilter(self, obj, event):
        try:
            et = event.type()
            # QEvent.Show == 17, QEvent.Paint == 12, QEvent.Resize == 22
            if et in (QEvent.Show, QEvent.Paint, QEvent.Resize):
                cls = obj.__class__.__name__
                geom = None
                try:
                    r = obj.geometry()
                    geom = f"{r.x()},{r.y()},{r.width()},{r.height()}"
                except Exception:
                    geom = "-"
                try:
                    self._log(f"EVENT {et} {cls} visible={getattr(obj,'isVisible',lambda:False)()} geom={geom} parent={obj.parent().__class__.__name__ if obj.parent() else 'None'}")
                except Exception:
                    self._log(f"EVENT {et} {cls}")
        except Exception:
            try:
                with open(self.log_path, "a", encoding="utf-8") as f:
                    f.write("UIEventTracer error:\n")
                    traceback.print_exc(file=f)
            except Exception:
                pass
        return super().eventFilter(obj, event)

from ui.main_window import MainWindow


def main():
    # ── High-DPI support ──────────────────────────────────────────────────
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("The Endless Tale")
    app.setOrganizationName("The Endless Tale")

    # Install global UI event tracer to log Show/Paint/Resize events
    try:
        log_path = Path(__file__).parent / "ui_event.log"
        tracer = UIEventTracer(log_path)
        app.installEventFilter(tracer)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"--- UIEventTracer started at {time.time()} ---\n")
    except Exception as e:
        try:
            md = Path(__file__).parent / "modal_debug.log"
            with open(md, "a", encoding="utf-8") as f:
                f.write(f"UIEventTracer failed at {time.time()}: {e}\n")
                import traceback
                traceback.print_exc(file=f)
        except Exception:
            pass

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
    # Debugging: instrument QDialog/QMessageBox show/exec to log unexpected modals
    try:
        from PyQt5.QtWidgets import QDialog, QMessageBox, QWidget
        import traceback, time
        from pathlib import Path
        log_path = Path(__file__).parent / "modal_debug.log"
        # ensure file exists
        try:
            with open(log_path, "a", encoding="utf-8") as _f:
                _f.write(f"\n--- UI instrumentation started at {time.time()} ---\n")
        except Exception:
            pass

        # Log QDialog instantiation to file
        _orig_qdialog_init = QDialog.__init__
        def _dbg_qdialog_init(self, *a, **k):
            _orig_qdialog_init(self, *a, **k)
            try:
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(f"[DEBUG] QDialog.__init__ for {self.__class__.__name__} at {time.time()}\n")
                    traceback.print_stack(limit=6, file=f)
                    f.write("\n")
            except Exception:
                pass
        QDialog.__init__ = _dbg_qdialog_init

        # Wrap QWidget.show to log when a dialog-like widget becomes visible
        _orig_widget_show = QWidget.show
        def _dbg_widget_show(self, *a, **k):
            try:
                cls = self.__class__.__name__
                if isinstance(self, QDialog) or cls in ("LoadingScreen", "QMessageBox"):
                    with open(log_path, "a", encoding="utf-8") as f:
                        f.write(f"[DEBUG] QWidget.show called for {cls} at {time.time()}\n")
                        traceback.print_stack(limit=6, file=f)
                        f.write("\n")
            except Exception:
                pass
            return _orig_widget_show(self, *a, **k)
        QWidget.show = _dbg_widget_show

        # Also intercept setVisible(True) which some dialogs use
        _orig_setVisible = QWidget.setVisible
        def _dbg_setVisible(self, visible, *a, **k):
            try:
                if visible:
                    cls = self.__class__.__name__
                    if isinstance(self, QDialog) or cls in ("LoadingScreen", "QMessageBox"):
                        with open(log_path, "a", encoding="utf-8") as f:
                            f.write(f"[DEBUG] setVisible(True) for {cls} at {time.time()}\n")
                            traceback.print_stack(limit=6, file=f)
                            f.write("\n")
            except Exception:
                pass
            return _orig_setVisible(self, visible, *a, **k)
        QWidget.setVisible = _dbg_setVisible

        # Wrap common QMessageBox entry points
        if hasattr(QMessageBox, 'exec_'):
            _orig_qmessagebox_exec = QMessageBox.exec_
            def _dbg_qmessagebox_exec(self, *a, **k):
                try:
                    with open(log_path, "a", encoding="utf-8") as f:
                        f.write(f"[DEBUG] QMessageBox.exec_ called for {self.__class__.__name__} at {time.time()}\n")
                        traceback.print_stack(limit=6, file=f)
                        f.write("\n")
                except Exception:
                    pass
                return _orig_qmessagebox_exec(self, *a, **k)
            QMessageBox.exec_ = _dbg_qmessagebox_exec
    except Exception:
        pass

    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
