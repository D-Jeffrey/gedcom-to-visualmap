"""
GVConfig: Implements IConfig (configuration and file commands) for gedcom-to-visualmap.

Refactored for better structure, reliability, and testability:
- Separated file loading logic (config_loader.py) from runtime state (GVConfig)
- No module-level side effects for better test isolation
- Dependency injection support for easier testing
- Factory methods for production and test use cases
"""
import configparser
from enum import Enum
from typing import Union, Dict, Optional, Any
from pathlib import Path
import os
import platform
import logging

from const import (
    GEO_CONFIG_FILENAME, INI_SECTION_GEO_CONFIG, INI_SECTIONS, INI_OPTION_SECTIONS
)
from render.result_type import ResultType
from services.interfaces import IConfig
from services.config_io import get_option_sections, set_options, settings_file_pathname
from services.config_loader import (
    YAMLConfigLoader, 
    INIConfigLoader, 
    LoggingConfigApplicator
)
from services.file_commands import FileOpenCommandLines

_log = logging.getLogger(__name__)


class GVConfig(IConfig):
    """
    Configuration service for gedcom-to-visualmap.
    Handles loading, saving, and managing both YAML and INI-based settings.
    Implements IConfig interface.
    
    Refactored design:
    - Uses config_loader.py for file I/O operations
    - Supports dependency injection for testing
    - Clearer initialization flow
    - No side effects in constructor
    """

    GEDCOM_OPTIONS_FILE = 'gedcom_options.yaml'
    INI_FILE_NAME = 'gedcom-visualmap.ini'

    def __init__(self, 
                 gedcom_options_path: Optional[Union[str, Path]] = None,
                 yaml_loader: Optional[YAMLConfigLoader] = None,
                 ini_loader: Optional[INIConfigLoader] = None,
                 logging_applicator: Optional[LoggingConfigApplicator] = None) -> None:
        """
        Initialize GVConfig, loading YAML and INI settings.
        
        Args:
            gedcom_options_path: Optional path to gedcom_options.yaml file.
                If None, searches in project root and parent directories.
            yaml_loader: Optional YAMLConfigLoader for dependency injection (testing).
            ini_loader: Optional INIConfigLoader for dependency injection (testing).
            logging_applicator: Optional LoggingConfigApplicator for dependency injection.
        
        Raises:
            FileNotFoundError: If gedcom_options.yaml cannot be found.
        """
        # === Dependency Injection Support ===
        self._yaml_loader = yaml_loader or YAMLConfigLoader
        self._logging_applicator = logging_applicator or LoggingConfigApplicator
        
        # === Load YAML Configuration ===
        self.options = self._yaml_loader.load(gedcom_options_path)
        
        # === Apply Default Logging Levels from YAML ===
        # This ensures child loggers use the correct level even during initialization
        self._apply_default_logging_levels()
        
        # === Initialize Core Settings ===
        self.gvConfig = None
        self.map_types = self.options.get('map_types', ["CartoDB.Voyager"])
        self._gui_colors = self._load_gui_colors()
        self._geo_config_overrides = self._load_geo_config_overrides()
        self.set_marker_defaults()
        
        # === Initialize INI Loader ===
        self.settingsfile = settings_file_pathname(self.INI_FILE_NAME)
        if ini_loader:
            self._ini_loader = ini_loader
        else:
            self._ini_loader = INIConfigLoader(self.settingsfile)
        
        self._geo_config_file: Path = Path(__file__).resolve().parent / GEO_CONFIG_FILENAME
        
        # === Load Option Defaults from YAML ===
        for section_name in get_option_sections(self.options):
            section = self.options.get(section_name, {})
            section_types = {k: v.get('type') for k, v in section.items()}
            section_defaults = {k: v.get('default') for k, v in section.items()}
            set_options(self, section_types, section_defaults)
        
        # === Configure Platform-Specific File Commands ===
        self._file_open_commands = FileOpenCommandLines()
        self._initialize_file_commands()
        
        # === Load INI Settings ===
        try:
            self.gvConfig = self._ini_loader.load()
            
            # Run migration if needed
            if self._ini_loader.exists():
                self._ini_loader.migrate(self.options)
                
            # Load settings from INI
            if self._ini_loader.exists():
                self.loadsettings()
            
        except Exception as e:
            _log.error("Error loading INI settings: %s", e)
    
    @classmethod
    def create_default(cls, gedcom_options_path: Optional[Union[str, Path]] = None) -> 'GVConfig':
        """Factory method to create GVConfig with default loaders.
        
        This is the recommended way to create GVConfig instances in production code.
        
        Args:
            gedcom_options_path: Optional path to gedcom_options.yaml
            
        Returns:
            Configured GVConfig instance
        """
        return cls(gedcom_options_path=gedcom_options_path)
    
    @classmethod
    def create_for_testing(cls,
                          yaml_data: Dict[str, Any],
                          ini_config: Optional[configparser.ConfigParser] = None) -> 'GVConfig':
        """Factory method to create GVConfig for testing with in-memory data.
        
        This allows tests to work without file system access.
        
        Args:
            yaml_data: Dictionary of YAML configuration options
            ini_config: Optional pre-configured ConfigParser instance
            
        Returns:
            GVConfig instance configured with provided data
        """
        # Create a mock loader that returns the provided data
        class MockYAMLLoader:
            @classmethod
            def load(cls, path=None):
                return yaml_data
        
        class MockINILoader:
            def __init__(self, ini_path):
                self.ini_path = Path(ini_path)
                self.config = ini_config or configparser.ConfigParser()
                
            def exists(self):
                return ini_config is not None
            
            def load(self):
                if ini_config:
                    # Ensure all required sections exist
                    for section in INI_SECTIONS:
                        if section not in self.config.sections():
                            self.config[section] = {}
                return self.config
            
            def save(self, config):
                self.config = config
            
            def migrate(self, yaml_options):
                return False
        
        return cls(
            yaml_loader=MockYAMLLoader,
            ini_loader=MockINILoader('/tmp/test_settings.ini')
        )

    # === INI/YAML Load/Save Methods ===
    def loadsettings(self) -> None:
        """Load all settings from INI file into attributes.
        
        Uses the injected INI loader for better testability.
        """
        # Sync INI loader path with settingsfile in case it was changed
        if hasattr(self, '_ini_loader') and hasattr(self, 'settingsfile'):
            self._ini_loader.ini_path = Path(self.settingsfile)
        
        # Reload from file
        self.gvConfig = self._ini_loader.load()
        
        # Load all option sections
        for section in INI_SECTIONS:
            if section in INI_OPTION_SECTIONS:
                section_keys = self._build_section_keys(section)
                self.loadsection(section, section_keys)
        
        # Load input file and set output file accordingly
        self.setInput(self.gvConfig['Core'].get('InputFile', ''), generalRequest=False)
        self.resultpath = os.path.split(self.gvConfig['Core'].get('OutputFile', ''))[0]
        
        # Load file open commands from INI into _file_open_commands object
        self._load_file_commands_from_ini()
        
        # Clean up stale logger names from [Logging] section and load active ones
        self._cleanup_and_load_logging_section()

    def _apply_default_logging_levels(self) -> None:
        """Apply default logging levels from YAML configuration.
        
        Called early during initialization to ensure correct logging levels
        are set before any significant logging occurs (e.g., during INI loading).
        Uses hierarchical application: parent levels apply to children unless overridden.
        """
        logging_defaults = self.options.get('logging_defaults', {})
        if not logging_defaults:
            return
        
        try:
            self._logging_applicator.apply_hierarchically(logging_defaults)
        except Exception as e:
            # Can't use _log here since logging might not be fully initialized
            pass  # Silently skip errors during early initialization

    def _cleanup_and_load_logging_section(self) -> None:
        """Clean up stale loggers and load active logger levels from [Logging] section.
        
        First applies default levels from logging_defaults, then INI overrides them.
        Removes logger names that are no longer in logging_defaults/logging_keys list.
        
        Uses the new LoggingConfigApplicator for cleaner separation of concerns.
        """
        # Get logger configuration
        logging_defaults = self.options.get('logging_defaults', {})
        logging_keys = list(logging_defaults.keys()) if logging_defaults else self.options.get('logging_keys', [])
        
        # Step 1: Apply default levels from YAML for all configured loggers (hierarchically)
        if logging_defaults:
            try:
                self._logging_applicator.apply_hierarchically(logging_defaults)
            except Exception as e:
                _log.error("Error applying hierarchical logging defaults: %s", e)
        
        # Step 2: Clean up stale loggers from INI using the applicator
        stale_loggers = self._logging_applicator.cleanup_stale_loggers(
            self.gvConfig, 
            logging_keys
        )
        
        # Save cleaned configuration if stale loggers were removed
        if stale_loggers:
            try:
                self._ini_loader.save(self.gvConfig)
            except Exception as e:
                _log.error("Error saving cleaned logging settings: %s", e)
        
        # Step 3: Apply INI overrides for active loggers (these override YAML defaults)
        if 'Logging' in self.gvConfig:
            ini_logging_config = dict(self.gvConfig.items('Logging'))
            if ini_logging_config:
                try:
                    self._logging_applicator.apply_hierarchically(ini_logging_config)
                except Exception as e:
                    _log.error("Error applying hierarchical INI logging overrides: %s", e)

    def _load_file_commands_from_ini(self) -> None:
        """Load file open commands from INI attributes into _file_open_commands object.
        
        Transfers command line settings (CSVcmdline, KMLcmdline, etc.) from
        configuration attributes to the FileOpenCommandLines object so they can
        be retrieved by FileOpener.
        """
        command_mappings = {
            'CSVcmdline': 'csv',
            'KMLcmdline': 'kml',
            'Tracecmdline': 'trace',
            'Defaultcmdline': 'default',
            'HTMLcmdline': 'html'
        }
        
        for attr_name, file_type in command_mappings.items():
            if hasattr(self, attr_name):
                cmd = getattr(self, attr_name, None)
                if cmd:
                    self._file_open_commands.add_file_type_command(file_type, cmd)

    # === INI/YAML Load/Save Methods ===
    def loadsection(self, sectionName: str, keys: Optional[Dict[str, str]] = None) -> None:
        """Load a section from INI config into attributes, coercing types.
        
        Args:
            sectionName: Name of the INI section to load.
            keys: Dictionary mapping attribute names to their types.
        """
        for key, typ in (keys or {}).items():
            value = self.gvConfig[sectionName].get(key, None)
            if value is None:
                continue
            parsed = self._coerce_value_to_type(value, typ, context=f"{sectionName}.{key}")
            setattr(self, key, parsed)

    def savesettings(self) -> None:
        """Save current attributes to INI file.
        
        Persists all configuration sections (Core, HTML, Summary, KML) to the INI file.
        Also saves the Main person ID to the Gedcom.Main section, keyed by GEDCOM filename.
        
        Uses the injected INI loader for better testability.
        """
        try:
            if not hasattr(self, 'gvConfig') or not self.gvConfig:
                self.gvConfig = configparser.ConfigParser()
                for section in INI_SECTIONS:
                    self.gvConfig[section] = {}
            elif 'Logging' not in self.gvConfig:
                self.gvConfig['Logging'] = {}
            
            # Sync INI loader path with settingsfile in case it was changed
            if hasattr(self, '_ini_loader') and hasattr(self, 'settingsfile'):
                self._ini_loader.ini_path = Path(self.settingsfile)
            
            # Save all configuration sections
            core_keys = self._build_section_keys('Core')
            for key in core_keys:
                self.gvConfig['Core'][key] = str(getattr(self, key))
            
            html_keys = self._build_section_keys('HTML')
            _log.debug("Saving HTML section with keys: %s", list(html_keys.keys()))
            for key in html_keys:
                value = getattr(self, key)
                _log.debug("  Saving HTML.%s = %s (type=%s)", key, value, type(value).__name__)
                self.gvConfig['HTML'][key] = str(getattr(self, key))
            
            summary_keys = self._build_section_keys('Summary')
            for key in summary_keys:
                self.gvConfig['Summary'][key] = str(getattr(self, key))
            
            kml_keys = self._build_section_keys('KML')
            for key in kml_keys:
                self.gvConfig['KML'][key] = str(getattr(self, key))
            
            geocoding_keys = self._build_section_keys('GeoCoding')
            for key in geocoding_keys:
                self.gvConfig['GeoCoding'][key] = str(getattr(self, key))
            
            # Save file open commands from _file_open_commands object to INI
            self._save_file_commands_to_ini()
            
            self.gvConfig['Core']['InputFile'] = getattr(self, 'GEDCOMinput', '')
            self.gvConfig['Core']['OutputFile'] = os.path.join(
                getattr(self, 'resultpath', ''), 
                getattr(self, 'ResultFile', '')
            )
            
            # Save Main person ID under Gedcom.Main section, keyed by GEDCOM filename
            if hasattr(self, 'GEDCOMinput') and self.GEDCOMinput:
                name = Path(self.GEDCOMinput).stem
                if hasattr(self, 'Main') and self.Main:
                    self.gvConfig['Gedcom.Main'][name] = self.Main

            # Save logger levels - only for loggers explicitly in logging_defaults
            # Clear existing entries first to avoid persisting stale loggers
            self.gvConfig.remove_section('Logging')
            self.gvConfig.add_section('Logging')
            
            # Get logger names from logging_defaults (dict) or logging_keys (list)
            logging_defaults = self.options.get('logging_defaults', {})
            logging_keys = list(logging_defaults.keys()) if logging_defaults else self.options.get('logging_keys', [])
            for logName in logging_keys:
                # Only save if this logger actually exists and has a non-default level
                if logName in logging.root.manager.loggerDict:
                    logger = logging.getLogger(logName)
                    logLevel = logging.getLevelName(logger.level)
                    if logLevel != 'NOTSET':
                        self.gvConfig['Logging'][logName] = logging.getLevelName(logger.getEffectiveLevel())
            
            # Save geo_config_overrides to GeoConfig section as flattened key-value pairs
            import json
            # Clear and recreate GeoConfig section to avoid stale keys
            if self.gvConfig.has_section(INI_SECTION_GEO_CONFIG):
                self.gvConfig.remove_section(INI_SECTION_GEO_CONFIG)
            self.gvConfig.add_section(INI_SECTION_GEO_CONFIG)
            
            if hasattr(self, '_geo_config_overrides') and self._geo_config_overrides:
                # Flatten nested dict into dot-notation keys
                def flatten_dict(d, parent_key=''):
                    items = []
                    for k, v in d.items():
                        new_key = f"{parent_key}.{k}" if parent_key else k
                        if isinstance(v, dict):
                            items.extend(flatten_dict(v, new_key).items())
                        else:
                            # Serialize complex types as JSON, simple types as strings
                            if v is None:
                                items.append((new_key, 'None'))
                            elif isinstance(v, (list, dict)):
                                items.append((new_key, json.dumps(v)))
                            else:
                                items.append((new_key, str(v)))
                    return dict(items)
                
                flattened = flatten_dict(self._geo_config_overrides)
                for key, value in flattened.items():
                    self.gvConfig[INI_SECTION_GEO_CONFIG][key] = value
            
            # Use INI loader to save (better encapsulation)
            self._ini_loader.save(self.gvConfig)
            
        except Exception as e:
            _log.error("Error saving settings to %s: %s", self.settingsfile, e)

    def _save_file_commands_to_ini(self) -> None:
        """Save file open commands from _file_open_commands object to INI attributes.
        
        Transfers command line settings from the FileOpenCommandLines object
        to configuration attributes (CSVcmdline, KMLcmdline, etc.) so they get
        persisted to the INI file.
        """
        command_mappings = {
            'csv': 'CSVcmdline',
            'kml': 'KMLcmdline',
            'trace': 'Tracecmdline',
            'default': 'Defaultcmdline',
            'html': 'HTMLcmdline'
        }
        
        for file_type, attr_name in command_mappings.items():
            cmd = self._file_open_commands.get_command_for_file_type(file_type)
            if cmd:
                self.gvConfig['Core'][attr_name] = cmd

    # === Option/Attribute Setters ===
    def setstatic(self,
                  GEDCOMinput: Optional[str],
                  ResultFile: Optional[str],
                  ResultType,
                  Main: Optional[str] = None,
                  MaxMissing: int = 0,
                  MaxLineWeight: int = 20,
                  geocode_only: bool = True,
                  cache_only: bool = False,
                  AllEntities: bool = False) -> None:
        """Set static configuration options.
        
        Args:
            GEDCOMinput: Path to input GEDCOM file.
            ResultFile: Path to output/results file.
            ResultType: Type of output (HTML, KML, KML2, SUM).
            Main: ID of main/root person for genealogy tree.
            MaxMissing: Maximum number of missing GPS coordinates to allow.
            MaxLineWeight: Maximum weight for connection lines.
            geocode_only: Whether to use GPS/geocoding services (ignore cache).
            cache_only: Whether to use cache-only mode (no network requests).
            AllEntities: Whether to process all entities in GEDCOM.
        """
        self.setInput(GEDCOMinput)
        self.setResultsFile(ResultFile or "", ResultType)
        self.Main = Main
        self.Name = None
        self.MaxMissing = MaxMissing
        self.MaxLineWeight = MaxLineWeight
        self.geocode_only = geocode_only
        self.cache_only = cache_only
        self.AllEntities = AllEntities

    def setInput(self, theInput: Optional[str], generalRequest: bool = True) -> None:
        """Set the input GEDCOM file and load associated Main person ID.
        
        Args:
            theInput: Path to the GEDCOM input file.
            generalRequest: If True, saves settings when input changes.
                Set to False during initialization to avoid premature saves.
        """
        org = getattr(self, 'GEDCOMinput', None)
        if hasattr(self, 'gvConfig') and self.gvConfig and generalRequest and org:
            if org != theInput:
                self.savesettings()
        self.GEDCOMinput = theInput
        if hasattr(self, 'gvConfig') and self.gvConfig and self.GEDCOMinput:
            name = Path(self.GEDCOMinput).stem
            if self.gvConfig['Gedcom.Main'].get(name):
                self.Main = self.gvConfig['Gedcom.Main'].get(name)
            else:
                self.Main = None
        if self.GEDCOMinput:
            filen, extension = os.path.splitext(self.GEDCOMinput)
            if extension == "" and self.GEDCOMinput != "":
                self.GEDCOMinput = self.GEDCOMinput + ".ged"
            if org != self.GEDCOMinput:
                self.resultpath = os.path.dirname(self.GEDCOMinput) or None
                self.setResultsFile(filen, getattr(self, 'ResultType', None))
        else:
            self.resultpath = None
        if org != self.GEDCOMinput:
            self.parsed = False

    def setResultsFile(self, ResultFile: str, OutputType) -> None:
        """Set the output results file with appropriate extension.
        
        Args:
            ResultFile: Base name for the results file (without extension).
            OutputType: Type of output, determines file extension (HTML, KML, KML2, SUM).
        """
        _log = logging.getLogger(__name__ + ".GVConfig.setResultsFile")
        _log.debug("setResultsFile called with ResultFile=%s, OutputType=%s", ResultFile, OutputType)
        
        from render.result_type import ResultType
        enforced = ResultType.ResultTypeEnforce(OutputType)
        self.ResultType = enforced
        extension = ResultType.file_extension(enforced)
        base, _ = os.path.splitext(os.path.basename(ResultFile or ""))
        _log.debug("Extracted base=%s, extension=%s", base, extension)
        self.ResultFile = base
        if self.ResultFile:
            self.ResultFile = self.ResultFile + "." + extension
        _log.debug("Final ResultFile=%s", self.ResultFile)

    def set_options(self, options_types: Dict[str, str], options_defaults: Dict[str, Any]) -> None:
        """Set configuration options from types and defaults dictionaries.
        
        Args:
            options_types: Dictionary mapping option names to their type strings.
            options_defaults: Dictionary mapping option names to their default values.
        """
        for key, typ in options_types.items():
            value = options_defaults.get(key, None)
            parsed = self._coerce_value_to_type(value, typ, context=f"option '{key}'")
            setattr(self, key, parsed)

    def set_marker_defaults(self) -> None:
        """Load default marker options from YAML configuration."""
        marker_options_unified = self.options.get('html_display_options', {}) or {}
        marker_options = {k: v.get('default') for k, v in marker_options_unified.items()}
        self.set_marker_options(marker_options)

    def set_marker_options(self, marker_options: Dict[str, Any]) -> None:
        """Set marker display options for map rendering.
        
        Args:
            marker_options: Dictionary of marker option names to values.
        """
        marker_options_unified = self.options.get('html_display_options', {}) or {}
        expected_keys = list(marker_options_unified.keys())
        for key, value in marker_options.items():
            if key in expected_keys:
                setattr(self, key, value)
            else:
                _log.warning("Unknown marker option '%s' in defaults; ignoring.", key)
        for key in expected_keys:
            if not hasattr(self, key):
                _log.warning("Marker option '%s' missing in defaults; setting to None.", key)
                setattr(self, key, None)

    def _load_gui_colors(self) -> dict:
        """Load GUI color definitions from YAML configuration.
        
        Returns:
            Dictionary mapping color names to color database names (strings).
        """
        return self.options.get('gui_colors', {})

    def _load_geo_config_overrides(self) -> dict:
        """Load geo_config_overrides from INI file, with YAML fallback.
        
        Loads from INI GeoConfig section if present, otherwise from YAML.
        INI format stores as flattened key-value pairs (e.g., geocode_settings.max_retries).
        
        Returns:
            Dictionary of geo_config_overrides settings.
        """
        import json
        # Try loading from INI first (if INI file exists and has been loaded)
        if hasattr(self, 'gvConfig') and self.gvConfig and INI_SECTION_GEO_CONFIG in self.gvConfig:
            try:
                result = {}
                for key, value in self.gvConfig[INI_SECTION_GEO_CONFIG].items():
                    # Parse nested keys (e.g., "geocode_settings.max_retries" -> {"geocode_settings": {"max_retries": ...}})
                    keys = key.split('.')
                    current = result
                    for k in keys[:-1]:
                        if k not in current:
                            current[k] = {}
                        current = current[k]
                    # Parse the value
                    final_key = keys[-1]
                    # Try to parse as JSON for complex types, otherwise use as string
                    try:
                        current[final_key] = json.loads(value)
                    except (json.JSONDecodeError, ValueError):
                        # Handle special values
                        if value.lower() == 'none':
                            current[final_key] = None
                        elif value.lower() in ('true', 'false'):
                            current[final_key] = value.lower() == 'true'
                        else:
                            try:
                                # Try to parse as number
                                if '.' in value:
                                    current[final_key] = float(value)
                                else:
                                    current[final_key] = int(value)
                            except ValueError:
                                current[final_key] = value
                if result:  # Only return if we found something
                    return result
            except Exception as e:
                _log.warning("Failed to load geo_config_overrides from INI: %s, falling back to YAML", e)
        # Fall back to YAML
        return self.options.get('geo_config_overrides', {})

    # === Getters/Setters ===
    def get(self, attribute: str, default: Any = None, ifNone: Any = None) -> Any:
        """Get a configuration attribute value with optional defaults.
        
        Args:
            attribute: Name of the attribute to retrieve.
            default: Value to return if attribute doesn't exist.
            ifNone: Value to return if attribute exists but is None.
        
        Returns:
            The attribute value, or default/ifNone as appropriate.
        """
        if attribute == 'resultpath':
            if getattr(self, 'GEDCOMinput', None):
                ged_dir = os.path.dirname(self.GEDCOMinput)
                return ged_dir if ged_dir else default
            val = getattr(self, attribute, None)
            return val if val else default
        
        # Special handling for ResultType to ensure proper Enum value
        if attribute == 'ResultType':
            val = getattr(self, attribute, default)
            if val is None:
                return default
            # If already a ResultType enum (from either location), return as-is
            if isinstance(val, Enum) and hasattr(val, 'value') and val.value in ('HTML', 'KML', 'KML2', 'SUM'):
                return val
            # Otherwise, ensure it's a proper ResultType enum (handles string/corrupted values)
            try:
                return ResultType.ResultTypeEnforce(val)
            except (ValueError, TypeError) as e:
                _log.warning("Invalid ResultType value '%s': %s, returning default", val, e)
                return default
        
        if ifNone is not None:
            val = getattr(self, attribute, default)
            if val == None:
                return ifNone
        return getattr(self, attribute, default)

    def has(self, key: str) -> bool:
        """Check if a configuration key exists.
        
        Args:
            key: Name of the attribute to check.
        
        Returns:
            True if the attribute exists, False otherwise.
        """
        return hasattr(self, key)

    def set(self, attribute: str, value: Any) -> None:
        """Set a configuration attribute value.
        
        Args:
            attribute: Name of the attribute to set.
            value: Value to set the attribute to.
        
        Raises:
            ValueError: If attempting to set a non-existent attribute (except 'Name').
        """
        if not hasattr(self, attribute) and attribute != 'Name':
            raise ValueError(f'attempting to set an attribute : {attribute} which does not exist')
        setattr(self, attribute, value)

    # === Timeframe Methods ===
    def resettimeframe(self) -> None:
        """Reset the timeframe tracking to empty state."""
        self.timeframe = {'from': None, 'to': None}

    def addtimereference(self, timeReference: Any) -> None:
        """Add a time reference to expand the tracked timeframe.
        
        Args:
            timeReference: Object with year_num attribute representing a date.
        """
        if not timeReference:
            return
        theyear = getattr(timeReference, 'year_num', None)
        if theyear is None:
            return
        if not hasattr(self, 'timeframe') or self.timeframe is None:
            self.timeframe = {'from': None, 'to': None}
        if self.timeframe['from'] is None:
            self.timeframe['from'] = theyear
        else:
            if theyear < self.timeframe['from']:
                self.timeframe['from'] = theyear
        if self.timeframe['to'] is None:
            self.timeframe['to'] = theyear
        else:
            if theyear > self.timeframe['to']:
                self.timeframe['to'] = theyear

    # === Helpers ===
    def _coerce_value_to_type(self, value: Any, target_type: str, context: Optional[str] = None) -> Any:
        """Coerce a value from INI/YAML to the specified target type.
        
        Args:
            value: The value to coerce.
            target_type: String indicating the target type ('bool', 'int', 'str', 'list', 'dict', 'result').
            context: Optional context string for error messages.
        
        Returns:
            The coerced value, or the original value if coercion fails.
        """
        import ast
        import re
        if value is None:
            return None
        try:
            if target_type == 'bool':
                if isinstance(value, bool):
                    return value
                return str(value).strip().lower() in ('1', 'true', 'yes', 'on', 'y', 't')
            elif target_type == 'int':
                if isinstance(value, int):
                    return value
                if isinstance(value, str) and value.strip().lower() in ('true', 'false'):
                    int_value = 1 if value.strip().lower() == 'true' else 0
                    if context:
                        _log.warning("Converting boolean '%s' to int %d for '%s'", value, int_value, context)
                    return int_value
                return int(str(value).strip())
            elif target_type == 'str':
                return str(value)
            elif target_type == 'list' or target_type == 'dict':
                if isinstance(value, (list, dict)):
                    return value
                if isinstance(value, str):
                    return yaml.safe_load(value)
                return value
            elif target_type == 'result':
                if isinstance(value, str):
                    m = re.match(r'^\s*ResultType\.([A-Za-z_][A-Za-z0-9_]*)\s*$', value)
                    if m:
                        value = m.group(1)
                from render.result_type import ResultType
                return ResultType.ResultTypeEnforce(value)
            else:
                if isinstance(value, (dict, list, int, float, bool)):
                    return value
                if isinstance(value, str):
                    m2 = re.match(r'^\s*LatLon\s*\((.*)\)\s*$', value)
                    if m2:
                        inside = m2.group(1)
                        parts = [p.strip() for p in inside.split(',')]
                        vals = []
                        for p in parts:
                            if p.lower() == 'none' or p == '':
                                vals.append(None)
                            else:
                                try:
                                    vals.append(float(p))
                                except Exception:
                                    vals.append(p.strip('\'"'))
                    try:
                        parsed_yaml = yaml.safe_load(value)
                        if parsed_yaml is not None and not isinstance(parsed_yaml, str):
                            return parsed_yaml
                    except Exception:
                        pass
                    try:
                        return ast.literal_eval(value)
                    except Exception as e:
                        _log.debug("Could not parse value '%s' for %s: %s - returning as string", value, context, e)
                        return value
                return value
        except Exception as e:
            _log.error("Error coercing value for '%s' type %s: %s", context, target_type, e)
            return value

    def _get_option_sections(self) -> list[str]:
        """Get list of option sections from YAML configuration.
        
        Returns:
            List of section names that contain option definitions.
        """
        sections = []
        for key, value in self.options.items():
            if isinstance(value, dict) and any(
                isinstance(v, dict) and 'type' in v and 'default' in v 
                for v in value.values()
            ):
                sections.append(key)
        return sections

    def _build_section_keys(self, section_name: str) -> Dict[str, str]:
        """Build a dictionary of keys and their types for an INI section.
        
        Args:
            section_name: Name of the INI section.
        
        Returns:
            Dictionary mapping option keys to their type strings.
        """
        section_keys = {}
        for section in self._get_option_sections():
            opts = self.options.get(section, {})
            for key, props in opts.items():
                if isinstance(props, dict) and props.get('ini_section') == section_name:
                    key_type = props.get('ini_type', props.get('type'))
                    section_keys[key] = key_type
        return section_keys

    # === Properties (IConfig interface) ===
    @property
    def file_open_commands(self) -> FileOpenCommandLines:
        """File open command lines for different file types."""
        return self._file_open_commands

    @property
    def geo_config_overrides(self) -> dict:
        """Geographic configuration overrides from YAML."""
        return self._geo_config_overrides

    # === File Commands Methods ===
    def _initialize_file_commands(self) -> None:
        """Initialize platform-specific default commands for opening files."""
        os_name = platform.system()
        
        # Get platform-specific defaults from YAML configuration
        file_defaults = self.options.get('file_command_defaults', {})
        if not file_defaults:
            _log.warning("Missing 'file_command_defaults' section in %s", self.GEDCOM_OPTIONS_FILE)
            return
        
        platform_defaults = file_defaults.get(os_name)
        if not platform_defaults:
            available = ', '.join(file_defaults.keys())
            _log.warning(
                "No file command defaults found for platform '%s' in %s. "
                "Available platforms: %s",
                os_name, self.GEDCOM_OPTIONS_FILE, available
            )
            return
        
        # Register all file type commands
        for file_type, command in platform_defaults.items():
            self._file_open_commands.add_file_type_command(file_type, command)

    def get_file_command(self, file_type: str) -> Optional[str]:
        """Get the file opening command for a specific file type.
        
        Implements IConfig interface method.
        
        Args:
            file_type: The file type identifier (case-insensitive)
            
        Returns:
            The command line string, or None if not found
        """
        try:
            return self._file_open_commands.get_command_for_file_type(file_type)
        except Exception:
            _log.exception("get_file_command failed for %s", file_type)
            return None
