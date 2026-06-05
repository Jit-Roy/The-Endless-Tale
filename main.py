# -*- coding: utf-8 -*-
"""
Main entry point for the RoleRealm multi-character roleplay system.
An AI-powered interactive storytelling experience with dynamic conversations.
"""

import sys
import io
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


def main():
    """Main entry point for the roleplay system."""

    # ── Configuration ─────────────────────────────────────────────────────────
    BASE_DIR          = "Pirate Adventure"
    PLAYER_NAME       = "Henry"
    CHARACTER_FILES   = ["marina", "jack", "captain"]
    SCENE_TITLE       = "Aboard the Sea Serpent"
    SCENE_LOCATION    = "The Sea Serpent - Main Deck"
    SCENE_DESCRIPTION = (
        "The sun is setting over the endless ocean, painting the sky in brilliant oranges and purples. "
        "The Sea Serpent rocks gently on the waves, her black sails billowing in the evening breeze. "
        "You stand on the main deck with your friends Jack and Marina, and Captain Morgan at the helm. "
        "The old map lies spread on a barrel - your ticket to fortune and glory. "
        "Adventure awaits, and the sea is calling."
    )
    INITIAL_GREETING = "This map looks incredible! Captain, what do you make of these markings?"

    # ── Load story ────────────────────────────────────────────────────────────
    print("\n📖 Loading Story...")
    try:
        story_loader = StoryLoader(BASE_DIR)
        story_arc = story_loader.load_story()
        print(f"✓ Loaded: {story_arc.title}\n")
    except Exception as e:
        print(f"❌ Error loading story: {e}")
        print("❌ Could not load story. Continuing without story progression.")
        story_arc = None

    story_manager = StoryManager(story_arc) if story_arc else None

    # ── Load characters ───────────────────────────────────────────────────────
    print("\n🔮 Loading characters...")
    try:
        character_loader = CharacterLoader(BASE_DIR)
        characters = character_loader.load_characters(CHARACTER_FILES)
        for char in characters:
            print(f"✨ {char.name} has joined")
        print()
    except Exception as e:
        print(f"❌ Error loading characters: {e}")
        print(f"Please make sure character JSON files exist in the '{BASE_DIR}/characters' folder.")
        return

    # ── Initialise the roleplay system ────────────────────────────────────────
    try:
        system = RoleplaySystem(
            player_name=PLAYER_NAME,
            characters=characters,
            chat_storage_dir=BASE_DIR,
            story_manager=story_manager,
            story_name=BASE_DIR,
            initial_location=SCENE_LOCATION,
            initial_scene_description=SCENE_DESCRIPTION,
        )

        # RoleplaySystem.display_welcome() prints the banner + commands list
        system.display_welcome()

        # Check if we resumed an existing conversation or are starting fresh
        is_continuing = len(system.timeline.events) > 1  # more than just the initial scene

        if not is_continuing:
            # ── New conversation ──────────────────────────────────────────────
            print("\n" + "="*70)
            print(f"🎬 SCENE: {SCENE_TITLE.upper()}")
            print("="*70)
            print(f"\n📍 Location: {SCENE_LOCATION}")
            print(f"\n📖 Setting:\n   {SCENE_DESCRIPTION}")
            print("\n" + "="*70 + "\n")

            if story_manager:
                current_objective = story_manager.get_current_objective()
                if current_objective:
                    print("\n" + "="*70)
                    print("📖 STORY BEGINS")
                    print("="*70)
                    print(f"\n🎯 Current Objective:\n   {current_objective}")
                    print("\n" + "="*70 + "\n")
                    print("   Character objectives will be assigned after first turn.\n")

            print("🎬 Starting the conversation...\n")
            print("="*70)

            print(f"\n💬 {PLAYER_NAME}: {INITIAL_GREETING}")
            system._add_player_message(INITIAL_GREETING)
            system.turn_manager.process_ai_responses()

        else:
            # ── Continuing conversation ───────────────────────────────────────
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

        # ── Main conversation loop ────────────────────────────────────────────
        player_messages_count = 0

        while True:
            try:
                print("\n" + "─"*70)
                user_input = input(f"⚡ {PLAYER_NAME}: ").strip()

                # Track player messages
                if user_input and user_input.lower() not in [
                    'listen', 'skip', 'progress', 'info', 'quit', 'exit', 'reset'
                ]:
                    player_messages_count += 1

                # progress ────────────────────────────────────────────────────
                if user_input.lower() == 'progress':
                    if story_manager:
                        print(story_manager.get_progress_summary())
                    else:
                        print("\n⚠️  No story loaded.")
                    continue

                # listen ──────────────────────────────────────────────────────
                if user_input.lower() == 'listen':
                    print(f"\n👂 {PLAYER_NAME} listens quietly as the conversation continues...")
                    ai_responses = system.turn_manager.process_ai_responses(max_turns=5)
                    if not ai_responses:
                        print(
                            f"\n💤 The conversation naturally pauses. "
                            f"Everyone seems to be waiting for {PLAYER_NAME} to say something."
                        )
                    continue

                # reset ───────────────────────────────────────────────────────
                if user_input.lower() == 'reset':
                    confirm = input(
                        "\n⚠️  Are you sure you want to reset? "
                        "This will delete all conversation history. (yes/no): "
                    ).strip().lower()
                    if confirm in ['yes', 'y']:
                        system.reset_conversation()
                        # Redisplay scene and re-add it to the timeline
                        print("\n" + "="*70)
                        print(f"🎬 SCENE: {SCENE_TITLE.upper()}")
                        print("="*70)
                        print(f"\n📍 Location: {SCENE_LOCATION}")
                        print(f"\n📖 Setting:\n   {SCENE_DESCRIPTION}")
                        print("\n" + "="*70 + "\n")
                        initial_scene = system.timeline_manager.create_scene(
                            scene_type="environmental",
                            location=SCENE_LOCATION,
                            description=SCENE_DESCRIPTION,
                        )
                        system.timeline_manager.add_event(system.timeline, initial_scene)
                        print(f"\n💬 {PLAYER_NAME}: {INITIAL_GREETING}")
                        system._add_player_message(INITIAL_GREETING)
                        system.turn_manager.process_ai_responses()
                        player_messages_count = 0
                    else:
                        print("\n✅ Reset cancelled. Continuing conversation...")
                    continue

                # quit / exit ─────────────────────────────────────────────────
                if user_input.lower() in ['quit', 'exit', 'end', 'goodbye']:
                    print("\n[ENDING] Ending roleplay session...")
                    print(f"💾 Chat saved to: {system.get_conversation_file_path()}")
                    break

                # skip ────────────────────────────────────────────────────────
                if user_input.lower() == 'skip':
                    print("\n[SKIP] Letting AI characters continue...")
                    system.turn_manager.process_ai_responses(max_turns=5)
                    continue

                # info ────────────────────────────────────────────────────────
                if user_input.lower() in ['info', 'characters', 'help']:
                    system.display_character_info()
                    continue

                # empty input ─────────────────────────────────────────────────
                if not user_input:
                    continue

                # normal dialogue ─────────────────────────────────────────────
                system._add_player_message(user_input)
                system.turn_manager.process_ai_responses()

            except KeyboardInterrupt:
                print("\n\n👋 Interrupted! Ending roleplay...")
                print(f"💾 Chat saved to: {system.get_conversation_file_path()}")
                break
            except Exception as e:
                print(f"\n❌ Error: {str(e)}\n")
                print("Please try again or type 'quit' to exit.")

    except ValueError as e:
        print(f"\n❌ Configuration Error: {e}")
        print("\nPlease make sure you have set up your GOOGLE_API_KEY in a .env file.")
        print("Example .env file content:")
        print("  GOOGLE_API_KEY=your_api_key_here")
    except Exception as e:
        print(f"\n❌ Unexpected Error: {e}")
        print("Please check your configuration and try again.")


if __name__ == "__main__":
    main()