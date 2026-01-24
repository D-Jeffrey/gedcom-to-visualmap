"""gedcom_options.py

Configuration and runtime options for gedcom-to-visualmap.

Provides:
- ResultType: typed enum of supported output types.
- gvOptions: central options/state container that loads defaults from YAML,
  persists a small INI-style config, and exposes helpers used by the UI and
  background workers.

The module also contains a small platform-aware helper to locate the settings
file path for storing per-user configuration.
"""
__all__ = ['gvOptions']
import logging
import os
import platform
import time
import threading
from datetime import datetime
import yaml
import re

from typing import Union, Dict, Optional
from enum import Enum
import configparser
from const import OFFICECMDLINE, GEO_CONFIG_FILENAME
from pathlib import Path
from geo_gedcom.person import Person
from geo_gedcom.lat_lon import LatLon
from geo_gedcom.life_event import LifeEvent

_log = logging.getLogger(__name__)

# INI file section constants
INI_SECTION_GEDCOM_MAIN = 'Gedcom.Main'
INI_SECTIONS = ['Core', 'HTML', 'Summary', 'Logging', INI_SECTION_GEDCOM_MAIN, 'KML']
INI_OPTION_SECTIONS = ['Core', 'HTML', 'Summary', 'KML']

# Migration version constants
MIGRATION_VERSION_UNSET = '0'
MIGRATION_VERSION_CURRENT = '1'

def settings_file_pathname(file_name: str) -> str:
    """Return a platform-appropriate full path for storing settings.

    Ensures the parent directory exists. Returns a fallback file_name string
    if the current platform is not recognised.
    """
    # Get the operating system name
    os_name = platform.system()

    # Define the settings file path based on the operating system
    if os_name == 'Windows':
        settings_file_path = os.path.join(os.getenv('LOCALAPPDATA'), 'gedcomvisual\\')
    elif os_name == 'Darwin':
        settings_file_path = os.path.join(os.path.expanduser('~'), 'Library', 'Application Support')
    elif os_name == 'Linux':
        settings_file_path = os.path.join(os.path.expanduser('~'), '.config')
    else:
        _log.error("Unsupported operating system: %s", os_name)
        return file_name
    Path(settings_file_path).mkdir(parents=True, exist_ok=True)
    settings_file_path = os.path.join(settings_file_path, file_name)
    
    _log.debug("Settings file location: %s", settings_file_path)
    return settings_file_path
    
class ResultType(Enum):
    HTML = "HTML"
    KML = "KML"
    KML2 = "KML2"
    SUM = "SUM"

    @staticmethod
    def ResultTypeEnforce(value) -> "ResultType":
        """Coerce a value to a ResultType.

        Accepts an existing ResultType or a string (case-insensitive). Raises
        TypeError/ValueError for unsupported values.
        """
        if isinstance(value, ResultType):
            return value
        elif isinstance(value, str):
            # handle ResultType like "ResultType.HTML"
            m = re.match(r'^\s*ResultType\.([A-Za-z_][A-Za-z0-9_]*)\s*$', value)
            if m:
                value = m.group(1)
            try:
                return ResultType[value.upper()]
            except KeyError:
                raise ValueError(f"Invalid ResultType string: {value}")
        else:
            raise TypeError(f"Cannot convert {type(value)} to ResultType")
    
    def __str__(self) -> str:
        """Return the enum member's name value for human-readable display."""
        return self.value
    
    def long_name(self) -> str:
        """Return a long-form identifier for the ResultType, e.g. 'ResultType.HTML'."""
        
        # Support classes that (incorrectly) define name() as a method as well
        # as standard enum members that expose .name attribute.
        try:
            name_attr = getattr(self, "name")
            if callable(name_attr):
                name_str = name_attr()
            else:
                name_str = name_attr
        except Exception:
            # Fallback to value if anything unexpected happens
            name_str = str(self.value)
        return f"ResultType.{name_str}"
    
    @staticmethod
    def list_values() -> list[str]:
        """Return a list of all ResultType values as strings."""
        return [rt.value for rt in ResultType]
    
    def index(self) -> int:
        """Return the integer index of a ResultType value."""
        rt = ResultType.ResultTypeEnforce(self)
        return list(ResultType).index(rt)
    
    @staticmethod
    def for_file_extension(file_extension: str) -> "ResultType":
        """Return the appropriate ResultType for a given file extension.

        Raises ValueError if the extension is not recognised.
        """
        ext = file_extension.lower()
        type = ResultType.HTML
        if ext == '.html' or ext == 'html':
            type = ResultType.HTML
        elif ext == '.kml' or ext == 'kml':
            type = ResultType.KML
        elif ext == '.txt' or ext == 'txt':
            type = ResultType.SUM
        else:
            type = ResultType.HTML
            _log.warning("Unsupported file extension for ResultType: %s; reverting to HTML", file_extension)
        return type

    @staticmethod
    def file_extension(result_type: "ResultType") -> str:
        """Return the standard file extension for a given ResultType."""
        rt = ResultType.ResultTypeEnforce(result_type)
        if rt == ResultType.HTML:
            return 'html'
        elif rt == ResultType.KML or rt == ResultType.KML2:
            return 'kml'
        elif rt == ResultType.SUM:
            return 'txt'
        else:
            return 'html'

class FileOpenCommandLines:
    def __init__(self) -> None:
        self.commands: Dict[str, str] = {}

    def add_file_type_command(self, file_type: str, command_line: str) -> None:
        """Register or update a command line for opening a specific file type.
        
        Args:
            file_type: The file type identifier (case-insensitive)
            command_line: The shell command to open files of this type
        """
        file_type_lower = file_type.lower()
        found_key = file_type
        for key in self.commands.keys():
            if key.lower() == file_type_lower:
                _log.warning("Overwriting existing command for file type '%s': '%s' -> '%s'", file_type, self.commands[key], command_line)
                found_key = key
                break
        self.commands[found_key] = command_line
        
    def get_command_for_file_type(self, file_type: str) -> Optional[str]:
        """Retrieve the registered command for a given file type.
        
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
        """Check whether a command is registered for the given file type.
        
        Args:
            file_type: The file type identifier (case-insensitive)
            
        Returns:
            True if a command exists for this file type
        """
        file_type_lower = file_type.lower()
        return any(key.lower() == file_type_lower for key in self.commands.keys())
    
    def list_file_types(self) -> list[str]:
        """Return a list of all registered file type identifiers."""
        return list(self.commands.keys())
    
class gvOptions:
    """Application options and transient runtime state.

    Responsibilities:
    - Load option metadata and defaults from gedcom_options.yaml.
    - Provide get/set helpers used throughout the UI and background workers.
    - Persist lightweight settings to an INI-style file in a platform-appropriate location.
    - Maintain runtime counters/timestamps used for progress and ETA display.
    """
    GEDCOM_OPTIONS_FILE = 'gedcom_options.yaml'

    def __init__(self) -> None:
        from gui.core.gui_hooks import GuiHooks

        """Load static defaults, initialize runtime state and read persisted settings."""
        # === Load Configuration Schema ===
        file_path = Path(__file__).parent / self.GEDCOM_OPTIONS_FILE
        with open(file_path, 'r') as file:
            self.options = yaml.safe_load(file)

        # === Initialize Core Settings ===
        self.gvConfig = None
        self.set_marker_defaults()
        self.settingsfile = settings_file_pathname("gedcom-visualmap.ini")
        self.geo_config_file: Path = Path(__file__).resolve().parent / GEO_CONFIG_FILENAME

        # === Load Option Defaults from YAML ===
        for section_name in self._get_option_sections():
            section = self.options.get(section_name, {})
            section_types = {k: v.get('type') for k, v in section.items()}
            section_defaults = {k: v.get('default') for k, v in section.items()}
            self.set_options(section_types, section_defaults)

        # === Initialize Runtime State ===
        self.people: Union[Dict[str, Person], None] = None
        self.time = time.ctime()
        self.resettimeframe()
        self.app_hooks: GuiHooks = GuiHooks(self)
        self._stop_lock = threading.Lock()  # Prevent race conditions in stop()
        
        # === Configure Platform-Specific File Commands ===
        self.file_open_commands = FileOpenCommandLines()
        self._initialize_file_commands()

        # === Load Persisted Settings ===
        if os.path.exists(self.settingsfile):
            self.loadsettings()

    def _initialize_file_commands(self) -> None:
        """Initialize platform-specific default commands for opening files."""
        os_name = platform.system()
        
        # Get platform-specific defaults from YAML configuration
        file_defaults = self.options.get('file_command_defaults', {})
        if not file_defaults:
            raise ValueError(f"Missing 'file_command_defaults' section in {self.GEDCOM_OPTIONS_FILE}")
        
        platform_defaults = file_defaults.get(os_name)
        if not platform_defaults:
            available = ', '.join(file_defaults.keys())
            raise ValueError(
                f"No file command defaults found for platform '{os_name}' in {self.GEDCOM_OPTIONS_FILE}. "
                f"Available platforms: {available}"
            )
        
        # Register all file type commands
        for file_type, command in platform_defaults.items():
            self.file_open_commands.add_file_type_command(file_type, command)

    # ============================================================================
    # YAML Configuration Discovery and Loading
    # ============================================================================

    def _coerce_value_to_type(self, value, target_type: str, context: str = ""):
        """Parse a value into the target Python type.
        
        Args:
            value: The value to parse (string, or already parsed type)
            target_type: Target type string ('bool', 'int', 'str', 'result', etc.)
            context: Context string for error messages (e.g., 'option name' or 'INI section.key')
            
        Returns:
            Parsed value in the appropriate Python type
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
                # Handle boolean strings that should be converted to int
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
                # Try to parse string as list/dict
                if isinstance(value, str):
                    return yaml.safe_load(value)
                return value
            
            elif target_type == 'result':
                # handle ResultType like "ResultType.HTML"
                if isinstance(value, str):
                    m = re.match(r'^\s*ResultType\.([A-Za-z_][A-Za-z0-9_]*)\s*$', value)
                    if m:
                        value = m.group(1)
                return ResultType.ResultTypeEnforce(value)
            
            else:
                # Complex types: if already a native type, keep it
                if isinstance(value, (dict, list, int, float, bool)):
                    return value
                
                # Try to parse string values
                if isinstance(value, str):
                    # Handle LatLon(...) first (before yaml/literal_eval that might fail on parens)
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
                            return LatLon(vals[0], vals[1])
                        except Exception as e:
                            _log.debug("Could not construct LatLon from '%s' for %s: %s", value, context, e)
                            return value
                    
                    # Try yaml (handles lists/dicts/numbers/null)
                    try:
                        parsed_yaml = yaml.safe_load(value)
                        if parsed_yaml is not None and not isinstance(parsed_yaml, str):
                            return parsed_yaml
                    except Exception:
                        pass
                    
                    # Last resort: safe literal eval, otherwise keep string
                    try:
                        return ast.literal_eval(value)
                    except Exception as e:
                        # If literal_eval fails, just return the string as-is
                        _log.debug("Could not parse value '%s' for %s: %s - returning as string", value, context, e)
                        return value
                
                return value
                
        except Exception as e:
            _log.error("Error coercing value for '%s' type %s: %s", context, target_type, e)
            return value

    def _get_option_sections(self) -> list[str]:
        """Discover all option sections from the loaded YAML structure.
        
        Returns sections that contain option definitions (dicts with 'type' and 'default').
        Excludes utility sections like 'logging_keys' and 'old_ini_settings'.
        """
        sections = []
        for key, value in self.options.items():
            # Include sections that are dicts containing option definitions
            if isinstance(value, dict) and any(
                isinstance(v, dict) and 'type' in v and 'default' in v 
                for v in value.values()
            ):
                sections.append(key)
        return sections

    def set_options(self, options_types: dict, options_defaults: dict) -> None:
        """Apply parsed defaults into instance attributes with type coercion.

        Supports simple types (bool/int/str) and attempts to safely parse more
        complex YAML- or literal-encoded values for lists/dicts.
        """
        for key, typ in options_types.items():
            value = options_defaults.get(key, None)
            parsed = self._coerce_value_to_type(value, typ, context=f"option '{key}'")
            setattr(self, key, parsed)
                    
    def set_marker_defaults(self) -> None:
        """Load and apply marker-related defaults from the YAML options payload."""
        # Extract defaults from unified marker_options structure
        marker_options_unified = self.options.get('marker_options', {}) or {}
        marker_options = {k: v.get('default') for k, v in marker_options_unified.items()}
        self.set_marker_options(marker_options)

    def set_marker_options(self, marker_options: dict) -> None:
        """Apply provided marker_options dict and ensure expected keys exist.

        Unknown keys are ignored with a warning; missing expected keys are set
        to None to ensure attributes are defined.
        """
        # Get expected keys from unified marker_options structure
        marker_options_unified = self.options.get('marker_options', {}) or {}
        expected_keys = list(marker_options_unified.keys())
        # Apply provided defaults, warn about unknown keys
        for key, value in marker_options.items():
            if key in expected_keys:
                setattr(self, key, value)
            else:
                _log.warning("Unknown marker option '%s' in defaults; ignoring.", key)
        # Ensure missing expected keys get a safe default
        for key in expected_keys:
            if not hasattr(self, key):
                _log.warning("Marker option '%s' missing in defaults; setting to None.", key)
                setattr(self, key, None)
    
    # ============================================================================
    # Timeframe Tracking (for Event Analysis)
    # ============================================================================

    def resettimeframe(self) -> None:
        """Reset the aggregated timeframe used when summarising people/events."""
        self.timeframe = {'from': None, 'to': None}

    def addtimereference(self, timeReference: LifeEvent) -> None:
        """Extend the global timeframe with a LifeEvent's year (if available)."""
        if not timeReference:
            return
        theyear = timeReference.year_num
        if theyear is None:
            return
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

        
    def setstatic(self,
                  GEDCOMinput: Optional[str],
                  ResultFile: Optional[str],
                  ResultType: ResultType,
                  Main: Optional[str] = None,
                  MaxMissing: int = 0,
                  MaxLineWeight: int = 20,
                  UseGPS: bool = True,
                  CacheOnly: bool = False,
                  AllEntities: bool = False) -> None:
        """Convenience setter for a typical group of static options used at startup.
        
        Args:
            GEDCOMinput: Path to the GEDCOM input file
            ResultFile: Path for the output file (without extension)
            ResultType: Type of output to generate (HTML, KML, etc.)
            Main: ID of the main person in the GEDCOM
            MaxMissing: Maximum number of missing locations allowed
            MaxLineWeight: Maximum line weight for rendering
            UseGPS: Whether to use GPS coordinates
            CacheOnly: If True, only update the geocoding cache without generating output
            AllEntities: If True, generate output for everyone in the system
        """
        self.setInput(GEDCOMinput)
        self.setResultsFile(ResultFile or "", ResultType)
        self.Main = Main
        self.Name = None
        self.MaxMissing = MaxMissing
        self.MaxLineWeight = MaxLineWeight
        self.UseGPS = UseGPS
        self.CacheOnly = CacheOnly
        self.AllEntities = AllEntities             # generate output of everyone in the system
        
    def _build_section_keys(self, section_name: str) -> dict:
        """Build dictionary of {field_name: type} for given INI section from option definitions.
        
        Scans all option sections in the YAML configuration to find fields that should be
        persisted to the specified INI section, returning a mapping of field names to their types.
        
        Args:
            section_name: The INI section name to build keys for (e.g., 'Core', 'HTML')
            
        Returns:
            Dictionary mapping field names to type strings (e.g., {'option1': 'bool', 'option2': 'int'})
        """
        section_keys = {}
        
        # Check all option sections for fields that belong to this INI section
        for section in self._get_option_sections():
            opts = self.options.get(section, {})
            for key, props in opts.items():
                if isinstance(props, dict) and props.get('ini_section') == section_name:
                    section_keys[key] = props.get('ini_type', props.get('type'))
        
        return section_keys

    # ============================================================================
    # INI File Persistence (Load/Save Settings)
    # ============================================================================

    def loadsection(self, sectionName: str, keys: Optional[dict] = None) -> None:
        """Load and coerce a named section from the INI-style gvConfig into attributes."""
        for key, typ in (keys or {}).items():
            value = self.gvConfig[sectionName].get(key, None)
            if value is None:
                continue
            parsed = self._coerce_value_to_type(value, typ, context=f"{sectionName}.{key}")
            setattr(self, key, parsed)

    def loadsettings(self) -> None:
        """Read persisted settings file and apply configured values into this instance."""
        self.gvConfig = configparser.ConfigParser()
        self.gvConfig.read(self.settingsfile)
        
        # Ensure all necessary sections exist
        for section in INI_SECTIONS:
            if section not in self.gvConfig.sections():
                self.gvConfig[section] = {}
            if section in INI_OPTION_SECTIONS:
                section_keys = self._build_section_keys(section)
                self.loadsection(section, section_keys)
        
        # Run legacy cleanup once - check if already migrated
        migration_version = self.gvConfig['Core'].get('_migration_version', MIGRATION_VERSION_UNSET)
        if migration_version == MIGRATION_VERSION_UNSET:
            # Remove old deprecated settings
            old_ini_settings = self.options.get('old_ini_settings', {})
            for key, section in old_ini_settings.items():
                if self.gvConfig.has_option(section, key):
                    _log.info("Removing deprecated setting '%s' from section '%s'", key, section)
                    self.gvConfig.remove_option(section, key)
            # Mark migration as complete
            self.gvConfig['Core']['_migration_version'] = MIGRATION_VERSION_CURRENT
            # Save the cleaned config
            try:
                with open(self.settingsfile, 'w') as configfile:
                    self.gvConfig.write(configfile)
            except Exception as e:
                _log.error("Error saving migrated settings: %s", e)
        
        self.setInput(self.gvConfig['Core'].get('InputFile', ''), generalRequest=False)
        self.resultpath, self.ResultFile = os.path.split(self.gvConfig['Core'].get('OutputFile', ''))
        self.setResultsFile(self.ResultFile, self.ResultType)
        for file_type in self.file_open_commands.list_file_types():
            cmd = self.gvConfig['Core'].get(f'{file_type}cmdline', '')
            if cmd:
                self.file_open_commands.add_file_type_command(file_type, cmd)
            else:
                cmd = self.file_open_commands.get_command_for_file_type(file_type)
            setattr(self, f'{file_type}cmdline', cmd)

        # Load logging settings
        for itm, lvl in self.gvConfig.items('Logging'):
            alogger = logging.getLogger(itm)
            if alogger:
                alogger.setLevel(lvl)

    def savesettings(self) -> None:
        """Persist selected options into the INI-style settings file.

        This writes only the configured keys and a small set of runtime values.
        """
        # Use this to remove old settings in sections

        try:
            if not self.gvConfig:
                self.gvConfig = configparser.ConfigParser()
                for section in INI_SECTIONS:
                    self.gvConfig[section] = {}
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

            self.gvConfig['Core']['InputFile'] =  self.GEDCOMinput
            self.gvConfig['Core']['OutputFile'] = os.path.join(self.resultpath, self.ResultFile)
            for file_type in self.file_open_commands.list_file_types():
                cmd = self.file_open_commands.get_command_for_file_type(file_type)
                if cmd:
                    self.gvConfig['Core'][f'{file_type}cmdline'] = cmd
            if self.GEDCOMinput and self.Main:
                name = Path(self.GEDCOMinput).stem
                self.gvConfig[INI_SECTION_GEDCOM_MAIN][name] = str(self.Main)
            
            loggerNames = list(logging.root.manager.loggerDict.keys())
            logging_keys = self.options.get('logging_keys', [])
            for logName in loggerNames:
                if logName in logging_keys:
                    logLevel = logging.getLevelName(logging.getLogger(logName).level)
                    if logLevel == 'NOTSET':
                        self.gvConfig.remove_option('Logging', logName)
                    else:
                        self.gvConfig['Logging'][logName] = logging.getLevelName(logging.getLogger(logName).getEffectiveLevel())
            with open(self.settingsfile, 'w') as configfile:
                self.gvConfig.write(configfile)

        except Exception as e:
            _log.error("Error saving settings to %s: %s", self.settingsfile, e)
    
    # ============================================================================
    # Main Person Selection and File Path Management
    # ============================================================================
    
    def setMainPerson(self, mainperson: Person) -> None:
        """Set the currently focused person and update derived state."""
        newMain = (self.mainPerson != mainperson and mainperson and self.Name != mainperson.name) or mainperson == None
        
        self.mainPerson = mainperson 
        if mainperson:
            self.Name = mainperson.name
            self.mainPersonLatLon = mainperson.bestLatLon()
        else:
            self.Name = "<not selected>"
            self.mainPersonLatLon = None
        if newMain:
            self.selectedpeople = 0
            self.lastlines = None
            self.heritage = None
            self.Referenced = None

    def setMain(self, Main: str) -> None:
        """Set the Main identifier and select the corresponding Person if present."""
        self.Main = Main
        if self.people and Main in self.people:
            self.setMainPerson(self.people[Main])
        else:
            self.setMainPerson(None)

    def setResultsFile(self, ResultFile: str, OutputType: ResultType) -> None:
        """Set the output filename (base) and enforce an extension based on OutputType."""
        enforced = ResultType.ResultTypeEnforce(OutputType)
        self.ResultType = enforced

        extension = ResultType.file_extension(enforced)
        
        base, _ = os.path.splitext(ResultFile or "")
        self.ResultFile = base
        if self.ResultFile:
            self.ResultFile = self.ResultFile + "." + extension
        # TODO Update Visual value

    def setInput(self, theInput: Optional[str], generalRequest: bool = True) -> None:
        """Set the GEDCOM input path and adjust derived output/result values.

        If generalRequest is True, previous settings may be saved before replacing.
        """
        org = self.GEDCOMinput
        # Before we lose track, let's do savesettings (unless we are being called from savesettings)
        if self.gvConfig and generalRequest and org:
            if org != theInput:
                self.savesettings()
        self.GEDCOMinput = theInput
        if self.gvConfig and self.GEDCOMinput:
            name = Path(self.GEDCOMinput).stem
            if self.gvConfig[INI_SECTION_GEDCOM_MAIN].get(name):
                self.setMain(self.gvConfig[INI_SECTION_GEDCOM_MAIN].get(name))
            else:
                self.setMain(None)

        if self.GEDCOMinput:
            filen, extension = os.path.splitext(self.GEDCOMinput)
            if extension == "" and self.GEDCOMinput != "":
                self.GEDCOMinput = self.GEDCOMinput + ".ged"
            #TODO needs refinement
            
            if org != self.GEDCOMinput:
                self.resultpath = os.path.dirname(self.GEDCOMinput)
                # Force the output to match the name and location of the input
                self.setResultsFile(filen, self.ResultType)
        else:
            self.resultpath = None
        if org != self.GEDCOMinput:
            self.parsed = False            

    # ============================================================================
    # Progress Tracking and Process Control
    # ============================================================================

    def KeepGoing(self) -> bool:
        """Return True if processing should continue (not stopping)."""
        return not self.ShouldStop()

    def ShouldStop(self) -> bool:
        """Return True when a stop request has been issued."""
        return self.stopping

    def stopstep(self, state: str) -> bool:
        """Record a stepping state for progress display and return True to continue."""
        self.state = state
            
        return True
    
    def stepCounter(self, newcounter: int) -> None:
        """Update the internal counter used for progress display."""
        self.counter = newcounter

    def step(self, state: Optional[str] = None, info: Optional[str] = None, target: int = -1, resetCounter: bool = True, plusStep: int = 1) -> bool:
        """Advance progress counters and optionally set a new target.

        When state is provided this marks the worker as running and optionally
        resets counters. Returns ShouldStop() so callers can respect stop requests.
        
        Args:
            state: New state description (e.g., "Processing people"). If provided, marks as running.
            info: Additional information about the current step
            target: New target count for progress tracking (-1 to leave unchanged)
            resetCounter: Whether to reset the counter to 0 when state is provided
            plusStep: Amount to increment the counter (when state is None)
            
        Returns:
            bool: True if processing should stop, False otherwise
        """
        if state:
            self.state = state
            if resetCounter:
                self.counter = 0
                self.runningSinceStep = datetime.now().timestamp()
            self.running = True
        else:
            self.counter += plusStep
            self.stepinfo = info
        if target>-1:
            self.runningSinceStep = datetime.now().timestamp()
            self.countertarget = target
            # logging.debug(">>>>>> stepped %d", self.counter)
        return self.ShouldStop()

    def stop(self) -> None:        
        """Request immediate stop and reset several runtime counters/flags.
        
        Thread-safe: Uses a lock to prevent race conditions when called from
        multiple threads or when checked concurrently by KeepGoing().
        """
        with self._stop_lock:
            self.running = False
            self.stopping = False
            time.sleep(.1)
            self.lastmax = self.counter
            self.time = time.ctime()
            self.counter = 0
            self.state = ""
            self.running = False
            self.stopping = False

    # ============================================================================
    # Generic Attribute Access (get/set helpers)
    # ============================================================================

    def get(self, attribute: str, default=None, ifNone=None):
        """Safely access an attribute, returning default or ifNone when appropriate."""
        if ifNone is not None:
            val = getattr(self,attribute, default)
            if val == None:
                return ifNone
        return getattr(self,attribute, default)

    def set(self, attribute: str, value) -> None:
        """Set an existing attribute on the options object.

        Raises ValueError if the attribute does not exist. Special-cases 'Main'.
        """
        if not hasattr(self, attribute):
            raise ValueError(f'attempting to set an attribute : {attribute} which does not exist')
        if attribute == "Main":
            self.setMain(value)
        else:
            setattr (self, attribute, value)
            