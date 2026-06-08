"""
Turn management system for natural conversation flow.
Handles ONLY turn decision logic - determines who should speak next.
All timeline operations are delegated to TimelineManager.
"""

from concurrent.futures import ThreadPoolExecutor, Future, as_completed
import random
import threading
import time
from typing import List, Optional, Tuple
from data_models import Message, TimelineHistory, Character, Scene, CharacterEntry, CharacterExit
from managers.timelineManager import TimelineManager
from managers.characterManager import CharacterManager
from managers.storyManager import StoryManager
from gemini_client import Config


class TurnManager:
    """
    Manages conversation flow and turn selection with natural timing.
    
    Responsibilities:
    - Decide who should speak next based on context
    - Coordinate between AI characters to determine speaking order
    - Process consecutive AI responses naturally
    """
    
    def __init__(
        self,
        characters: List[Character],
        timeline: TimelineHistory,
        story_manager: Optional[StoryManager] = None,
        max_consecutive_ai_turns: int = None,
        priority_randomness: float = None,
        save_callback: Optional[callable] = None,
        on_status: Optional[callable] = None
    ):
        """
        Initialize the turn manager.
        
        Args:
            characters: List of AI characters in the conversation
            timeline: TimelineHistory instance containing all events and participants
            story_manager: Optional StoryManager for narrative progression
            max_consecutive_ai_turns: Maximum number of consecutive AI turns 
            priority_randomness: Random factor to add to priority for naturalness 
            save_callback: Optional callback function to save conversation after AI responses
            on_status: Optional callback(str) called instead of print() for status messages.
                       When set, time.sleep() calls are also skipped (GUI mode).
        """
        self.characters = characters
        self.timeline = timeline
        
        self.max_consecutive_ai_turns = max_consecutive_ai_turns or Config.MAX_CONSECUTIVE_AI_TURNS
        self.priority_randomness = priority_randomness or Config.PRIORITY_RANDOMNESS
        self.save_callback = save_callback
        self.on_status = on_status  # injectable status callback for GUI mode
        
        # Initialize managers
        self.timeline_manager = TimelineManager()
        self.character_manager = CharacterManager()
        self.story_manager = story_manager if story_manager is not None else StoryManager()
        
        self.turn_count = 0
        self.turns_since_last_background_task = 0
        self.timeline_lock = threading.Lock()
        self.background_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="background-story")
        self.background_task_future: Optional[Future] = None
        # Optional callbacks (set by UI worker)
        # on_new_event(event) -> called whenever this manager adds an event to timeline
        # on_thinking_update(name, text) -> called when a character's decision reasoning arrives
        # on_background_update() -> called when background story tasks complete
        self.on_new_event = None
        self.on_thinking_update = None
        self.on_background_update = None
    
    def _status(self, text: str):
        """Emit a status message via callback if set, otherwise print."""
        if self.on_status:
            self.on_status(text)
        else:
            try:
                print(text)
            except UnicodeEncodeError:
                # Fallback: strip unencodable chars for Windows terminals
                print(text.encode('ascii', errors='replace').decode('ascii'))

    def _sleep(self, seconds: float):
        """Sleep only in terminal mode; skip in GUI mode (on_status is set)."""
        if not self.on_status:
            time.sleep(seconds)

    def _safe_save(self) -> None:
        """Save the current conversation safely using timeline locking."""
        if self.save_callback:
            with self.timeline_lock:
                try:
                    self.save_callback()
                except Exception as e:
                    self._status(f"⚠️ Save callback error: {e}")

    def _process_meta_narrative_decisions(self) -> None:
        """
        Process meta-narrative decisions in a SINGLE unified API call.

        Previously this was two sequential API calls:
          1. should_generate_scene()       (decide + generate scene)
          2. decide_character_movements()  (entries / exits)

        Now both are resolved in one LLM call via prepare_turn_context(),
        which shares the same timeline context and saves one round-trip.
        """
        all_character_names = [c.persona.name for c in self.characters]

        # --- Single unified API call ---
        context = self.timeline_manager.prepare_turn_context(
            timeline=self.timeline,
            all_characters=all_character_names,
            recent_event_count=15
        )

        # --- Handle scene (if any) ---
        scene_data = context.get("scene")
        if scene_data:
            scene_type = scene_data.get("scene_type", "environmental")
            scene = self.timeline_manager.create_scene(
                scene_type=scene_type,
                location=scene_data.get("location", "Unknown"),
                description=scene_data.get("event_description", ""),
                time_of_day=scene_data.get("time_of_day")
            )
            self.timeline_manager.add_event(self.timeline, scene)
            try:
                if self.on_new_event:
                    self.on_new_event(scene)
            except Exception:
                pass

            self._safe_save()

            with self.timeline_lock:
                active_characters = [c for c in self.characters if c.persona.name in self.timeline.current_participants]
            self.character_manager.broadcast_event_to_characters(active_characters, scene)

            if scene_type == "transition":
                self._status(f"SCENE TRANSITION → {scene.location}")
            else:
                self._status(f"ENVIRONMENTAL SCENE at {scene.location}")
            self._status(scene.description)
            self._sleep(1)

        # --- Handle character movements (entries then exits) ---
        entries = context.get("entries", [])
        exits = context.get("exits", [])

        for movement_info, is_entry in [(info, True) for info in entries] + [(info, False) for info in exits]:
            character_name = movement_info.get("character")
            description = movement_info.get("description")

            if not character_name or not description:
                continue

            character = next((c for c in self.characters if c.persona.name == character_name), None)
            if not character:
                continue

            action = "entering" if is_entry else "leaving"
            self._status(f"{character_name} is {action}...")

            if is_entry:
                event = CharacterEntry(character=character_name, description=description)
            else:
                event = CharacterExit(character=character_name, description=description)

            self.timeline_manager.add_event(self.timeline, event)
            try:
                if self.on_new_event:
                    self.on_new_event(event)
            except Exception:
                pass

            self._safe_save()

            with self.timeline_lock:
                active_characters = [c for c in self.characters if c.persona.name in self.timeline.current_participants]
            self.character_manager.broadcast_event_to_characters(active_characters, event)

            self._status(f"   {description}")
            self._sleep(1)

    def _schedule_background_story_tasks(self) -> None:
        """Schedule judge, scene, and movement decisions in the background."""
        if self.background_task_future is None or self.background_task_future.done():
            self.background_task_future = self.background_executor.submit(
                self._run_parallel_background_story_tasks
            )

    def _run_parallel_background_story_tasks(self) -> None:
        """Run judge, scene generation, and movement decisions concurrently in background."""
        self._status("Background story tasks starting…")

        with self.timeline_lock:
            all_character_names = [c.persona.name for c in self.characters]
            current_participants = list(self.timeline.current_participants)
            current_location = self.timeline_manager.get_current_location(self.timeline) or "Unknown"
            current_tod = self.timeline_manager.get_current_time_of_day(self.timeline) or "Unknown"
            timeline_context = self.timeline_manager.get_timeline_context(
                self.timeline,
                recent_event_count=15
            )

        def background_get_active_characters():
            return [c for c in self.characters if c.persona.name in current_participants]

        results = {}
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(
                    self.timeline_manager.decide_character_movements,
                    timeline_context,
                    all_character_names,
                    current_participants,
                    current_location,
                    current_tod
                ): "movements",
                executor.submit(
                    self.timeline_manager.should_generate_scene,
                    self.timeline,
                    15
                ): "scene",
                executor.submit(
                    self.story_manager.evaluate_and_assign_objectives,
                    background_get_active_characters(),
                    self.timeline
                ): "judge",
            }

            for future in as_completed(futures):
                key = futures[future]
                try:
                    results[key] = future.result()
                except Exception as e:
                    self._status(f"Background {key} task error: {e}")
                    results[key] = None

        # Process scene result
        scene_data = results.get("scene")
        if scene_data and scene_data.get("scene_generated"):
            scene_type = scene_data.get("scene_type", "environmental")
            scene = self.timeline_manager.create_scene(
                scene_type=scene_type,
                location=scene_data.get("location", "Unknown"),
                description=scene_data.get("event_description", ""),
                time_of_day=scene_data.get("time_of_day")
            )
            with self.timeline_lock:
                self.timeline_manager.add_event(self.timeline, scene)
            try:
                if self.on_new_event:
                    self.on_new_event(scene)
            except Exception:
                pass

            with self.timeline_lock:
                active_characters = [c for c in self.characters if c.persona.name in self.timeline.current_participants]
            self.character_manager.broadcast_event_to_characters(active_characters, scene)
            self._safe_save()

            if scene_type == "transition":
                self._status(f"SCENE TRANSITION → {scene.location}")
            else:
                self._status(f"ENVIRONMENTAL SCENE at {scene.location}")
            self._status(scene.description)

        # Process character movements
        movements = results.get("movements") or ([], [])
        entries, exits = movements if isinstance(movements, tuple) else ([], [])
        for movement_info, is_entry in [(info, True) for info in entries] + [(info, False) for info in exits]:
            character_name = movement_info.get("character")
            description = movement_info.get("description")
            if not character_name or not description:
                continue

            character = next((c for c in self.characters if c.persona.name == character_name), None)
            if not character:
                continue

            if is_entry:
                event = self.timeline_manager.create_character_entry(
                    character=character_name,
                    description=description
                )
            else:
                event = self.timeline_manager.create_character_exit(
                    character=character_name,
                    description=description
                )

            with self.timeline_lock:
                self.timeline_manager.add_event(self.timeline, event)
            try:
                if self.on_new_event:
                    self.on_new_event(event)
            except Exception:
                pass

            self._safe_save()

            with self.timeline_lock:
                active_characters = [c for c in self.characters if c.persona.name in self.timeline.current_participants]
            self.character_manager.broadcast_event_to_characters(active_characters, event)
            action = "entering" if is_entry else "leaving"
            self._status(f"{character_name} is {action}...")
            self._status(f"   {description}")

        # Process judge results
        judge_result = results.get("judge") or {}
        char_updates = judge_result.get("character_updates", {}) if isinstance(judge_result, dict) else {}
        for character in background_get_active_characters():
            char_name = character.persona.name
            if char_name not in char_updates:
                continue
            char_update = char_updates[char_name]
            new_objective = char_update.get("objective")
            status = char_update.get("status", "unknown")
            reasoning = char_update.get("reasoning", "")

            if status == "assigned":
                self._status(f"{char_name}: New objective — {new_objective}")
                character.state.current_objective = new_objective
            elif status == "completed":
                self._status(f"{char_name}: Objective completed → {new_objective}")
                character.state.current_objective = new_objective
            elif status == "continuing" and new_objective:
                character.state.current_objective = new_objective

        if judge_result.get("story_objective_complete"):
            self._status(f"Story objective COMPLETED: {judge_result.get('reasoning', '')}")
            advanced = self.story_manager.advance_story_objective()
            if advanced:
                new_objective = self.story_manager.get_current_objective()
                self._status(f"Story advancing → {new_objective}")
                for character in background_get_active_characters():
                    character.state.current_objective = None
            else:
                if self.story_manager.story:
                    self._status(f"STORY COMPLETE: {self.story_manager.story.title}")
        else:
            if judge_result.get("reasoning"):
                self._status(f"Story in progress: {judge_result.get('reasoning')}")

        if self.save_callback:
            self._safe_save()

        if self.on_background_update:
            try:
                self.on_background_update()
            except Exception:
                pass

    def select_next_speaker(self, last_speaker_name: Optional[str] = None) -> Optional[Tuple[Character, str, Optional[str], Optional[str], float]]:
        """
        Select which AI character should respond next (speak or act).
        
        Each character decides whether to SPEAK (dialogue + action), ACT (action only), or stay SILENT.
        This function collects all decisions and selects the highest-priority speaker/actor.
        Characters who choose to stay SILENT are filtered out and do not contribute to the result.
        
        When there are multiple active AI characters, the previous speaker is excluded from
        decision-making so they do not consume an API call unnecessarily.
        
        Returns:
            Tuple of (character, response_type, dialogue, action) for the selected character, or None
            - For "speak": dialogue=spoken words, action=body language
            - For "act": response_type="act", dialogue=None, action=physical action
            - If all characters choose "silent": returns None (no one wants to speak/act)
        """
        # Check if there are any events in the timeline
        with self.timeline_lock:
            recent_events = self.timeline_manager.get_recent_events(timeline=self.timeline)
        if not recent_events:
            return None
        
        self._status("AI characters are thinking…")
        
        # Collect decisions from all currently active characters
        with self.timeline_lock:
            active_characters = [c for c in self.characters if c.persona.name in self.timeline.current_participants]
        if not active_characters:
            self._status("No one wants to speak right now.")
            return None
        
        if last_speaker_name:
            active_characters = [c for c in active_characters if c.persona.name != last_speaker_name]
            if not active_characters:
                self._status("No other active character is available to speak right now.")
                return None
        
        def get_character_decision(character: Character):
            # NOTE: decide_turn_response() ALWAYS returns a tuple (never None)
            # It returns (type, priority, reasoning, dialogue, action) where type is "speak", "act", or "silent"
            return character, self.character_manager.decide_turn_response(character)
        
        # This list only contains characters who chose "speak" or "act" (silent responses are filtered out)
        decisions = []
        quota_exceeded = False
        with ThreadPoolExecutor(max_workers=len(active_characters)) as executor:
            futures = {executor.submit(get_character_decision, char): char for char in active_characters}
            for future in as_completed(futures):
                try:
                    character, (response_type, priority, reasoning, dialogue, action) = future.result()
                    
                    if reasoning == "API_QUOTA_EXCEEDED":
                        quota_exceeded = True
                        continue
                    
                    if response_type == "speak":
                        # Character wants to speak: add to decisions list (will be considered for selection)
                        decisions.append((character, (response_type, priority, reasoning, dialogue, action)))
                        self._status(f"💭 {character.persona.name}: Priority {priority:.2f} (Speech) - {reasoning}")
                        # Notify UI about the character's thinking/reasoning text
                        try:
                            if self.on_thinking_update:
                                self.on_thinking_update(character.persona.name, reasoning)
                        except Exception:
                            pass
                    elif response_type == "act":
                        # Character wants to act: add to decisions list (will be considered for selection)
                        decisions.append((character, (response_type, priority, reasoning, dialogue, action)))
                        self._status(f"👤 {character.persona.name}: Priority {priority:.2f} (Action) - {reasoning}")
                        # Notify UI about the character's thinking/reasoning text
                        try:
                            if self.on_thinking_update:
                                self.on_thinking_update(character.persona.name, reasoning)
                        except Exception:
                            pass
                    else:
                        # response_type == "silent": NOT added to decisions list (filtered out)
                        # This character chose to remain quiet and will not be selected as the next speaker
                        self._status(f"🤐 {character.persona.name}: {reasoning}")
                        # Emit thinking update for silent decisions so UI can show why the character stayed quiet
                        try:
                            if self.on_thinking_update:
                                self.on_thinking_update(character.persona.name, reasoning)
                        except Exception:
                            pass
                except Exception as e:
                    character = futures[future]
                    self._status(f"⚠️ Error getting decision from {character.persona.name}: {e}")
        
        if quota_exceeded:
            self._status("⚠️ API QUOTA EXCEEDED")
        
        if not decisions:
            # decisions list is empty = all characters chose type="silent" and were filtered out
            # In this case, return None to signal there are no more speakers/actors
            self._status("No one wants to speak right now.")
            return None
        
        # Filter out extremely low-priority decisions (treat as silent)
        PRIORITY_THRESHOLD = 0.01
        filtered_decisions = [(char, decision_tuple) for (char, decision_tuple) in decisions
                              if isinstance(decision_tuple[1], (int, float)) and decision_tuple[1] > PRIORITY_THRESHOLD]
        if not filtered_decisions:
            self._status("No one has sufficient priority to speak right now.")
            return None

        # Sort by priority with small random factor for naturalness
        decisions_with_adjusted_priority = [
            (char, decision_tuple, decision_tuple[1] + random.uniform(-self.priority_randomness, self.priority_randomness))
            for char, decision_tuple in filtered_decisions
        ]
        decisions_with_adjusted_priority.sort(key=lambda x: x[2], reverse=True)
        selected_character, decision_tuple, _ = decisions_with_adjusted_priority[0]
        response_type = decision_tuple[0]
        dialogue = decision_tuple[3]
        action = decision_tuple[4]
        priority = decision_tuple[1]
        return (selected_character, response_type, dialogue, action, priority)
    
    def process_ai_responses(self, max_turns: Optional[int] = None) -> List[Tuple[Character, str]]:
        """Process AI responses ONE AT A TIME until no one wants to speak or max turns reached.
        Each character sees the updated conversation including previous AI responses.
        Returns the list of (character, message) tuples for the caller to handle.
        
        Args:
            max_turns: Maximum number of consecutive AI turns (uses default if None)
            
        Returns:
            List of (character, message) tuples for AI turns that want to speak """
        
        if max_turns is None:
            max_turns = self.max_consecutive_ai_turns

        responses = []
        consecutive_count = 0
        last_speaker = None
        self.turns_since_last_background_task = 0
        self._schedule_background_story_tasks()
        
        while consecutive_count < max_turns:
            # Ask ONE character at a time (sequentially, not in parallel)
            # select_next_speaker() collects decisions from all characters, filters out "silent" responses,
            # and returns the highest-priority speaker/actor. Returns None if all characters chose "silent".
            result = self.select_next_speaker(last_speaker)
            
            if result is None:
                # All characters chose type="silent" and were filtered out from the decisions list.
                # No one wants to speak or act, so we end the turn sequence.
                break
            
            # Unpack result (now includes priority)
            character, response_type, dialogue, action, priority = result
            
            # Validate that we have dialouge before processing
            if response_type == "speak" and not dialogue:
                self._status(f"{character.persona.name} chose to speak but provided no dialogue, skipping...")
                continue
            elif response_type == "act" and not action:
                self._status(f"{character.persona.name} chose to act but provided no action, skipping...")
                continue
            
            # Handle different response types
            if response_type == "speak":
                # For speak: dialogue = spoken words, action = body language
                body_language = action
                
                # Create and add the message to the timeline
                message_obj = self.timeline_manager.create_message(
                    character=character.persona.name,
                    dialouge=dialogue,
                    action_description=body_language or "speaks"
                )
                with self.timeline_lock:
                    self.timeline_manager.add_event(self.timeline, message_obj)
                try:
                    if self.on_new_event:
                        self.on_new_event(message_obj)
                except Exception:
                    pass
                
                self._safe_save()

                responses.append((character, dialogue))

                with self.timeline_lock:
                    active_characters = [c for c in self.characters if c.persona.name in self.timeline.current_participants]
                self.character_manager.broadcast_event_to_characters(active_characters, message_obj)
            
            elif response_type == "act":
                # For act: dialogue is None, action contains the physical action
                physical_action = action
                
                # Create and add the action to the timeline
                action_obj = self.timeline_manager.create_action(
                    character=character.persona.name,
                    description=physical_action
                )
                with self.timeline_lock:
                    self.timeline_manager.add_event(self.timeline, action_obj)
                try:
                    if self.on_new_event:
                        self.on_new_event(action_obj)
                except Exception:
                    pass
                
                self._safe_save()

                with self.timeline_lock:
                    active_characters = [c for c in self.characters if c.persona.name in self.timeline.current_participants]
                self.character_manager.broadcast_event_to_characters(active_characters, action_obj)

            last_speaker = character.persona.name
            consecutive_count += 1
            
            if self.story_manager:
                self.turns_since_last_background_task += 1
                if self.turns_since_last_background_task >= 3:
                    self.turns_since_last_background_task = 0
                    self._schedule_background_story_tasks()
            
            # Small delay for readability in terminal mode only
            self._sleep(2)
        
        # Save conversation after AI responses if callback is provided
        if responses and self.save_callback:
            self._safe_save()
        
        return responses
    
    def _evaluate_objectives_with_judge(self) -> None:
        """Evaluate and update character objectives using unified judge LLM call."""
        if not self.story_manager or not self.story_manager.story:
            return
        
        # Skip if story is complete
        if self.story_manager.is_story_complete():
            return
        
        self._status("Judge evaluating objectives…")
        
        # Get active characters
        with self.timeline_lock:
            active_characters = [c for c in self.characters if c.persona.name in self.timeline.current_participants]
        
        if not active_characters:
            return
        
        # Call unified judge LLM (handles both initial assignment and evaluation)
        result = self.story_manager.evaluate_and_assign_objectives(active_characters, self.timeline)
        
        # Process character updates
        char_updates = result.get("character_updates", {})
        
        for character in active_characters:
            char_name = character.persona.name
            if char_name not in char_updates:
                continue
            
            char_update = char_updates[char_name]
            new_objective = char_update.get("objective")
            status = char_update.get("status", "unknown")
            reasoning = char_update.get("reasoning", "")
            
            if status == "assigned":
                self._status(f"{char_name}: New objective — {new_objective}")
                character.state.current_objective = new_objective
            elif status == "completed":
                self._status(f"{char_name}: Objective completed → {new_objective}")
                character.state.current_objective = new_objective
            elif status == "continuing":
                if new_objective:
                    character.state.current_objective = new_objective
        
        # Check story objective completion
        story_complete = result.get("story_objective_complete", False)
        story_reasoning = result.get("reasoning", "")
        
        if story_complete:
            self._status(f"Story objective COMPLETED: {story_reasoning}")
            
            # Advance to next objective
            advanced = self.story_manager.advance_story_objective()
            
            if advanced:
                new_objective = self.story_manager.get_current_objective()
                self._status(f"Story advancing → {new_objective}")
                
                # Clear current objectives so next cycle will assign new ones
                for character in active_characters:
                    character.state.current_objective = None
            else:
                # Story fully complete
                self._status(f"STORY COMPLETE: {self.story_manager.story.title}")
        else:
            self._status(f"Story in progress: {story_reasoning}")
        
        # Save after evaluation
        if self.save_callback:
            self._safe_save()

    def shutdown(self) -> None:
        """
        Gracefully shutdown the TurnManager.
    
        Waits for any pending background tasks to complete and then shuts down the executor.
        This MUST be called before the system exits to ensure background-generated events are saved.
        """
        self._status("TurnManager: Waiting for background tasks to complete…")
    
        # Wait for any pending background task to complete (up to 10 seconds)
        if self.background_task_future is not None and not self.background_task_future.done():
            try:
                # Wait for the background task with timeout
                self.background_task_future.result(timeout=10)
            except Exception as e:
                self._status(f"[WARNING] Background task did not complete gracefully: {e}")
    
        # Shut down the background executor
        try:
            self.background_executor.shutdown(wait=True, timeout=5)
        except Exception as e:
            self._status(f"[WARNING] Error shutting down background executor: {e}")
    
        # Final save to ensure all background-generated events are persisted
        self._safe_save()
        self._status("TurnManager: Shutdown complete.")