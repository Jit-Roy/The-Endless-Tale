# RoleRealm API Reference

## Table of Contents
- [Data Models](#data-models)
- [Managers](#managers)
- [Loaders](#loaders)
- [RoleplaySystem](#roleplaysystem)
- [Configuration](#configuration)
- [Utilities](#utilities)

---

## Data Models

All data models are defined in `data_models.py` using Pydantic.

### TimelineEvent (Base Class)

**Description**: Base class for all timeline events.

```python
class TimelineEvent(BaseModel):
    timeline_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.now)
```

**Fields**:
- `timeline_id` (str): Unique identifier for the event
- `timestamp` (datetime): When the event occurred

---

### Message

**Description**: Represents a character's spoken dialogue with accompanying action.

```python
class Message(TimelineEvent):
    character: str
    dialouge: str
    action_description: str
```

**Fields**:
- `character` (str): Name of the speaking character
- `dialouge` (str): What they say
- `action_description` (str): Physical action or body language

**Example**:
```python
message = Message(
    character="Captain",
    dialouge="Avast! We sail at dawn!",
    action_description="slams fist on the table"
)
```

---

### Scene

**Description**: Represents an environmental or transitional narrative event.

```python
class Scene(TimelineEvent):
    scene_type: str
    location: str
    description: str
```

**Fields**:
- `scene_type` (str): Type of scene - "transition" or "environmental"
- `location` (str): Where the scene takes place
- `description` (str): What happens in the scene

**Example**:
```python
scene = Scene(
    scene_type="environmental",
    location="Ship Deck",
    description="Dark storm clouds gather on the horizon as waves crash against the hull"
)
```

---

### Action

**Description**: Represents a character's physical action or decision point.

```python
class Action(TimelineEvent):
    character: str
    description: str
```

**Fields**:
- `character` (str): Name of the acting character
- `description` (str): Details about the action

**Example**:
```python
action = Action(
    character="Marina",
    description="carefully unfurls the ancient map on the table"
)
```

---

### CharacterEntry

**Description**: Represents a character joining the conversation.

```python
class CharacterEntry(TimelineEvent):
    character: str
    description: str
```

**Fields**:
- `character` (str): Name of entering character
- `description` (str): How they enter

**Example**:
```python
entry = CharacterEntry(
    character="Jack",
    description="Jack bursts through the door, out of breath"
)
```

---

### CharacterExit

**Description**: Represents a character leaving the conversation.

```python
class CharacterExit(TimelineEvent):
    character: str
    description: str
```

**Fields**:
- `character` (str): Name of leaving character
- `description` (str): How they leave

---

### CharacterPersona

**Description**: Defines a character's immutable personality and characteristics.

```python
class CharacterPersona(BaseModel):
    name: str
    traits: List[str]
    relationships: Dict[str, str]
    speaking_style: str
    background: str
    goals: Optional[List[str]] = None
    knowledge_base: Optional[Dict[str, Any]] = None
    temperature: Optional[float] = 0.75
    top_p: Optional[float] = 0.9
    frequency_penalty: Optional[float] = 0.2
```

**Fields**:
- `name` (str): Character's full name
- `traits` (List[str]): Personality traits
- `relationships` (Dict[str, str]): Character name → relationship description
- `speaking_style` (str): How the character speaks
- `background` (str): Character's history and context
- `goals` (List[str], optional): Long-term motivations
- `knowledge_base` (Dict, optional): Special knowledge or secrets
- `temperature` (float, optional): LLM creativity parameter (default: 0.75)
- `top_p` (float, optional): Sampling parameter (default: 0.9)
- `frequency_penalty` (float, optional): Repetition control (default: 0.2)

**Example**:
```json
{
  "name": "Captain Morgan",
  "traits": ["wise", "authoritative", "protective"],
  "relationships": {
    "Marina": "Impressed by her skills",
    "Jack": "Appreciates his spirit"
  },
  "speaking_style": "Speaks with gravitas, uses seafaring expressions",
  "background": "Decades of sailing experience",
  "goals": ["Lead crew to fortune", "Keep everyone safe"],
  "knowledge_base": {
    "secret_routes": "Knows hidden passages through dangerous waters"
  }
}
```

---

### CharacterMemory

**Description**: Stores what a character has witnessed from their perspective.

```python
class CharacterMemory(BaseModel):
    name: str
    event: List[TimelineEvent] = Field(default_factory=list)
```

**Fields**:
- `name` (str): Character name
- `event` (List[TimelineEvent]): Events this character witnessed

**Note**: Each character only remembers events they were present for.

---

### CharacterState

**Description**: Represents a character's current, mutable state.

```python
class CharacterState(BaseModel):
    name: str
    current_objective: Optional[str] = None
```

**Fields**:
- `name` (str): Character name
- `current_objective` (str, optional): Current goal or task

---

### Character

**Description**: Complete representation of an AI character.

```python
class Character(BaseModel):
    persona: CharacterPersona
    memory: Optional[CharacterMemory] = None
    state: Optional[CharacterState] = None
```

**Fields**:
- `persona` (CharacterPersona): Personality and traits
- `memory` (CharacterMemory, optional): What they've witnessed
- `state` (CharacterState, optional): Current condition and objectives

---

### TimelineHistory

**Description**: Master timeline containing all chronological events.

```python
class TimelineHistory(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: Optional[str] = None
    events: List[TimelineEvent] = Field(default_factory=list)
    participants: List[str] = Field(default_factory=list)
    current_participants: List[str] = Field(default_factory=list)
    timeline_summary: Optional[str] = None
    visible_to_user: bool = True
```

**Fields**:
- `id` (str): Unique timeline identifier
- `title` (str, optional): Timeline title
- `events` (List[TimelineEvent]): All events in chronological order
- `participants` (List[str]): All characters who participated
- `current_participants` (List[str]): Characters currently present
- `timeline_summary` (str, optional): Auto-generated summary
- `visible_to_user` (bool): Whether user can view (default: True)

---

### Story

**Description**: Story structure with sequential objectives.

```python
class Story(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str
    objectives: List[str]
    current_objective_index: int = 0
```

**Fields**:
- `id` (str): Unique story identifier
- `title` (str): Story title
- `description` (str): Overall story description
- `objectives` (List[str]): Sequential list of story objectives
- `current_objective_index` (int): Current progress (default: 0)

**Example**:
```json
{
  "title": "The Quest for the Phantom Pearl",
  "description": "A treasure hunt through cursed waters",
  "objectives": [
    "Decipher the mysterious map",
    "Navigate through the Siren's Strait",
    "Find the abandoned island"
  ],
  "current_objective_index": 0
}
```

---

## Managers

### CharacterManager

**Location**: `managers/characterManager.py`

**Description**: Manages character lifecycle, memory, and decision-making.

#### Methods

##### `__init__()`
```python
def __init__(self) -> None
```
Initialize CharacterManager with default model configuration.

---

##### `create_character()`
```python
def create_character(
    persona: CharacterPersona,
    memory: Optional[CharacterMemory] = None,
    state: Optional[CharacterState] = None
) -> Character
```

Create a new AI character instance.

**Parameters**:
- `persona` (CharacterPersona): Character personality definition
- `memory` (CharacterMemory, optional): Initial memory
- `state` (CharacterState, optional): Initial state

**Returns**: Character instance

**Example**:
```python
persona = CharacterPersona(name="Jack", traits=["brave", "reckless"], ...)
character = character_manager.create_character(persona)
```

---

##### `update_character_memory()`
```python
def update_character_memory(
    character: Character,
    event: TimelineEvent
) -> None
```

Add a timeline event to character's memory.

**Parameters**:
- `character` (Character): Character to update
- `event` (TimelineEvent): Event to add to memory

**Example**:
```python
message = Message(character="Captain", dialouge="Set sail!", ...)
character_manager.update_character_memory(jack, message)
```

---

##### `update_character_state()`
```python
def update_character_state(
    character: Character,
    current_objective: Optional[str] = None
) -> None
```

Update character's current state.

**Parameters**:
- `character` (Character): Character to update
- `current_objective` (str, optional): New objective

---

##### `build_persona_context()`
```python
def build_persona_context(character: Character) -> str
```

Build character personality context for LLM prompts.

**Parameters**:
- `character` (Character): Character to build context for

**Returns**: Formatted string with persona information

---

##### `build_state_context()`
```python
def build_state_context(character: Character) -> str
```

Build character state context including current objective.

**Returns**: Formatted string with state information

---

##### `build_memory_context()`
```python
def build_memory_context(
    character: Character,
    last_n_messages: Optional[int] = None
) -> str
```

Build memory context from character's perspective.

**Parameters**:
- `character` (Character): Character whose memory to build
- `last_n_messages` (int, optional): Number of recent events (None = all)

**Returns**: Formatted string with memory from character's POV

---

##### `decide_turn_response()`
```python
def decide_turn_response(
    character: Character
) -> Tuple[str, float, str, Optional[str], Optional[str]]
```

Determine if character should speak, act, or stay silent.

**Parameters**:
- `character` (Character): Character making decision

**Returns**: Tuple of:
- `response_type` (str): "speak", "act", or "silent"
- `priority` (float): 0.0-1.0 importance score
- `reasoning` (str): Why they chose this
- `dialogue` (str, optional): What they say (if speaking)
- `action` (str, optional): Physical action

---

##### `generate_character_response()`
```python
def generate_character_response(
    character: Character,
    response_type: str
) -> Tuple[str, str]
```

Generate actual character response (dialogue and/or action).

**Parameters**:
- `character` (Character): Character responding
- `response_type` (str): "speak" or "act"

**Returns**: Tuple of (dialogue, action)

---

### TimelineManager

**Location**: `managers/timelineManager.py`

**Description**: Manages timeline events and context building.

#### Methods

##### `__init__()`
```python
def __init__(self) -> None
```
Initialize TimelineManager.

---

##### `create_timeline_history()`
```python
def create_timeline_history(
    title: Optional[str] = None,
    participants: Optional[List[str]] = None,
    visible_to_user: bool = True
) -> TimelineHistory
```

Create a new timeline.

**Parameters**:
- `title` (str, optional): Timeline title
- `participants` (List[str], optional): Initial participants
- `visible_to_user` (bool): Visibility flag (default: True)

**Returns**: TimelineHistory instance

---

##### `add_event()`
```python
def add_event(
    timeline: TimelineHistory,
    event: TimelineEvent
) -> None
```

Add event to timeline and update participants.

**Parameters**:
- `timeline` (TimelineHistory): Timeline to add to
- `event` (TimelineEvent): Event to add

---

##### `create_message()`
```python
def create_message(
    character: str,
    dialouge: str,
    action_description: str
) -> Message
```

Factory method for creating messages.

**Parameters**:
- `character` (str): Speaker name
- `dialouge` (str): What they say
- `action_description` (str): Body language/action

**Returns**: Message instance

---

##### `create_scene()`
```python
def create_scene(
    scene_type: str,
    location: str,
    description: str
) -> Scene
```

Factory method for creating scenes.

**Parameters**:
- `scene_type` (str): "transition" or "environmental"
- `location` (str): Where it happens
- `description` (str): What happens

**Returns**: Scene instance

---

##### `get_recent_events()`
```python
def get_recent_events(
    timeline: TimelineHistory,
    n: Optional[int] = 10,
    event_type: Optional[str] = None
) -> List[TimelineEvent]
```

Get recent events from timeline.

**Parameters**:
- `timeline` (TimelineHistory): Timeline to query
- `n` (int, optional): Number of events (None = all)
- `event_type` (str, optional): Filter by "message", "scene", "action", "entry", "exit"

**Returns**: List of events

---

##### `get_current_location()`
```python
def get_current_location(timeline: TimelineHistory) -> Optional[str]
```

Get current location from most recent scene.

**Returns**: Location string or None

---

##### `get_timeline_context()`
```python
def get_timeline_context(
    timeline: TimelineHistory,
    recent_event_count: int = 10
) -> str
```

Build formatted timeline string.

**Parameters**:
- `timeline` (TimelineHistory): Timeline to format
- `recent_event_count` (int): Number of events to include

**Returns**: Formatted timeline string

---

### TurnManager

**Location**: `managers/turn_manager.py`

**Description**: Coordinates conversation flow and turn selection.

#### Methods

##### `__init__()`
```python
def __init__(
    characters: List[Character],
    timeline: TimelineHistory,
    max_consecutive_ai_turns: int = None,
    priority_randomness: float = None,
    save_callback: Optional[callable] = None
)
```

Initialize turn manager.

**Parameters**:
- `characters` (List[Character]): AI characters in conversation
- `timeline` (TimelineHistory): Main timeline
- `max_consecutive_ai_turns` (int, optional): Max AI turns (default: Config.MAX_CONSECUTIVE_AI_TURNS)
- `priority_randomness` (float, optional): Random factor (default: Config.PRIORITY_RANDOMNESS)
- `save_callback` (callable, optional): Function to save conversation

---

##### `process_ai_responses()`
```python
def process_ai_responses(
    max_turns: Optional[int] = None,
    force_one_response: bool = False
) -> List[Message]
```

Main conversation loop - process consecutive AI responses.

**Parameters**:
- `max_turns` (int, optional): Override max turns
- `force_one_response` (bool): Force at least one response

**Returns**: List of generated messages

**Flow**:
1. Collect decisions from all characters (parallel)
2. Select speaker based on priority
3. Generate and add response
4. Check meta-narrative events
5. Evaluate story progression
6. Repeat until silence or max turns

---

### StoryManager

**Location**: `managers/storyManager.py`

**Description**: Manages story progression and objectives.

#### Methods

##### `__init__()`
```python
def __init__(story: Optional[Story] = None)
```

Initialize story manager.

**Parameters**:
- `story` (Story, optional): Story to manage

---

##### `get_current_objective()`
```python
def get_current_objective() -> Optional[str]
```

Get current story objective.

**Returns**: Current objective string or None

---

##### `is_story_complete()`
```python
def is_story_complete() -> bool
```

Check if all objectives are complete.

**Returns**: True if story is complete

---

##### `get_progress_percentage()`
```python
def get_progress_percentage() -> float
```

Get completion percentage.

**Returns**: 0.0-100.0 progress percentage

---

##### `get_story_context()`
```python
def get_story_context() -> str
```

Get formatted story context for LLM prompts.

**Returns**: Story context string

---

##### `evaluate_and_assign_objectives()`
```python
def evaluate_and_assign_objectives(
    active_characters: List[Character],
    timeline: TimelineHistory
) -> Dict[str, Any]
```

Evaluate completion and assign objectives.

**Parameters**:
- `active_characters` (List[Character]): Currently active characters
- `timeline` (TimelineHistory): Current timeline

**Returns**: Dictionary with:
```python
{
    "character_updates": {
        "CharacterName": {
            "objective": "...",
            "status": "assigned|completed|continuing",
            "reasoning": "..."
        }
    },
    "story_objective_complete": bool,
    "reasoning": "..."
}
```

---

## Loaders

### CharacterLoader

**Location**: `loaders/character_loader.py`

**Description**: Load character personas from JSON files.

#### Methods

##### `__init__()`
```python
def __init__(base_dir: str)
```

Initialize loader.

**Parameters**:
- `base_dir` (str): Story directory path (e.g., "Pirate Adventure")

Automatically looks in `[base_dir]/characters/` subdirectory.

---

##### `load_character()`
```python
def load_character(character_name: str) -> CharacterPersona
```

Load single character.

**Parameters**:
- `character_name` (str): Character name without .json extension

**Returns**: CharacterPersona instance

**Raises**:
- `FileNotFoundError`: Character file doesn't exist
- `ValueError`: Invalid JSON or missing fields

---

##### `load_multiple_characters()`
```python
def load_multiple_characters(character_names: List[str]) -> List[CharacterPersona]
```

Load multiple characters.

**Parameters**:
- `character_names` (List[str]): List of character names

**Returns**: List of CharacterPersona instances

---

##### `list_available_characters()`
```python
def list_available_characters() -> List[str]
```

List all available character files.

**Returns**: List of character names

---

### StoryLoader

**Location**: `loaders/story_loader.py`

**Description**: Load story configuration from JSON.

#### Methods

##### `__init__()`
```python
def __init__(base_dir: str)
```

Initialize loader.

**Parameters**:
- `base_dir` (str): Story directory path

Automatically looks in `[base_dir]/story/` subdirectory.

---

##### `load_story()`
```python
def load_story() -> Story
```

Load story from JSON file.

**Returns**: Story instance

**Raises**:
- `FileNotFoundError`: No story file found
- `ValueError`: Multiple story files or invalid JSON

**Note**: Only one story file allowed per directory.

---

## RoleplaySystem

**Location**: `roleplay_system.py`

**Description**: Main coordinator for the roleplay system.

### Methods

##### `__init__()`
```python
def __init__(
    player_name: str,
    characters: List[CharacterPersona],
    model_name: str = None,
    chat_storage_dir: str = None,
    story_manager = None,
    story_name: str = "default",
    initial_location: str = "Common Room",
    initial_scene_description: str = None
)
```

Initialize roleplay system.

**Parameters**:
- `player_name` (str): Human player name
- `characters` (List[CharacterPersona]): AI character personas
- `model_name` (str, optional): LLM model (default: Config.DEFAULT_MODEL)
- `chat_storage_dir` (str, optional): Storage directory (default: Config.CHAT_STORAGE_DIR)
- `story_manager` (StoryManager, optional): Story manager instance
- `story_name` (str): Story name for file naming
- `initial_location` (str): Starting location
- `initial_scene_description` (str, optional): Initial scene text

**Raises**:
- `ValueError`: GOOGLE_API_KEY not set

**Example**:
```python
system = RoleplaySystem(
    player_name="Henry",
    characters=[captain_persona, jack_persona, marina_persona],
    story_manager=story_manager,
    story_name="Pirate Adventure",
    initial_location="Ship Deck",
    initial_scene_description="The adventure begins..."
)
```

---

##### `get_conversation_file_path()`
```python
def get_conversation_file_path() -> Path
```

Get path to conversation save file.

**Returns**: Path object

---

## Configuration

**Location**: `config.py`

### Config Class

```python
class Config:
    # API Settings
    GOOGLE_API_KEY: Optional[str]
    
    # Model Settings
    DEFAULT_MODEL: str = "gemma-4-31b-it"
    MODEL_TEMPERATURE: float = 0.7
    MAX_TOKENS: int = 1024
    RESPONSE_TIMEOUT: int = 20
    
    # Conversation Settings
    DEFAULT_CONTEXT_WINDOW: int = 100
    MAX_CONSECUTIVE_AI_TURNS: int = 3
    PRIORITY_RANDOMNESS: float = 0.1
    
    # Storage Settings
    CHAT_STORAGE_DIR: str = "Chat_Logs"
```

### Environment Variables

Create `.env` file:
```
GOOGLE_API_KEY=your_api_key_here
```

---

## Utilities

### ResponseParser

**Location**: `helpers/response_parser.py`

#### Methods

##### `parse_json_response()`
```python
def parse_json_response(response_text: str) -> Dict[str, Any]
```

Parse JSON from LLM response, handling markdown code blocks.

**Parameters**:
- `response_text` (str): Raw LLM response

**Returns**: Parsed JSON dictionary

**Raises**:
- `json.JSONDecodeError`: Invalid JSON

**Example**:
```python
response = model.generate_content(prompt)
data = parse_json_response(response.text)
```

---

### GenerativeModel

**Location**: `gemini_client.py`

#### Methods

##### `__init__()`
```python
def __init__(model_name: str, api_key: Optional[str] = None)
```

Initialize Google Gemini API client.

**Parameters**:
- `model_name` (str): Model to use
- `api_key` (str, optional): API key (default: Config.GOOGLE_API_KEY)

---

##### `generate_content()`
```python
def generate_content(prompt: str, **kwargs)
```

Generate content from prompt.

**Parameters**:
- `prompt` (str): Text prompt
- `**kwargs`: Additional parameters
  - `temperature` (float): Creativity (default: 0.7)
  - `max_tokens` (int): Max response length (default: 1024)
  - `top_p` (float): Sampling parameter (default: 1.0)
  - `frequency_penalty` (float): Repetition control (default: 0.0)

**Returns**: Response object with `.text` attribute

**Raises**:
- `Exception`: API errors (rate limit, invalid key, etc.)

---

## Error Handling

### Common Exceptions

**FileNotFoundError**:
- Character file doesn't exist
- Story file not found

**ValueError**:
- Invalid JSON in character/story file
- Missing required fields
- Multiple story files (only one allowed)
- API key not set

**Exception (API Errors)**:
- `ResourceExhausted: 429` - Rate limit exceeded
- `InvalidAPIKey: 401` - Invalid API key

### Best Practices

1. **Always validate input**:
```python
if not character_name:
    raise ValueError("character_name cannot be empty")
```

2. **Provide helpful error messages**:
```python
raise FileNotFoundError(
    f"Character file not found: {filepath}\n"
    f"Available characters: {self.list_available_characters()}"
)
```

3. **Handle API errors gracefully**:
```python
try:
    response = model.generate_content(prompt)
except Exception as e:
    if "429" in str(e):
        print("Rate limit exceeded. Please wait and try again.")
    else:
        raise
```

---

**Last Updated**: December 2025  
**Author**: Jit Roy  
**License**: MIT
