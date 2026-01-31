"""
GVConfig: Implements IConfig (configuration and file commands) for gedcom-to-visualmap.
"""
import configparser
from enum import Enum
from typing import Union, Dict, Optional, Any
from pathlib import Path
import os
import platform
import yaml
import logging

from const import (
    ResultType, GEO_CONFIG_FILENAME, 
    INI_SECTION_GEDCOM_MAIN, INI_SECTIONS, INI_OPTION_SECTIONS,
    MIGRATION_VERSION_UNSET, MIGRATION_VERSION_CURRENT
)
from services.interfaces import IConfig
from services.config_io import get_option_sections, set_options, settings_file_pathname
from services.file_commands import FileOpenCommandLines

_log = logging.getLogger(__name__)

class GVConfig(IConfig):
    """
    Configuration service for gedcom-to-visualmap.
    Handles loading, saving, and managing both YAML and INI-based settings.
    Implements IConfig interface.
    """

    GEDCOM_OPTIONS_FILE = 'gedcom_options.yaml'
    INI_FILE_NAME = 'gedcom-visualmap.ini'

    def __init__(self, gedcom_options_path: Optional[Union[str, Path]] = None) -> None:
        """
        Initialize GVConfig, loading YAML and INI settings.
        
        Args:
            gedcom_options_path: Optional path to gedcom_options.yaml file.
                If None, searches in project root and parent directories.
        
        Raises:
            FileNotFoundError: If gedcom_options.yaml cannot be found.
        """
        if gedcom_options_path is not None:
            file_path = Path(gedcom_options_path)
            if not file_path.exists():
                raise FileNotFoundError(f"Could not find gedcom_options.yaml at {file_path}")
        else:
            project_root = Path(__file__).resolve().parent.parent.parent
            file_path = project_root / self.GEDCOM_OPTIONS_FILE
            if not file_path.exists():
                file_path = Path(__file__).resolve().parent.parent / self.GEDCOM_OPTIONS_FILE
            if not file_path.exists():
                raise FileNotFoundError(f"Could not find {self.GEDCOM_OPTIONS_FILE} at {file_path}")
        with open(file_path, 'r') as file:
            self.options = yaml.safe_load(file)
        
        # === Initialize Core Settings ===
        self.gvConfig = None
        self.set_marker_defaults()
        self.settingsfile = settings_file_pathname(self.INI_FILE_NAME)
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
            self.gvConfig = configparser.ConfigParser()
            if os.path.exists(self.settingsfile):
                # self.gvConfig.read(self.settingsfile)
                self.loadsettings()
            else:
                for section in INI_SECTIONS:
                    self.gvConfig[section] = {}
        except Exception as e:
            _log.error("Error loading INI settings: %s", e)

    # === INI/YAML Load/Save Methods ===
    def loadsettings(self) -> None:
        """Load all settings from INI file into attributes."""
        self.gvConfig = configparser.ConfigParser()
        self.gvConfig.read(self.settingsfile)
        for section in INI_SECTIONS:
            if section not in self.gvConfig.sections():
                self.gvConfig[section] = {}
            if section in INI_OPTION_SECTIONS:
                section_keys = self._build_section_keys(section)
                self.loadsection(section, section_keys)
        migration_version = self.gvConfig['Core'].get('_migration_version', MIGRATION_VERSION_UNSET)
        if migration_version == MIGRATION_VERSION_UNSET:
            old_ini_settings = self.options.get('old_ini_settings', {})
            for key, section in old_ini_settings.items():
                if self.gvConfig.has_option(section, key):
                    _log.info("Removing deprecated setting '%s' from section '%s'", key, section)
                    self.gvConfig.remove_option(section, key)
            self.gvConfig['Core']['_migration_version'] = MIGRATION_VERSION_CURRENT
            try:
                with open(self.settingsfile, 'w') as configfile:
                    self.gvConfig.write(configfile)
            except Exception as e:
                _log.error("Error saving migrated settings: %s", e)
        self.setInput(self.gvConfig['Core'].get('InputFile', ''), generalRequest=False)
        self.resultpath, self.ResultFile = os.path.split(self.gvConfig['Core'].get('OutputFile', ''))
        self.setResultsFile(self.ResultFile, getattr(self, 'ResultType', None))
        
        # Load file open commands from INI into _file_open_commands object
        self._load_file_commands_from_ini()
        
        # Clean up stale logger names from [Logging] section and load active ones
        self._cleanup_and_load_logging_section()

    def _cleanup_and_load_logging_section(self) -> None:
        """Clean up stale loggers and load active logger levels from [Logging] section.
        
        Removes logger names that are no longer in logging_keys list,
        then applies levels for remaining loggers.
        """
        if 'Logging' not in self.gvConfig:
            return
        
        logging_keys = self.options.get('logging_keys', [])
        stale_loggers = []
        
        # Identify stale loggers (not in current logging_keys)
        for logger_name, _ in self.gvConfig.items('Logging'):
            if logger_name not in logging_keys:
                stale_loggers.append(logger_name)
        
        # Remove stale loggers
        if stale_loggers:
            _log.info("Removing %d stale logger(s) from INI: %s", len(stale_loggers), ', '.join(stale_loggers))
            for logger_name in stale_loggers:
                self.gvConfig.remove_option('Logging', logger_name)
            
            # Save cleaned configuration
            try:
                with open(self.settingsfile, 'w') as configfile:
                    self.gvConfig.write(configfile)
            except Exception as e:
                _log.error("Error saving cleaned logging settings: %s", e)
        
        # Load and apply logger levels for active loggers
        for logger_name, log_level in self.gvConfig.items('Logging'):
            try:
                alogger = logging.getLogger(logger_name)
                alogger.setLevel(log_level)
                _log.debug("Set logger '%s' to level %s", logger_name, log_level)
            except Exception as e:
                _log.warning("Failed to set logger '%s' level to %s: %s", logger_name, log_level, e)

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
        """
        try:
            if not hasattr(self, 'gvConfig') or not self.gvConfig:
                self.gvConfig = configparser.ConfigParser()
                for section in INI_SECTIONS:
                    self.gvConfig[section] = {}
            elif 'Logging' not in self.gvConfig:
                self.gvConfig['Logging'] = {}
            core_keys = self._build_section_keys('Core')
            for key in core_keys:
                self.gvConfig['Core'][key] = str(getattr(self, key))
            html_keys = self._build_section_keys('HTML')
            for key in html_keys:
                self.gvConfig['HTML'][key] =  str(getattr(self, key))
            summary_keys = self._build_section_keys('Summary')
            for key in summary_keys:
                self.gvConfig['Summary'][key] = str(getattr(self, key))
            kml_keys = self._build_section_keys('KML')
            for key in kml_keys:
                self.gvConfig['KML'][key] =  str(getattr(self, key))
            
            # Save file open commands from _file_open_commands object to INI
            self._save_file_commands_to_ini()
            
            self.gvConfig['Core']['InputFile'] =  getattr(self, 'GEDCOMinput', '')
            self.gvConfig['Core']['OutputFile'] = os.path.join(getattr(self, 'resultpath', ''), getattr(self, 'ResultFile', ''))
            
            # Save Main person ID under Gedcom.Main section, keyed by GEDCOM filename
            if hasattr(self, 'GEDCOMinput') and self.GEDCOMinput:
                name = Path(self.GEDCOMinput).stem
                if hasattr(self, 'Main') and self.Main:
                    self.gvConfig['Gedcom.Main'][name] = self.Main

            # Save logger levels - only for loggers explicitly in logging_keys
            # Clear existing entries first to avoid persisting stale loggers
            self.gvConfig.remove_section('Logging')
            self.gvConfig.add_section('Logging')
            
            logging_keys = self.options.get('logging_keys', [])
            for logName in logging_keys:
                # Only save if this logger actually exists and has a non-default level
                if logName in logging.root.manager.loggerDict:
                    logger = logging.getLogger(logName)
                    logLevel = logging.getLevelName(logger.level)
                    if logLevel != 'NOTSET':
                        self.gvConfig['Logging'][logName] = logging.getLevelName(logger.getEffectiveLevel())
            
            with open(self.settingsfile, 'w') as configfile:
                self.gvConfig.write(configfile)
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
                  UseGPS: bool = True,
                  CacheOnly: bool = False,
                  AllEntities: bool = False) -> None:
        """Set static configuration options.
        
        Args:
            GEDCOMinput: Path to input GEDCOM file.
            ResultFile: Path to output/results file.
            ResultType: Type of output (HTML, KML, KML2, SUM).
            Main: ID of main/root person for genealogy tree.
            MaxMissing: Maximum number of missing GPS coordinates to allow.
            MaxLineWeight: Maximum weight for connection lines.
            UseGPS: Whether to use GPS/geocoding services.
            CacheOnly: Whether to use cache-only mode (no network requests).
            AllEntities: Whether to process all entities in GEDCOM.
        """
        self.setInput(GEDCOMinput)
        self.setResultsFile(ResultFile or "", ResultType)
        self.Main = Main
        self.Name = None
        self.MaxMissing = MaxMissing
        self.MaxLineWeight = MaxLineWeight
        self.UseGPS = UseGPS
        self.CacheOnly = CacheOnly
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
        from const import ResultType
        enforced = ResultType.ResultTypeEnforce(OutputType)
        self.ResultType = enforced
        extension = ResultType.file_extension(enforced)
        base, _ = os.path.splitext(os.path.basename(ResultFile or ""))
        self.ResultFile = base
        if self.ResultFile:
            self.ResultFile = self.ResultFile + "." + extension

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
        marker_options_unified = self.options.get('marker_options', {}) or {}
        marker_options = {k: v.get('default') for k, v in marker_options_unified.items()}
        self.set_marker_options(marker_options)

    def set_marker_options(self, marker_options: Dict[str, Any]) -> None:
        """Set marker display options for map rendering.
        
        Args:
            marker_options: Dictionary of marker option names to values.
        """
        marker_options_unified = self.options.get('marker_options', {}) or {}
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
                from const import ResultType
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
                    section_keys[key] = props.get('ini_type', props.get('type'))
        return section_keys

    # === Properties (IConfig interface) ===
    @property
    def file_open_commands(self) -> FileOpenCommandLines:
        """File open command lines for different file types."""
        return self._file_open_commands

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
