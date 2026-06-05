"""
Story loader module for loading story configurations from JSON files.
"""

import json
from pathlib import Path
from data_models import Story


class StoryLoader:
    """Load story configurations from JSON files."""
    
    def __init__(self, base_dir: str):
        """
        Initialize the story loader.
        
        Args:
            base_dir: Base story directory (e.g., 'D:\RoleRealm\Pirate Adventure')
            The loader will automatically look in the 'story' subdirectory
        """
        if not base_dir:
            raise ValueError("base_dir is required and cannot be None or empty")
        self.base_dir = Path(base_dir)
        if not self.base_dir.exists():
            raise ValueError(f"Story base directory not found: {self.base_dir}")
        
        # Automatically append 'story' subdirectory
        self.stories_dir = self.base_dir / "story"
        if not self.stories_dir.exists():
            raise ValueError(f"Story directory not found: {self.stories_dir}")
    
    def load_story(self) -> Story:
        """
        Load the story from the single JSON file in the story directory.
        
        Returns:
            Story instance
            
        Raises:
            FileNotFoundError: If no story file found or multiple story files found
            ValueError: If JSON is invalid or missing required fields
        """
        # Find all JSON files in the story directory
        story_files = list(self.stories_dir.glob("*.json"))
        
        if len(story_files) == 0:
            raise FileNotFoundError(f"No story file found in: {self.stories_dir}")
        elif len(story_files) > 1:
            raise ValueError(
                f"Multiple story files found in {self.stories_dir}. "
                f"Only one story file is allowed: {[f.name for f in story_files]}"
            )
        
        filepath = story_files[0]
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                story_data = json.load(f)
            
            if "current_objective_index" not in story_data:
                story_data["current_objective_index"] = 0
            
            # Create and return Story
            return Story(**story_data)
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {filepath}: {e}")
        except Exception as e:
            raise ValueError(f"Error loading story from {filepath}: {e}")