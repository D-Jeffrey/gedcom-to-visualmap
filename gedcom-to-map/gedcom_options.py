"""gedcom_options.py

Configuration and runtime options for gedcom-to-visualmap.

Provides:
- ResultsType: typed enum of supported output types.
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
from datetime import datetime
import yaml
import re

from typing import Union, Dict, Optional
from enum import Enum
import configparser
from const import OFFICECMDLINE
from pathlib import Path
from models.Person import Person, LatLon, LifeEvent

_log = logging.getLogger(__name__)

def settings_file_pathname(file_name):
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
        _log.error (f"Unsupported operating system: {os_name}")
        return file_name
    Path(settings_file_path).mkdir(parents=True, exist_ok=True)
    settings_file_path = os.path.join(settings_file_path, file_name)
    
    _log.debug (f"Settings file location: {settings_file_path}")
    return settings_file_path
    
class ResultsType(Enum):
    HTML = "HTML"
    KML = "KML"
    KML2 = "KML2"
    SUM = "SUM"

    @staticmethod
    def ResultsTypeEnforce(value) -> "ResultsType":
        """Coerce a value to a ResultsType.

        Accepts an existing ResultsType or a string (case-insensitive). Raises
        TypeError/ValueError for unsupported values.
        """
        if isinstance(value, ResultsType):
            return value
        elif isinstance(value, str):
            # handle ResultsType like "ResultsType.HTML"
            m = re.match(r'^\s*ResultsType\.([A-Za-z_][A-Za-z0-9_]*)\s*$', value)
            if m:
                value = m.group(1)
            try:
                return ResultsType[value.upper()]
            except KeyError:
                raise ValueError(f"Invalid ResultsType string: {value}")
        else:
            raise TypeError(f"Cannot convert {type(value)} to ResultsType")
    
    def __str__(self) -> str:
        """Return the enum member's name value for human-readable display."""
        return self.value
    
    def long_name(self) -> str:
        """Return a long-form identifier for the ResultsType, e.g. 'ResultsType.HTML'."""
        
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
        return f"ResultsType.{name_str}"
    
    @staticmethod
    def list_values() -> list[str]:
        """Return a list of all ResultsType values as strings."""
        return [rt.value for rt in ResultsType]
    
    def index(self) -> int:
        """Return the integer index of a ResultsType value."""
        rt = ResultsType.ResultsTypeEnforce(self)
        return list(ResultsType).index(rt)

class gvOptions:
    """Application options and transient runtime state.

    Responsibilities:
    - Load option metadata and defaults from gedcom_options.yaml.
    - Provide get/set helpers used throughout the UI and background workers.
    - Persist lightweight settings to an INI-style file in a platform-appropriate location.
    - Maintain runtime counters/timestamps used for progress and ETA display.
    """
    GEDCOM_OPTIONS_FILE = 'gedcom_options.yaml'

    def __init__ (self):
        """Load static defaults, initialize runtime state and read persisted settings."""
        file_path = Path(__file__).parent / self.GEDCOM_OPTIONS_FILE
        with open(file_path, 'r') as file:
            self.options = yaml.safe_load(file)

        self.gvConfig = None
        self.set_marker_defaults()
        self.settingsfile = settings_file_pathname("gedcom-visualmap.ini")

        gedcom_options_types = self.options.get('gedcom_options_types', {})
        gedcom_options_defaults = self.options.get('gedcom_options_defaults', {})
        self.set_options(gedcom_options_types, gedcom_options_defaults)

        gui_options_types = self.options.get('gui_options_types', {})
        gui_options_defaults = self.options.get('gui_options_defaults', {})
        self.set_options(gui_options_types, gui_options_defaults)

        self.people: Union[Dict[str, Person], None] = None
        self.time = time.ctime()
        self.resettimeframe()
        
        os_name = platform.system()
        if os_name == 'Windows':
            self.KMLcmdline = "notepad $n"
            self.CSVcmdline = "$n"
            self.Tracecmdline = "notepad $n"
        
        elif os_name == 'Darwin':
            self.KMLcmdline = "Numbers $n"
            self.CSVcmdline = OFFICECMDLINE + " --calc $n"
            self.Tracecmdline = "Numbers $n"
        elif os_name == 'Linux':
            self.KMLcmdline = "nano $n"
            self.CSVcmdline = OFFICECMDLINE + " --calc $n"
            self.Tracecmdline = OFFICECMDLINE + " --calc $n"

        else:
            self.KMLcmdline = "notepad $n"
            self.CSVcmdline = "notepad $n"
            self.Tracecmdline = "notepad $n"

        if os.path.exists(self.settingsfile):
            self.loadsettings()            


    def set_options(self, options_types, options_defaults):
        """Apply parsed defaults into instance attributes with type coercion.

        Supports simple types (bool/int/str) and attempts to safely parse more
        complex YAML- or literal-encoded values for lists/dicts.
        """
        for key, typ in options_types.items():
            value = options_defaults.get(key, None)
            # Explicitly accept YAML null -> Python None as a valid value
            if value is None:
                setattr(self, key, None)
                continue
            try:
                # Accept native YAML types (bool/int/str) and fall back to parsing strings
                if typ == 'bool':
                    if isinstance(value, bool):
                        parsed = value
                    else:
                        parsed = str(value).strip().lower() in ('1', 'true', 'yes', 'on', 'y', 't')
                elif typ == 'int':
                    if isinstance(value, int):
                        parsed = value
                    else:
                        parsed = int(str(value).strip())
                elif typ == 'str':
                    parsed = str(value)
                elif typ == 'list' or typ == 'dict':
                    if isinstance(value, (list, dict)):
                        parsed = value
                elif typ == 'result':
                    parsed = ResultsType.ResultsTypeEnforce(value)
                # For complex types: if YAML already provided a list/dict/number, keep it;
                # if it's a string try safe eval via yaml (or fallback to literal eval)
                elif isinstance(value, (dict, list, int, float, bool)):
                    parsed = value
                elif isinstance(value, str):
                    try:
                        # try to parse structured literal using yaml (safe)
                        parsed = yaml.safe_load(value)
                    except Exception:
                        _log.error("YAML parsing failed for option '%s'; trying literal_eval", key)
                        # try:
                        #     # final fallback: evaluate simple Python literal
                        #     from ast import literal_eval
                        #     parsed = literal_eval(value)
                        # except Exception:
                        #     parsed = value
                else:
                    parsed = value

                setattr(self, key, parsed)
            except Exception as e:
                _log.error("Error setting option '%s' type %s: %s", key, typ, e)
                    
    def set_marker_defaults(self):
        """Load and apply marker-related defaults from the YAML options payload."""
        marker_options = self.options.get('marker_options_defaults', {}) or {}
        self.set_marker_options(marker_options)

    def set_marker_options(self, marker_options: dict):
        """Apply provided marker_options dict and ensure expected keys exist.

        Unknown keys are ignored with a warning; missing expected keys are set
        to None to ensure attributes are defined.
        """
        expected_keys = self.options.get('marker_options_list', []) or []
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
    
    def resettimeframe(self):
        """Reset the aggregated timeframe used when summarising people/events."""
        """ Reset the timeframe for the process """
        self.timeframe = {'from': None, 'to': None}

    def addtimereference(self, timeRefrence: LifeEvent):
        """Extend the global timeframe with a LifeEvent's year (if available)."""
        """ 
        Update the over all timeframe with person event details
        timeRefrence: LifeEvent
        """
        if not timeRefrence:
            return
        theyear = timeRefrence.whenyearnum()
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
                  Result: Optional[str],
                  ResultType: ResultsType,
                  Main: Optional[str] = None,
                  MaxMissing: int = 0,
                  MaxLineWeight: int = 20,
                  UseGPS: bool = True,
                  CacheOnly: bool = False,
                  AllEntities: bool = False):
        """Convenience setter for a typical group of static options used at startup."""
        self.setInput(GEDCOMinput)
        self.setResults(Result or "", ResultType)
        self.Main = Main
        self.Name = None
        self.MaxMissing = MaxMissing
        self.MaxLineWeight = MaxLineWeight
        self.UseGPS = UseGPS
        self.CacheOnly = CacheOnly
        self.AllEntities = AllEntities             # generte output of everyone in the system
        
    def loadsection(self, sectionName, keys=None):
        """Load and coerce a named section from the INI-style gvConfig into attributes."""
        import ast
        import re
        for key, typ in (keys or {}).items():
            value = self.gvConfig[sectionName].get(key, None)
            if value is None:
                continue
            try:
                if typ == 'bool':
                    setattr(self, key, str(value).strip().lower() == 'true')
                elif typ == 'int':
                    setattr(self, key, int(value))
                elif typ == 'str':
                    setattr(self, key, value)
                elif typ == 'result':
                    # handle ResultsType like "ResultsType.HTML"
                    m = re.match(r'^\s*ResultsType\.([A-Za-z_][A-Za-z0-9_]*)\s*$', value)
                    if m:
                        value = m.group(1)
                    try:
                        parsed = ResultsType.ResultsTypeEnforce(value)
                    except Exception:
                        _log("Invalid ResultsType string in settings for '%s': %s", key, value)
                else:
                    parsed = None
                    # try yaml first (handles lists/dicts/numbers/null)
                    try:
                        parsed_yaml = yaml.safe_load(value)
                    except Exception:
                        parsed_yaml = None

                    if parsed_yaml is not None and not isinstance(parsed_yaml, str):
                        parsed = parsed_yaml
                    else:
                        # handle LatLon(...) specifically
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
                                parsed = LatLon(vals[0], vals[1])
                            except Exception:
                                parsed = value
                        else:
                            # last resort: safe literal eval, otherwise keep string
                            try:
                                parsed = ast.literal_eval(value)
                            except Exception:
                                parsed = value

                    setattr(self, key, parsed)
            except Exception as e:
                _log.error("Error loading setting '%s' type %s in section %s: %s", key, typ, sectionName, e)

    def loadsettings(self):
        """Read persisted settings file and apply configured values into this instance."""
        self.gvConfig = configparser.ConfigParser()
        self.gvConfig.read(self.settingsfile)
        
        # Ensure all necessary sections exist
        for section in ['Core', 'HTML', 'Logging', 'Gedcom.Main', 'KML']:
            if section not in self.gvConfig.sections():
                self.gvConfig[section] = {}
            if section in ['Core', 'HTML', 'KML']:
                section_keys = self.options.get('config_file_settings', {}).get(f'{section}', {})
                self.loadsection(section, section_keys)
        
        self.setInput(self.gvConfig['Core'].get('InputFile', ''), generalRequest=False)
        self.resultpath, self.Result = os.path.split(self.gvConfig['Core'].get('OutputFile', ''))
        self.setResults(self.Result, self.ResultType)
        self.KMLcmdline = self.gvConfig['Core'].get('KMLcmdline', '')

        # Load logging settings
        for itm, lvl in self.gvConfig.items('Logging'):
            alogger = logging.getLogger(itm)
            if alogger:
                alogger.setLevel(lvl)

    def savesettings(self):
        """Persist selected options into the INI-style settings file.

        This writes only the configured keys and a small set of runtime values.
        """
        # Use this to remove old settings in sections

        try:
            if not self.gvConfig:
                self.gvConfig = configparser.ConfigParser()
                for section in ['Core', 'HTML', 'Logging', 'Gedcom.Main', 'KML']:
                    self.gvConfig[section] = {}
            core_keys = self.options.get('config_file_settings', {}).get('Core', {})
            for key in core_keys:
                self.gvConfig['Core'][key] = str(getattr(self, key))
            html_keys = self.options.get('config_file_settings', {}).get('HTML', {})
            for key in html_keys:
                self.gvConfig['HTML'][key] =  str(getattr(self, key))
            kml_keys = self.options.get('config_file_settings', {}).get('KML', {})
            for key in kml_keys:
                self.gvConfig['KML'][key] =  str(getattr(self, key))

            self.gvConfig['Core']['InputFile'] =  self.GEDCOMinput
            self.gvConfig['Core']['OutputFile'] = os.path.join(self.resultpath, self.Result)
            self.gvConfig['Core']['KMLcmdline'] =  self.KMLcmdline
            if self.GEDCOMinput and self.Main:
                name = Path(self.GEDCOMinput).stem
                self.gvConfig['Gedcom.Main'][name] = str(self.Main)
            #for key in range(0, self.panel.fileConfig.filehistory.GetCount()):
            #    self.gvConfig['Files'][key] = self.panel.fileConfig[key]
            
            loggerNames = list(logging.root.manager.loggerDict.keys())
            logging_keys = self.options.get('config_file_settings', {}).get('Logging', [])
            for logName in loggerNames:
                if logName in logging_keys:
                    logLevel = logging.getLevelName(logging.getLogger(logName).level)
                    if logLevel == 'NOTSET':
                        self.gvConfig.remove_option('Logging', logName)
                    else:
                        self.gvConfig['Logging'][logName] = logging.getLevelName(logging.getLogger(logName).getEffectiveLevel())
            old_settings = self.options.get('config_file_settings', {}).get('old_settings', {})
            for key, section  in old_settings.items():
                self.gvConfig.remove_option(section, key)
            with open(self.settingsfile, 'w') as configfile:
                self.gvConfig.write(configfile)

        except Exception as e:
            _log.error("Error saving settings to %s: %s", self.settingsfile, e)
    
    
    def setMainPerson(self, mainperson: Person):
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
            self.GridView = False

    def setMain(self, Main: str):
        """Set the Main identifier and select the corresponding Person if present."""
        self.Main = Main
        if self.people and Main in self.people:
            self.setMainPerson(self.people[Main])
        else:
            self.setMainPerson(None)

    def setResults(self, Result, OutputType):
        """Set the output filename (base) and enforce an extension based on OutputType."""
        enforced = ResultsType.ResultsTypeEnforce(OutputType)
        self.ResultType = enforced

        extension = "txt"
        if enforced is ResultsType.HTML:
            extension = "html"
        elif enforced is ResultsType.KML:
            extension = "kml"
        elif enforced is ResultsType.KML2:
            extension = "kml"
        elif enforced is ResultsType.SUM:
            extension = "txt"
        
        base, _ = os.path.splitext(Result or "")
        self.Result = base
        if self.Result:
            self.Result = self.Result + "." + extension
        # TODO Update Visual value

    def setInput(self, theInput, generalRequest=True):
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
            if self.gvConfig['Gedcom.Main'].get(name):
                self.setMain(self.gvConfig['Gedcom.Main'].get(name))
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
                self.setResults(filen, self.ResultType)
        else:
            self.resultpath = None
        if org != self.GEDCOMinput:
            self.parsed = False            

    def KeepGoing(self):
        """Return True if processing should continue (not stopping)."""
        return not self.ShouldStop()

    def ShouldStop(self):
        """Return True when a stop request has been issued."""
        return self.stopping

    def stopstep(self, state):
        """Record a stepping state for progress display and return True to continue."""
        """ Update the counter used to show progress to the end user """
        """ return true if we should stop stepping """
        self.state = state
            
        return True
    
    def stepCounter(self, newcounter):
        """Update the internal counter used for progress display."""
        """ Update the counter used to show progress to the end user """
        self.counter = newcounter

    def step(self, state = None, info=None, target=-1, resetCounter=True, plusStep=1):
        """Advance progress counters and optionally set a new target.

        When state is provided this marks the worker as running and optionally
        resets counters. Returns ShouldStop() so callers can respect stop requests.
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

    def stop(self):        
        """Request immediate stop and reset several runtime counters/flags."""
        self.running = False
        self.stopping = False
        time.sleep(.1)
        self.lastmax = self.counter
        self.time = time.ctime()
        self.counter = 0
        self.state = ""
        self.running = False        # Race conditions
        self.stopping = False

    def get (self, attribute, default=None, ifNone=None):
        """Safely access an attribute, returning default or ifNone when appropriate."""
        if ifNone is not None:
            val = getattr(self,attribute, default)
            if val == None:
                return ifNone
        return getattr(self,attribute, default)

    def set(self, attribute, value):
        """Set an existing attribute on the options object.

        Raises ValueError if the attribute does not exist. Special-cases 'Main'.
        """
        if not hasattr(self, attribute):
            _log.error(f'attempting to set an attribute : {attribute} which does not exist')
            raise ValueError(f'attempting to set an attribute : {attribute} which does not exist')
        if attribute == "Main":
            self.setMain(value)
        else:
            setattr (self, attribute, value)