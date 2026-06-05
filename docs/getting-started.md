# Getting Started with RoleRealm

Welcome to RoleRealm! This guide will help you set up and create your first interactive AI roleplay experience.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Creating Your First Story](#creating-your-first-story)
- [Running Your Story](#running-your-story)
- [Understanding the Interface](#understanding-the-interface)
- [Next Steps](#next-steps)

## Prerequisites

Before you begin, ensure you have:

- **Python 3.8 or higher** installed on your system
- A **Google Gemini API key** ([Get one here](https://developers.generativeai.google/))
- Basic familiarity with JSON format
- A text editor or IDE (VS Code, PyCharm, etc.)

## Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/Jit-Roy/RoleRealm.git
cd RoleRealm
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

This will install:
- `pydantic` - Data validation and settings management
- `google-genai` - Google Gemini API client
- `python-dotenv` - Environment variable management
- `colorama` - Colored terminal output

### Step 3: Configure Your API Key

Create a `.env` file in the project root:

```bash
# Windows
copy NUL .env

# Linux/Mac
touch .env
```

Add your Google Gemini API key:

```
GOOGLE_API_KEY=your_api_key_here
```

**Important**: Never commit your `.env` file to version control!

## Quick Start

The fastest way to see RoleRealm in action is to run the included example:

```bash
python main.py
```

This runs the "Pirate Adventure" example story with pre-configured characters.

### What You'll See

1. **Welcome Screen**: Introduction to the system and commands
2. **Initial Scene**: The story setting and location
3. **Story Objective**: Current goal to work toward
4. **Conversation**: Interactive dialogue with AI characters

### Basic Commands

While in a conversation:

- **Type naturally** to speak as your character
- `listen` - Stay quiet and let AI characters continue talking
- `skip` - Prompt AI characters to continue the conversation
- `progress` - Check current story progress and objectives
- `info` - See character details
- `reset` - Start a completely new conversation (deletes history)
- `quit` or `exit` - End the session and save the conversation

## Creating Your First Story

Let's create a simple fantasy tavern story from scratch.

### Step 1: Create Story Folder Structure

```
RoleRealm/
└── Fantasy Tavern/
    ├── characters/
    └── story/
```

Create the folders:

```bash
# Windows
mkdir "Fantasy Tavern"
mkdir "Fantasy Tavern\characters"
mkdir "Fantasy Tavern\story"

# Linux/Mac
mkdir -p "Fantasy Tavern/characters"
mkdir -p "Fantasy Tavern/story"
```

### Step 2: Create Characters

Create `Fantasy Tavern/characters/innkeeper.json`:

```json
{
  "name": "Bartram",
  "traits": [
    "friendly",
    "talkative",
    "observant",
    "helpful"
  ],
  "speaking_style": "Warm and welcoming, uses colloquial expressions, speaks with a slight country accent",
  "background": "Bartram has run the Golden Oak Tavern for twenty years, hearing countless stories from travelers. He knows everyone in town and enjoys helping adventurers find their way.",
  "relationships": {
    "Elara": "Regular customer, appreciates her magical knowledge",
    "Thorne": "Old friend, enjoys their philosophical debates"
  },
  "goals": [
    "Make everyone feel welcome",
    "Help travelers with information",
    "Keep the peace in his tavern"
  ],
  "knowledge_base": {
    "local_rumors": "Knows all the latest gossip and rumors",
    "tavern_secrets": "Hidden room upstairs for important meetings"
  }
}
```

Create `Fantasy Tavern/characters/elara.json`:

```json
{
  "name": "Elara",
  "traits": [
    "intelligent",
    "mysterious",
    "cautious",
    "studious"
  ],
  "speaking_style": "Precise and thoughtful, occasionally uses arcane terminology, speaks softly",
  "background": "A traveling mage studying ancient artifacts and lost magic. She spends her evenings at the tavern reading old tomes and gathering information.",
  "relationships": {
    "Bartram": "Trusts him with some magical knowledge",
    "Thorne": "Curious about his mysterious past"
  },
  "goals": [
    "Research ancient magical artifacts",
    "Find clues about the Lost Temple",
    "Understand the strange dreams she's been having"
  ],
  "knowledge_base": {
    "magic_expertise": "Expert in divination and elemental magic",
    "ancient_languages": "Can read old elvish and dwarven texts"
  }
}
```

Create `Fantasy Tavern/characters/thorne.json`:

```json
{
  "name": "Thorne",
  "traits": [
    "stoic",
    "experienced",
    "protective",
    "scarred by past"
  ],
  "speaking_style": "Brief and direct, rarely elaborates unless necessary, speaks with a gravelly voice",
  "background": "A veteran warrior with a dark past. He doesn't talk much about where he's been, but the scars tell a story. Now he seeks redemption by helping those in need.",
  "relationships": {
    "Bartram": "Respects his wisdom and hospitality",
    "Elara": "Protective of her, admires her courage"
  },
  "goals": [
    "Protect the innocent",
    "Find redemption for past mistakes",
    "Stay vigilant against threats"
  ],
  "knowledge_base": {
    "combat_expertise": "Master swordsman and tactician",
    "dark_knowledge": "Knows about the Shadow Brotherhood cult"
  }
}
```

### Step 3: Create Story File

Create `Fantasy Tavern/story/tavern_mystery.json`:

```json
{
  "title": "Mystery at the Golden Oak",
  "description": "Strange things have been happening in the quiet town of Millhaven. Travelers have gone missing, strange symbols have appeared on buildings, and locals speak of shadowy figures in the night. You and your companions gather at the Golden Oak Tavern to investigate these mysterious events.",
  "objectives": [
    "Gather information about the recent disappearances from the locals",
    "Investigate the strange symbols appearing around town",
    "Discover the connection between the symbols and the Shadow Brotherhood",
    "Find the hidden entrance to the cult's underground lair",
    "Confront the cult leader and rescue the missing townsfolk",
    "Return to the tavern and celebrate your victory"
  ],
  "current_objective_index": 0
}
```

### Step 4: Create Your Main Script

Create `run_fantasy_tavern.py` in the project root:

```python
"""
Fantasy Tavern roleplay story.
"""

from roleplay_system import RoleplaySystem
from config import Config
from managers.storyManager import StoryManager
from loaders.character_loader import CharacterLoader
from loaders.story_loader import StoryLoader
from colorama import init

# Initialize colorama
init(autoreset=True)

def main():
    # Configuration
    BASE_DIR = "Fantasy Tavern"
    PLAYER_NAME = "Adventurer"  # Your character name
    CHARACTER_FILES = ["bartram", "elara", "thorne"]
    
    # Scene setup
    SCENE_TITLE = "The Golden Oak Tavern"
    SCENE_LOCATION = "Golden Oak Tavern - Main Hall"
    SCENE_DESCRIPTION = (
        "The Golden Oak Tavern glows warmly in the evening light. "
        "The smell of roasted meat and fresh bread fills the air. "
        "You sit at a corner table with Bartram the innkeeper, "
        "Elara the mage, and Thorne the warrior. The atmosphere "
        "is tense - everyone has heard the rumors of disappearances."
    )
    INITIAL_GREETING = "Thank you all for meeting me. Have any of you heard more about these disappearances?"
    
    # Load story
    print("\\n📖 Loading Story...")
    story_loader = StoryLoader(BASE_DIR)
    story = story_loader.load_story()
    print(f"   ✓ Loaded: {story.title}\\n")
    
    story_manager = StoryManager(story)
    
    # Load characters
    print("\\n🔮 Loading characters...")
    character_loader = CharacterLoader(BASE_DIR)
    characters = character_loader.load_multiple_characters(CHARACTER_FILES)
    for char in characters:
        print(f"✨ {char.name} has joined")
    
    # Initialize system
    system = RoleplaySystem(
        player_name=PLAYER_NAME,
        characters=characters,
        model_name=Config.DEFAULT_MODEL,
        chat_storage_dir=BASE_DIR,
        story_manager=story_manager,
        story_name=BASE_DIR,
        initial_location=SCENE_LOCATION,
        initial_scene_description=SCENE_DESCRIPTION
    )
    
    # Check if continuing existing conversation
    is_continuing = len(system.timeline.events) > 1
    
    if not is_continuing:
        # New conversation - show initial scene
        print("\\n" + "="*70)
        print(f"🎬 SCENE: {SCENE_TITLE}")
        print("="*70)
        print(f"\\n📍 Location: {SCENE_LOCATION}")
        print(f"\\n📖 Setting:\\n   {SCENE_DESCRIPTION}")
        print("\\n" + "="*70 + "\\n")
        
        # Send initial greeting
        print(f"\\n💬 {PLAYER_NAME}: {INITIAL_GREETING}")
        system._add_player_message(INITIAL_GREETING)
        system.turn_manager.process_ai_responses()
    else:
        print("\\n📜 Continuing from previous session...\\n")
    
    # Main conversation loop
    while True:
        user_input = input(f"\\n⚡ {PLAYER_NAME}: ").strip()
        
        # Handle commands
        if user_input.lower() in ['quit', 'exit']:
            print("\\n👋 Farewell, adventurer!")
            break
        elif user_input.lower() == 'progress':
            print(story_manager.get_progress_summary())
            continue
        elif user_input.lower() == 'listen':
            print(f"\\n👂 {PLAYER_NAME} listens quietly...")
            system.turn_manager.process_ai_responses(max_turns=5)
            continue
        elif user_input.lower() == 'skip':
            system.turn_manager.process_ai_responses(max_turns=1, force_one_response=True)
            continue
        elif user_input and user_input.lower() not in ['reset']:
            # Player speaks
            system._add_player_message(user_input)
            system.turn_manager.process_ai_responses()

if __name__ == "__main__":
    main()
```

## Running Your Story

```bash
python run_fantasy_tavern.py
```

### Your First Interaction

The system will:
1. Load your characters and story
2. Display the initial scene
3. Send your initial greeting
4. AI characters will respond naturally based on their personalities

Example interaction:
```
⚡ Adventurer: Thank you all for meeting me. Have any of you heard more about these disappearances?

💬 Bartram: leans forward with concern
I've heard plenty, friend. Three travelers in the past fortnight, just... vanished. 
No trace, no struggle. Folk are getting scared to travel after dark.

💬 Elara: looks up from her tome, eyes serious
I've been researching. There are patterns in the disappearances - all happened during 
the new moon. And those symbols appearing around town... they're ancient dark magic.

⚡ Adventurer: What kind of symbols? Can you show me what they look like?
```

## Understanding the Interface

### Conversation Flow

1. **Your Turn**: Type your character's dialogue
2. **AI Response**: Characters decide who speaks based on:
   - Context relevance
   - Character priorities
   - Natural conversation flow
3. **Meta Events**: Scene changes, character entries/exits happen automatically
4. **Story Progression**: Objectives complete automatically based on narrative progress

### Visual Indicators

- `💬` - Character dialogue
- `🎬` - Scene description
- `👤` - Character action (no dialogue)
- `🚪 →` - Character entering
- `🚪 ←` - Character leaving
- `⚡` - Your turn to speak

### Story Progress

Check your progress anytime:
```
⚡ Adventurer: progress
```

Output:
```
📖 STORY PROGRESS
════════════════════════════════════════════════════════════════════
Story: Mystery at the Golden Oak
Progress: 16% (1 of 6 objectives complete)

✓ COMPLETED OBJECTIVES:
  1. Gather information about the recent disappearances from the locals

→ CURRENT OBJECTIVE:
  Investigate the strange symbols appearing around town

UPCOMING OBJECTIVES:
  3. Discover the connection between the symbols and the Shadow Brotherhood
  4. Find the hidden entrance to the cult's underground lair
  5. Confront the cult leader and rescue the missing townsfolk
  6. Return to the tavern and celebrate your victory
```

## Next Steps

### Explore Advanced Features

1. **Character Entry/Exit**
   - Characters can dynamically join or leave conversations
   - Create private conversations between subsets of characters

2. **Scene Transitions**
   - Story can move to new locations
   - Environmental events change the atmosphere

3. **Dynamic Objectives**
   - Characters receive specific goals aligned with story progression
   - Objectives adapt based on character capabilities

4. **Memory System**
   - Each character remembers only what they witnessed
   - Information asymmetry creates interesting dynamics

### Customize Your Experience

1. **Adjust AI Parameters** in character JSON:
   ```json
   "temperature": 0.8,
   "top_p": 0.95,
   "frequency_penalty": 0.3
   ```

2. **Change LLM Model** in `config.py`:
   ```python
   DEFAULT_MODEL = "anthropic/claude-3.5-sonnet"
   ```

3. **Modify Conversation Settings**:
   ```python
   MAX_CONSECUTIVE_AI_TURNS = 5  # More AI dialogue
   PRIORITY_RANDOMNESS = 0.2      # More unpredictable speakers
   ```

### Learn More

- [Architecture Documentation](architecture.md) - Deep dive into system design
- [API Reference](api-reference.md) - Complete API documentation
- [User Guide](user-guide.md) - Detailed feature explanations
- [Character Guide](character-guide.md) - Creating compelling characters
- [Story Design Guide](story-design-guide.md) - Crafting engaging narratives

### Get Help

- Check the README.md for common issues
- Review example stories in the repository
- Experiment with different character personalities
- Try various story structures and objectives

## Tips for Success

1. **Start Simple**: Begin with 2-3 characters and a clear objective
2. **Define Relationships**: Character dynamics make conversations interesting
3. **Give Characters Goals**: Personal motivations drive natural dialogue
4. **Use Specific Traits**: "Sarcastic librarian" is better than "nice person"
5. **Create Conflict**: Different goals and personalities create drama
6. **Test Iteratively**: Run conversations and refine character definitions
7. **Save Often**: The system auto-saves, but you can also use quit/exit safely

Enjoy creating your interactive stories with RoleRealm! 🎭

---

**Last Updated**: December 2025  
**Author**: Jit Roy  
**License**: MIT
