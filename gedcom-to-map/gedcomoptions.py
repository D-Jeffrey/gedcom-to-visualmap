__all__ = ['gvOptions']
from calendar import c
import logging
import os
import platform
import time

import configparser
from pathlib import Path
from xmlrpc.client import boolean
from wx import LogGeneric
from models.Human import Human, Pos


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
    
AllPlaceType = ['native','born','death']

class gvOptions:
    def __init__ (self):

        self.gvConfig = None
        self.defaults()
        self.settingsfile = settings_file_pathname("gedcom-visualmap.ini")

        self.GEDCOMinput = None
        self.resultpath = None              # directory for .Result
        self.Result = ''                    # output file (could be of resulttype .html or .kml)
        self.ResultType = "html"
        self.ResultHTML = True
        self.Main = None                    # xref_id
        self.mainHuman = None               # point to Human
        self.Name = None                    # name of human
        self.mainHumanPos = Pos(None, None)
        self.MaxMissing = 0
        self.MaxLineWeight = 20
        self.UseGPS = True
        self.CacheOnly = False
        self.AllEntities = False
        self.PlaceType = {'native':'native'}        # Dict add/replace with multiple 'native', 'born' & 'death'
        self.GridView = False

        self.showLayerControl = True
        self.mapMini = True
        self.counter = 0
        self.countertarget = 0
        self.running = False
        self.runningLast = 0
        self.runingSince = 0
        self.time = time.ctime()
        self.parsed = False
        self.goodmain = False
        self.state = ''
        self.gpsfile = None
        self.stopping = False
        self.lookup = None
        self.totalpeople = None
        self.stepinfo = ''
        self.lastmax = self.counter
        self.humans = None
        self.Referenced = None
        self.panel = None
        self.selectedpeople = 0
        self.lastlines = None
        self.KMLcmdline = "notepad $n"
        self.BackgroundProcess = None     # Background Thread for processing set later
        self.heritage = None

        # Types 0 - boolean, 1: int, 2: str
        self.html_keys = {'MarksOn':0, 'HeatMap':0, 'BornMark':0, 'DieMark':0, 'MapStyle':1, 'MarkStarOn':0, 'GroupBy':1, 
                          'UseAntPath':0, 'HeatMapTimeLine':0, 'HeatMapTimeStep':1, 'HomeMarker':0, 'showLayerControl':0, 
                          'mapMini':0}
        self.core_keys = {'UseGPS':0, 'CacheOnly':0, 'AllEntities':0, 'KMLcmdline':''}
        self.logging_keys = ['gedcomvisualgui', 'gedcom.gpslookup', 'ged4py.parser', '__main__', 'gedcomoptions','models.Human','models.Creator','render.foiumExp']
        
        if os.path.exists(self.settingsfile):
            self.loadsettings()            

    def defaults(self):
        
        self.MarksOn = True
        self.HeatMap = False
        self.BornMark = True
        self.DieMark = True
        self.MapStyle = 3
        self.MarkStarOn = True
        self.GroupBy = 2
        self.UseAntPath = False
        self.HeatMapTimeLine = False
        self.HeatMapTimeStep = 10
        self.HomeMarker = False

    def setmarkers (self, MarksOn = True, HeatMap = False, MarkStarOn = True, BornMark = True, DieMark = True, MapStyle = 3, GroupBy=2, UseAntPath=False, HeatMapTimeLine=False, HeatMapTimeStep=1, HomeMarker=False):
        
        self.MarksOn = MarksOn
        self.HeatMap = HeatMap
        self.BornMark = BornMark
        self.DieMark = DieMark
        self.MapStyle = MapStyle
        self.MarkStarOn = MarkStarOn
        self.GroupBy = GroupBy
        self.UseAntPath = UseAntPath
        self.HeatMapTimeLine = HeatMapTimeLine
        self.HeatMapTimeStep = HeatMapTimeStep
        self.HomeMarker = HomeMarker
    



        
    def setstatic(self,  GEDCOMinput:2, Result:2, ResultHTML: bool, Main=None, MaxMissing:1 = 0, MaxLineWeight:1 = 20, UseGPS:bool = True, CacheOnly:bool = False,  AllEntities:bool = False, PlaceType = {'native':'native'}):
        
        self.setInput(GEDCOMinput)
        self.setResults(Result, ResultHTML)
        self.Main = Main
        self.Name = None
        self.MaxMissing = MaxMissing
        self.MaxLineWeight = MaxLineWeight
        self.UseGPS = UseGPS
        self.CacheOnly = CacheOnly
        self.AllEntities = AllEntities             # generte output of everyone in the system
        self.PlaceType = PlaceType                 # Dict add/replace with multiple 'native', 'born' & 'death'

                    
    def loadsettings(self):
        self.gvConfig = configparser.ConfigParser()
        self.gvConfig.read(self.settingsfile)
        
        # Ensure all necessary sections exist
        for section in ['Core', 'HTML', 'Logging', 'Gedcom.Main', 'KML']:
            if section not in self.gvConfig.sections():
                self.gvConfig[section] = {}
        
        # Load HTML settings
        for key, typ in self.html_keys.items():
            value = self.gvConfig['HTML'].get(key, None)
            if value is not None:
                if typ == 0:  # Boolean
                    setattr(self, key, value.lower() == 'true')
                elif typ == 1:  # int
                    setattr(self, key, int(value))
                else:  # str
                    setattr(self, key, value)
        
        # Load Core settings
        for key, typ in self.core_keys.items():
            value = self.gvConfig['Core'].get(key, None)
            if value is not None:
                if typ == 0:  # Boolean
                    setattr(self, key, value.lower() == 'true')
                elif typ == 1:  # int
                    setattr(self, key, int(value))
                else:  # str
                    setattr(self, key, value)
        
        self.setInput(self.gvConfig['Core'].get('InputFile', ''), generalRequest=False)
        self.resultpath, self.Result = os.path.split(self.gvConfig['Core'].get('OutputFile', ''))
        self.setResults(self.Result, not ('.kml' in self.Result.lower()))
        self.KMLcmdline = self.gvConfig['Core'].get('KMLcmdline', '')
        self.PlaceType = []
        for key in AllPlaceType:
            if self.gvConfig['KML'][key].lower() == 'true':
                self.PlaceType.append(key)

        # Load logging settings
        for itm, lvl in self.gvConfig.items('Logging'):
            alogger = logging.getLogger(itm)
            if alogger:
                alogger.setLevel(lvl)
               
    def savesettings(self):
        if not self.gvConfig:
            self.gvConfig = configparser.ConfigParser()
            for section in ['Core', 'HTML', 'Logging', 'Gedcom.Main', 'KML']:
                self.gvConfig[section] = {}
            
        for key in self.core_keys:
            self.gvConfig['Core'][key] = str(getattr(self, key))
        for key in self.html_keys:
            self.gvConfig['HTML'][key] =  str(getattr(self, key))
            
        for key in AllPlaceType:
            self.gvConfig['KML'][key] =  str(key in self.PlaceType)
            
        self.gvConfig['Core']['InputFile'] =  self.GEDCOMinput
        self.gvConfig['Core']['OutputFile'] = os.path.join(self.resultpath, self.Result)
        self.gvConfig['Core']['KMLcmdline'] =  self.KMLcmdline
        if self.GEDCOMinput and self.Main:
            name = Path(self.GEDCOMinput).stem
            self.gvConfig['Gedcom.Main'][name] = str(self.Main)
        for key in self.logging_keys:
            self.gvConfig['Logging'][key] = logging.getLevelName(logging.getLogger(key).getEffectiveLevel())
        with open(self.settingsfile, 'w') as configfile:
            self.gvConfig.write(configfile)
    
    
    def setMainHuman(self, mainhuman: Human):
        """ Set the name of the starting person """
        self.mainHuman = mainhuman 
        if mainhuman:
            self.Name = mainhuman.name
            self.mainHumanPos = mainhuman.bestPos()
        else:
            self.Name = "<not selected>"
            self.mainHumanPos = None
         
        self.selectedpeople = 0
        self.lastlines = None
        self.heritage = None
        self.Referenced = None
        self.GridView = False

    def setMain(self, Main: str):
        self.Main = Main
        if self.humans and Main in self.humans:
            self.setMainHuman(self.humans[Main])
        else:
            self.setMainHuman(None)

    def setResults(self, Result, useHTML):
        """ Set the Output file and type (Only the file name) """
        self.ResultHTML = useHTML
        if (useHTML):
            self.ResultType = "html"
        else:
            self.ResultType = "kml"
        self.Result, extension = os.path.splitext(Result)                   # output file (could be of resulttype .html or .kml)
        if self.Result != "":
            self.Result = self.Result + "." + self.ResultType
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
                self.setResults(filen, self.ResultHTML)
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
    
    def step(self, state = None, info=None, target=-1, resetCounter=True):
        """ Update the counter used to show progress to the end user """
        """ return true if we should stop stepping """
        if state:
            self.state = state
            if resetCounter:
                self.counter = 0
            self.running = True
        else:
            self.counter += 1
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

    def get (self, attribute):
        """ check an gOptions attribute """
        return getattr(self,attribute)

    def set(self, attribute, value):
        """ set an gOptions attribute """
        if not hasattr(self, attribute):
            _log.error(f'attempting to set an attribute : {attribute} which does not exist')
            raise ValueError(f'attempting to set an attribute : {attribute} which does not exist')
        if attribute == "Main":
            self.setMain(value)
        else:
            setattr (self, attribute, value)


