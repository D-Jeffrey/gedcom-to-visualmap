__all__ = ['gvOptions']
from calendar import c
import logging
import os
import platform
import time

from typing import Union, Dict
from enum import Enum
import configparser
from const import OFFICECMDLINE
from pathlib import Path
from xmlrpc.client import boolean
from wx import LogGeneric
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
    def __init__ (self):

        self.gvConfig = None
        self.defaults()
        self.settingsfile = settings_file_pathname("gedcom-visualmap.ini")

        self.GEDCOMinput = "gedcomfile.ged"
        self.resultpath = None              # directory for .Result
        self.Result = ''                    # output file (could be of resulttype .html or .kml)
        self.ResultType : ResultsType = ResultsType.HTML
        self.Main = None                    # xref_id
        self.mainPerson = None               # point to Person
        self.Name = None                    # name of person
        self.mainPersonLatLon : LatLon = LatLon(None, None)
        self.MaxMissing = 0
        self.MaxLineWeight = 20
        self.UseGPS = True
        self.CacheOnly = False
        self.AllEntities = False
        self.GridView = False
        self.UseBalloonFlyto = True
        self.KMLsort = 1                  # 0 = none, 1 = folder
        self.badAge = True

        self.showLayerControl = True
        self.mapMini = True
        self.counter = 0
        self.countertarget = 0
        self.running = False
        self.runningLast = 0
        self.runningSince = 0
        self.time = time.ctime()
        self.parsed = False
        self.newload = False
        self.state = ''
        self.gpsfile = None
        self.stopping = False
        self.lookup = None
        self.totalpeople = None
        self.stepinfo = ''
        self.lastmax = self.counter
        self.people: Union[Dict[str, Person], None] = None
        self.Referenced = None
        self.panel = None
        self.selectedpeople = 0
        self.lastlines = None
        self.timeframe = {'from': None, 'to': None}
        self.runavg = []
        self.SummaryOpen = True
        self.SummaryPlaces = True
        self.SummaryPeople = True
        self.SummaryCountries = False
        self.SummaryCountriesGrid = True
        self.SummaryCountries = False
        self.SummaryGeocode = True
        self.SummaryAltPlaces = False
        

        self.skip_file_geocache = False
        self.skip_file_alt_places = False
        self.defaultCountry = None
        self.include_canonical = True
        
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

        self.heritage = None
        self.UpdateBackgroundEvent = None
        self.totalGEDpeople = None
        self.totalGEDfamily = None
        self.fileHistory = None

        # Types 0 - boolean, 1: int, 2: str, 3 : complex
        self.html_keys = {'MarksOn':0, 'HeatMap':0, 'BornMark':0, 'DieMark':0,  'MarkStarOn':0, 'GroupBy':1, 
                          'UseAntPath':0, 'MapTimeLine':0, 'HeatMapTimeStep':1, 'HomeMarker':0, 'showLayerControl':0, 
                          'mapMini':0, 'MapStyle':2}
        self.core_keys = {'UseGPS':0, 'CacheOnly':0, 'AllEntities':0, 'ResultType':3, 'KMLcmdline':2, 'CSVcmdline':2, 'Tracecmdline':2, 'badAge':0,
                        'SummaryPlaces':0, 'SummaryPeople':0, 'SummaryCountries':0, 'SummaryCountriesGrid':0, 
                        'SummaryCountries':0, 'SummaryGeocode':0, 'SummaryAltPlaces':0, 'SummaryOpen':0, 
                        'defaultCountry':2}
        self.logging_keys = ['models.person', 'models', 'ged4py.parser', 'ged4py', 'models.creator', 'models.location', 'gedcomoptions', 'gedcom.gedcomparser', 
                             'gedcom', 'gedcom.gedcom', 'gedcom.geocode','gedcom.geocache','gedcom.addressbook',
                             'geopy', 'render.kmlexporter', 'render', 'render.foliumexp', 'gedcomvisual', 'gedcomdialogs', 'gedcomvisualgui', '__main__']
        
        self.kml_keys = {'MaxLineWeight':1, 'MaxMissing':1, 'UseBalloonFlyto':0, 'KMLsort':0}
        # Old settings that should be removed from the config file
        self.oldsettings = {'native': 'KML', 'born': 'KML', 'death':'KML', 'PlaceType': 'KML', 'HeatMapTimeLine': 'HTML'}

        if os.path.exists(self.settingsfile):
            self.loadsettings()            


    def defaults(self):
        
        self.MarksOn = True
        self.HeatMap = False
        self.BornMark = True
        self.DieMark = True
        
        self.MarkStarOn = True
        self.GroupBy = 2
        self.UseAntPath = False
        self.MapTimeLine = False
        self.HeatMapTimeStep = 20
        self.HomeMarker = False
        self.MapStyle = "CartoDB.Voyager"

    def setmarkers (self, MarksOn = True, HeatMap = False, MarkStarOn = True, BornMark = True, DieMark = True, MapStyle = 3, GroupBy=2, UseAntPath=False, MapTimeLine=False, HeatMapTimeStep=1, HomeMarker=False):
        
        self.MarksOn = MarksOn
        self.HeatMap = HeatMap
        self.BornMark = BornMark
        self.DieMark = DieMark
        self.MapStyle = MapStyle
        self.MarkStarOn = MarkStarOn
        self.GroupBy = GroupBy
        self.UseAntPath = UseAntPath
        self.MapTimeLine = MapTimeLine
        self.HeatMapTimeStep = HeatMapTimeStep
        self.HomeMarker = HomeMarker
    

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

        
    def setstatic(self,  GEDCOMinput:2, Result:2, ResultType: ResultsType, Main=None, MaxMissing:1 = 0, MaxLineWeight:1 = 20, UseGPS:bool = True, CacheOnly:bool = False,  AllEntities:bool = False):
        
        self.setInput(GEDCOMinput)
        self.setResults(Result, ResultType)
        self.Main = Main
        self.Name = None
        self.MaxMissing = MaxMissing
        self.MaxLineWeight = MaxLineWeight
        self.UseGPS = UseGPS
        self.CacheOnly = CacheOnly
        self.AllEntities = AllEntities             # generte output of everyone in the system
        
    def loadsection(self, sectionName, keys=None):
        for key, typ in keys.items():
            value = self.gvConfig[sectionName].get(key, None)
            if value is not None:
                # Trap for manual editing of the configuration file
                try:
                    if typ == 0:  # Boolean
                        setattr(self, key, value.lower() == 'true')
                    elif typ == 1:  # int
                        setattr(self, key, int(value))
                    elif typ == 2:  # str
                        setattr(self, key, value)
                    else:  # complex
                        setattr(self, key, eval(value))
                except Exception as e:
                    _log.error(f"Error loading setting '{key}' type {typ} in section {sectionName}: {e}")
    def loadsettings(self):
        self.gvConfig = configparser.ConfigParser()
        self.gvConfig.read(self.settingsfile)
        
        # Ensure all necessary sections exist
        for section in ['Core', 'HTML', 'Logging', 'Gedcom.Main', 'KML']:
            if section not in self.gvConfig.sections():
                self.gvConfig[section] = {}
        # Load HTML settings
        self.loadsection('HTML', self.html_keys)
        # Load KML settings
        self.loadsection('KML', self.kml_keys)
        # Load Core settings
        self.loadsection('Core', self.core_keys)
        
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
            
        for key in self.core_keys:
            self.gvConfig['Core'][key] = str(getattr(self, key))
        for key in self.html_keys:
            self.gvConfig['HTML'][key] =  str(getattr(self, key))
            
        for key in self.kml_keys:
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
        for logName in loggerNames:
            if logName in self.logging_keys:
                logLevel = logging.getLevelName(logging.getLogger(logName).level)
                if logLevel == 'NOTSET':
                    self.gvConfig.remove_option('Logging', logName)
                else:
                    self.gvConfig['Logging'][logName] = logging.getLevelName(logging.getLogger(logName).getEffectiveLevel())
        for key, section  in self.oldsettings.items():
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

    def setResults(self, Result, OutputType: ResultsType):
        """ Set the Output file and type (Only the file name) """
        self.ResultType = ResultsType.ResultsTypeEnforce(OutputType)
        extension = "txt"
        if OutputType is ResultsType.HTML:
            extension = "html"
        elif OutputType is ResultsType.KML:
            extension = "kml"
        elif OutputType is ResultsType.KML2:
            extension = "kml"
        elif OutputType is ResultsType.SUM:
            extension = "txt"
        
        self.Result, e = os.path.splitext(Result)                   # output file (could be of resulttype .html or .kml)
        if self.Result != "":
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
            self.running = True
        else:
            self.counter += plusStep
            self.stepinfo = info
        if target>-1:
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


