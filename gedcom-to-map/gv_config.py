"""
GVConfig: Implements IConfig (configuration and file commands) for gedcom-to-visualmap.
"""
from typing import Union, Dict, Optional
from pathlib import Path
import os
import platform
import yaml
import logging
from const import GEO_CONFIG_FILENAME
from services import IConfig

_log = logging.getLogger(__name__)

def settings_file_pathname(file_name: str) -> str:
    os_name = platform.system()
    if os_name == 'Windows':
        settings_file_path = os.path.join(os.getenv('LOCALAPPDATA'), r'gedcomvisual')
    elif os_name == 'Darwin':
        settings_file_path = os.path.join(os.path.expanduser('~'), 'Library', 'Application Support')
    elif os_name == 'Linux':
        settings_file_path = os.path.join(os.path.expanduser('~'), '.config')
    else:
        _log.error("Unsupported operating system: %s", os_name)
        return file_name
    Path(settings_file_path).mkdir(parents=True, exist_ok=True)
    return os.path.join(settings_file_path, file_name)

class GVConfig(IConfig):

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
        self.setInput(GEDCOMinput)
        self.setResultsFile(ResultFile or "", ResultType)
        self.Main = Main
        self.Name = None
        self.MaxMissing = MaxMissing
        self.MaxLineWeight = MaxLineWeight
        self.UseGPS = UseGPS
        self.CacheOnly = CacheOnly
        self.AllEntities = AllEntities

    def resettimeframe(self) -> None:
        self.timeframe = {'from': None, 'to': None}

    def addtimereference(self, timeReference) -> None:
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

    def setMainPerson(self, mainperson) -> None:
        newMain = (getattr(self, 'mainPerson', None) != mainperson and mainperson and getattr(self, 'Name', None) != getattr(mainperson, 'name', None)) or mainperson is None
        self.mainPerson = mainperson
        if mainperson:
            self.Name = mainperson.name
            if hasattr(mainperson, 'bestLatLon'):
                self.mainPersonLatLon = mainperson.bestLatLon()
            else:
                self.mainPersonLatLon = None
        else:
            self.Name = "<not selected>"
            self.mainPersonLatLon = None
        if newMain:
            self.selectedpeople = 0
            self.lastlines = None
            self.heritage = None
            self.Referenced = None

    def setMain(self, Main: str) -> None:
        self.Main = Main
        if hasattr(self, 'people') and self.people and Main in self.people:
            self.setMainPerson(self.people[Main])
        else:
            self.setMainPerson(None)

    def setResultsFile(self, ResultFile: str, OutputType) -> None:
        from const import ResultType
        enforced = ResultType.ResultTypeEnforce(OutputType)
        self.ResultType = enforced
        extension = ResultType.file_extension(enforced)
        base, _ = os.path.splitext(os.path.basename(ResultFile or ""))
        self.ResultFile = base
        if self.ResultFile:
            self.ResultFile = self.ResultFile + "." + extension

    def setInput(self, theInput: Optional[str], generalRequest: bool = True) -> None:
        org = getattr(self, 'GEDCOMinput', None)
        if hasattr(self, 'gvConfig') and self.gvConfig and generalRequest and org:
            if org != theInput:
                self.savesettings()
        self.GEDCOMinput = theInput
        if hasattr(self, 'gvConfig') and self.gvConfig and self.GEDCOMinput:
            from const import INI_SECTION_GEDCOM_MAIN
            name = Path(self.GEDCOMinput).stem
            if self.gvConfig[INI_SECTION_GEDCOM_MAIN].get(name):
                self.setMain(self.gvConfig[INI_SECTION_GEDCOM_MAIN].get(name))
            else:
                self.setMain(None)
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

        def loadsection(self, sectionName: str, keys: Optional[dict] = None) -> None:
            import configparser
            for key, typ in (keys or {}).items():
                value = self.gvConfig[sectionName].get(key, None)
                if value is None:
                    continue
                parsed = self._coerce_value_to_type(value, typ, context=f"{sectionName}.{key}")
                setattr(self, key, parsed)

        def loadsettings(self) -> None:
            import configparser
            from const import INI_SECTIONS, INI_OPTION_SECTIONS, MIGRATION_VERSION_UNSET, MIGRATION_VERSION_CURRENT
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
            # File open commands and logging settings omitted for brevity, add as needed

        def savesettings(self) -> None:
            import configparser
            from const import INI_SECTIONS
            try:
                if not hasattr(self, 'gvConfig') or not self.gvConfig:
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
                self.gvConfig['Core']['InputFile'] =  getattr(self, 'GEDCOMinput', '')
                self.gvConfig['Core']['OutputFile'] = os.path.join(getattr(self, 'resultpath', ''), getattr(self, 'ResultFile', ''))
                # File open commands and logging settings omitted for brevity, add as needed
                with open(self.settingsfile, 'w') as configfile:
                    self.gvConfig.write(configfile)
            except Exception as e:
                _log.error("Error saving settings to %s: %s", self.settingsfile, e)
    """Configuration service for gedcom-to-visualmap."""
    GEDCOM_OPTIONS_FILE = 'gedcom_options.yaml'
    def __init__(self):
        file_path = Path(__file__).parent / self.GEDCOM_OPTIONS_FILE
        with open(file_path, 'r') as file:
            self.options = yaml.safe_load(file)
        self.settingsfile = settings_file_pathname("gedcom-visualmap.ini")
        self.geo_config_file: Path = Path(__file__).resolve().parent / GEO_CONFIG_FILENAME
        # ...initialize config, load defaults, file commands, etc...

    def _coerce_value_to_type(self, value, target_type, context=None):
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
        sections = []
        for key, value in self.options.items():
            if isinstance(value, dict) and any(
                isinstance(v, dict) and 'type' in v and 'default' in v 
                for v in value.values()
            ):
                sections.append(key)
        return sections

    def set_options(self, options_types: dict, options_defaults: dict) -> None:
        for key, typ in options_types.items():
            value = options_defaults.get(key, None)
            parsed = self._coerce_value_to_type(value, typ, context=f"option '{key}'")
            setattr(self, key, parsed)

    def set_marker_defaults(self) -> None:
        marker_options_unified = self.options.get('marker_options', {}) or {}
        marker_options = {k: v.get('default') for k, v in marker_options_unified.items()}
        self.set_marker_options(marker_options)

    def set_marker_options(self, marker_options: dict) -> None:
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

    def _build_section_keys(self, section_name: str) -> dict:
        section_keys = {}
        for section in self._get_option_sections():
            opts = self.options.get(section, {})
            for key, props in opts.items():
                if isinstance(props, dict) and props.get('ini_section') == section_name:
                    section_keys[key] = props.get('ini_type', props.get('type'))
        return section_keys

    def get(self, attribute: str, default=None, ifNone=None):
        if attribute == 'resultpath':
            if getattr(self, 'GEDCOMinput', None):
                ged_dir = os.path.dirname(self.GEDCOMinput)
                return ged_dir if ged_dir else default
            val = getattr(self, attribute, None)
            return val if val else default
        if ifNone is not None:
            val = getattr(self, attribute, default)
            if val == None:
                return ifNone
        return getattr(self, attribute, default)

    def set(self, attribute: str, value) -> None:
        if not hasattr(self, attribute):
            raise ValueError(f'attempting to set an attribute : {attribute} which does not exist')
        if attribute == "Main":
            self.setMain(value)
        else:
            setattr(self, attribute, value)
