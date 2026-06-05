"""
Turn management system for natural conversation flow.
Handles ONLY turn decision logic - determines who should speak next.
All timeline operations are delegated to TimelineManager.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
import random
import time
from typing import List, Optional, Tuple
from colorama import Fore, Style

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
            max_consecutive_ai_turns: Maximum number of consecutive AI turns (defaults to Config.MAX_CONSECUTIVE_AI_TURNS)
            priority_randomness: Random factor to add to priority for naturalness (defaults to Config.PRIORITY_RANDOMNESS)
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
        self.story_manager = StoryManager()
        
        self.turn_count = 0
        self.consecutive_silence_rounds = 0
    
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

    def _collect_speaking_decisions(self) -> List[Tuple[Character, Tuple[str, float, str, Optional[str], Optional[str]]]]:
        """
        Collect response decisions from all AI characters using parallel execution.
        
        Returns:
            List of tuples containing (character, decision_tuple) for characters that want to respond (speak or act)
        """
        decisions = []
        quota_exceeded = False
        
        # Define worker function for parallel execution
        def get_character_decision(character):
            return character, self.character_manager.decide_turn_response(
                character
            )
        
        # Execute all character decisions in parallel
        with ThreadPoolExecutor(max_workers=len(self.characters)) as executor:
            futures = {executor.submit(get_character_decision, char): char for char in self.characters}
            
            # Process results as they complete
            for future in as_completed(futures):
                try:
                    character, (response_type, priority, reasoning, dialogue, action) = future.result()
                    
                    # Check for quota exceeded error
                    if reasoning == "API_QUOTA_EXCEEDED":
                        quota_exceeded = True
                        continue
                    
                    if response_type in ["speak", "act"]:
                        decisions.append((character, (response_type, priority, reasoning, dialogue, action)))
                        emoji = "💭" if response_type == "speak" else "👤"
                        type_label = "Speech" if response_type == "speak" else "Action"
                        self._status(f"{emoji} {character.persona.name}: Priority {priority:.2f} ({type_label}) - {reasoning}")
                    else:
                        self._status(f"🤐 {character.persona.name}: {reasoning}")
                        
                except Exception as e:
                    character = futures[future]
                    self._status(f"⚠️ Error getting decision from {character.persona.name}: {e}")
        
        if quota_exceeded:
            self._status("⚠️ API QUOTA EXCEEDED")
        
        return decisions
    
    def _select_speaker_from_decisions(
        self, 
        decisions: List[Tuple[Character, Tuple[str, float, str, Optional[str], Optional[str]]]]
    ) -> Optional[Tuple[Character, str, Optional[str], Optional[str]]]:
        """
        Select which character should respond (speak or act) based on priorities.
        
        Args:
            decisions: List of (character, decision_tuple) tuples
            
        Returns:
            Tuple of (character, response_type, dialogue, action) for the selected character, or None
            - For "speak": dialogue=spoken words, action=body language
            - For "act": dialogue=None, action=physical action
        """
        if not decisions:
            return None
        
        # Sort by priority with small random factor for naturalness
        decisions_with_adjusted_priority = [
            (char, decision_tuple, decision_tuple[1] + random.uniform(-self.priority_randomness, self.priority_randomness))
            for char, decision_tuple in decisions
        ]
        
        decisions_with_adjusted_priority.sort(key=lambda x: x[2], reverse=True)
        selected_character, decision_tuple, _ = decisions_with_adjusted_priority[0]
        response_type = decision_tuple[0]
        dialogue = decision_tuple[3]  
        action = decision_tuple[4]
        return (selected_character, response_type, dialogue, action)
    
    def _process_meta_narrative_decisions(self) -> None:
        """
        Process meta-narrative decisions sequentially.
        
        Workflow:
        1. Check if scene transition should happen
        2. Check for character entries and exits (ONE combined API call)
        
        All decisions use full timeline context (not filtered by character memory).
        """
        # Step 1: Check for scene transition
        scene_decision = self.timeline_manager.should_generate_scene(self.timeline, recent_event_count=15)
        if scene_decision:
            scene_type = scene_decision.get('scene_type', 'environmental')
            scene = self.timeline_manager.create_scene(
                scene_type=scene_type,
                location=scene_decision['location'],
                description=scene_decision['event_description']
            )
            self.timeline_manager.add_event(self.timeline, scene)
            
            # Broadcast scene to currently active characters only
            active_characters = [c for c in self.characters if c.persona.name in self.timeline.current_participants]
            self.character_manager.broadcast_event_to_characters(active_characters, scene)
            
            # Display scene based on type
            if scene_type == 'transition':
                self._status(f"SCENE TRANSITION → {scene.location}")
            else:
                self._status(f"ENVIRONMENTAL SCENE at {scene.location}")
            self._status(scene.description)
            
            self._sleep(1)
        
        # Step 2: Check for character entries AND exits 
        timeline_context = self.timeline_manager.get_timeline_context(self.timeline, recent_event_count=15)
        current_location = self.timeline_manager.get_current_location(self.timeline)
        all_character_names = [c.persona.name for c in self.characters]
        
        entries, exits = self.timeline_manager.decide_character_movements(
            timeline_context=timeline_context,
            all_characters=all_character_names,
            current_participants=self.timeline.current_participants,
            current_location=current_location or "Unknown"
        )
        
        # Process all character movements (entries and exits) in a single loop
        for movement_info, is_entry in [(info, True) for info in entries] + [(info, False) for info in exits]:
            character_name = movement_info.get('character')
            description = movement_info.get('description')
            
            if not character_name or not description:
                continue
            
            # Find the character object
            character = next((c for c in self.characters if c.persona.name == character_name), None)
            if not character:
                continue
            
            action = "entering" if is_entry else "leaving"
            self._status(f"{character_name} is {action}...")
            
            # Create appropriate event
            if is_entry:
                event = CharacterEntry(character=character_name, description=description)
            else: 
                event = CharacterExit(character=character_name, description=description)
            
            self.timeline_manager.add_event(self.timeline, event)
            
            # Broadcast to currently active characters
            active_characters = [c for c in self.characters if c.persona.name in self.timeline.current_participants]
            self.character_manager.broadcast_event_to_characters(active_characters, event)
            
            # For entries, also add to the entering character's memory
            if is_entry:
                self.character_manager.broadcast_event_to_characters([character], event)
            
            self._status(f"   {description}")
            self._sleep(1)
    
    def select_next_speaker(self) -> Optional[Tuple[Character, str, Optional[str], Optional[str]]]:
        """
        Select which AI character should respond next (speak or act).
        
        Returns:
            Tuple of (character, response_type, dialogue, action) for the selected character, or None
            - For "speak": dialogue=spoken words, action=body language
            - For "act": dialogue=physical action, action=None
        """
        # Check if there are any events in the timeline
        recent_events = self.timeline_manager.get_recent_events(timeline=self.timeline)
        if not recent_events:
            return None
        
        self._status("AI characters are thinking…")
        
        # Collect decisions from all currently active characters
        active_characters = [c for c in self.characters if c.persona.name in self.timeline.current_participants]
        
        # Temporarily update self.characters for _collect_speaking_decisions
        original_characters = self.characters
        self.characters = active_characters
        decisions = self._collect_speaking_decisions()
        self.characters = original_characters
        
        if not decisions:
            self._status("No one wants to speak right now.")
            return None
        
        # Select the speaker
        result = self._select_speaker_from_decisions(decisions)
        
        return result
    
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
        
        # STEP 1: Process meta-narrative decisions FIRST
        # This happens before character decisions to set the stage
        self._process_meta_narrative_decisions()
        
        responses = []
        consecutive_count = 0
        last_speaker = None
        
        while consecutive_count < max_turns:
            # Ask ONE character at a time (sequentially, not in parallel)
            # Note: select_next_speaker() prints its own "thinking" and "no one speaks" messages
            result = self.select_next_speaker()
            
            if result is None:
                # No one wants to speak - increment silence counter
                self.consecutive_silence_rounds += 1
                self._status(f"Silence round {self.consecutive_silence_rounds}/2")
                
                # Generate scene event when conversation stalls
                if self.consecutive_silence_rounds >= 2:
                    try:
                        scene = self.timeline_manager.generate_scene_event(
                            scene_type="environmental",
                            timeline=self.timeline,
                            recent_event_count=15
                        )
                        
                        self._status(scene.description)
                        
                        # Add scene to timeline
                        self.timeline_manager.add_event(self.timeline, scene)
                        
                        # Broadcast scene event to currently active characters only
                        active_characters = [c for c in self.characters if c.persona.name in self.timeline.current_participants]
                        self.character_manager.broadcast_event_to_characters(active_characters, scene)
                        
                        # Save conversation after scene event if callback is provided
                        if self.save_callback:
                            self.save_callback()
                        
                        self._sleep(2)
                        
                    except Exception as e:
                        self._status(f"Error generating scene event: {e}")
                    # Reset silence counter after scene event
                    self.consecutive_silence_rounds = 0
                
                break
            
            # Reset silence counter when someone responds
            self.consecutive_silence_rounds = 0
            
            character, response_type, dialogue, action = result
            
            # Prevent the same character from responding twice in a row
            if last_speaker == character.persona.name:
                self._status(f"{character.persona.name} already responded, giving others a chance...")
                continue  # Continue to next iteration instead of breaking, let other characters respond
            
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
                self.timeline_manager.add_event(self.timeline, message_obj)
                
                # Broadcast this TimelineEvent to currently active characters only
                active_characters = [c for c in self.characters if c.persona.name in self.timeline.current_participants]
                self.character_manager.broadcast_event_to_characters(active_characters, message_obj)
                
                # Log the spoken message
                self._status(f"{character.persona.name}: \"{dialogue}\"")
                
                responses.append((character, dialogue))
            
            elif response_type == "act":
                # For act: dialogue is None, action contains the physical action
                physical_action = action
                
                # Create and add the action to the timeline
                action_obj = self.timeline_manager.create_action(
                    character=character.persona.name,
                    description=physical_action
                )
                self.timeline_manager.add_event(self.timeline, action_obj)
                
                # Broadcast this TimelineEvent to currently active characters only
                active_characters = [c for c in self.characters if c.persona.name in self.timeline.current_participants]
                self.character_manager.broadcast_event_to_characters(active_characters, action_obj)
                
                self._status(f"{character.persona.name}: *{physical_action}*")
                responses.append((character, f"[ACTION: {physical_action}]"))
            
            last_speaker = character.persona.name
            consecutive_count += 1
            
            # Small delay for readability in terminal mode only
            self._sleep(2)
        
        # JUDGE EVALUATION: After turn cycle completes, evaluate objectives
        if self.story_manager and responses:
            self._evaluate_objectives_with_judge()
        
        # Save conversation after AI responses if callback is provided
        if responses and self.save_callback:
            self.save_callback()
        
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
            self.save_callback()