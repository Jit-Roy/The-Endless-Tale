"""
Data models for the multi-character roleplay system.
All Pydantic models are defined here.
"""

from datetime import datetime
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
import uuid


class TimelineEvent(BaseModel):
    """Base class for all timeline events (messages, scenes, etc.)."""
    
    timeline_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this timeline event"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="When this event occurred"
    )


class Message(TimelineEvent):
    """Represents a single message in the conversation."""

    character: str = Field(..., description="Name of the character speaking")
    dialouge: str = Field(..., description="dialouge of the message")
    action_description: str = Field(..., description="Physical action or body language accompanying the message")


class Scene(TimelineEvent):
    """
    Represents a dynamic scene event that drives the story forward.
    Part of the timeline alongside Message objects.
    """
    
    scene_type: str = Field(..., description="Type of scene: 'transition' or 'environmental'")
    location: str = Field(..., description="Where this scene event takes place")
    time_of_day: Optional[str] = Field(default=None, description="Time of day during this scene")
    description: str = Field(..., description="What happens in this scene event")


class Action(TimelineEvent):
    """Represents a character's action or decision point."""
    
    character: str = Field(..., description="Name of the character taking the action")
    description: str = Field(..., description="Details about the action taken")


class CharacterEntry(TimelineEvent):
    """
    Represents a character entering the scene.
    Used to track when characters join conversations and what they witness.
    """
    
    character: str = Field(..., description="Name of the character entering")
    description: str = Field(..., description="Description of how the character enters (e.g., 'Harry walks in looking exhausted')")


class CharacterExit(TimelineEvent):
    """
    Represents a character leaving the scene.
    Used to track when characters depart and stop witnessing events.
    """
    
    character: str = Field(..., description="Name of the character leaving")
    description: str = Field(..., description="Description of how the character leaves (e.g., 'Hermione hurries off to the library')")
    

class TimelineHistory(BaseModel):
    """Represents the complete conversation history."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique ID for the conversation")
    title: Optional[str] = Field(default=None, description="Optional title for the conversation (e.g., 'Midnight Planning')")
    events: List[TimelineEvent] = Field(
        default_factory=list,
        description="List of all timeline events (messages and scenes)"
    ) 
    participants: List[str] = Field(
        default_factory=list,
        description="List of characters involved in this conversation"
    )
    current_participants: List[str] = Field(
        default_factory=list,
        description="List of characters currently present in the conversation"
    )
    timeline_summary: Optional[str] = Field(
        default=None,
        description="Brief automatically generated summary of the timeline"
    )
    visible_to_user: bool = Field(
        default=True,
        description="Whether the user can view this conversation (for private NPC chats, set False)"
    )


class CharacterPersona(BaseModel):
    """Defines a character's personality, background, and relationships."""
    
    name: str = Field(..., description="Character's full name")
    traits: List[str] = Field(..., description="List of personality traits")
    relationships: Dict[str, str] = Field(
        default_factory=dict,
        description="Mapping of character names to relationship descriptions"
    )
    speaking_style: str = Field(..., description="Description of how the character speaks")
    background: str = Field(..., description="Character's background and context")
    goals: Optional[List[str]] = Field(
        default=None,
        description="Character's goals or motivations that influence decision-making"
    )
    knowledge_base: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Information, secrets, or world knowledge specific to this character"
    )


class CharacterMemory(BaseModel):
    """
    Represents a character's evolving understanding of the world, based on observations and personal interpretations. 
    Each character has their OWN perspective - what THEY experienced.
    """

    name: str = Field(..., description="Name of the character this memory belongs to")

    event: List[TimelineEvent] = Field(
        default_factory=list,
        description="Scenes and Messages this character observed from its perspective"
    )


class CharacterState(BaseModel):
    """Represents the character's current, moment-to-moment condition."""
    
    name: str
    current_objective: Optional[str] = Field(default=None, description="Current activity or intent")


class Character(BaseModel):
    """Encapsulates all aspects of a single character."""

    persona: CharacterPersona
    memory: Optional[CharacterMemory] = None
    state: Optional[CharacterState] = None
    

class Story(BaseModel):
    """
    Unified story management class that handles progression, beats, and dynamic events.
    Consolidates StoryArc, StoryBeat, and StoryEvent functionality.
    """
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique ID for the story")
    title: str = Field(..., description="Title of the story arc")
    description: str = Field(..., description="Overall description of the story")
    objectives: List[str] = Field(..., description="List of main objectives for the story")
    current_objective_index: int = Field(default=0, description="Index of the current objective")