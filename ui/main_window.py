"""
Main window — premium 3-column layout with tab bar matching the RoleRealm reference design.
Left: StoryPanel  |  Center: TabBar + ChatDisplay  |  Right: StatusPanel
"""

import sys
from datetime import datetime
from pathlib import Path

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QStatusBar, QMessageBox, QFrame,
    QSizePolicy, QDialog, QDialogButtonBox, QTextEdit,
    QPushButton
)
from PyQt5.QtCore import Qt, QThread, pyqtSlot, QMetaObject, Q_ARG, QTimer
from PyQt5.QtGui import QFont

from ui.chat_display import ChatDisplay
from ui.story_panel import StoryPanel
from ui.status_panel import StatusPanel
from ui.input_bar import InputBar
from ui.loading_screen import LoadingScreen
from ui.worker import RoleplayWorker


# ── Palette ──────────────────────────────────────────────────────────────────
DARK_BG      = "#111111"
MAIN_BG      = "#161616"
PANEL_BG     = "#141414"
BORDER       = "#1e1e1e"
TEXT_PRIMARY = "#e8e8e8"
TEXT_MUTED   = "#444444"
TAB_ACTIVE   = "#e8e8e8"
TAB_INACTIVE = "#555555"
STATUS_TEXT  = "#444444"


# ── Default story config (mirrors main.py) ───────────────────────────────────
DEFAULT_CONFIG = {
    "base_dir":        "Pirate Adventure",
    "player_name":     "Henry",
    "character_files": ["marina", "jack", "captain"],
    "scene_title":     "Aboard the Sea Serpent",
    "scene_location":  "The Sea Serpent - Main Deck",
    "scene_description": (
        "The sun is setting over the endless ocean, painting the sky in brilliant oranges and purples. "
        "The Sea Serpent rocks gently on the waves, her black sails billowing in the evening breeze. "
        "You stand on the main deck with your friends Jack and Marina, and Captain Morgan at the helm. "
        "The old map lies spread on a barrel — your ticket to fortune and glory. "
        "Adventure awaits, and the sea is calling."
    ),
    "initial_greeting": "This map looks incredible! Captain, what do you make of these markings?",
}


# (TabBar removed) Top tab bar was decorative/placeholding; removed per request.


# ── Main window ───────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):

    def __init__(self, config: dict = None):
        super().__init__()
        self._config      = config or DEFAULT_CONFIG
        self._worker      = None
        self._thread      = None
        self._is_new      = True
        self._elapsed_s   = 0
        self._msg_count   = 0
        self._evt_count   = 0

        self._build_window()
        self._build_ui()
        self._start_backend()

    # ── Window chrome ─────────────────────────────────────────────────────

    def _build_window(self):
        self.setWindowTitle("RoleRealm")
        self.resize(1200, 760)
        self.setMinimumSize(900, 600)
        self.setStyleSheet(f"QMainWindow {{ background-color: {DARK_BG}; }}")

        sb = self.statusBar()
        sb.setStyleSheet(f"""
            QStatusBar {{
                background-color: {DARK_BG};
                color: {STATUS_TEXT};
                font-size: 10px;
                font-family: 'Segoe UI', sans-serif;
                border-top: 1px solid {BORDER};
                padding: 1px 10px;
            }}
        """)
        self._status_lbl = QLabel("Initialising…")
        self._status_lbl.setStyleSheet(f"color: {STATUS_TEXT}; font-size: 10px;")
        sb.addPermanentWidget(self._status_lbl)

    # ── UI construction ───────────────────────────────────────────────────

    def _build_ui(self):
        player = self._config["player_name"]
        root   = QWidget()
        root.setStyleSheet(f"background-color: {DARK_BG};")
        rl = QHBoxLayout(root)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(0)
        self.setCentralWidget(root)

        # ── Left sidebar ─────────────────────────────────────────────────
        self._story_panel = StoryPanel()
        rl.addWidget(self._story_panel)

        # ── Vertical divider ─────────────────────────────────────────────
        rl.addWidget(self._vdivider())

        # ── Center column ─────────────────────────────────────────────────
        center = QWidget()
        center.setStyleSheet(f"background-color: {MAIN_BG};")
        center.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        cl = QVBoxLayout(center)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)

        # (Tabs removed) — main canvas will be shown directly

        # Chat display
        self._chat = ChatDisplay(player_name=player)
        cl.addWidget(self._chat, stretch=1)

        # Divider above input
        cl.addWidget(self._hdivider())

        # Input bar
        self._input_bar = InputBar(player_name=player)
        self._input_bar.set_enabled(False)
        cl.addWidget(self._input_bar)

        rl.addWidget(center, stretch=1)

        # ── Vertical divider ─────────────────────────────────────────────
        rl.addWidget(self._vdivider())

        # ── Right sidebar ─────────────────────────────────────────────────
        self._status_panel = StatusPanel()
        rl.addWidget(self._status_panel)

        # ── Input bar signal wiring ───────────────────────────────────────
        self._input_bar.message_submitted.connect(self._on_player_message)
        self._input_bar.listen_clicked.connect(self._on_listen)
        self._input_bar.progress_clicked.connect(self._on_progress)
        self._status_panel.save_clicked.connect(self._on_save_session)

    # ── Backend / Worker ──────────────────────────────────────────────────

    def _start_backend(self):
        self._loading = LoadingScreen(self)
        self._loading.show()

        self._thread = QThread(self)
        self._worker = RoleplayWorker()
        self._worker.moveToThread(self._thread)

        self._worker.load_complete.connect(self._on_load_complete)
        self._worker.event_added.connect(self._on_event_added)
        self._worker.ai_thinking.connect(self._on_ai_thinking)
        self._worker.status_update.connect(self._on_status_update)
        self._worker.error_occurred.connect(self._on_error)
        self._worker.characters_updated.connect(self._status_panel.update_characters)
        self._worker.story_updated.connect(self._on_story_updated)
        self._worker.reset_complete.connect(self._on_reset_complete)

        self._thread.started.connect(self._run_load)
        self._thread.start()

    def _run_load(self):
        self._worker.initialize(self._config)
        self._worker.load_system()

    # ── Session timer ─────────────────────────────────────────────────────

    def _start_session_timer(self):
        self._elapsed_s = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick_timer)
        self._timer.start(1000)

    def _tick_timer(self):
        self._elapsed_s += 1
        self._status_panel.update_session_time(self._elapsed_s)

    # ── Worker signal slots ───────────────────────────────────────────────

    @pyqtSlot(bool, str)
    def _on_load_complete(self, success: bool, error_msg: str):
        self._loading.close()
        if not success:
            QMessageBox.critical(self, "Load Error",
                f"Failed to load RoleRealm:\n\n{error_msg}")
            return

        # Detect new vs resumed session
        if self._worker.system:
            self._is_new = len(self._worker.system.timeline.events) <= 1

        self._input_bar.set_enabled(True)
        self._on_status_update("Ready")
        self._start_session_timer()

        if self._is_new:
            # Fire greeting immediately; the initial scene is already present in the backend timeline.
            self._input_bar.set_enabled(False)
            self._invoke_worker("start_new_session")
        else:
            self._chat.append_system("Conversation resumed from previous session.")

    @pyqtSlot(dict)
    def _on_event_added(self, event: dict):
        t = event.get("type", "")
        if t == "message":
            self._msg_count += 1
        self._evt_count += 1
        self._chat.append_event(event)
        self._update_session_info()

    @pyqtSlot(bool)
    def _on_ai_thinking(self, thinking: bool):
        self._input_bar.set_enabled(not thinking)
        if thinking:
            self._chat.append_system("Characters are thinking…")
            self._on_status_update("AI thinking…")
        else:
            self._on_status_update("Ready")

    @pyqtSlot(str)
    def _on_status_update(self, text: str):
        self._status_lbl.setText(text)
        if hasattr(self, "_loading") and self._loading.isVisible():
            self._loading.set_status(text)

    @pyqtSlot(str)
    def _on_error(self, msg: str):
        self._input_bar.set_enabled(True)
        self._chat.append_system(f"Error: {msg}")
        self._on_status_update(f"Error: {msg[:60]}")

    @pyqtSlot(dict)
    def _on_story_updated(self, data: dict):
        self._story_panel.update_story(data)

    @pyqtSlot()
    def _on_reset_complete(self):
        self._msg_count = 0
        self._evt_count = 0
        self._elapsed_s = 0
        self._update_session_info()
        self._chat.append_system("Conversation reset. Starting fresh…")

    # ── Input bar slots ───────────────────────────────────────────────────

    @pyqtSlot(str)
    def _on_player_message(self, text: str):
        self._invoke_worker("send_player_message", text)

    @pyqtSlot()
    def _on_listen(self):
        self._invoke_worker("send_listen")
    @pyqtSlot()
    def _on_progress(self):
        if self._worker and self._worker.story_manager:
            sm = self._worker.story_manager
            if sm.story:
                self._chat.append_system(sm.get_progress_summary())
                return
        self._chat.append_system("No story loaded.")



    @pyqtSlot()
    def _on_save_session(self):
        if self._worker and self._worker.system:
            try:
                self._worker.system._save_conversation()
                now = datetime.now().strftime("%H:%M:%S")
                self._status_panel.update_session_info(
                    self._msg_count, self._evt_count, now
                )
                self._on_status_update("Session saved")
            except Exception as e:
                self._on_error(f"Save failed: {e}")

    # ── Helpers ───────────────────────────────────────────────────────────

    def _update_session_info(self):
        self._status_panel.update_session_info(
            self._msg_count, self._evt_count
        )
        # Also update location from timeline
        if self._worker and self._worker.system:
            loc = self._worker.system.timeline_manager.get_current_location(
                self._worker.system.timeline
            )
            self._story_panel.update_location(loc or self._config["scene_location"])

    def _invoke_worker(self, method_name: str, *args):
        if not self._worker:
            return
        if args:
            QMetaObject.invokeMethod(
                self._worker, method_name,
                Qt.QueuedConnection,
                Q_ARG(str, args[0])
            )
        else:
            QMetaObject.invokeMethod(
                self._worker, method_name,
                Qt.QueuedConnection,
            )

    @staticmethod
    def _vdivider() -> QFrame:
        f = QFrame()
        f.setFrameShape(QFrame.VLine)
        f.setStyleSheet("color: #1a1a1a;")
        f.setFixedWidth(1)
        return f

    @staticmethod
    def _hdivider() -> QFrame:
        f = QFrame()
        f.setFrameShape(QFrame.HLine)
        f.setStyleSheet("color: #1a1a1a;")
        f.setFixedHeight(1)
        return f

    def closeEvent(self, event):
        if self._thread and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait(3000)
        super().closeEvent(event)
