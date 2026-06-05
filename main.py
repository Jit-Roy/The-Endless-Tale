# -*- coding: utf-8 -*-
"""
Main entry point for the RoleRealm multi-character roleplay system.
An AI-powered interactive storytelling experience with dynamic conversations.
"""

import sys
import io
import time
from colorama import Fore, Style, init
from roleplay_system import RoleplaySystem
from gemini_client import Config
from managers.storyManager import StoryManager
from loaders.character_loader import CharacterLoader
from loaders.story_loader import StoryLoader
from data_models import Message, Scene, Action, CharacterEntry, CharacterExit

# Force UTF-8 encoding on Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="backslashreplace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="backslashreplace")

# Initialize colorama for Windows color support
init(autoreset=True)


def display_initial_scene(title: str, location: str, description: str) -> None:
    """Display the initial scene for the roleplay."""
    print("\n" + "="*70)
    print(f"🎬 SCENE: {title.upper()}")
    print("="*70)
    print(f"\n📍 Location: {location}")
    print(f"\n📖 Setting:")
    print(f"   {description}")
    print("\n" + "="*70 + "\n")


def display_welcome(player_name: str, character_names: list):
    """Display the welcome message for the roleplay session."""
    char_list = " and ".join(character_names)
    welcome = f"""
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║                      🎭 ROLEREALM SYSTEM 🎭                         ║
║                                                                      ║
║                  Interactive AI-Powered Roleplay                     ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝

You are playing as {player_name.upper()}, joined by {char_list}.

The story unfolds naturally through your conversations! Characters have objectives
that guide them, and the story progresses automatically as objectives are completed.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📜 COMMANDS:
   • Just type naturally to speak as {player_name}
   • 'listen' - Stay quiet and let AI characters continue talking
   • 'skip' - Prompt AI characters to continue the conversation
   • 'progress' - Check current story progress and objectives
   • 'info' - See character details
   • 'reset' - Start a completely new conversation (deletes history)
   • 'quit' or 'exit' - End the session and save the conversation

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    print(welcome)


def main():
    """Main entry point for the roleplay system."""
    
    # Configuration - Customize these for your roleplay
    BASE_DIR = "Pirate Adventure"  # Base directory containing 'characters' and 'story' folders
    
    PLAYER_NAME = "Henry"  # You, the player
    CHARACTER_FILES = ["marina", "jack", "captain"]  # Names of JSON files
    SCENE_TITLE = "Aboard the Sea Serpent"
    SCENE_LOCATION = "The Sea Serpent - Main Deck"
    SCENE_DESCRIPTION = (
        "The sun is setting over the endless ocean, painting the sky in brilliant oranges and purples. "
        "The Sea Serpent rocks gently on the waves, her black sails billowing in the evening breeze. "
        "You stand on the main deck with your friends Jack and Marina, and Captain Morgan at the helm. "
        "The old map lies spread on a barrel - your ticket to fortune and glory. "
        "Adventure awaits, and the sea is calling."
    )
    INITIAL_GREETING = "This map looks incredible! Captain, what do you make of these markings?"
    
    # Load story from JSON
    print("\n📖 Loading Story...")
    try:
        story_loader = StoryLoader(BASE_DIR)
        story_arc = story_loader.load_story()
        print(f"   ✓ Loaded: {story_arc.title}\n")
    except Exception as e:
        print(f"❌ Error loading story: {e}")
        print("❌ Could not load story. Continuing without story progression.")
        story_arc = None
    
    # Create story manager
    story_manager = StoryManager(story_arc) if story_arc else None
    
    # Load character personas from JSON
    print("\n🔮 Loading characters...")
    try:
        character_loader = CharacterLoader(BASE_DIR)
        characters = character_loader.load_multiple_characters(CHARACTER_FILES)
        for char in characters:
            print(f"✨ {char.name} has joined")
        print()
    except Exception as e:
        print(f"❌ Error loading characters: {e}")
        print(f"Please make sure character JSON files exist in the '{BASE_DIR}/characters' folder.")
        return
    
    # Display welcome message
    character_names = [char.name for char in characters]
    display_welcome(PLAYER_NAME, character_names)
    
    # Initialize the roleplay system
    try:
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
        
        # Check if we loaded an existing conversation
        is_continuing = len(system.timeline.events) > 1  # More than just initial scene
        
        if not is_continuing:
            # Only display scene and send greeting for NEW conversations
            # Display the initial scene
            display_initial_scene(SCENE_TITLE, SCENE_LOCATION, SCENE_DESCRIPTION)
            
            # Display initial story objectives
            if story_manager:
                current_objective = story_manager.get_current_objective()
                if current_objective:
                    print("\n" + "="*70)
                    print("📖 STORY BEGINS")
                    print("="*70)
                    print(f"\n🎯 Current Objective:")
                    print(f"   {current_objective}")
                    print("\n" + "="*70 + "\n")
                    print("   Character objectives will be assigned after first turn.\n")
            
            # Start the roleplay session
            print("🎬 Starting the conversation...\n")
            print("="*70)
            
            # Send initial greeting
            print(f"\n💬 {PLAYER_NAME}: {INITIAL_GREETING}")
            system._add_player_message(INITIAL_GREETING)
            
            # Let AI characters respond (objectives assigned automatically in first evaluation)
            ai_responses = system.turn_manager.process_ai_responses()
        else:
            # Continuing conversation - show recent events
            print("\n📜 RECENT CONVERSATION:")
            print("="*70)
            recent_events = system.timeline_manager.get_recent_events(system.timeline, n=5)
            
            for event in recent_events:
                if isinstance(event, Message):
                    print(f"💬 {event.character}: {event.dialouge}")
                elif isinstance(event, Scene):
                    print(f"🎬 [Scene at {event.location}]: {event.description}")
                elif isinstance(event, Action):
                    print(f"👤 {event.character}: *{event.description}*")
                elif isinstance(event, CharacterEntry):
                    print(f"🚪 → {event.character} entered: {event.description}")
                elif isinstance(event, CharacterExit):
                    print(f"🚪 ← {event.character} left: {event.description}")
            print("="*70)
            print("✨ Ready to continue!\n")
        
        # Main conversation loop
        player_messages_count = 0
        
        while True:
            try:
                # Get player input
                print("\n" + "─"*70)
                user_input = input(f"⚡ {PLAYER_NAME}: ").strip()
                
                # Track player messages
                if user_input and user_input.lower() not in ['listen', 'skip', 'progress', 'info', 'quit', 'exit', 'reset']:
                    player_messages_count += 1
                
                # Handle progress command
                if user_input.lower() == 'progress':
                    if story_manager:
                        print(story_manager.get_progress_summary())
                    else:
                        print("\n⚠️  No story loaded.")
                    continue
                
                # Handle listen command
                if user_input.lower() == 'listen':
                    print(f"\n👂 {PLAYER_NAME} listens quietly as the conversation continues...")
                    ai_responses = system.turn_manager.process_ai_responses(max_turns=5)
                    if not ai_responses:
                        print(f"\n💤 The conversation naturally pauses. Everyone seems to be waiting for {PLAYER_NAME} to say something.")
                    continue
                
                # Handle reset command
                if user_input.lower() == 'reset':
                    confirm = input("\n⚠️  Are you sure you want to reset? This will delete all conversation history. (yes/no): ").strip().lower()
                    if confirm in ['yes', 'y']:
                        system.reset_conversation()
                        # Restart with initial greeting
                        display_initial_scene(SCENE_TITLE, SCENE_LOCATION, SCENE_DESCRIPTION)
                        # Re-add initial scene to timeline
                        initial_scene = system.timeline_manager.create_scene(
                            scene_type="environmental",
                            location=SCENE_LOCATION,
                            description=SCENE_DESCRIPTION
                        )
                        system.timeline_manager.add_event(system.timeline, initial_scene)
                        print(f"\n💬 {PLAYER_NAME}: {INITIAL_GREETING}")
                        system._add_player_message(INITIAL_GREETING)
                        ai_responses = system.turn_manager.process_ai_responses()
                        message_count_at_beat_start = 0
                        player_messages_count = 0
                    else:
                        print("\n✅ Reset cancelled. Continuing conversation...")
                    continue
                
                # Handle normal input
                should_continue = system._handle_player_input(user_input)
                if not should_continue:
                    break
                    
            except KeyboardInterrupt:
                print("\n\n👋 Interrupted! Ending roleplay...")
                print(f"💾 Chat saved to: {system.get_conversation_file_path()}")
                break
            except Exception as e:
                print(f"\n❌ Error: {str(e)}\n")
                print("Please try again or type 'quit' to exit.")
        
        # Display session statistics
        total_events = len(system.timeline.events)
        total_messages = sum(1 for evt in system.timeline.events if isinstance(evt, Message))
        print("\n" + "="*70)
        print("📊 SESSION STATISTICS")
        print("="*70)
        print(f"Total timeline events: {total_events}")
        print(f"Total messages exchanged: {total_messages}")
        print(f"Participants: {', '.join(system.timeline.participants)}")
        print(f"💾 Conversation saved to: {system.get_conversation_file_path()}")
        print("="*70)
        print("\n✨ Thanks for using RoleRealm! Until next time! 🎭\n")
        
    except ValueError as e:
        print(f"\n❌ Configuration Error: {e}")
        print("\nPlease make sure you have set up your GEMINI_API_KEY in a .env file.")
        print("Example .env file content:")
        print("  GEMINI_API_KEY=your_api_key_here")
    except Exception as e:
        print(f"\n❌ Unexpected Error: {e}")
        print("Please check your configuration and try again.")


if __name__ == "__main__":
    main()
