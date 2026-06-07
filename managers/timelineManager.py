"""
Timeline Manager for unified timeline event operations.
Combines message and scene management into a single chronological timeline.
"""

from typing import List, Optional, Dict
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from data_models import Message, Scene, Action, TimelineHistory, TimelineEvent, CharacterEntry, CharacterExit
from gemini_client import GenerativeModel
from helpers.response_parser import parse_json_response


class TimelineManager:
    """Manager for timeline operations including messages and scenes."""
    
    def __init__(self):
        """Initialize TimelineManager."""
        self.model = GenerativeModel()

    # ========== Timeline Operations ==========
    
    def create_timeline_history(
        self,
        title: Optional[str] = None,
        participants: Optional[List[str]] = None,
        visible_to_user: bool = True
    ) -> TimelineHistory:
        """
        Create a new timeline history.
        
        Args:
            title: Optional timeline title 
            participants: Optional initial participants list
            visible_to_user: Whether user can view this timeline (default True)
            
        Returns:
            New TimelineHistory instance
        """
        return TimelineHistory(
            title=title,
            participants=participants,
            current_participants=participants.copy() if participants else None, 
            visible_to_user=visible_to_user
        )
    
    def add_event(
        self,
        timeline: TimelineHistory,
        event: TimelineEvent
    ) -> None:
        """
        Add an event (Message or Scene) to the timeline.
        
        Args:
            timeline: TimelineHistory instance to add event to
            event: TimelineEvent instance to add (Message or Scene)
        """
        timeline.events.append(event)
        
        # If it's a message, update participants
        if isinstance(event, Message):
            if event.character not in timeline.participants:
                timeline.participants.append(event.character)
            if event.character not in timeline.current_participants:
                timeline.current_participants.append(event.character)

        elif isinstance(event, Action):
            if event.character not in timeline.participants:
                timeline.participants.append(event.character)
            if event.character not in timeline.current_participants:
                timeline.current_participants.append(event.character)
        
        elif isinstance(event, CharacterEntry):
            if event.character not in timeline.participants:
                timeline.participants.append(event.character)
            if event.character not in timeline.current_participants:
                timeline.current_participants.append(event.character)
        
        elif isinstance(event, CharacterExit):
            if event.character not in timeline.participants:
                timeline.participants.append(event.character)
            if event.character in timeline.current_participants:
                timeline.current_participants.remove(event.character)

    
    def get_recent_events(
        self, 
        timeline: TimelineHistory, 
        n: Optional[int] = 10,
        event_type: Optional[str] = None
    ) -> List[TimelineEvent]:
        """
        Get the n most recent events from timeline.
        
        Args:
            timeline: TimelineHistory instance to retrieve from
            n: Number of recent events, or None to get all events
            event_type: Optional filter - "message", "scene", "action", "entry", "exit" or None for all
            
        Returns:
            List of recent events
        """
        events = timeline.events
        
        # Filter by type if specified
        if event_type == "message":
            events = [e for e in events if isinstance(e, Message)]
        elif event_type == "scene":
            events = [e for e in events if isinstance(e, Scene)]
        elif event_type == "action":
            events = [e for e in events if isinstance(e, Action)]
        elif event_type == "entry":
            events = [e for e in events if isinstance(e, CharacterEntry)]
        elif event_type == "exit":
            events = [e for e in events if isinstance(e, CharacterExit)]
        
        # Return all events if n is None, otherwise return last n events
        if n is None:
            return events
        return events[-n:] if len(events) > n else events
    
    def get_current_location(self, timeline: TimelineHistory) -> Optional[str]:
        """
        Get the current location from the most recent Scene.
        
        Args:
            timeline: TimelineHistory instance
            
        Returns:
            Current location string or None
        """
        scenes = self.get_recent_events(timeline,n=1,event_type="scene")
        return scenes[0].location if scenes else None
    
    def get_timeline_context(self, timeline: TimelineHistory, recent_event_count: int = 10) -> str:
        """
        Build a formatted string representation of timeline events.
        
        Args:
            events: List of TimelineEvent instances to format
            
        Returns:
            Formatted timeline string with one event per line
        """
        timeline_context = []
        events = self.get_recent_events(timeline, n=recent_event_count)
        for event in events:
            if isinstance(event, Message):
                timeline_context.append(f"{event.character}: {event.dialouge}")
            elif isinstance(event, Scene):
                timeline_context.append(f"[SCENE at {event.location}] {event.description}")
            elif isinstance(event, Action):
                timeline_context.append(f"[ACTION] {event.character}: {event.description}")
            elif isinstance(event, CharacterEntry):
                timeline_context.append(f"[ENTERED] {event.character}: {event.description}")
            elif isinstance(event, CharacterExit):
                timeline_context.append(f"[LEFT] {event.character}: {event.description}")
        
        return "\n".join(timeline_context) if timeline_context else "No recent activity"
    
    # ========== Message Operations ==========
    
    def create_message(
        self, 
        character: str, 
        dialouge: str, 
        action_description: str
    ) -> Message:
        """
        Create a new message instance.
        
        Args:
            character: Name of the character speaking
            dialouge: Message dialouge
            action_description: Physical action or body language
            
        Returns:
            New Message instance
        """
        return Message(
            character=character, 
            dialouge=dialouge, 
            action_description=action_description
        )
    
    # ========== Scene Operations ==========
    
    def create_scene(
        self,
        scene_type: str,
        location: str,
        description: str
    ) -> Scene:
        """
        Create a new scene event.
        
        Args:
            scene_type: Type of scene - 'transition' or 'environmental'
            location: Where this scene event takes place
            description: What happens in this scene event
            
        Returns:
            New Scene instance
        """
        return Scene(
            scene_type=scene_type,
            location=location,
            description=description
        )
    
    def generate_scene_event(
        self,
        scene_type: str,
        timeline: TimelineHistory,
        recent_event_count: int = 15
    ) -> Scene:
        """
        Generate a scene event based on specified type.
        
        Args:
            scene_type: Type of scene to generate - 'transition' or 'environmental' (required)
            timeline: TimelineHistory instance
            recent_event_count: How many recent events to consider for context
            
        Returns:
            The newly created Scene
        """
        try:
            timeline_str = self.get_timeline_context(timeline, recent_event_count=recent_event_count)
            current_location = self.get_current_location(timeline)
            
            if scene_type == "transition":
                prompt = f"""You are generating a SCENE TRANSITION for a roleplay story.
                Current Location: {current_location or 'Unknown'}
                Characters Present: {', '.join(timeline.current_participants)}

                RECENT TIMELINE (in chronological order):
                {timeline_str}

                YOUR TASK:
                Generate a location transition scene. Characters need to move to a new location based on context.

                GUIDELINES:
                1. **Identify destination** - Where should they go based on recent conversation?
                2. **Describe journey** - Brief description of traveling from current to new location
                3. **Arrival description** - Vivid details of the new location they arrive at
                4. **Set the atmosphere** - Make the new location feel real and immersive

                CRITICAL RULES:
                - Choose a NEW location different from {current_location or 'Unknown'}
                - 2-3 sentences: journey + arrival + atmospheric details
                - Include sensory details (what they see/hear/feel)
                - Naturally flow from recent events
                - Match the tone and setting of the world established in the timeline

                OUTPUT FORMAT (strict JSON):
                {{
                "location": "The NEW location they arrive at",
                "event_description": "2-3 sentences describing journey and arrival at new location"
                }}

                EXAMPLE:
                {{
                "location": "The Elder's Office",
                "event_description": "The group made their way through the winding corridors, their footsteps echoing off the stone walls. They arrived at the heavy wooden door, which opened to reveal a circular room filled with ancient artifacts and softly glowing instruments, while mysterious portraits watched their arrival."
                }}"""
            
            else:  # environmental
                prompt = f"""You are generating an ENVIRONMENTAL SCENE EVENT for a roleplay story.
                Current Location: {current_location or 'Unknown'}
                Characters Present: {', '.join(timeline.current_participants)}

                RECENT TIMELINE (in chronological order):
                {timeline_str}

                SITUATION:
                Generate a dramatic environmental event that interrupts the current moment and forces the characters to react or make a decision.

                YOUR TASK:
                Create an event that happens in the CURRENT location that:
                1. **Interrupts the moment** - Something happens in the environment
                2. **Demands attention** - Characters MUST notice and can react
                3. **Pushes story forward** - Creates tension, reveals a complication, or introduces a stake
                4. **Creates a decision point** - The event should require characters to choose, investigate, respond, or adapt
                5. **Is different** from previous scene events above

                STORY-DRIVEN EVENT TYPES (choose dynamically):
                - **Immediate threat**: A rival ship appears, a fire breaks out, a dangerous creature approaches
                - **Complication**: A hidden object is found, a map goes wrong, a key item is missing
                - **Mysterious clue**: The compass spins, a strange signal arrives, a door opens by itself
                - **Character consequence**: Someone returns injured or silent, a secret is exposed, a tense argument erupts
                - **Forced choice**: The characters must decide how to act now, not later

                CRITICAL RULES:
                - Event happens in CURRENT location: {current_location or 'Unknown'}
                - Do NOT change location
                - Make it SPECIFIC and VIVID (not generic)
                - Include sensory details (what they see/hear/feel)
                - Must create a story problem or dramatic question
                - Should feel like an event the player must engage with, not mere atmosphere
                - Vary event type - don't repeat patterns from timeline
                - Match the tone and setting of the world established in the timeline

                OUTPUT FORMAT (strict JSON):
                {{
                "location": "{current_location or 'Unknown'}",
                "event_description": "2-3 sentence vivid description of what happens and why it matters"
                }}

                EXAMPLE:
                {{
                "location": "The Library",
                "event_description": "A sudden gust of ice-cold wind tears through the library, extinguishing half the lights. Pages flutter wildly as a single ancient tome slides off a high shelf and crashes open on the table between them—landing on a page marked with a glowing symbol that demands investigation."
                }}"""
            
            response = self.model.generate_content(prompt)
            result = parse_json_response(response.text)
            location = (result.get("location") or "Unknown Location").strip()
            event_desc = (result.get("event_description") or "").strip()
            
            return Scene(
                scene_type=scene_type,
                location=location,
                description=event_desc
            )
            
        except Exception as e:
            raise RuntimeError(f"Failed to generate {scene_type} scene event: {e}")
        
    def should_generate_scene(self, timeline: TimelineHistory, recent_event_count: int = 15) -> Optional[dict]:
        """
        Use LLM to decide if a scene event should be generated and what type it should be.
        
        Args:
            timeline: TimelineHistory instance
            recent_event_count: Number of recent events to include in context
            
        Returns:
            dict with 'scene_generated' (bool), 'scene_type' (str), 'location' (str), 'event_description' (str) if scene should be generated,
            None if no scene should be generated
        """
        timeline_str = self.get_timeline_context(timeline, recent_event_count=recent_event_count)
        current_location = self.get_current_location(timeline)
        
        prompt = f"""You are a narrative AI assistant for a roleplay story.
        Current Location: {current_location or 'Unknown'}
        Characters Present: {', '.join(timeline.current_participants)}
        
        RECENT TIMELINE (in chronological order):
        {timeline_str}

        YOUR TASK:
        Analyze the recent conversation flow and decide whether a SCENE EVENT should be generated.

        SCENE EVENT TYPES:
        
        1. **TRANSITION** - Change of location (time/place transition):
           - Characters decide to go somewhere
           - Narrative needs to move forward to a new location
           - Story progression requires a location change
           Example: "The three friends left the common room and walked through the castle corridors, arriving at Dumbledore's office. The circular room was lined with portraits, and Fawkes sat on his golden perch."
        
        2. **ENVIRONMENTAL** - Something happens in current location:
           - Physical events (wind, objects falling, door slams)
           - Discoveries (hidden objects, clues)
           - Mysterious occurrences (sounds, shadows, magic)
           - Interruptions (someone enters, owl arrives)
           Example: "A sudden gust of wind tore through the library, extinguishing the torches and causing an ancient book to fall open on the table."

        GENERATE A SCENE EVENT IF:
        1. **Location change needed** - Characters expressed intent to go somewhere
        2. **Conversation has stalled** - Multiple silence rounds or repetitive exchanges
        3. **Natural transition point** - Topic concluded, awkward pause
        4. **Story needs momentum** - Environmental interruption would enhance drama

        DO NOT GENERATE A SCENE IF:
        1. **Active conversation** - Characters are engaged and responding naturally
        2. **Recent scene event** - Already generated one in last 5-10 messages
        3. **Mid-dialogue** - Someone is in the middle of making an important point
        4. **Emotional moment** - Characters processing feelings

        OUTPUT FORMAT (strict JSON):
        If TRANSITION scene should be generated:
        {{
            "scene_generated": true,
            "scene_type": "transition",
            "location": "The NEW location they're moving to",
            "event_description": "2-3 sentences describing the journey and arrival at new location with vivid details"
        }}
        
        If ENVIRONMENTAL scene should be generated:
        {{
            "scene_generated": true,
            "scene_type": "environmental",
            "location": "{current_location or 'Unknown'}",
            "event_description": "2-3 sentences describing what happens in current location with sensory details"
        }}

        If no scene should be generated:
        {{
            "scene_generated": false
        }}

        Decide now based on the timeline above."""
        
        try:
            response = self.model.generate_content(prompt)
            
            try:
                scene_data = parse_json_response(response.text)
            except ValueError:
                return None
            
            if scene_data.get("scene_generated", False):
                return {
                    'scene_generated': True,
                    'location': scene_data.get('location'),
                    'event_description': scene_data.get('event_description')
                }
            else:
                return None
                
        except Exception as e:
            print(f"⚠️  Error in scene generation decision: {e}")
            return None
    
        
    # ========= Action Operations ==========

    def create_action(
        self,
        character: str,
        description: str
    ) -> Action:
        """
        Create a new action instance.
        Args:
            character: Name of the character taking the action
            description: Details about the action taken

        Returns:
            New Action instance
        """
        action = Action(
            character=character,
            description=description
        )
        return action
        
    # ========== Charracter Entry/Exit Operations ==========

    def create_character_entry(
        self,
        character: str,
        description: str
    ) -> CharacterEntry:
        """
        Create a new character entry event.
        
        Args:
            character: Name of the character entering
            description: Description of how the character enters
            
        Returns:
            New CharacterEntry instance
        """
        entry = CharacterEntry(
            character=character,
            description=description
        )
        return entry
    
    def create_character_exit(
        self,
        character: str,
        description: str
    ) -> CharacterExit:
        """
        Create a new character exit event.
        
        Args:
            character: Name of the character leaving
            description: Description of how the character leaves
            
        Returns:
            New CharacterExit instance
        """
        exit_event = CharacterExit(
            character=character,
            description=description
        )
        return exit_event
    
    def decide_character_movements(
        self,
        timeline_context: str,
        all_characters: List[str],
        current_participants: List[str],
        current_location: str
    ) -> tuple[List[Dict[str, str]], List[Dict[str, str]]]:
        """
        Make ONE API call to decide both character entries AND exits.
        
        Args:
            timeline_context: Full timeline history context
            all_characters: List of all character names in the story
            current_participants: List of characters currently present
            current_location: Current scene location
            
        Returns:
            Tuple of (entries, exits):
            - entries: List of dicts with keys: 'character', 'description'
            - exits: List of dicts with keys: 'character', 'description'
        """
        absent_characters = [c for c in all_characters if c not in current_participants]
        
        prompt = f"""You are the meta-narrator for this story. Based on the full timeline context, decide which characters (if any) should enter or exit the current scene.
        CURRENT SCENE:
        Location: {current_location}
        Currently Present: {', '.join(current_participants) if current_participants else 'None'}
        Absent Characters: {', '.join(absent_characters) if absent_characters else 'None'}
        RECENT TIMELINE CONTEXT:
        {timeline_context}
        YOUR TASK:
        Decide which characters should naturally enter or exit RIGHT NOW based on:
        - Story flow and narrative logic
        - Character motivations and goals
        - Natural cause-and-effect from recent events
        - Whether the scene/location would attract or repel them
        CRITICAL ENTRY DESCRIPTION RULES:
        For character ENTRIES, the description MUST include what the entering character can PHYSICALLY OBSERVE:
        1. **Location/Environment** - Brief description of where they are (the room, surroundings)
        2. **Who is present** - Mention the characters they see in front of them
        3. **Observable state** - Body language, facial expressions, tension they can SEE (not what was said)
        DO NOT include in entry descriptions:
        - Previous conversations (they weren't there to hear it)
        - Why people are there (they don't know yet)
        - Internal thoughts of others
        ENTRY DESCRIPTION EXAMPLE:
        "Dumbledore looks up from his ancient desk, taking in the three students standing before him - Harry, Ron, and Hermione. Their faces show visible concern, and tension fills the circular office lined with portraits and magical instruments."
        EXIT DESCRIPTION EXAMPLE:
        "Ron nods and quietly steps toward the door, glancing back once before leaving the room."
        RESPONSE FORMAT (JSON):
        {{
            "entries": [
                {{
                    "character": "character_name",
                    "description": "2-3 sentences describing their entry with what they observe (location + who's present + observable state)"
                }}
            ],
            "exits": [
                {{
                    "character": "character_name",
                    "description": "1-2 sentences describing how they leave"
                }}
            ]
        }}

        If no movements should happen, return: {{"entries": [], "exits": []}}
        Remember: Only include movements that make narrative sense RIGHT NOW."""
        try:
            response = self.model.generate_content(prompt)
            result = parse_json_response(response.text)
            entries = result.get("entries", [])
            exits = result.get("exits", [])

            return entries, exits
            
        except Exception as e:
            print(f"Error deciding character movements: {e}")
            return [], []
    
    
    # ========== Unified Meta-Narrative ==========

    def prepare_turn_context(
        self,
        timeline: TimelineHistory,
        all_characters: List[str],
        recent_event_count: int = 15
    ) -> Dict:
        """
        Single unified LLM call that replaces should_generate_scene() + decide_character_movements().

        Instead of two sequential API calls (scene decision, then movements), this asks the
        model to decide BOTH in one shot since they share the same context.

        Args:
            timeline: TimelineHistory instance
            all_characters: All character names registered in the story
            recent_event_count: Number of recent events to include in context

        Returns:
            dict with keys:
              - 'scene': None  OR  dict{'scene_type', 'location', 'event_description'}
              - 'entries': List[dict{'character', 'description'}]
              - 'exits':   List[dict{'character', 'description'}]
        """
        timeline_str = self.get_timeline_context(timeline, recent_event_count=recent_event_count)
        current_location = self.get_current_location(timeline) or "Unknown"
        current_participants = timeline.current_participants
        absent_characters = [c for c in all_characters if c not in current_participants]

        prompt = f"""You are the meta-narrator for a roleplay story. Analyse the recent timeline and make ALL of the following decisions in ONE response:
        === STORY STATE ===
        Current Location: {current_location}
        Currently Present: {', '.join(current_participants) if current_participants else 'None'}
        Absent Characters: {', '.join(absent_characters) if absent_characters else 'None'}
        RECENT TIMELINE (chronological): {timeline_str}
        === DECISION 1 — SCENE EVENT ===
        Decide whether a scene event should occur RIGHT NOW.

        GENERATE A SCENE IF:
        - Characters expressed intent to move to a new location (→ use "transition")
        - Conversation has naturally stalled or a topic has concluded (→ use "environmental")
        - An environmental interruption would meaningfully advance the story

        DO NOT GENERATE A SCENE IF:
        - Characters are engaged in active, flowing dialogue
        - A scene event already appears in the recent timeline above
        - The story is mid-emotional or mid-revelation

        For TRANSITION scenes: describe the journey and vivid arrival at the NEW location.
        For ENVIRONMENTAL scenes: describe a physical/mysterious event in the CURRENT location.

        === DECISION 2 — CHARACTER MOVEMENTS ===
        Decide which characters (if any) should enter or exit the scene RIGHT NOW based on narrative logic and character motivations.

        For ENTRY descriptions, include what the entering character physically observes:
        - The environment/location they walk into
        - Who is visibly present
        - Observable body language or tension (NOT what was said before they arrived)

        For EXIT descriptions: 1-2 sentences describing how they leave.

        === OUTPUT FORMAT (strict JSON) ===
        {{
            "scene": null,
            "entries": [],
            "exits": []
        }}

        OR if a scene and/or movements should happen:
        {{
            "scene": {{
                "scene_type": "transition" | "environmental",
                "location": "location name",
                "event_description": "2-3 vivid sentences"
            }},
            "entries": [
                {{"character": "name", "description": "entry description"}}
            ],
            "exits": [
                {{"character": "name", "description": "exit description"}}
            ]
        }}

        Only include movements and scenes that make narrative sense RIGHT NOW. If nothing should happen, return null for scene and empty lists."""

        try:
            response = self.model.generate_content(prompt)
            result = parse_json_response(response.text)

            return {
                "scene": result.get("scene"),       # None or dict
                "entries": result.get("entries", []),
                "exits": result.get("exits", []),
            }

        except Exception as e:
            print(f"⚠️  Error in prepare_turn_context: {e}")
            # Safe fallback: no scene, no movements
            return {"scene": None, "entries": [], "exits": []}

    # ========== Summary Operations ==========
    
    def summarize_timeline(self, timeline: TimelineHistory) -> str:
        """
        Generate a brief AI-powered summary of the timeline.
        
        Args:
            timeline: TimelineHistory instance to summarize
            
        Returns:
            Summary string
        """
        if not timeline.events:
            return "No events to summarize."
        
        timeline_str = self.get_timeline_context(timeline, recent_event_count=None)
        
        prompt = f"""You are summarizing a roleplay timeline between characters.
        Title: {timeline.title}
        TIMELINE:
        {timeline_str}
        TASK: Generate a concise summary (2-4 sentences) of this timeline covering:
        - What the main topics discussed were
        - Any important scene events that occurred
        - Any important decisions or revelations
        - The overall mood or tone
        - Key character interactions or conflicts

        OUTPUT FORMAT (strict JSON):
        {{
        "summary": "Your 2-4 sentence summary here"
        }}
        Keep it brief but capture the essence of what happened."""

        try:
            response = self.model.generate_content(prompt)
            summary_data = parse_json_response(response.text)
            summary = summary_data.get("summary", "Unable to generate summary.")
            timeline.timeline_summary = summary
            return summary
            
        except Exception as e:
            raise RuntimeError(f"Failed to generate summary: {e}")
