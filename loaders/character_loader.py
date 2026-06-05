"""
Character loader module for loading character personas from JSON files.
"""

import json
from pathlib import Path
from data_models import CharacterPersona


class CharacterLoader:
    """Load character personas from JSON files."""
    
    def __init__(self, base_dir: str):
        """
        Initialize the character loader.
        
        Args:
            base_dir: Base story directory (e.g., 'D:\RoleRealm\Pirate Adventure')
            The loader will automatically look in the 'characters' subdirectory
        """
        if not base_dir:
            raise ValueError("base_dir is required and cannot be None or empty")
        self.base_dir = Path(base_dir)
        if not self.base_dir.exists():
            raise ValueError(f"Story base directory not found: {self.base_dir}")
        
        self.characters_dir = self.base_dir / "characters"
        if not self.characters_dir.exists():
            raise ValueError(f"Characters directory not found: {self.characters_dir}")
    
    def load_character(self, character_name: str) -> CharacterPersona:
        """
        Load a character persona from a JSON file.
        
        Args:
            character_name: Name of the character (without .json extension)
            
        Returns:
            CharacterPersona instance
            
        Raises:
            FileNotFoundError: If character file doesn't exist
            ValueError: If JSON is invalid or missing required fields
        """
        # Convert character name to lowercase for file lookup
        filename = f"{character_name.lower()}.json"
        filepath = self.characters_dir / filename
        
        if not filepath.exists():
            raise FileNotFoundError(
                f"Character file not found: {filepath}\n"
                f"Available characters: {self.list_available_characters()}"
            )
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                character_data = json.load(f)
            
            return CharacterPersona(**character_data)
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {filepath}: {e}")
        except Exception as e:
            raise ValueError(f"Error loading character from {filepath}: {e}")
    
    def load_characters(self, character_names: list[str]) -> list[CharacterPersona]:
        """
        Load multiple character personas from JSON files.
        
        Args:
            character_names: List of character names to load
            
        Returns:
            List of CharacterPersona instances
        """
        characters = []
        for name in character_names:
            characters.append(self.load_character(name))
        return characters
    
    def list_available_characters(self) -> list[str]:
        """
        List all available character JSON files.
        
        Returns:
            List of character names (without .json extension)
        """
        character_files = self.characters_dir.glob("*.json")
        return [f.stem for f in character_files]
    
    def character_exists(self, character_name: str) -> bool:
        """
        Check if a character JSON file exists.
        
        Args:
            character_name: Name of the character to check
            
        Returns:
            True if character file exists, False otherwise
        """
        filename = f"{character_name.lower()}.json"
        filepath = self.characters_dir / filename
        return filepath.exists()