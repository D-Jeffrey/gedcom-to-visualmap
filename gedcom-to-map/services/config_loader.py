"""
Configuration loaders for YAML and INI files.
Separates concerns: loading from storage vs managing runtime configuration.
"""
import configparser
import logging
from pathlib import Path
from typing import Dict, Optional, Any, Union
import yaml

from const import (
    INI_SECTIONS,
    MIGRATION_VERSION_UNSET,
    MIGRATION_VERSION_CURRENT
)

_log = logging.getLogger(__name__)


class YAMLConfigLoader:
    """Loads and parses YAML configuration files."""
    
    DEFAULT_FILENAME = 'gedcom_options.yaml'
    
    @classmethod
    def find_config_file(cls, custom_path: Optional[Union[str, Path]] = None) -> Path:
        """Find gedcom_options.yaml file.
        
        Args:
            custom_path: Optional explicit path to config file
            
        Returns:
            Path to the config file
            
        Raises:
            FileNotFoundError: If config file cannot be found
        """
        if custom_path is not None:
            file_path = Path(custom_path)
            if not file_path.exists():
                raise FileNotFoundError(f"Could not find gedcom_options.yaml at {file_path}")
            return file_path
        
        # Search in project directories
        project_root = Path(__file__).resolve().parent.parent.parent
        file_path = project_root / cls.DEFAULT_FILENAME
        
        if not file_path.exists():
            file_path = Path(__file__).resolve().parent.parent / cls.DEFAULT_FILENAME
        
        if not file_path.exists():
            raise FileNotFoundError(f"Could not find {cls.DEFAULT_FILENAME}")
        
        return file_path
    
    @classmethod
    def load(cls, custom_path: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
        """Load YAML configuration.
        
        Args:
            custom_path: Optional path to YAML file
            
        Returns:
            Dictionary of configuration options
        """
        file_path = cls.find_config_file(custom_path)
        
        with open(file_path, 'r') as file:
            return yaml.safe_load(file) or {}


class INIConfigLoader:
    """Loads and saves INI configuration files with migration support."""
    
    def __init__(self, ini_path: Union[str, Path]):
        """Initialize INI loader.
        
        Args:
            ini_path: Path to INI settings file
        """
        self.ini_path = Path(ini_path)
        self.config = configparser.ConfigParser()
    
    def exists(self) -> bool:
        """Check if INI file exists."""
        return self.ini_path.exists()
    
    def load(self) -> configparser.ConfigParser:
        """Load INI file.
        
        Returns:
            ConfigParser instance with loaded settings
        """
        self.config = configparser.ConfigParser()
        
        if self.exists():
            self.config.read(self.ini_path)
            _log.debug("Loaded INI settings from %s", self.ini_path)
        else:
            _log.debug("INI file does not exist: %s", self.ini_path)
        
        # Ensure all required sections exist
        for section in INI_SECTIONS:
            if section not in self.config.sections():
                self.config[section] = {}
        
        return self.config
    
    def save(self, config: configparser.ConfigParser) -> None:
        """Save configuration to INI file.
        
        Args:
            config: ConfigParser instance to save
        """
        self.config = config
        
        try:
            # Ensure parent directory exists
            self.ini_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.ini_path, 'w') as configfile:
                self.config.write(configfile)
            
            _log.debug("Saved INI settings to %s", self.ini_path)
        except Exception as e:
            _log.error("Error saving INI settings to %s: %s", self.ini_path, e)
            raise
    
    def migrate(self, yaml_options: Dict[str, Any]) -> bool:
        """Run migration to remove deprecated settings.
        
        Args:
            yaml_options: YAML configuration containing old_ini_settings
            
        Returns:
            True if migration was performed, False otherwise
        """
        migration_version = self.config['Core'].get('_migration_version', MIGRATION_VERSION_UNSET)
        
        if migration_version == MIGRATION_VERSION_CURRENT:
            return False
        
        _log.info("Running INI migration from version '%s' to '%s'", 
                  migration_version, MIGRATION_VERSION_CURRENT)
        
        old_ini_settings = yaml_options.get('old_ini_settings', {})
        removed_count = 0
        
        for key, section in old_ini_settings.items():
            # ConfigParser converts option names to lowercase
            if self.config.has_section(section) and self.config.has_option(section, key):
                _log.info("Removing deprecated setting '%s' from section '%s'", key, section)
                self.config.remove_option(section, key)
                removed_count += 1
        
        _log.info("Removed %d deprecated settings during migration", removed_count)
        
        # Update migration version
        self.config['Core']['_migration_version'] = MIGRATION_VERSION_CURRENT
        
        # Save migrated config
        self.save(self.config)
        
        return True


class LoggingConfigApplicator:
    """Applies logging configuration from YAML and INI."""
    
    @staticmethod
    def apply_hierarchically(logging_config: Dict[str, str]) -> None:
        """Apply logging levels hierarchically - parents first, then children.
        
        Args:
            logging_config: Dict mapping logger names to log levels
        """
        if not logging_config:
            return
        
        # Sort by depth (parents before children)
        sorted_loggers = sorted(logging_config.items(), key=lambda x: x[0].count('.'))
        
        # Track explicitly set loggers
        explicitly_set = set()
        
        for logger_name, level_str in sorted_loggers:
            try:
                level_value = logging.getLevelName(level_str)
                
                if not isinstance(level_value, int):
                    _log.warning("Invalid log level '%s' for logger '%s'", level_str, logger_name)
                    continue
                
                # Set the logger
                logger = logging.getLogger(logger_name)
                logger.setLevel(level_value)
                explicitly_set.add(logger_name)
                
                # Apply to existing child loggers not explicitly set
                logger_prefix = logger_name + '.'
                for existing_logger_name in list(logging.root.manager.loggerDict.keys()):
                    if (existing_logger_name.startswith(logger_prefix) and 
                        existing_logger_name not in explicitly_set):
                        child_logger = logging.getLogger(existing_logger_name)
                        child_logger.setLevel(level_value)
            
            except Exception as e:
                _log.warning("Error setting log level for '%s': %s", logger_name, e)
    
    @classmethod
    def cleanup_stale_loggers(cls, 
                             config: configparser.ConfigParser,
                             valid_logger_names: list) -> list:
        """Remove stale logger names from INI [Logging] section.
        
        Args:
            config: ConfigParser instance
            valid_logger_names: List of currently valid logger names
            
        Returns:
            List of removed logger names
        """
        if 'Logging' not in config:
            return []
        
        stale_loggers = []
        
        for logger_name, _ in config.items('Logging'):
            if logger_name not in valid_logger_names:
                stale_loggers.append(logger_name)
        
        # Remove stale loggers
        for logger_name in stale_loggers:
            config.remove_option('Logging', logger_name)
        
        if stale_loggers:
            _log.info("Removed %d stale logger(s): %s", 
                     len(stale_loggers), ', '.join(stale_loggers))
        
        return stale_loggers
