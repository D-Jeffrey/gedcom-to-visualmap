"""
Tests for services.file_commands module.
"""
import pytest
from services.file_commands import FileOpenCommandLines


class TestFileOpenCommandLines:
    """Test FileOpenCommandLines class."""
    
    def test_init(self):
        """Test initialization creates empty commands dict."""
        fcl = FileOpenCommandLines()
        assert fcl.commands == {}
        assert fcl.list_file_types() == []
    
    def test_add_file_type_command(self):
        """Test adding a command for a file type."""
        fcl = FileOpenCommandLines()
        fcl.add_file_type_command('html', 'open {file}')
        
        assert 'html' in fcl.commands
        assert fcl.commands['html'] == 'open {file}'
    
    def test_add_multiple_file_types(self):
        """Test adding multiple file type commands."""
        fcl = FileOpenCommandLines()
        fcl.add_file_type_command('html', 'open {file}')
        fcl.add_file_type_command('kml', 'gearth {file}')
        fcl.add_file_type_command('txt', 'notepad {file}')
        
        assert len(fcl.commands) == 3
        assert fcl.commands['html'] == 'open {file}'
        assert fcl.commands['kml'] == 'gearth {file}'
        assert fcl.commands['txt'] == 'notepad {file}'
    
    def test_add_overwrites_same_case(self):
        """Test that adding same file type overwrites the command."""
        fcl = FileOpenCommandLines()
        fcl.add_file_type_command('html', 'open {file}')
        fcl.add_file_type_command('html', 'chrome {file}')
        
        assert fcl.commands['html'] == 'chrome {file}'
        assert len(fcl.commands) == 1
    
    def test_add_overwrites_different_case(self, caplog):
        """Test that adding file type with different case overwrites (case-insensitive)."""
        fcl = FileOpenCommandLines()
        fcl.add_file_type_command('HTML', 'open {file}')
        fcl.add_file_type_command('html', 'chrome {file}')
        
        # Should overwrite the original key
        assert 'HTML' in fcl.commands
        assert fcl.commands['HTML'] == 'chrome {file}'
        assert len(fcl.commands) == 1
        
        # Should log warning
        assert 'Overwriting existing command' in caplog.text
    
    def test_get_command_exact_case(self):
        """Test getting command with exact case match."""
        fcl = FileOpenCommandLines()
        fcl.add_file_type_command('html', 'open {file}')
        
        assert fcl.get_command_for_file_type('html') == 'open {file}'
    
    def test_get_command_case_insensitive(self):
        """Test getting command is case-insensitive."""
        fcl = FileOpenCommandLines()
        fcl.add_file_type_command('HTML', 'open {file}')
        
        assert fcl.get_command_for_file_type('html') == 'open {file}'
        assert fcl.get_command_for_file_type('Html') == 'open {file}'
        assert fcl.get_command_for_file_type('HTML') == 'open {file}'
    
    def test_get_command_not_found(self):
        """Test getting non-existent command returns None."""
        fcl = FileOpenCommandLines()
        fcl.add_file_type_command('html', 'open {file}')
        
        assert fcl.get_command_for_file_type('kml') is None
        assert fcl.get_command_for_file_type('pdf') is None
    
    def test_exists_command_true(self):
        """Test exists_command returns True for existing types."""
        fcl = FileOpenCommandLines()
        fcl.add_file_type_command('html', 'open {file}')
        
        assert fcl.exists_command_for_file_type('html') is True
        assert fcl.exists_command_for_file_type('HTML') is True
        assert fcl.exists_command_for_file_type('Html') is True
    
    def test_exists_command_false(self):
        """Test exists_command returns False for non-existent types."""
        fcl = FileOpenCommandLines()
        fcl.add_file_type_command('html', 'open {file}')
        
        assert fcl.exists_command_for_file_type('kml') is False
        assert fcl.exists_command_for_file_type('pdf') is False
    
    def test_list_file_types_empty(self):
        """Test list_file_types returns empty list when no types registered."""
        fcl = FileOpenCommandLines()
        assert fcl.list_file_types() == []
    
    def test_list_file_types(self):
        """Test list_file_types returns all registered file types."""
        fcl = FileOpenCommandLines()
        fcl.add_file_type_command('html', 'open {file}')
        fcl.add_file_type_command('kml', 'gearth {file}')
        fcl.add_file_type_command('txt', 'notepad {file}')
        
        types = fcl.list_file_types()
        assert len(types) == 3
        assert 'html' in types
        assert 'kml' in types
        assert 'txt' in types
    
    def test_list_preserves_original_case(self):
        """Test list_file_types preserves the original case of keys."""
        fcl = FileOpenCommandLines()
        fcl.add_file_type_command('HTML', 'open {file}')
        fcl.add_file_type_command('KML', 'gearth {file}')
        
        types = fcl.list_file_types()
        assert 'HTML' in types
        assert 'KML' in types
