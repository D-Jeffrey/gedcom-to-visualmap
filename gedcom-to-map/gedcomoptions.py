import os
import time

class gvOptions:
    def __init__ (self, MarksOn = True, HeatMap = True, MarkStarOn = True, BornMark = False, DieMark = True, MapStyle = 3, GroupBy=0, AntPath=True, HeatMapTimeLine=False, HeatMapTimeStep=1, HomeMarker=False):

        self.MarksOn = MarksOn
        self.HeatMap = HeatMap
        self.BornMark = BornMark
        self.DieMark = DieMark
        self.MapStyle = MapStyle
        self.MarkStarOn = MarkStarOn
        self.GroupBy = GroupBy
        self.UseAntPath = AntPath
        self.HeatMapTimeLine = HeatMapTimeLine
        self.HeatMapTimeStep = HeatMapTimeStep
        self.HomeMarker = HomeMarker

        self.GEDCOMinput= None
        self.Result = None      # output file (could be of resulttype .html or .kml)
        self.ResultType = "html"
        self.ResultHTML = True
        self.Main = None
        self.Name = None
        self.MaxMissing = 0
        self.MaxLineWeight = 20
        self.UseGPS = True
        self.CacheOnly = False
        self.AllEntities = False
        self.PlaceType = {'native':'native'}        # Dict add/replace with multiple 'native', 'born' & 'death'
        
        self.showLayerControl = True
        self.mapMini = True
        self.counter = 0
        self.running = False
        self.commandline = False
        self.time = time.ctime()
        self.parsed = False
        self.goodmain = False
        self.state = ''
        self.gpsfile = None
        self.stopping = False
        self.lookup = None
        self.totalpeople = None
        
        
        
            # HKEY_LOCAL_MACHINE\SOFTWARE\Classes\.csv
            # HKEY_LOCAL_MACHINE\SOFTWARE\Classes\.csv\Content Type
            #   HKEY_CLASSES_ROOT\CLSID\{5e941d80-bf96-11cd-b579-08002b30bfeb}
            # HKEY_CLASSES_ROOT\MIME\Database\Content Type\application/vnd.ms-excel
            # HKEY_CLASSES_ROOT\Excel.CSV\shell\Open\command

        self.csvprogram = '"C:\Program Files\Microsoft Office\Root\Office16\EXCEL.EXE"'

    def setstatic(self,  GEDCOMinput:str, Result:str, ResultHTML: bool, Main=None, MaxMissing:int = 0, MaxLineWeight:int = 20, UseGPS:bool = True, CacheOnly:bool = False,  AllEntities:bool = False, PlaceType = {'native':'native'}):
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
                
        
        
    def setMainName(self, name):
        """ Set the name of the starting person """
        self.Name = name

    def setResults(self, Result, isResultHTML):
        """ Set the Results Output file and type """
        self.Result = Result                  # output file (could be of resulttype .html or .kml)
        self.ResultHTML = isResultHTML
        if (isResultHTML):
            self.ResultType = "html"
        else:
            self.ResultType = "kml"
        pathname, extension = os.path.splitext(self.Result)
        if extension == "" and self.Result != "":
           self.Result = self.Result + "." + self.ResultType

    def setInput(self, GEDCOMinput):
        """ Set the Results Output file and type """
        org = self.GEDCOMinput
        self.GEDCOMinput= GEDCOMinput

        pathname, extension = os.path.splitext(self.GEDCOMinput)
        if extension == "" and self.GEDCOMinput != "":
           self.GEDCOMinput = self.GEDCOMinput + ".ged"
        if org != self.GEDCOMinput:
            self.parsed = False

    def KeepGoing(self):
        return not self.ShouldStop()

    def ShouldStop(self):
        return self.stopping

    def step(self, state = None):
        if state:
            self.state = state
            self.counter = 0
        else:
            self.counter = self.counter+1
        self.running = True
        return self.ShouldStop()
                
        
    def stop(self):        
        self.lastmax = self.counter
        self.time = time.ctime()
        self.counter = 0
        self.running = False
        self.state = ""
        self.stopping = False

    def get (self, attribute):
        return getattr(self,attribute)

    def set(self, attribute, value):
        if not hasattr(self, attribute):
            raise ValueError(f'attempting to set an attribute : {attribute} which does not exist')
        setattr (self, attribute, value)
        
             
