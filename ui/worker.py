"""
QThread Worker for UI.
Runs all blocking AI calls off the main thread, emitting signals to update the UI.
"""

import sys
from pathlib import Path

from PyQt5.QtCore import QThread, pyqtSignal, QObject, pyqtSlot

# Add parent dir to path so we can import backend modules
sys.path.insert(0, str(Path(__file__).parent.parent))


class RoleplayWorker(QObject):
    """
    Worker object that lives on a QThread.
    Calls blocking backend methods and emits signals for each result.
    """

    # --- Signals ---
    # Fired whenever a new event is added to the timeline
    event_added = pyqtSignal(dict)            # event_data dict
    # Fired when AI starts/stops thinking
    ai_thinking = pyqtSignal(bool)
    # Fired when a character's thinking/reasoning text is available
    thinking_update = pyqtSignal(str, str)  # name, text
    # Status bar / debug text
    status_update = pyqtSignal(str)
    # Fired when an error occurs
    error_occurred = pyqtSignal(str)
    # Fired when character objectives or presence changes
    characters_updated = pyqtSignal(list)    # list of {name, objective, in_scene}
    # Fired when story progress changes
    story_updated = pyqtSignal(dict)         # {title, current_objective, beat_index, total_beats, complete}
    # Fired when initial load is done
    load_complete = pyqtSignal(bool, str)    # success, error_message
    # Fired when a reset completes
    reset_complete = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.system = None
        self.story_manager = None
        self._init_config = None   # dict passed from main thread
        self._pending_message = None
        self._is_shutting_down = False  # Flag to signal shutdown to prevent new operations

    # ------------------------------------------------------------------
    # Initialisation (called from worker thread via QThread.started)
    # ------------------------------------------------------------------

    def initialize(self, config: dict):
        """Store config; actual loading triggered by load_system()."""
        self._init_config = config

    def load_system(self):
        """Load the backend system. Must be called from worker thread."""
        try:
            cfg = self._init_config
            self.status_update.emit("Loading story…")

            from loaders.story_loader import StoryLoader
            from loaders.character_loader import CharacterLoader
            from managers.storyManager import StoryManager
            from roleplay_system import RoleplaySystem
            from gemini_client import Config

            base_dir = cfg["base_dir"]

            # Load story
            try:
                story_loader = StoryLoader(base_dir)
                story_arc = story_loader.load_story()
                self.story_manager = StoryManager(story_arc)
                self.status_update.emit(f"Story loaded: {story_arc.title}")
            except Exception as e:
                self.status_update.emit(f"No story file found: {e}")
                story_arc = None
                self.story_manager = None

            # Load characters
            self.status_update.emit("Loading characters…")
            from loaders.character_loader import CharacterLoader
            character_loader = CharacterLoader(base_dir)
            characters = character_loader.load_characters(cfg["character_files"])
            self.status_update.emit(f"Loaded {len(characters)} characters")

            # Build system
            self.status_update.emit("Initialising roleplay system…")
            self.system = RoleplaySystem(
                player_name=cfg["player_name"],
                characters=characters,
                chat_storage_dir=base_dir,
                story_manager=self.story_manager,
                story_name=base_dir,
                initial_location=cfg["scene_location"],
                initial_time_of_day=cfg.get("scene_time_of_day"),
                initial_scene_description=cfg["scene_description"],
            )

            # Patch turn_manager to use our status callback instead of print
            self.system.turn_manager.on_status = self._on_backend_status
            # Stream new events immediately to the UI
            self.system.turn_manager.on_new_event = lambda ev: self.event_added.emit(self._serialize_event(ev))
            # Stream per-character thinking text
            self.system.turn_manager.on_thinking_update = lambda name, text: self.thinking_update.emit(name, text)
            # Refresh character and story UI when background tasks complete
            self.system.turn_manager.on_background_update = self._emit_characters_and_story_update

            # Emit existing events (from loaded conversation)
            from data_models import Message, Scene, Action, CharacterEntry, CharacterExit
            for event in self.system.timeline.events:
                self.event_added.emit(self._serialize_event(event))

            self._emit_characters_updated()
            self._emit_story_updated()

            self.load_complete.emit(True, "")

        except Exception as e:
            self.load_complete.emit(False, str(e))

    # ------------------------------------------------------------------
    # Public slots called from UI thread
    # ------------------------------------------------------------------

    @pyqtSlot(str)
    def send_player_message(self, text: str):
        """Add player message and run AI responses. Called from worker thread."""
        if not self.system or self._is_shutting_down:
            return
        try:
            self.status_update.emit(f"You said: {text[:60]}…")

            # Add and emit the player's message first so it appears before the thinking indicator
            self.system._add_player_message(text)
            from data_models import Message
            player_msg = self.system.timeline.events[-1]
            self.event_added.emit(self._serialize_event(player_msg))

            # Now indicate AI is thinking and run responses
            self.ai_thinking.emit(True)
            self._run_ai_responses()
            
            # CRITICAL: Explicit save after AI responses to ensure all messages are persisted
            # This prevents message loss if the app closes immediately after responses
            if self.system:
                self.system._save_conversation()

        except Exception as e:
            self.error_occurred.emit(str(e))
        finally:
            self.ai_thinking.emit(False)

    @pyqtSlot()
    def send_listen(self):
        """Let AI characters continue without player input."""
        if not self.system or self._is_shutting_down:
            return
        try:
            self.ai_thinking.emit(True)
            self.status_update.emit("Listening quietly…")
            self._run_ai_responses(max_turns=3)
            # CRITICAL: Explicit save after AI responses
            if self.system:
                self.system._save_conversation()
        except Exception as e:
            self.error_occurred.emit(str(e))
        finally:
            self.ai_thinking.emit(False)

    @pyqtSlot()
    def send_skip(self):
        """Skip turn – let AI continue."""
        if not self.system or self._is_shutting_down:
            return
        try:
            self.ai_thinking.emit(True)
            self.status_update.emit("Skipping turn…")
            self._run_ai_responses(max_turns=3)
            # CRITICAL: Explicit save after AI responses
            if self.system:
                self.system._save_conversation()
        except Exception as e:
            self.error_occurred.emit(str(e))
        finally:
            self.ai_thinking.emit(False)

    @pyqtSlot()
    def reset_conversation(self):
        """Reset the conversation."""
        if not self.system or self._is_shutting_down:
            return
        try:
            self.status_update.emit("Resetting conversation…")
            self.system.reset_conversation()

            # Re-add the initial scene
            cfg = self._init_config
            initial_scene = self.system.timeline_manager.create_scene(
                scene_type="environmental",
                location=cfg["scene_location"],
                description=cfg["scene_description"],
            )
            self.system.timeline_manager.add_event(self.system.timeline, initial_scene)
            self.event_added.emit(self._serialize_event(initial_scene))

            # Send initial greeting
            greeting = cfg.get("initial_greeting", "Hello everyone!")
            self.system._add_player_message(greeting)
            from data_models import Message
            player_msg = self.system.timeline.events[-1]
            self.event_added.emit(self._serialize_event(player_msg))

            # Now indicate AI is thinking and run responses
            self.ai_thinking.emit(True)
            self._run_ai_responses()
            # CRITICAL: Explicit save after AI responses
            if self.system:
                self.system._save_conversation()
            self._emit_characters_updated()
            self._emit_story_updated()
            self.reset_complete.emit()
        except Exception as e:
            self.error_occurred.emit(str(e))
        finally:
            self.ai_thinking.emit(False)

    @pyqtSlot()
    def start_new_session(self):
        """Send initial greeting for a brand new session."""
        if not self.system or self._is_shutting_down:
            return
        try:
            cfg = self._init_config
            greeting = cfg.get("initial_greeting", "Hello everyone!")

            self.status_update.emit("Starting session…")
            self.system._add_player_message(greeting)
            from data_models import Message
            player_msg = self.system.timeline.events[-1]
            self.event_added.emit(self._serialize_event(player_msg))

            # Indicate AI is thinking and run responses
            self.ai_thinking.emit(True)
            self._run_ai_responses()
            # CRITICAL: Explicit save after AI responses
            if self.system:
                self.system._save_conversation()
            self._emit_characters_updated()
            self._emit_story_updated()
        except Exception as e:
            self.error_occurred.emit(str(e))
        finally:
            self.ai_thinking.emit(False)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def shutdown(self):
        """Gracefully shutdown the worker. Called before thread termination.
        
        This CRITICAL sequence ensures:
        1. Background tasks are allowed to complete
        2. TurnManager shuts down its executor gracefully
        3. All events (including background-generated) are saved
        4. New operations are blocked
        
        Must be called before the thread is quit to prevent message loss.
        """
        # 1. Wait for background tasks to complete in TurnManager
        if self.system and hasattr(self.system, 'turn_manager'):
            try:
                self.system.turn_manager.shutdown()
            except Exception as e:
                print(f"[WARNING] Failed to shutdown TurnManager: {e}")
        
        # 2. Set flag to stop accepting new operations
        self._is_shutting_down = True
        
        # 3. Final save to ensure all events are persisted
        if self.system:
            try:
                self.system._save_conversation()
            except Exception as e:
                print(f"[WARNING] Failed to save during worker shutdown: {e}")

    def _on_backend_status(self, text: str):
        """Callback injected into TurnManager to receive status prints."""
        self.status_update.emit(text)

    def _run_ai_responses(self, max_turns: int = None):
        """
        Run AI responses and emit each new event as it arrives.
        We snapshot the timeline length before and after each speaker turn.
        """
        import time
        from data_models import Message, Scene, Action, CharacterEntry, CharacterExit

        turn_manager = self.system.turn_manager

        if max_turns is None:
            max_turns = turn_manager.max_consecutive_ai_turns

        # Run the full AI response cycle. TurnManager will call our
        # on_new_event callback for each event as it's created, so we
        # don't need to batch-emit here.
        responses = turn_manager.process_ai_responses(max_turns=max_turns)

        # After the AI turn sequence completes, refresh character/story views
        self._emit_characters_updated()
        self._emit_story_updated()

    def _serialize_event(self, event) -> dict:
        """Convert a timeline event to a plain dict for cross-thread signalling."""
        from data_models import Message, Scene, Action, CharacterEntry, CharacterExit

        base = {
            "timeline_id": event.timeline_id,
            "timestamp": event.timestamp.isoformat(),
        }
        if isinstance(event, Message):
            base.update({
                "type": "message",
                "character": event.character,
                "dialouge": event.dialouge,
                "action_description": event.action_description,
            })
        elif isinstance(event, Scene):
            base.update({
                "type": "scene",
                "scene_type": event.scene_type,
                "location": event.location,
                "description": event.description,
            })
        elif isinstance(event, Action):
            base.update({
                "type": "action",
                "character": event.character,
                "description": event.description,
            })
        elif isinstance(event, CharacterEntry):
            base.update({
                "type": "character_entry",
                "character": event.character,
                "description": event.description,
            })
        elif isinstance(event, CharacterExit):
            base.update({
                "type": "character_exit",
                "character": event.character,
                "description": event.description,
            })
        else:
            base["type"] = "unknown"
        return base

    def _emit_characters_updated(self):
        """Emit characters_updated signal with current character data."""
        if not self.system:
            return
        chars = []
        for char in self.system.ai_characters:
            chars.append({
                "name": char.persona.name,
                "objective": char.state.current_objective if char.state else None,
                "in_scene": char.persona.name in self.system.timeline.current_participants,
            })
        self.characters_updated.emit(chars)

    def _emit_story_updated(self):
        """Emit story_updated signal with current story data."""
        if not self.system or not self.system.story_manager or not self.system.story_manager.story:
            return
        story = self.system.story_manager.story
        self.story_updated.emit({
            "title": story.title,
            "current_objective": self.system.story_manager.get_current_objective() or "None",
            "beat_index": story.current_objective_index,
            "total_beats": len(story.objectives),
            "complete": self.system.story_manager.is_story_complete(),
        })

    def _emit_characters_and_story_update(self):
        """Called when background tasks complete."""
        self._emit_characters_updated()
        self._emit_story_updated()
