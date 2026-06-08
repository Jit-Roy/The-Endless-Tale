"""
Main window — premium 3-column layout with tab bar.
Left: StoryPanel  |  Center: TabBar + ChatDisplay  |  Right: StatusPanel
"""

import sys
from datetime import datetime
from pathlib import Path

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QStatusBar, QMessageBox, QFrame,
    QSizePolicy, QDialog, QDialogButtonBox, QTextEdit,
    QPushButton, QStackedWidget
)
from PyQt5.QtCore import Qt, QThread, pyqtSlot, QMetaObject, Q_ARG, QTimer
from PyQt5.QtGui import QFont

from ui.chat_display import ChatDisplay, ObjectiveView
from ui.story_panel import StoryPanel
from ui.status_panel import StatusPanel
from ui.thinking_panel import ThinkingPanel
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
    "scene_time_of_day": "Evening",
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
        self._msg_count   = 0
        self._evt_count   = 0

        self._build_window()
        self._build_ui()
        self._start_backend()

    # ── Window chrome ─────────────────────────────────────────────────────

    def _build_window(self):
        self.setWindowTitle("The Endless Tale")
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

        # View selector (Chat / Objectives)
        self._view_bar = QWidget()
        self._view_bar.setStyleSheet(f"background-color: {MAIN_BG};")
        vb = QHBoxLayout(self._view_bar)
        vb.setContentsMargins(14, 12, 14, 12)
        vb.setSpacing(8)

        self._chat_button = QPushButton("Chat")
        self._chat_button.setCheckable(True)
        self._chat_button.clicked.connect(lambda: self._set_view_index(0))
        self._obj_button = QPushButton("Objectives")
        self._obj_button.setCheckable(True)
        self._obj_button.clicked.connect(lambda: self._set_view_index(1))

        button_style = f"""
            QPushButton {{
                color: {TEXT_PRIMARY};
                background-color: {PANEL_BG};
                border: 1px solid {BORDER};
                border-radius: 6px;
                padding: 8px 14px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 12px;
            }}
            QPushButton:checked {{
                background-color: {MAIN_BG};
                border-color: {TEXT_PRIMARY};
            }}
        """
        self._chat_button.setStyleSheet(button_style)
        self._obj_button.setStyleSheet(button_style)

        vb.addWidget(self._chat_button)
        vb.addWidget(self._obj_button)
        vb.addStretch()
        cl.addWidget(self._view_bar)

        # Main center views
        self._chat = ChatDisplay(player_name=player)
        self._objective_view = ObjectiveView()
        self._view_stack = QStackedWidget()
        self._view_stack.addWidget(self._chat)
        self._view_stack.addWidget(self._objective_view)
        cl.addWidget(self._view_stack, stretch=1)

        self._set_view_index(0)

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
        right_col = QWidget()
        right_col.setStyleSheet(f"background-color: {PANEL_BG};")
        rc_layout = QVBoxLayout(right_col)
        rc_layout.setContentsMargins(0, 10, 10, 10)
        rc_layout.setSpacing(10)

        # Thinking panel (ephemeral per-character thinking)
        self._thinking_panel = ThinkingPanel()
        rc_layout.addWidget(self._thinking_panel)
        rc_layout.addStretch()

        # Status panel (character list anchored to the bottom)
        self._status_panel = StatusPanel()
        rc_layout.addWidget(self._status_panel)
        rl.addWidget(right_col)

        # ── Input bar signal wiring ───────────────────────────────────────
        self._input_bar.message_submitted.connect(self._on_player_message)
        self._input_bar.listen_clicked.connect(self._on_listen)
        self._input_bar.progress_clicked.connect(self._on_progress)

    # ── Backend / Worker ──────────────────────────────────────────────────

    def _start_backend(self):
        self._loading = LoadingScreen(self)
        self._loading.show()

        self._thread = QThread(self)
        self._worker = RoleplayWorker()
        self._worker.moveToThread(self._thread)

        self._worker.load_complete.connect(self._on_load_complete)
        self._worker.event_added.connect(self._on_event_added)
        self._worker.thinking_update.connect(self._on_thinking_update)
        self._worker.ai_thinking.connect(self._on_ai_thinking)
        self._worker.status_update.connect(self._on_status_update)
        self._worker.error_occurred.connect(self._on_error)
        self._worker.characters_updated.connect(self._status_panel.update_characters)
        self._worker.characters_updated.connect(self._on_characters_updated)
        self._worker.story_updated.connect(self._on_story_updated)
        self._worker.story_updated.connect(self._on_objective_view_story_updated)
        self._worker.reset_complete.connect(self._on_reset_complete)

        self._thread.started.connect(self._run_load)
        self._thread.start()

    def _run_load(self):
        self._worker.initialize(self._config)
        self._worker.load_system()

    # ── Worker signal slots ───────────────────────────────────────────────

    @pyqtSlot(bool, str)
    def _on_load_complete(self, success: bool, error_msg: str):
        self._loading.close()
        self._loading.hide()  # Explicitly hide the modal dialog
        if not success:
            QMessageBox.critical(self, "Load Error",
                f"Failed to load The Endless Tale:\n\n{error_msg}")
            return

        # Detect new vs resumed session
        if self._worker.system:
            self._is_new = len(self._worker.system.timeline.events) <= 1

        self._input_bar.set_enabled(True)
        self._on_status_update("Ready")

        if self._is_new:
            # Fire greeting immediately; the initial scene is already present in the backend timeline.
            self._input_bar.set_enabled(False)
            self._invoke_worker("start_new_session")
        else:
            self._chat.append_system("Conversation resumed from previous session.")

        # Force the viewport to the latest event after history restoration.
        QTimer.singleShot(0, self._chat.scroll_to_bottom)
        QTimer.singleShot(180, self._chat.scroll_to_bottom)
        QTimer.singleShot(360, self._chat.scroll_to_bottom)

    @pyqtSlot(dict)
    def _on_event_added(self, event: dict):
        t = event.get("type", "")
        if t == "message":
            self._msg_count += 1
        self._evt_count += 1
        self._chat.append_event(event)
        # If this event is a character message/action/entry/exit, clear any
        # temporary "thinking" indicator for that character.
        if t in ("message", "action", "character_entry", "character_exit"):
            char = event.get("character")
            if char:
                if hasattr(self, "_thinking_panel"):
                    self._thinking_panel.clear_thinking(char)
        self._update_session_info()

    @pyqtSlot(str, str)
    def _on_thinking_update(self, name: str, text: str):
        # Forward thinking updates to the dedicated ThinkingPanel
        if hasattr(self, "_thinking_panel"):
            self._thinking_panel.update_thinking(name, text)

    @pyqtSlot(bool)
    def _on_ai_thinking(self, thinking: bool):
        self._input_bar.set_enabled(not thinking)
        if thinking:
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

    @pyqtSlot(list)
    def _on_characters_updated(self, characters: list):
        if hasattr(self, '_objective_view'):
            self._objective_view.update_objectives(characters)

    @pyqtSlot(dict)
    def _on_objective_view_story_updated(self, data: dict):
        if hasattr(self, '_objective_view'):
            self._objective_view.update_story(data)

    def _set_view_index(self, index: int):
        if hasattr(self, '_view_stack'):
            self._view_stack.setCurrentIndex(index)
        if hasattr(self, '_chat_button') and hasattr(self, '_obj_button'):
            self._chat_button.setChecked(index == 0)
            self._obj_button.setChecked(index == 1)

    @pyqtSlot()
    def _on_reset_complete(self):
        self._msg_count = 0
        self._evt_count = 0
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



    # ── Helpers ───────────────────────────────────────────────────────────

    def _update_session_info(self):
        # Only update story location in the UI; session statistics are removed.
        if self._worker and self._worker.system:
            loc = self._worker.system.timeline_manager.get_current_location(
                self._worker.system.timeline
            )
            tod = self._worker.system.timeline_manager.get_current_time_of_day(
                self._worker.system.timeline
            )
            self._story_panel.update_location(
                loc or self._config["scene_location"],
                tod or self._config.get("scene_time_of_day", "")
            )

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
        """Handle window close event with proper shutdown sequence to prevent message loss."""
        # CRITICAL: Graceful shutdown sequence
        
        # 1. Signal worker to stop accepting new requests and perform final save
        if self._worker:
            try:
                self._worker.shutdown()  # Sets _is_shutting_down flag and saves
            except Exception as e:
                print(f"[WARNING] Worker shutdown error: {e}")
        
        # 2. Stop accepting input from UI
        if self._input_bar:
            self._input_bar.set_enabled(False)
        
        # 3. Wait for worker thread to finish current operations (up to 5 seconds)
        if self._thread and self._thread.isRunning():
            self._status_lbl.setText("Saving conversation…")
            # Request thread to quit gracefully
            self._thread.quit()
            # Wait for thread to finish
            if not self._thread.wait(5000):
                # If thread doesn't quit gracefully in 5 seconds, force terminate
                print("[WARNING] Worker thread did not finish gracefully, forcing termination")
                self._thread.terminate()
                self._thread.wait(1000)
        
        super().closeEvent(event)
