__all__ = ['gvOptions']
import logging
import os
import platform
import time
from datetime import datetime
import yaml

from typing import Union, Dict, Optional
from enum import Enum
import configparser
from const import OFFICECMDLINE
from pathlib import Path
from models.Person import Person, LatLon, LifeEvent

_log = logging.getLogger(__name__)

def settings_file_pathname(file_name):
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
    def ResultsTypeEnforce(value):
        if isinstance(value, ResultsType):
            return value
        elif isinstance(value, str):
            try:
                return ResultsType[value.upper()]
            except KeyError:
                raise ValueError(f"Invalid ResultsType string: {value}")
        else:
            raise TypeError(f"Cannot convert {type(value)} to ResultsType")

class gvOptions:
    GEDCOM_OPTIONS_FILE = 'gedcom_options.yaml'

    def __init__ (self):
        file_path = Path(__file__).parent / self.GEDCOM_OPTIONS_FILE
        with open(file_path, 'r') as file:
            self.options = yaml.safe_load(file)

        self.gvConfig = None
        self.set_marker_defaults()
        self.settingsfile = settings_file_pathname("gedcom-visualmap.ini")

        gedcom_options_types = self.options.get('gedcom_options_types', {})
        gedcom_options_defaults = self.options.get('gedcom_options_defaults', {})
        self.set_options(gedcom_options_types, gedcom_options_defaults)

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
                else:
                    # For complex types: if YAML already provided a list/dict/number, keep it;
                    # if it's a string try safe eval via yaml (or fallback to literal eval)
                    if isinstance(value, (dict, list, int, float, bool)):
                        parsed = value
                    elif isinstance(value, str):
                        try:
                            # try to parse structured literal using yaml (safe)
                            parsed = yaml.safe_load(value)
                        except Exception:
                            try:
                                # final fallback: evaluate simple Python literal
                                from ast import literal_eval
                                parsed = literal_eval(value)
                            except Exception:
                                parsed = value
                    else:
                        parsed = value

                setattr(self, key, parsed)
            except Exception as e:
                _log.error("Error setting option '%s' type %s: %s", key, typ, e)
                    
    def set_marker_defaults(self):
        marker_options = self.options.get('marker_options_defaults', {}) or {}
        self.set_marker_options(marker_options)

    def set_marker_options(self, marker_options: dict):
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
        """ Reset the timeframe for the process """
        self.timeframe = {'from': None, 'to': None}

    def addtimereference(self, timeRefrence: LifeEvent):
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
                        # handle ResultsType like "ResultsType.HTML"
                        m = re.match(r'^\s*ResultsType\.([A-Za-z_][A-Za-z0-9_]*)\s*$', value)
                        if m:
                            try:
                                parsed = ResultsType.ResultsTypeEnforce(m.group(1))
                            except Exception:
                                parsed = value
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
        # Use this to remove old settings in sections

        
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
    
    
    def setMainPerson(self, mainperson: Person):
        """ Set the name of the starting person """
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
        self.Main = Main
        if self.people and Main in self.people:
            self.setMainPerson(self.people[Main])
        else:
            self.setMainPerson(None)

    def setResults(self, Result, OutputType):
        """ Set the Output file and type (Only the file name) """
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
        """ Set the input file, update output file """
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
        return not self.ShouldStop()

    def ShouldStop(self):
        return self.stopping

    def stopstep(self, state):
        """ Update the counter used to show progress to the end user """
        """ return true if we should stop stepping """
        self.state = state
            
        return True
    
    def stepCounter(self, newcounter):
        """ Update the counter used to show progress to the end user """
        self.counter = newcounter

    def step(self, state = None, info=None, target=-1, resetCounter=True, plusStep=1):
        """ Update the counter used to show progress to the end user """
        """ return true if we should stop stepping """
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
        """ check an gOp attribute """
        if ifNone is not None:
            val = getattr(self,attribute, default)
            if val == None:
                return ifNone
        return getattr(self,attribute, default)

    def set(self, attribute, value):
        """ set an gOp attribute """
        if not hasattr(self, attribute):
            _log.error(f'attempting to set an attribute : {attribute} which does not exist')
            raise ValueError(f'attempting to set an attribute : {attribute} which does not exist')
        if attribute == "Main":
            self.setMain(value)
        else:
            setattr (self, attribute, value)