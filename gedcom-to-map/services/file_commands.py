"""
File command management for opening different file types.

Provides platform-specific command line utilities for opening files
with appropriate applications.
"""
import logging
from typing import Dict, Optional

_log = logging.getLogger(__name__)


class FileOpenCommandLines:
    """Manages command lines for opening different file types.
    
    Stores and retrieves platform-specific commands for opening files
    of various types (HTML, KML, text, etc.).
    
    Attributes:
        commands: Dictionary mapping file types to command line strings
    """
    
    def __init__(self) -> None:
        """Initialize with empty command dictionary."""
        self.commands: Dict[str, str] = {}

    def add_file_type_command(self, file_type: str, command_line: str) -> None:
        """Add or update a command for a file type.
        
        File type matching is case-insensitive. If a command already exists
        for this file type (with different casing), it will be overwritten
        and a warning logged.
        
        Args:
            file_type: The file type identifier (e.g., 'html', 'kml')
            command_line: The command line string to execute
        """
        file_type_lower = file_type.lower()
        found_key = file_type
        for key in self.commands.keys():
            if key.lower() == file_type_lower:
                _log.warning(
                    "Overwriting existing command for file type '%s': '%s' -> '%s'",
                    file_type, self.commands[key], command_line
                )
                found_key = key
                break
        self.commands[found_key] = command_line

    def get_command_for_file_type(self, file_type: str) -> Optional[str]:
        """Get the command for a specific file type.
        
        Args:
            file_type: The file type identifier (case-insensitive)
            
        Returns:
            The command line string, or None if not found
        """
        file_type_lower = file_type.lower()
        for key, value in self.commands.items():
            if key.lower() == file_type_lower:
                return value
        return None

    def exists_command_for_file_type(self, file_type: str) -> bool:
        """Check if a command exists for a file type.
        
        Args:
            file_type: The file type identifier (case-insensitive)
            
        Returns:
            True if command exists, False otherwise
        """
        file_type_lower = file_type.lower()
        return any(key.lower() == file_type_lower for key in self.commands.keys())

    def list_file_types(self) -> list[str]:
        """Get list of all registered file types.
        
        Returns:
            List of file type identifiers
        """
        return list(self.commands.keys())
