"""config_io.py

Centralized INI and YAML configuration file handling.

Provides functions for loading, saving, and parsing configuration files
used by the gedcom-to-visualmap application.
"""
import configparser
import yaml
import logging
import os
import platform
from pathlib import Path
from typing import Any, Optional
from const import INI_SECTIONS, INI_OPTION_SECTIONS, INI_SECTION_GEDCOM_MAIN, MIGRATION_VERSION_UNSET, MIGRATION_VERSION_CURRENT
from geo_gedcom.lat_lon import LatLon

_log = logging.getLogger(__name__)

def settings_file_pathname(file_name: str) -> str:
    """Return a platform-appropriate full path for storing settings.
    
    Creates platform-specific paths for application settings:
    - macOS: ~/Library/Application Support/
    - Linux: ~/.config/
    - Windows: %LOCALAPPDATA%\\gedcomvisual\\
    
    Args:
        file_name: Name of the settings file (e.g., 'settings.ini').
    
    Returns:
        str: Full path to settings file. Returns file_name unchanged if
             platform is not recognized.
    
    Note:
        Automatically creates parent directories if they don't exist.
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

def coerce_value_to_type(value: Any, target_type: str, context: str = "") -> Any:
    """Coerce a value to a specified type with intelligent parsing.
    
    Supports multiple type conversions including bool, int, str, list, dict,
    result types, LatLon objects, and automatic YAML/literal parsing.
    
    Args:
        value: Value to coerce (can be any type).
        target_type: Target type name ('bool', 'int', 'str', 'list', 'dict',
                    'result', or other type names).
        context: Optional context string for logging (e.g., 'Core.inputfile').
    
    Returns:
        Any: Coerced value. Returns None if input is None.
        
    Type-specific behavior:
        - bool: Recognizes '1', 'true', 'yes', 'on', 'y', 't' as True
        - int: Converts strings, handles boolean strings
        - str: Converts any value to string
        - list/dict: Parses YAML or returns existing collections
        - result: Parses ResultType enum values
        - LatLon: Parses 'LatLon(lat, lon)' strings
        - Other: Attempts YAML parsing, then literal_eval, then returns as-is
    
    Note:
        Logs warnings and errors for conversion failures.
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
            # Late import to avoid circular dependency
            from render.result_type import ResultType
            if isinstance(value, str):
                m = re.match(r'^\s*ResultType\.([A-Za-z_][A-Za-z0-9_]*)\s*$', value)
                if m:
                    value = m.group(1)
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
                        return LatLon(vals[0], vals[1])
                    except Exception as e:
                        _log.debug("Could not construct LatLon from '%s' for %s: %s", value, context, e)
                        return value
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

def get_option_sections(options: dict) -> list[str]:
    """Extract section names from options dictionary.
    
    Identifies sections that contain option definitions (dicts with 'type'
    and 'default' keys).
    
    Args:
        options: Options dictionary from YAML configuration.
    
    Returns:
        list[str]: List of section names that contain option definitions.
    """
    sections = []
    for key, value in options.items():
        if isinstance(value, dict) and any(
            isinstance(v, dict) and 'type' in v and 'default' in v 
            for v in value.values()
        ):
            sections.append(key)
    return sections

def set_options(obj: Any, options_types: dict, options_defaults: dict) -> None:
    """Set attributes on an object from options configuration.
    
    For each option, coerces the default value to the specified type
    and sets it as an attribute on the object.
    
    Args:
        obj: Object to set attributes on.
        options_types: Dict mapping option names to type strings.
        options_defaults: Dict mapping option names to default values.
    """
    for key, typ in options_types.items():
        value = options_defaults.get(key, None)
        parsed = coerce_value_to_type(value, typ, context=f"option '{key}'")
        setattr(obj, key, parsed)

def set_marker_defaults(obj: Any) -> None:
    """Initialize marker options with their default values.
    
    Extracts default values from obj.options['html_display_options'] and
    applies them using set_marker_options().
    
    Args:
        obj: Object with 'options' attribute containing html_display_options.
    """
    marker_options_unified = obj.options.get('html_display_options', {}) or {}
    marker_options = {k: v.get('default') for k, v in marker_options_unified.items()}
    set_marker_options(obj, marker_options)

def set_marker_options(obj: Any, marker_options: dict) -> None:
    """Set marker option attributes on an object.
    
    Validates option names against expected marker options from
    obj.options['html_display_options'] and sets matching attributes.
    Logs warnings for unknown options or missing attributes.
    
    Args:
        obj: Object with 'options' attribute containing html_display_options.
        marker_options: Dict of marker option names to values.
    """
    marker_options_unified = obj.options.get('html_display_options', {}) or {}
    expected_keys = list(marker_options_unified.keys())
    for key, value in marker_options.items():
        if key in expected_keys:
            setattr(obj, key, value)
        else:
            _log.warning("Unknown marker option '%s' in defaults; ignoring.", key)
    for key in expected_keys:
        if not hasattr(obj, key):
            _log.warning("Marker option '%s' missing in defaults; setting to None.", key)
            setattr(obj, key, None)

def build_section_keys(options: dict, section_name: str) -> dict:
    """Build a mapping of option keys to types for a specific INI section.
    
    Scans all option sections in the configuration and extracts keys that
    belong to the specified INI section (via 'ini_section' property).
    
    Args:
        options: Options dictionary from YAML configuration.
        section_name: Name of INI section (e.g., 'Core', 'HTML', 'KML').
    
    Returns:
        dict: Mapping of option key names to their type strings.
              Uses 'ini_type' if specified, otherwise falls back to 'type'.
    """
    section_keys = {}
    for section in get_option_sections(options):
        opts = options.get(section, {})
        for key, props in opts.items():
            if isinstance(props, dict) and props.get('ini_section') == section_name:
                section_keys[key] = props.get('ini_type', props.get('type'))
    return section_keys

def loadsection(obj: Any, sectionName: str, keys: Optional[dict] = None) -> None:
    """Load settings from an INI section into object attributes.
    
    Reads values from obj.gvConfig[sectionName], coerces them to the
    specified types, and sets them as attributes on obj.
    
    Args:
        obj: Object with 'gvConfig' ConfigParser attribute.
        sectionName: Name of INI section to load from.
        keys: Optional dict mapping option names to type strings.
              If None, no values are loaded.
    """
    for key, typ in (keys or {}).items():
        value = obj.gvConfig[sectionName].get(key, None)
        if value is None:
            continue
        parsed = coerce_value_to_type(value, typ, context=f"{sectionName}.{key}")
        setattr(obj, key, parsed)

def loadsettings(obj: Any) -> None:
    """Load all settings from INI file into object.
    
    Comprehensive loading that:
    1. Reads INI file from obj.settingsfile
    2. Creates missing sections from INI_SECTIONS
    3. Loads option values for sections in INI_OPTION_SECTIONS
    4. Handles migration from old settings format
    5. Loads input/output file paths
    6. Loads file open commands
    7. Configures logger levels from [Logging] section
    
    Args:
        obj: Configuration object with attributes:
            - settingsfile: Path to INI file
            - options: YAML options dictionary
            - file_open_commands: FileOpenCommandLines instance
    
    Migration:
        If '_migration_version' is unset, removes deprecated settings
        listed in options['old_ini_settings'] and updates version.
    """
    obj.gvConfig = configparser.ConfigParser()
    obj.gvConfig.read(obj.settingsfile)
    for section in INI_SECTIONS:
        if section not in obj.gvConfig.sections():
            obj.gvConfig[section] = {}
        if section in INI_OPTION_SECTIONS:
            section_keys = build_section_keys(obj.options, section)
            loadsection(obj, section, section_keys)
    migration_version = obj.gvConfig['Core'].get('_migration_version', MIGRATION_VERSION_UNSET)
    if migration_version == MIGRATION_VERSION_UNSET:
        old_ini_settings = obj.options.get('old_ini_settings', {})
        for key, section in old_ini_settings.items():
            if obj.gvConfig.has_option(section, key):
                _log.info("Removing deprecated setting '%s' from section '%s'", key, section)
                obj.gvConfig.remove_option(section, key)
        obj.gvConfig['Core']['_migration_version'] = MIGRATION_VERSION_CURRENT
        try:
            with open(obj.settingsfile, 'w') as configfile:
                obj.gvConfig.write(configfile)
        except Exception as e:
            _log.error("Error saving migrated settings: %s", e)
    obj.setInput(obj.gvConfig['Core'].get('InputFile', ''), generalRequest=False)
    # Note: setInput already calls setResultsFile, so we don't need to call it again
    # The resultpath can be loaded from INI if saved separately
    obj.resultpath = os.path.split(obj.gvConfig['Core'].get('OutputFile', ''))[0]
    for file_type in obj.file_open_commands.list_file_types():
        cmd = obj.gvConfig['Core'].get(f'{file_type}cmdline', '')
        if cmd:
            obj.file_open_commands.add_file_type_command(file_type, cmd)
        else:
            cmd = obj.file_open_commands.get_command_for_file_type(file_type)
        setattr(obj, f'{file_type}cmdline', cmd)
    for itm, lvl in obj.gvConfig.items('Logging'):
        alogger = logging.getLogger(itm)
        if alogger:
            alogger.setLevel(lvl)

def savesettings(obj: Any) -> None:
    """Save all settings from object to INI file.
    
    Comprehensive saving that:
    1. Creates ConfigParser if needed with all INI_SECTIONS
    2. Saves option values for Core, HTML, Summary, and KML sections
    3. Saves input/output file paths to Core section
    4. Saves file open commands for all file types
    5. Saves main person ID to Gedcom.Main section (if set)
    6. Saves effective logger levels to Logging section
    7. Writes configuration to obj.settingsfile
    
    Args:
        obj: Configuration object with attributes:
            - gvConfig: ConfigParser instance (created if None)
            - settingsfile: Path to INI file
            - options: YAML options dictionary
            - file_open_commands: FileOpenCommandLines instance
            - GEDCOMinput: Input GEDCOM file path
            - Main: Main person object (optional)
            - resultpath: Results directory path
            - ResultFile: Results filename
    
    Note:
        Logs errors if saving fails. Only saves logger levels for
        loggers listed in options['logging_keys'].
    """
    try:
        if not obj.gvConfig:
            obj.gvConfig = configparser.ConfigParser()
            for section in INI_SECTIONS:
                obj.gvConfig[section] = {}
        core_keys = build_section_keys(obj.options, 'Core')
        for key in core_keys:
            obj.gvConfig['Core'][key] = str(getattr(obj, key))
        html_keys = build_section_keys(obj.options, 'HTML')
        for key in html_keys:
            obj.gvConfig['HTML'][key] =  str(getattr(obj, key))
        summary_keys = build_section_keys(obj.options, 'Summary')
        for key in summary_keys:
            obj.gvConfig['Summary'][key] = str(getattr(obj, key))
        kml_keys = build_section_keys(obj.options, 'KML')
        for key in kml_keys:
            obj.gvConfig['KML'][key] =  str(getattr(obj, key))
        obj.gvConfig['Core']['InputFile'] =  obj.GEDCOMinput
        obj.gvConfig['Core']['OutputFile'] = os.path.join(obj.resultpath, obj.ResultFile)
        for file_type in obj.file_open_commands.list_file_types():
            cmd = obj.file_open_commands.get_command_for_file_type(file_type)
            if cmd:
                obj.gvConfig['Core'][f'{file_type}cmdline'] = cmd
        if obj.GEDCOMinput and obj.Main:
            name = Path(obj.GEDCOMinput).stem
            obj.gvConfig[INI_SECTION_GEDCOM_MAIN][name] = str(obj.Main)
        loggerNames = list(logging.root.manager.loggerDict.keys())
        # Get logger names from logging_defaults (dict) or logging_keys (list) for backwards compatibility
        logging_defaults = obj.options.get('logging_defaults', {})
        logging_keys = list(logging_defaults.keys()) if logging_defaults else obj.options.get('logging_keys', [])
        for logName in loggerNames:
            if logName in logging_keys:
                logLevel = logging.getLevelName(logging.getLogger(logName).level)
                if logLevel == 'NOTSET':
                    obj.gvConfig.remove_option('Logging', logName)
                else:
                    obj.gvConfig['Logging'][logName] = logging.getLevelName(logging.getLogger(logName).getEffectiveLevel())
        with open(obj.settingsfile, 'w') as configfile:
            obj.gvConfig.write(configfile)
    except Exception as e:
        _log.error("Error saving settings to %s: %s", obj.settingsfile, e)
