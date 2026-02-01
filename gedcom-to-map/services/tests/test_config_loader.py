"""Tests for config_loader module (YAMLConfigLoader, INIConfigLoader, LoggingConfigApplicator).

These tests focus on the separated file loading and configuration logic,
independent from the main GVConfig class. This separation allows for more
focused unit testing of file I/O operations.
"""
import pytest
import tempfile
import configparser
import logging
from pathlib import Path
from unittest.mock import patch, MagicMock

from services.config_loader import (
    YAMLConfigLoader,
    INIConfigLoader,
    LoggingConfigApplicator
)


class TestYAMLConfigLoader:
    """Test YAMLConfigLoader class."""
    
    def test_find_config_file_with_custom_path(self):
        """Test finding config file with explicit custom path."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write('test: value\n')
            temp_path = Path(f.name)
        
        try:
            found = YAMLConfigLoader.find_config_file(custom_path=temp_path)
            assert found == temp_path
            assert found.exists()
        finally:
            temp_path.unlink()
    
    def test_find_config_file_nonexistent_raises(self):
        """Test that nonexistent custom path raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            YAMLConfigLoader.find_config_file(custom_path="/nonexistent/path.yaml")
    
    def test_load_returns_dict(self):
        """Test that load returns a dictionary of YAML data."""
        # Use project's actual gedcom_options.yaml file
        config = YAMLConfigLoader.load()
        assert isinstance(config, dict)
        assert len(config) > 0
    
    def test_load_with_custom_path(self):
        """Test loading YAML from custom path."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write('custom_key: custom_value\n')
            f.write('nested:\n')
            f.write('  item1: value1\n')
            temp_path = Path(f.name)
        
        try:
            config = YAMLConfigLoader.load(custom_path=temp_path)
            assert config['custom_key'] == 'custom_value'
            assert config['nested']['item1'] == 'value1'
        finally:
            temp_path.unlink()
    
    def test_load_invalid_yaml_raises(self):
        """Test that invalid YAML content raises an error."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write('invalid: yaml: content: [broken\n')
            temp_path = Path(f.name)
        
        try:
            with pytest.raises(Exception):  # yaml.YAMLError
                YAMLConfigLoader.load(path=temp_path)
        finally:
            temp_path.unlink()
    
    def test_load_preserves_structure(self):
        """Test that load preserves nested YAML structure."""
        yaml_content = """
root_level: value
nested_dict:
  level1:
    level2:
      key: deep_value
list_items:
  - item1
  - item2
  - item3
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            temp_path = Path(f.name)
        
        try:
            config = YAMLConfigLoader.load(custom_path=temp_path)
            assert config['root_level'] == 'value'
            assert config['nested_dict']['level1']['level2']['key'] == 'deep_value'
            assert len(config['list_items']) == 3
            assert 'item2' in config['list_items']
        finally:
            temp_path.unlink()


class TestINIConfigLoader:
    """Test INIConfigLoader class."""
    
    def test_init_creates_loader(self):
        """Test that INIConfigLoader initializes correctly."""
        with tempfile.NamedTemporaryFile(suffix='.ini', delete=False) as f:
            temp_path = Path(f.name)
        
        try:
            loader = INIConfigLoader(temp_path)
            assert loader.ini_path == temp_path
            assert isinstance(loader.config, configparser.ConfigParser)
        finally:
            temp_path.unlink()
    
    def test_exists_returns_false_for_new_file(self):
        """Test exists() returns False when INI file doesn't exist."""
        temp_path = Path('/tmp/test_nonexistent_config.ini')
        if temp_path.exists():
            temp_path.unlink()
        
        loader = INIConfigLoader(temp_path)
        assert loader.exists() is False
    
    def test_exists_returns_true_for_existing_file(self):
        """Test exists() returns True when INI file exists."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
            f.write('[Section]\n')
            f.write('key = value\n')
            temp_path = Path(f.name)
        
        try:
            loader = INIConfigLoader(temp_path)
            assert loader.exists() is True
        finally:
            temp_path.unlink()
    
    def test_load_creates_sections_for_new_file(self):
        """Test that load creates all required sections for new file."""
        temp_path = Path(tempfile.mktemp(suffix='.ini'))
        
        try:
            loader = INIConfigLoader(temp_path)
            config = loader.load()
            
            # All INI_SECTIONS should be created
            from const import INI_SECTIONS
            for section in INI_SECTIONS:
                assert config.has_section(section)
        finally:
            if temp_path.exists():
                temp_path.unlink()
    
    def test_load_reads_existing_file(self):
        """Test that load reads values from existing INI file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
            f.write('[Core]\n')
            f.write('InputFile = /path/to/file.ged\n')
            f.write('MaxMissing = 5\n')
            f.write('[HTML]\n')
            f.write('ShowBirthMarker = True\n')
            temp_path = Path(f.name)
        
        try:
            loader = INIConfigLoader(temp_path)
            config = loader.load()
            
            assert config.get('Core', 'InputFile') == '/path/to/file.ged'
            assert config.get('Core', 'MaxMissing') == '5'
            assert config.get('HTML', 'ShowBirthMarker') == 'True'
        finally:
            temp_path.unlink()
    
    def test_save_writes_to_file(self):
        """Test that save writes configuration to INI file."""
        temp_path = Path(tempfile.mktemp(suffix='.ini'))
        
        try:
            loader = INIConfigLoader(temp_path)
            config = configparser.ConfigParser()
            config['TestSection'] = {'key1': 'value1', 'key2': 'value2'}
            
            loader.save(config)
            
            assert temp_path.exists()
            
            # Verify by reading back
            loader2 = INIConfigLoader(temp_path)
            loaded_config = loader2.load()
            assert loaded_config.get('TestSection', 'key1') == 'value1'
            assert loaded_config.get('TestSection', 'key2') == 'value2'
        finally:
            if temp_path.exists():
                temp_path.unlink()
    
    def test_save_creates_parent_directory(self):
        """Test that save creates parent directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_path = Path(tmpdir) / 'subdir' / 'config.ini'
            assert not temp_path.parent.exists()
            
            loader = INIConfigLoader(temp_path)
            config = configparser.ConfigParser()
            config['Section'] = {'key': 'value'}
            
            loader.save(config)
            
            assert temp_path.exists()
            assert temp_path.parent.exists()
    
    def test_migrate_with_unset_version(self):
        """Test migration when version is UNSET."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
            f.write('[Core]\n')
            f.write('_migration_version = -1\n')  # MIGRATION_VERSION_UNSET
            f.write('InputFile = /old/path.ged\n')
            temp_path = Path(f.name)
        
        try:
            loader = INIConfigLoader(temp_path)
            config = loader.load()
            
            yaml_options = {'logging_defaults': {'root': 'WARNING'}}
            migrated = loader.migrate(yaml_options)
            
            # Should have migrated
            assert migrated is True
            
            # Version should be updated
            from const import MIGRATION_VERSION_CURRENT
            assert config.get('Core', '_migration_version') == str(MIGRATION_VERSION_CURRENT)
        finally:
            temp_path.unlink()
    
    def test_migrate_with_current_version_skips(self):
        """Test migration skips when already at current version."""
        from const import MIGRATION_VERSION_CURRENT
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
            f.write('[Core]\n')
            f.write(f'_migration_version = {MIGRATION_VERSION_CURRENT}\n')
            f.write('InputFile = /path.ged\n')
            temp_path = Path(f.name)
        
        try:
            loader = INIConfigLoader(temp_path)
            config = loader.load()
            
            yaml_options = {}
            migrated = loader.migrate(yaml_options)
            
            # Should not have migrated
            assert migrated is False
        finally:
            temp_path.unlink()
    
    def test_load_and_save_preserves_all_sections(self):
        """Test that loading and saving preserves all section data."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
            f.write('[Core]\n')
            f.write('InputFile = /test.ged\n')
            f.write('[HTML]\n')
            f.write('ShowBirthMarker = True\n')
            f.write('[Summary]\n')
            f.write('GenerateSummary = False\n')
            f.write('[Logging]\n')
            f.write('services = DEBUG\n')
            temp_path = Path(f.name)
        
        try:
            loader = INIConfigLoader(temp_path)
            config = loader.load()
            
            # Modify a value
            config.set('Core', 'InputFile', '/modified.ged')
            
            # Save
            loader.save(config)
            
            # Load again and verify
            loader2 = INIConfigLoader(temp_path)
            config2 = loader2.load()
            
            assert config2.get('Core', 'InputFile') == '/modified.ged'
            assert config2.get('HTML', 'ShowBirthMarker') == 'True'
            assert config2.get('Summary', 'GenerateSummary') == 'False'
            assert config2.get('Logging', 'services') == 'DEBUG'
        finally:
            temp_path.unlink()


class TestLoggingConfigApplicator:
    """Test LoggingConfigApplicator class."""
    
    def setup_method(self):
        """Reset logging configuration before each test."""
        # Store original levels to restore later
        self.original_levels = {}
        for name in ['test.parent', 'test.parent.child', 'test.parent.child.grandchild']:
            logger = logging.getLogger(name)
            self.original_levels[name] = logger.level
    
    def teardown_method(self):
        """Restore logging configuration after each test."""
        for name, level in self.original_levels.items():
            logger = logging.getLogger(name)
            logger.setLevel(level)
    
    def test_apply_hierarchically_sets_levels(self):
        """Test that apply_hierarchically sets logger levels."""
        config = {
            'test.parent': 'INFO',
            'test.parent.child': 'DEBUG'
        }
        
        LoggingConfigApplicator.apply_hierarchically(config)
        
        assert logging.getLogger('test.parent').level == logging.INFO
        assert logging.getLogger('test.parent.child').level == logging.DEBUG
    
    def test_apply_hierarchically_inheritance(self):
        """Test that child loggers inherit parent level when not specified."""
        config = {
            'test.parent': 'WARNING'
        }
        
        LoggingConfigApplicator.apply_hierarchically(config)
        
        parent_logger = logging.getLogger('test.parent')
        child_logger = logging.getLogger('test.parent.child')
        
        assert parent_logger.level == logging.WARNING
        # Child should inherit parent's effective level
        assert child_logger.getEffectiveLevel() == logging.WARNING
    
    def test_apply_hierarchically_override(self):
        """Test that child can override parent level."""
        config = {
            'test.parent': 'WARNING',
            'test.parent.child': 'DEBUG'
        }
        
        LoggingConfigApplicator.apply_hierarchically(config)
        
        parent_logger = logging.getLogger('test.parent')
        child_logger = logging.getLogger('test.parent.child')
        
        assert parent_logger.level == logging.WARNING
        assert child_logger.level == logging.DEBUG
        assert child_logger.getEffectiveLevel() == logging.DEBUG
    
    def test_apply_hierarchically_invalid_level_logs_warning(self, caplog):
        """Test that invalid log level generates warning."""
        config = {
            'test.logger': 'INVALID_LEVEL'
        }
        
        with caplog.at_level(logging.WARNING):
            LoggingConfigApplicator.apply_hierarchically(config)
            assert 'Invalid log level' in caplog.text
    
    def test_cleanup_stale_loggers_removes_old(self):
        """Test that cleanup_stale_loggers removes loggers not in current list."""
        config = configparser.ConfigParser()
        config['Logging'] = {
            'services.config_service': 'DEBUG',
            'old.module': 'INFO',
            'another.old.module': 'WARNING'
        }
        
        current_loggers = ['services.config_service', 'geo_gedcom']
        
        stale = LoggingConfigApplicator.cleanup_stale_loggers(config, current_loggers)
        
        assert 'old.module' in stale
        assert 'another.old.module' in stale
        assert len(stale) == 2
        
        # Verify stale loggers were removed from config
        logging_section = dict(config.items('Logging'))
        assert 'services.config_service' in logging_section
        assert 'old.module' not in logging_section
        assert 'another.old.module' not in logging_section
    
    def test_cleanup_stale_loggers_no_logging_section(self):
        """Test cleanup_stale_loggers when Logging section doesn't exist."""
        config = configparser.ConfigParser()
        current_loggers = ['services.config_service']
        
        stale = LoggingConfigApplicator.cleanup_stale_loggers(config, current_loggers)
        
        assert stale == []
    
    def test_cleanup_stale_loggers_empty_list(self):
        """Test cleanup_stale_loggers with empty current logger list."""
        config = configparser.ConfigParser()
        config['Logging'] = {
            'logger1': 'DEBUG',
            'logger2': 'INFO'
        }
        
        stale = LoggingConfigApplicator.cleanup_stale_loggers(config, [])
        
        # All loggers should be considered stale
        assert len(stale) == 2
        assert 'logger1' in stale
        assert 'logger2' in stale
    
    def test_cleanup_stale_loggers_preserves_valid(self):
        """Test that cleanup preserves loggers in the current list."""
        config = configparser.ConfigParser()
        config['Logging'] = {
            'services.config_service': 'DEBUG',
            'geo_gedcom': 'INFO',
            'old.module': 'WARNING'
        }
        
        current_loggers = ['services.config_service', 'geo_gedcom', 'render']
        
        stale = LoggingConfigApplicator.cleanup_stale_loggers(config, current_loggers)
        
        assert 'old.module' in stale
        assert len(stale) == 1
        
        # Valid loggers should still be there
        logging_section = dict(config.items('Logging'))
        assert 'services.config_service' in logging_section
        assert 'geo_gedcom' in logging_section
        assert logging_section['services.config_service'] == 'DEBUG'
        assert logging_section['geo_gedcom'] == 'INFO'


class TestINIConfigLoaderIntegration:
    """Integration tests for INIConfigLoader with realistic scenarios."""
    
    def test_full_lifecycle_new_file(self):
        """Test complete lifecycle: create, load, modify, save, reload."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ini_path = Path(tmpdir) / 'test.ini'
            
            # Create new loader for nonexistent file
            loader = INIConfigLoader(ini_path)
            assert not loader.exists()
            
            # Load creates default structure (in memory, not on disk yet)
            config = loader.load()
            assert not loader.exists()  # File not written yet
            
            from const import INI_SECTIONS
            for section in INI_SECTIONS:
                assert config.has_section(section)
            
            # Modify configuration
            config.set('Core', 'InputFile', '/test/file.ged')
            config.set('Core', 'MaxMissing', '10')
            config.set('HTML', 'ShowBirthMarker', 'True')
            
            # Save changes
            loader.save(config)
            
            # Create new loader and verify persistence
            loader2 = INIConfigLoader(ini_path)
            config2 = loader2.load()
            
            assert config2.get('Core', 'InputFile') == '/test/file.ged'
            assert config2.get('Core', 'MaxMissing') == '10'
            assert config2.get('HTML', 'ShowBirthMarker') == 'True'
    
    def test_migration_workflow(self):
        """Test realistic migration workflow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ini_path = Path(tmpdir) / 'old_config.ini'
            
            # Create old version INI file
            with open(ini_path, 'w') as f:
                f.write('[Core]\n')
                f.write('_migration_version = -1\n')
                f.write('InputFile = /old/style.ged\n')
                f.write('[Logging]\n')
                f.write('old_module = DEBUG\n')
            
            # Load and migrate
            loader = INIConfigLoader(ini_path)
            config = loader.load()
            
            yaml_options = {
                'logging_defaults': {
                    'services': 'INFO',
                    'geo_gedcom': 'WARNING'
                }
            }
            
            was_migrated = loader.migrate(yaml_options)
            assert was_migrated
            
            # Clean up stale loggers
            current_loggers = list(yaml_options['logging_defaults'].keys())
            stale = LoggingConfigApplicator.cleanup_stale_loggers(config, current_loggers)
            assert 'old_module' in stale
            
            # Save migrated config
            loader.save(config)
            
            # Reload and verify
            loader2 = INIConfigLoader(ini_path)
            config2 = loader2.load()
            
            from const import MIGRATION_VERSION_CURRENT
            assert config2.get('Core', '_migration_version') == str(MIGRATION_VERSION_CURRENT)
            assert config2.get('Core', 'InputFile') == '/old/style.ged'
            
            # Old logger should be gone
            logging_dict = dict(config2.items('Logging'))
            assert 'old_module' not in logging_dict
