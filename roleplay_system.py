"""
Main roleplay system coordinator.
"""

from typing import List, Optional
from pathlib import Path
from datetime import datetime
import json
from data_models import CharacterPersona, Character, TimelineHistory
from managers.turn_manager import TurnManager
from managers.timelineManager import TimelineManager
from gemini_client import Config


class RoleplaySystem:
    """Main coordinator for the multi-character roleplay system."""
    
    def __init__(
        self,
        player_name: str,
        characters: List[CharacterPersona],
        chat_storage_dir: str = None,
        story_manager = None,
        story_name: str = "default",
        initial_location: str = None,
        initial_scene_description: str = None
    ):
        """
        Initialize the roleplay system.
        
        Args:
            player_name: Name of the human player
            characters: List of character personas for AI characters
            chat_storage_dir: Directory to store chat logs (defaults to Config.CHAT_STORAGE_DIR)
            story_manager: Optional StoryManager for narrative progression
            story_name: Name of the story (used for unique conversation filenames)
            initial_location: Starting location for the conversation
            initial_scene_description: Optional initial scene description
        """
        
        self.player_name = player_name
        self.story_name = story_name
        
        # Import character manager early to create characters properly
        from managers.characterManager import CharacterManager
        temp_character_manager = CharacterManager()
        
        # Create AI characters with proper memory and state initialization
        self.ai_characters = [
            temp_character_manager.create_character(persona=persona)
            for persona in characters
        ]
        
        # Create timeline manager
        temp_timeline_manager = TimelineManager()
        
        # Create timeline with initial scene
        participant_names = [player_name] + [char.persona.name for char in self.ai_characters]
        timeline = temp_timeline_manager.create_timeline_history(
            title="Group Roleplay Session",
            participants=participant_names,
            visible_to_user=True
        )
        
        # Add initial scene
        if not initial_scene_description:
            initial_scene_description = f"The conversation begins in the {initial_location}."
        
        initial_scene = temp_timeline_manager.create_scene(
            scene_type="environmental",
            location=initial_location,
            description=initial_scene_description
        )
        temp_timeline_manager.add_event(timeline, initial_scene)
        
        # Create turn manager with pre-built timeline
        self.story_manager = story_manager if story_manager is not None else None
        self.turn_manager = TurnManager(
            characters=self.ai_characters,
            timeline=timeline,
            story_manager=self.story_manager,
            save_callback=lambda: self._save_conversation()
        )
        
        # Get references to managers for direct access
        self.timeline_manager = self.turn_manager.timeline_manager
        self.character_manager = self.turn_manager.character_manager
        self.timeline = self.turn_manager.timeline
        
        # Setup storage
        self.chat_storage_dir = Path(chat_storage_dir or Config.CHAT_STORAGE_DIR)
        self.chat_storage_dir.mkdir(exist_ok=True)
        
        # Try to load existing conversation; store result so callers can branch on it
        self.is_loaded_from_save = self._load_conversation_if_exists()
    
    def _load_conversation_if_exists(self) -> bool:
        """
        Load existing conversation from file if it exists.
        
        Returns:
            True if conversation was loaded, False otherwise
        """
        filepath = self.get_conversation_file_path()
        
        if not filepath.exists():
            return False
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Restore timeline from saved data
            from data_models import Message, Scene
            
            # Clear current timeline events
            self.timeline.events.clear()
            
            # Restore timeline metadata
            if 'id' in data:
                self.timeline.id = data['id']
            if 'title' in data:
                self.timeline.title = data['title']
            if 'participants' in data:
                self.timeline.participants = data['participants']
            if 'current_participants' in data:
                # Restore who was actively present in the conversation when saved
                self.timeline.current_participants = data['current_participants']
            if 'timeline_summary' in data:
                self.timeline.timeline_summary = data['timeline_summary']
            if 'visible_to_user' in data:
                self.timeline.visible_to_user = data['visible_to_user']

            # Restore story progress if available
            if 'story' in data:
                try:
                    sdata = data['story']
                    from data_models import Story
                    from managers.storyManager import StoryManager

                    if not self.story_manager:
                        self.story_manager = StoryManager(Story(**sdata))
                        self.turn_manager.story_manager = self.story_manager
                    elif not self.story_manager.story:
                        self.story_manager.story = Story(**sdata)
                    else:
                        # Preserve the loaded story structure, but restore saved progress
                        if 'title' in sdata:
                            self.story_manager.story.title = sdata['title']
                        if 'description' in sdata:
                            self.story_manager.story.description = sdata['description']
                        if isinstance(sdata.get('objectives'), list):
                            self.story_manager.story.objectives = sdata['objectives']

                        idx = sdata.get('current_objective_index', self.story_manager.story.current_objective_index)
                        if isinstance(idx, str) and idx.isdigit():
                            idx = int(idx)
                        if isinstance(idx, int):
                            idx = max(0, min(idx, len(self.story_manager.story.objectives)))
                            self.story_manager.story.current_objective_index = idx
                except Exception:
                    pass

            # Restore per-character objectives if available
            saved_char_states = data.get('character_states', {}) or {}
            if saved_char_states:
                for c in self.ai_characters:
                    try:
                        if c.persona.name in saved_char_states:
                            if not c.state:
                                from data_models import CharacterState
                                c.state = CharacterState(name=c.persona.name)
                            c.state.current_objective = saved_char_states[c.persona.name]
                    except Exception:
                        pass
            
            # Restore events (messages, scenes, and actions)
            for event_data in data.get('events', []):
                # Check for explicit type field first (new format)
                event_type = event_data.get('type')
                
                if event_type == 'message' or ('character' in event_data and 'dialouge' in event_data):
                    # This is a Message
                    message = Message(
                        timeline_id=event_data.get('timeline_id'),
                        timestamp=datetime.fromisoformat(event_data['timestamp']) if 'timestamp' in event_data else datetime.now(),
                        character=event_data['character'],
                        dialouge=event_data['dialouge'],
                        action_description=event_data['action_description']
                    )
                    self.timeline.events.append(message)
                elif event_type == 'scene' or ('location' in event_data and 'description' in event_data):
                    # This is a Scene
                    scene = Scene(
                        timeline_id=event_data.get('timeline_id'),
                        timestamp=datetime.fromisoformat(event_data['timestamp']) if 'timestamp' in event_data else datetime.now(),
                        scene_type=event_data.get('scene_type', 'environmental'),
                        location=event_data['location'],
                        description=event_data['description']
                    )
                    self.timeline.events.append(scene)
                elif event_type == 'character_entry':
                    # This is a CharacterEntry
                    from data_models import CharacterEntry
                    entry = CharacterEntry(
                        timeline_id=event_data.get('timeline_id'),
                        timestamp=datetime.fromisoformat(event_data['timestamp']) if 'timestamp' in event_data else datetime.now(),
                        character=event_data['character'],
                        description=event_data['description']
                    )
                    self.timeline.events.append(entry)
                elif event_type == 'character_exit':
                    # This is a CharacterExit
                    from data_models import CharacterExit
                    exit_event = CharacterExit(
                        timeline_id=event_data.get('timeline_id'),
                        timestamp=datetime.fromisoformat(event_data['timestamp']) if 'timestamp' in event_data else datetime.now(),
                        character=event_data['character'],
                        description=event_data['description']
                    )
                    self.timeline.events.append(exit_event)
                elif event_type == 'action':
                    # This is an Action
                    from data_models import Action
                    action = Action(
                        timeline_id=event_data.get('timeline_id'),
                        timestamp=datetime.fromisoformat(event_data['timestamp']) if 'timestamp' in event_data else datetime.now(),
                        character=event_data['character'],
                        description=event_data['description']
                    )
                    self.timeline.events.append(action)
                elif 'character' in event_data and 'description' in event_data:
                    # Legacy fallback for untyped events: assume an action if the event has a character and description
                    from data_models import Action
                    action = Action(
                        timeline_id=event_data.get('timeline_id'),
                        timestamp=datetime.fromisoformat(event_data['timestamp']) if 'timestamp' in event_data else datetime.now(),
                        character=event_data['character'],
                        description=event_data['description']
                    )
                    self.timeline.events.append(action)
            
            # Broadcast all events to characters so they have the full context
            # Replay timeline to track who was present at each point
            # Start with the saved "current_participants" if available, otherwise fall back to all participants
            if getattr(self.timeline, 'current_participants', None):
                present_at_moment = set(self.timeline.current_participants)
            else:
                present_at_moment = set(self.timeline.participants)
            
            for event in self.timeline.events:
                # Broadcast to whoever was present at this moment
                active_characters = [c for c in self.ai_characters if c.persona.name in present_at_moment]
                self.character_manager.broadcast_event_to_characters(active_characters, event)
                
                # Update presence based on Entry/Exit events
                from data_models import CharacterEntry, CharacterExit
                if isinstance(event, CharacterEntry):
                    present_at_moment.add(event.character)
                elif isinstance(event, CharacterExit):
                    present_at_moment.discard(event.character)
            
            print("\n" + "="*70)
            print("[LOADED] Existing conversation restored")
            print("="*70)
            print(f"Restored {len(self.timeline.events)} events from previous session")
            print(f"Participants: {', '.join(self.timeline.participants)}")
            print("Continuing from where you left off...")
            print("="*70 + "\n")
            
            return True
            
        except Exception as e:
            print(f"\n[WARNING] Could not load previous conversation: {e}")
            print("Starting fresh conversation instead.\n")
            return False
    
    def _save_conversation(self) -> None:
        """Save the current conversation to a JSON file in TimelineHistory format."""
        filepath = self.get_conversation_file_path()
        
        try:
            from data_models import Message, Scene, Action, CharacterEntry, CharacterExit
            
            # Manually construct the data structure to ensure proper serialization
            timeline_data = {
                "id": self.timeline.id,
                "title": self.timeline.title,
                "events": [],
                "participants": self.timeline.participants,
                "current_participants": self.timeline.current_participants,
                "timeline_summary": self.timeline.timeline_summary,
                "visible_to_user": self.timeline.visible_to_user
            }
            
            # Serialize each event with all its fields
            for event in self.timeline.events:
                if isinstance(event, Message):
                    event_data = {
                        "type": "message",
                        "timeline_id": event.timeline_id,
                        "timestamp": event.timestamp.isoformat(),
                        "character": event.character,
                        "dialouge": event.dialouge,
                        "action_description": event.action_description
                    }
                elif isinstance(event, Scene):
                    event_data = {
                        "type": "scene",
                        "timeline_id": event.timeline_id,
                        "timestamp": event.timestamp.isoformat(),
                        "location": event.location,
                        "description": event.description
                    }
                elif isinstance(event, Action):
                    event_data = {
                        "type": "action",
                        "timeline_id": event.timeline_id,
                        "timestamp": event.timestamp.isoformat(),
                        "character": event.character,
                        "description": event.description
                    }
                elif isinstance(event, CharacterEntry):
                    event_data = {
                        "type": "character_entry",
                        "timeline_id": event.timeline_id,
                        "timestamp": event.timestamp.isoformat(),
                        "character": event.character,
                        "description": event.description
                    }
                elif isinstance(event, CharacterExit):
                    event_data = {
                        "type": "character_exit",
                        "timeline_id": event.timeline_id,
                        "timestamp": event.timestamp.isoformat(),
                        "character": event.character,
                        "description": event.description,
                        "reason": event.reason if hasattr(event, 'reason') else None
                    }
                else:
                    continue
                
                timeline_data["events"].append(event_data)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                # Include story progress and character objectives for persistence
                if self.story_manager and self.story_manager.story:
                    story = self.story_manager.story
                    timeline_data["story"] = {
                        "id": story.id,
                        "title": story.title,
                        "description": getattr(story, "description", ""),
                        "objectives": story.objectives,
                        "current_objective_index": story.current_objective_index,
                    }
                # Save current per-character objectives
                char_states = {}
                for c in self.ai_characters:
                    if c.state and c.state.current_objective:
                        char_states[c.persona.name] = c.state.current_objective
                timeline_data["character_states"] = char_states

                json.dump(timeline_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"[WARNING] Error saving conversation: {e}")
    
    def _add_player_message(self, content: str) -> None:
        """Add a player message to the conversation."""
        # Extract action description from brackets if present
        import re
        action_desc = None
        dialogue = content
        
        bracket_match = re.search(r'\[([^\]]+)\]', content)
        if bracket_match:
            action_desc = bracket_match.group(1).strip()
            # Remove brackets from the dialogue
            dialogue = re.sub(r'\[([^\]]+)\]', '', content).strip()
        
        # If no action description found in brackets, set a default
        if not action_desc:
            action_desc = "speaks"
        
        # Create and add message to timeline
        message = self.timeline_manager.create_message(
            character=self.player_name,
            dialouge=dialogue,
            action_description=action_desc
        )
        self.timeline_manager.add_event(self.timeline, message)
        
        # Broadcast player message as a TimelineEvent to currently active characters only
        active_characters = [c for c in self.ai_characters if c.persona.name in self.timeline.current_participants]
        self.character_manager.broadcast_event_to_characters(active_characters, message)
        self._save_conversation()
    
    def get_conversation_file_path(self) -> Path:
        """Get the file path where the conversation is saved."""
        # Use story name to create unique conversation file
        safe_story_name = self.story_name.lower().replace(" ", "_")
        return self.chat_storage_dir / f"{safe_story_name}_chat.json"

    
    def display_welcome(self) -> None:
        """Display welcome message with character information."""
        char_names = ", ".join([char.persona.name for char in self.ai_characters])
        
        welcome = f"""You are playing as {self.player_name.upper()}, joined by {char_names}.

        The conversation will flow naturally - AI characters will respond when they
        have something to say, creating an organic, dynamic storytelling experience!

        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

        📜 COMMANDS:
        • Just type naturally to speak as {self.player_name}
        • 'skip' - Let AI characters continue talking without you
        • 'info' - See character details
        • 'quit' or 'exit' - End the roleplay session

        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        """
        print(welcome)