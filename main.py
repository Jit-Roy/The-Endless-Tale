"""
Main entry point for the RoleRealm multi-character roleplay system.
An AI-powered interactive storytelling experience with dynamic conversations.
"""

import sys
import io
from roleplay_system import RoleplaySystem
from managers.storyManager import StoryManager
from loaders.character_loader import CharacterLoader
from loaders.story_loader import StoryLoader
from data_models import Message, Scene, Action, CharacterEntry, CharacterExit

# Force UTF-8 encoding on Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="backslashreplace", line_buffering=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="backslashreplace", line_buffering=True)


def main():
    """Main entry point for the roleplay system."""

    BASE_DIR          = "Pirate Adventure"
    PLAYER_NAME       = "Henry"
    CHARACTER_FILES   = ["marina", "jack", "captain"]
    SCENE_TITLE       = "Aboard the Sea Serpent"
    SCENE_LOCATION    = "The Sea Serpent - Main Deck"
    SCENE_TIME_OF_DAY = "Evening"
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
            initial_time_of_day=SCENE_TIME_OF_DAY,
            initial_scene_description=SCENE_DESCRIPTION,
        )

        system.display_welcome()

        if not system.is_loaded_from_save:
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

        # ── Main conversation loop ────────────────────────────────────────────
        player_messages_count = 0

        while True:
            try:
                print("\n" + "─"*70)
                user_input = input(f"⚡ {PLAYER_NAME}: ").strip()

                if user_input and user_input.lower() not in ['listen', 'progress', 'exit']:
                    player_messages_count += 1

                # progress ────────────────────────────────────────────────────
                if user_input.lower() == 'progress':
                    if story_manager:
                        print(story_manager.get_progress_summary())
                    else:
                        print("\nNo story loaded.")
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


                # exit ─────────────────────────────────────────────────
                if user_input.lower() in ['exit']:
                    print("\n[ENDING] Ending roleplay session...")
                    print(f"💾 Chat saved to: {system.get_conversation_file_path()}")
                    break

                # player message ─────────────────────────────────────────────
                if user_input:
                    system._add_player_message(user_input)
                    system.turn_manager.process_ai_responses()
                    continue

            except KeyboardInterrupt:
                print("\n\n👋 Interrupted! Ending roleplay...")
                print(f"💾 Chat saved to: {system.get_conversation_file_path()}")
                break
            except Exception as e:
                print(f"\n❌ Error: {str(e)}\n")
                print("Please try again or type 'quit' to exit.")

    except ValueError as e:
        print(f"\nConfiguration Error: {e}")
    except Exception as e:
        print(f"\nUnexpected Error: {e}")

if __name__ == "__main__":
    main()