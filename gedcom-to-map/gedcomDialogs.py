__all__ = ['AboutDialog', 'ConfigDialog', 'PersonDialog', 'FindDialog', 'BackgroundActions', 'formatHumanName']

import _thread
import logging
import logging.config
import time

import wx
import wx.lib.newevent
import wx.html
import wx.grid as gridlib
from models.Creator import Human, Pos, LifeEvent

from const import GVFONT, ABOUTFONT, VERSION, GUINAME, ABOUTLINK, NAME
# from gedcomoptions import gvOptions, AllPlaceType
from gedcomvisual import ParseAndGPS, doHTML, doKML, doTraceTo
# import gedcom.gpslookup 

_log = logging.getLogger(__name__)

global BackgroundProcess, panel
BackgroundProcess = None
panel = None
UpdateBackgroundEvent = None

class AboutDialog(wx.Dialog):
    def __init__(self, parent, title):
        super(AboutDialog, self).__init__(parent, title=title, size=(ABOUTFONT[1]*55, ABOUTFONT[1]*45))

        self.icon = wx.ArtProvider.GetBitmap(wx.ART_INFORMATION, wx.ART_OTHER, (32, 32))
        self.icon_ctrl = wx.StaticBitmap(self, bitmap=self.icon)
        self.html = wx.html.HtmlWindow(self)
        self.html.SetFonts(ABOUTFONT[0], ABOUTFONT[0], [ABOUTFONT[1]] * 7)  # Set font-family to Garamond and font-size to 6 points
        self.html.SetPage("""
        <html><body>
<h2><a href="PROJECTLINK">VERVER</a></h2>
<p>The "GEDCOM to Visual Map" project is a powerful tool designed to read <a href="https://en.wikipedia.org/wiki/GEDCOM">GEDCOM files</a> and translate the locations into GPS addresses. It produces different KML map types that show timelines and movements around the earth. The project includes both command-line and GUI interfaces (tested on Windows) to provide flexibility in usage.</p>
<h3>Key Features:</h3>
<ul><li><b>Interactive Maps:</b> Generates interactive HTML files that display relationships between children and parents, and where people lived over the years.</li>
<li><b>Heatmaps:</b> Includes heatmaps to show busier places, with markers overlayed for detailed views.</li>
<li><b>Geocoding:</b> Converts place names into GPS coordinates, allowing for accurate mapping.</li>
<li><b>Multiple Output Formats:</b> Supports both <a href="https://python-visualization.github.io/folium/latest/">HTML</a> and <a href="https://support.google.com/earth/answer/7365595">KML</a> output formats for versatile map visualization.</li>
<li><b>User-Friendly GUI:</b> The GUI version allows users to easily load GEDCOM files, set options, and generate maps with a few clicks.</li>
<li><b>Customizable Options:</b> Offers various options to customize the map, such as grouping by family name, turning on/off markers, and adjusting heatmap settings.</li>
</ul>
<h3>Things to know</h3>
<ul><li><b>Right-click:</b> Right-click on (Activate) a person in the list to view more details.</li>
<li><b>Double-click</b> Double-click on a person in the list to set them as the main person and find all their associcated parents</li>
<li><b>Trace</b> For the selected person save to a text file all the associcated parents(tab seperated)</li>
<li><b>Geo Table</b> Edit the file and translates so that next time it does better location lookups by putting replacement values in the 'alt' column or by filling in the 'Country', 
then blank the lat, long and boundary have it looked up again. Do not convert it to another format and close Excel so the file can be access.</li>
<li><b>Logging Options</b> Can be updated while the application is loading or resolves addresses.</li>
<li><b>Relatives</b> Can Activate a person and the bring up the Person and if they are in a direct line, it will list the father & mother trace.</li>                          
</ul>                          
<h3>Additional Information:</h3>
<ul><li><b>Forked From:</b> Originally forked from <a href="https://github.com/lmallez/gedcom-to-map/">gedcom-to-map.</a></li>
<li><b>License:</b> MIT License.</li>
</ul>
For more details and to contribute, visit the <a href="PROJECTLINK">GitHub repository.</a></li>
<p>

</p>
</body></html>
        """.replace('VERVER', f"{GUINAME} {VERSION}").replace('PROJECTLINK', f"{ABOUTLINK}{NAME}"))

        self.okButton = wx.Button(self, wx.ID_OK, "OK")
        self.okButton.Bind(wx.EVT_BUTTON, self.on_ok)

        sizer = wx.BoxSizer(wx.VERTICAL)
        icon_sizer = wx.BoxSizer(wx.HORIZONTAL)

        icon_sizer.Add(self.icon_ctrl, 0, wx.ALL, 10)
        icon_sizer.Add(self.html, 1, wx.EXPAND | wx.ALL, 7)
        
        sizer.Add(icon_sizer, 1, wx.EXPAND)
        sizer.Add(self.okButton, 0, wx.ALIGN_CENTER | wx.ALL, 5)

        self.SetSizer(sizer)

        self.Bind(wx.html.EVT_HTML_LINK_CLICKED, self.on_link_clicked, self.html)

    def on_link_clicked(self, event):
        wx.LaunchDefaultBrowser(event.GetLinkInfo().GetHref())

    def on_ok(self, event):
        self.Destroy()
#==============================================================
class ConfigDialog(wx.Frame):
    def __init__(self, parent, title):
        super(ConfigDialog, self).__init__(parent, title=title, size=(500, 650))

        includeNOTSET = False               # DEFAULT Disabled with False
        self.loggerNames = list(logging.root.manager.loggerDict.keys())
        cfgpanel = wx.Panel(self,style=wx.SIMPLE_BORDER  )
        TEXTkmlcmdlinelbl = wx.StaticText(cfgpanel, -1,  " KML Editor Command line:   ") 
        self.TEXTkmlcmdline = wx.TextCtrl(cfgpanel, wx.ID_FILE1, "", size=(250,20))
        if panel.gO.KMLcmdline:
            self.TEXTkmlcmdline.SetValue(panel.gO.KMLcmdline)
        TEXTcsvcmdlinelbl = wx.StaticText(cfgpanel, -1,  " CSV Table Editor Command line:   ") 
        self.TEXTcsvcmdline = wx.TextCtrl(cfgpanel, wx.ID_FILE1, "", size=(250,20))
        if panel.gO.CSVcmdline:
            self.TEXTcsvcmdline.SetValue(panel.gO.CSVcmdline)            
        GRIDctl = gridlib.Grid(cfgpanel)
        if includeNOTSET:
            gridlen = len(logging.root.manager.loggerDict)
        else:
            gridlen =  sum(1 for erow, loggerName in enumerate(self.loggerNames) if logging.getLogger(loggerName).level != 0)     # Hack NOTSET

        GRIDctl.CreateGrid(gridlen, 2)
        GRIDctl.SetColLabelValue(0, "Logger Name")
        GRIDctl.SetColLabelValue(1, "Log Level")

        self.logging_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        row = 0
        for erow, loggerName in enumerate(self.loggerNames):
            _log = logging.getLogger(loggerName)
            if logging.getLevelName(_log.level) != "NOTSET":
                GRIDctl.SetCellValue(row, 0, loggerName)
                GRIDctl.SetCellBackgroundColour(row, 0, wx.LIGHT_GREY)
                GRIDctl.SetCellValue(row, 1, logging.getLevelName(_log.level))
                GRIDctl.SetCellEditor(row, 1, gridlib.GridCellChoiceEditor(self.logging_levels))
                GRIDctl.SetReadOnly(row, 0)
                row += 1
        # The following only is relavent for modules that could have `logging`` added to them
        if includeNOTSET:
            for erow, loggerName in enumerate(self.loggerNames):
                _log = logging.getLogger(loggerName)
                if logging.getLevelName(_log.level) == "NOTSET":
                    GRIDctl.SetCellValue(row, 0, loggerName)
                    GRIDctl.SetCellValue(row, 1, logging.getLevelName(_log.level))
                    GRIDctl.SetCellBackgroundColour(row, 0, wx.LIGHT_GREY)
                    GRIDctl.SetCellBackgroundColour(row, 1, wx.LIGHT_GREY)
                    GRIDctl.SetReadOnly(row, 0)
                    GRIDctl.SetReadOnly(row, 1)
                    row += 1 
            
        GRIDctl.AutoSizeColumn(0,False)
        GRIDctl.AutoSizeColumn(1,False)
        

        saveBTN = wx.Button(cfgpanel, label="Save Changes")
        saveBTN.Bind(wx.EVT_BUTTON, self.onSave)
        cancelBTN = wx.Button(cfgpanel, label="Cancel")
        cancelBTN.Bind(wx.EVT_BUTTON, self.onCancel)

        sizer = wx.BoxSizer(wx.VERTICAL)
        l1 = wx.BoxSizer(wx.HORIZONTAL)
        l1.AddMany([TEXTkmlcmdlinelbl,      (6,20),     self.TEXTkmlcmdline])
        l2 = wx.BoxSizer(wx.HORIZONTAL)
        l2.AddMany([TEXTcsvcmdlinelbl,      (6,20),     self.TEXTcsvcmdline])
        sizer.AddSpacer(5)
        sizer.Add(l1)
        sizer.AddSpacer(10)
        sizer.Add(l2)
        sizer.AddSpacer(10)
        
        sizer.Add( wx.StaticText(cfgpanel, -1,  "Use   $n  for the name of the file within a command line - such as    notepad $n"))   
        sizer.Add( wx.StaticText(cfgpanel, -1,  "Use   $n  without any command to open default application for that file type"))   
        sizer.AddSpacer(20)
        sizer.Add(wx.StaticText(cfgpanel, -1,  " Logging Options:"))
        l3 = wx.BoxSizer(wx.HORIZONTAL)
        l3.AddMany([(20,20),      GRIDctl,     (20,20)])
        
        sizer.Add(l3)
        buttonsizer = wx.BoxSizer(wx.HORIZONTAL)
        buttonsizer.Add(saveBTN, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        buttonsizer.Add(cancelBTN, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        sizer.Add(buttonsizer, 0, wx.ALIGN_CENTER | wx.ALL, 5)

        cfgpanel.SetSizer(sizer)
        self.GRIDctl = GRIDctl
        self.Show(True)

    def onSave(self, event):
        for row in range(self.GRIDctl.GetNumberRows()):
            loggerName = self.GRIDctl.GetCellValue(row, 0)
            logLevel = self.GRIDctl.GetCellValue(row, 1)
            _log = logging.getLogger(loggerName)
            _log.setLevel(getattr(logging, logLevel))
        panel.gO.KMLcmdline = self.TEXTkmlcmdline.GetValue()
        panel.gO.CSVcmdline = self.TEXTcsvcmdline.GetValue()
        panel.gO.savesettings()
        self.Close()
        self.DestroyLater()

    def onCancel(self, event):
        self.Close()
        self.DestroyLater()

class FamilyPanel(wx.Panel):
    def __init__(self, parent, hertiageData, *args, **kwargs):
        super(FamilyPanel, self).__init__(parent, *args, **kwargs)

        # Data structure: Family data with parent-child relationships
        # Example: {"parent_id": ("Name", "Mother/Father", BornYear, DeathYear, BornAddress, [children_born_years])}
        self.hertiageData = hertiageData

        # Create a grid
        self.grid = gridlib.Grid(self)
        self.grid.CreateGrid(len(self.hertiageData), 6)  # Number of rows based on family data

        # Set column labels
        self.grid.SetColLabelValue(0, "Name")
        self.grid.SetColLabelValue(1, "Mom/Dad")
        self.grid.SetColLabelValue(2, "Born Yr")
        self.grid.SetColLabelValue(3, "Death Yr")
        self.grid.SetColLabelValue(4, "Age")
        self.grid.SetColLabelValue(5, "Born Address")
        
        # Populate the grid with family data
        self.populateGrid()

        # Layout
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.grid, 1, wx.EXPAND | wx.ALL, 10)
        self.SetSizer(sizer)

    def populateGrid(self):
        """Populate the grid with family data and calculate the age dynamically."""
        for row, (parent_id, details) in enumerate(self.hertiageData.items()):
            name, mother_father, born_year, death_year, born_address, children_born_years = details

            # Calculate age dynamically based on the oldest child's birth year
            if children_born_years:
                age = min(children_born_years) - born_year
            else:
                age = "N/A"  # No children provided

            # Set cell values
            self.grid.SetCellValue(row, 0, name)  # Name
            self.grid.SetCellValue(row, 1, mother_father)  # Mother/Father
            self.grid.SetCellValue(row, 2, str(born_year) if born_year else "N/A") # Born Year
            self.grid.SetCellValue(row, 3, str(death_year) if death_year else "N/A")  # Death Year
            self.grid.SetCellValue(row, 4, str(age))  # Age
            self.grid.SetCellValue(row, 5, born_address if born_year else "N/A")  # Born Address
        self.grid.AutoSizeColumns()
        for row in range(self.grid.GetNumberRows()):
            self.grid.SetCellAlignment(row, 2, wx.ALIGN_RIGHT, wx.ALIGN_CENTER)  # Right-align numbers in the third column
            self.grid.SetCellAlignment(row, 3, wx.ALIGN_RIGHT, wx.ALIGN_CENTER)  # Right-align numbers in the third column
            self.grid.SetCellAlignment(row, 4, wx.ALIGN_RIGHT, wx.ALIGN_CENTER)  # Right-align numbers in the third column



def formatHumanName(human: Human, longForm=True):
    if human:
        if longForm:
            maiden = f" ({human.maiden})" if human.maiden else ""
            title = f" - {human.title}" if human.title else ""
        else:
            maiden = ""
            title = ""
        return f"{human.first} {human.surname}{maiden}{title}" 
    else:
        return "<none>"

class PersonDialog(wx.Dialog):
    def __init__(self, parent, human, panel):
        super().__init__(parent, title="Person Details", size=(600, 600))
        
        def sizeAttr(attr,pad=1):
            return (min(len(attr),3)+pad)*(GVFONT[1]+5)  if attr else GVFONT[1]
        
        humans = BackgroundProcess.humans
        # create the UI controls to display the person's data
        nameLabel = wx.StaticText(self, label="Name: ")
        fatherLabel = wx.StaticText(self, label="Father: ")
        motherLabel = wx.StaticText(self, label="Mother: ")
        birthLabel = wx.StaticText(self, label="Birth: ")
        deathLabel = wx.StaticText(self, label="Death: ")
        sexLabel = wx.StaticText(self, label="Sex: ")
        marriageLabel = wx.StaticText(self, label="Marriages: ")
        homeLabel = wx.StaticText(self, label="Homes: ")
        # TODO multiple marriages
        marrying = []
        if human.marriage:
            for marry in human.marriage:
                marrying.append(f"{formatHumanName(humans[marry[0]], False)}{LifeEvent.asEventstr(marry[1])}")
        marriage = "\n".join(marrying)        
        # TODO multiple homes
        homes = []
        if human.home:
            for homedesc in human.home:
                homes.append(f"{LifeEvent.asEventstr(homedesc)}")
        homelist = "\n".join(homes)
        self.nameTextCtrl = wx.TextCtrl(self, style=wx.TE_READONLY, size=(550,-1))
        self.fatherTextCtrl = wx.TextCtrl(self, style=wx.TE_READONLY)
        self.motherTextCtrl = wx.TextCtrl(self, style=wx.TE_READONLY)
        self.birthTextCtrl = wx.TextCtrl(self, style=wx.TE_READONLY)
        self.deathTextCtrl = wx.TextCtrl(self, style=wx.TE_READONLY)
        self.sexTextCtrl = wx.TextCtrl(self, style=wx.TE_READONLY)
        self.marriageTextCtrl = wx.TextCtrl(self, style=wx.TE_READONLY|wx.TE_MULTILINE, size=(-1,sizeAttr(marriage)))
        self.homeTextCtrl = wx.TextCtrl(self, style=wx.TE_READONLY|wx.TE_MULTILINE, size=(-1,sizeAttr(homelist)))

        # layout the UI controls using a grid sizer

        sizer = wx.FlexGridSizer(cols=2, hgap=5, vgap=5)

        sizer.Add(nameLabel, 0, wx.LEFT|wx.TOP, border=5)
        sizer.Add(self.nameTextCtrl, 0, wx.EXPAND, border=5)
        sizer.Add(fatherLabel, 0, wx.LEFT|wx.TOP, border=5)
        sizer.Add(self.fatherTextCtrl, 1, wx.EXPAND)
        sizer.Add(motherLabel, 0, wx.LEFT|wx.TOP, border=5)
        sizer.Add(self.motherTextCtrl, 1, wx.EXPAND)
        sizer.Add(birthLabel, 0, wx.LEFT|wx.TOP, border=5)
        sizer.Add(self.birthTextCtrl, 0, wx.EXPAND)
        sizer.Add(deathLabel, 0, wx.LEFT|wx.TOP, border=5)
        sizer.Add(self.deathTextCtrl, 0, wx.EXPAND)
        sizer.Add(sexLabel, 0, wx.LEFT|wx.TOP, border=5)
        sizer.Add(self.sexTextCtrl, 0, wx.EXPAND)
        sizer.Add(marriageLabel, 0, wx.LEFT|wx.TOP, border=5)
        sizer.Add(self.marriageTextCtrl, 1, wx.EXPAND, border=5)
        sizer.Add(homeLabel, 0, wx.LEFT|wx.TOP, border=5)
        sizer.Add(self.homeTextCtrl, 1, wx.EXPAND, border=5)
        # self.SetSizer(sizer)

        # set the person's data in the UI controls
        self.nameTextCtrl.SetValue(formatHumanName(human))

        if human.father:
            self.fatherTextCtrl.SetValue(formatHumanName(humans[human.father]))
        if human.mother:
            self.motherTextCtrl.SetValue(formatHumanName(humans[human.mother]))
        self.birthTextCtrl.SetValue(f"{LifeEvent.asEventstr(human.birth)}")
        self.deathTextCtrl.SetValue(f"{LifeEvent.asEventstr(human.death)}")
        self.sexTextCtrl.SetValue(str(human.sex) if human.sex else "")
        self.marriageTextCtrl.SetValue(marriage)
        
        
        self.homeTextCtrl.SetValue(homelist)
        if panel.gO.Referenced:
            self.related = None
            relatedLabel = wx.StaticText(self, label="Relative: ")
            if panel.gO.Referenced.exists(human.xref_id):
                hertiageList = doTraceTo(panel.gO, human)
                personRelated = panel.gO.Referenced.gettag(human.xref_id)
                if personRelated:
                    hertiageSet = {}
                    for (hertiageparent, hertiageperson, hyear, hid) in hertiageList:
                        hertiageSet[hid] = (hertiageperson, hertiageparent, humans[hid].birth.whenyear() if humans[hid].birth else None, humans[hid].death.whenyear() if humans[hid].death else None, humans[hid].birth.getattr('where') if humans[hid].birth else None,[])
                    # Create the panel and pass the data
                    self.related = FamilyPanel(self, hertiageSet)

            if not self.related:
               self.related = wx.StaticText(self, label="No References to selected person")
            
            sizer.Add(relatedLabel, 0, wx.LEFT|wx.TOP, border=5)
            sizer.Add(self.related, 1, wx.EXPAND, border=5)
    
        sizer.AddSpacer(2)    
        # create the OK button
        ok_btn = wx.Button(self, wx.ID_OK)
        btn_sizer = wx.StdDialogButtonSizer()
        btn_sizer.AddButton(ok_btn)
        btn_sizer.Realize()
        sizer.Add(btn_sizer, 0, wx.RIGHT|wx.BOTTOM, border=10)
        self.SetSizer(sizer)
        self.SetBackgroundColour(wx.TheColourDatabase.FindColour('WHITE'))
        self.Fit()

class FindDialog(wx.Dialog):
    def __init__(self, parent, title, LastSearch=""):
        super(FindDialog, self).__init__(parent, title=title, size=(300, 150))
        
        self.LastSearch = LastSearch
        
        # Layout
        Findpanel = wx.Panel(self, style=wx.SIMPLE_BORDER)
        vbox = wx.BoxSizer(wx.VERTICAL)
        
        self.SearchLabel = wx.StaticText(Findpanel, label="Enter search string:")
        vbox.Add(self.SearchLabel, flag=wx.ALL, border=10)
        
        self.SearchText = wx.TextCtrl(Findpanel)
        self.SearchText.SetValue(self.LastSearch)
        vbox.Add(self.SearchText, flag=wx.EXPAND | wx.LEFT | wx.RIGHT, border=10)
        
        self.okButton = wx.Button(Findpanel, label="OK")
        self.cancelButton = wx.Button(Findpanel, label="Cancel")
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(self.okButton, flag=wx.RIGHT, border=10)
        hbox.Add(self.cancelButton, flag=wx.LEFT, border=10)
        vbox.Add(hbox, flag=wx.ALIGN_CENTER | wx.ALL, border=10)
        
        Findpanel.SetSizer(vbox)
        # Set OK button as default
        self.okButton.SetDefault()
        
        # Event bindings
        self.okButton.Bind(wx.EVT_BUTTON, self.OnOk)
        self.cancelButton.Bind(wx.EVT_BUTTON, self.OnCancel)
    
    def OnOk(self, event):
        self.LastSearch = self.SearchText.GetValue()
        self.EndModal(wx.ID_OK)
    
    def OnCancel(self, event):
        self.EndModal(wx.ID_CANCEL)
    
    def GetSearchString(self):
        return self.LastSearch








class BackgroundActions:
    """
This runs the backgrund tasks on another thread.
This includes update messages, running of load, calling gpslookups, 
and generating the output so that the GUI can continue to be responsive

"""
    def __init__(self, win, threadnum):
        self.win = win
        self.gOptions = None
        self.humans = None
        self.threadnum = threadnum
        self.updategrid = False
        self.updategridmain = True
        self.updateinfo = ''  # This will prime the update
        self.errorinfo = None
        self.keepGoing = True
        self.threadrunning = True
        self.do = -1
        self.readyToDo = True
        

    def DefgOps(self, gOps):
        global panel, BackgroundProcess
        self.gOptions = gOps
        panel = gOps.panel
        BackgroundProcess = gOps.BackgroundProcess
        

    def Start(self):
        self.keepGoing = self.threadrunning = True
        
        self.do = 0
        logging.info("Started thread %d from thread %d", self.threadnum, _thread.get_ident())
        _thread.start_new_thread(self.Run, ())
        

    def Stop(self):
        self.keepGoing = False


    def IsRunning(self):
        return self.threadrunning

    def IsTriggered(self):
        return self.do != 0

    def Trigger(self, dolevel):
        global panel

        if dolevel & 1 or dolevel & 4:
            panel.id.BTNLoad.SetBackgroundColour(panel.id.GetColor('BTN_DONE'))
        if dolevel & 2:
            panel.id.BTNUpdate.SetBackgroundColour(panel.id.GetColor('BTN_DONE'))
        self.do = dolevel
        
    def SayInfoMessage(self, line, newline= True):
        if newline and self.updateinfo and self.updateinfo != '':
            self.updateinfo = self.updateinfo + "\n"
        self.updateinfo = self.updateinfo + line if self.updateinfo else line
        
    def SayErrorMessage(self, line, newline= True):
        if newline and self.errorinfo and self.errorinfo != '':
            self.errorinfo = self.errorinfo + "\n"
        self.errorinfo = self.errorinfo + line if self.errorinfo else line

    def Run(self):
        global UpdateBackgroundEvent
        self.SayInfoMessage(' ',True)      # prime the InfoBox
        while self.keepGoing:
            # We communicate with the UI by sending events to it. There can be
            # no manipulation of UI objects from the worker thread.
            if self.do != 0 and self.readyToDo:
                self.readyToDo = False          # Avoid a Race
                _log.info("triggered thread %d (Thread# %d / %d)", self.do, self.threadnum, _thread.get_ident())
                if not UpdateBackgroundEvent:
                    UpdateBackgroundEvent = self.gOptions.UpdateBackgroundEvent
                self.gOptions.stopping = False
                wx.Yield()
                if self.do & 1 or (self.do & 4 and not self.gOptions.parsed):
                    wx.PostEvent(self.win, UpdateBackgroundEvent(state='busy'))
                    wx.Yield()
                    _log.info("start ParseAndGPS")
                    if hasattr(self, 'humans'):
                        if self.humans:                            
                            del self.humans
                            self.gOptions.humans = None
                            self.humans = None
                    _log.info("ParseAndGPS")
                    try:
                        self.humans = ParseAndGPS(self.gOptions, 1)
                    
                    except Exception as e:
                        # Capture other exceptions
                        if hasattr(self, 'humans'):
                            if self.humans:                            
                                del self.humans
                                self.humans = None
                        self.do = 0
                        _log.warning(str(e))
                        self.gOptions.stopping = False
                        self.SayErrorMessage('Failed to Parse', True)
                        self.SayErrorMessage(str(e), True)
                        
                    if self.do & 1 and self.gOptions.Referenced:
                        del self.gOptions.Referenced
                        self.gOptions.Referenced = None    
                    # self.updategrid = True
                    wx.PostEvent(self.win, UpdateBackgroundEvent(state='busy'))
                    wx.Yield()
                    if hasattr (self, 'humans') and self.humans:                            
                        _log.info("human count %d", len(self.humans))
                        self.humans = ParseAndGPS(self.gOptions, 2)
                        self.updategrid = True
                        if self.humans:
                            self.SayInfoMessage(f"Loaded {len(self.humans)} people")
                        else:
                            self.SayInfoMessage(f"Cancelled loading people")
                        if self.gOptions.Main:
                            self.SayInfoMessage(f" with '{self.gOptions.Main}' as starting person", False)
                    else:
                        self.SayErrorMessage("File could not be read as a GEDCOM file", True)
                    
                if self.do & 2:
                    _log.info("start do 2")
                    if (self.gOptions.parsed):
                        _log.info("doHTML or doKML")
                        fname = self.gOptions.Result
                        if (self.gOptions.ResultHTML):
                            needAGridUpdate = not self.gOptions.Referenced
                            doHTML(self.gOptions, self.humans, True)
                            # We only need to update the Grid if we have not calculated the Referenced before
                            self.updategridmain = needAGridUpdate
                            self.SayInfoMessage(f"HTML generated for {self.gOptions.totalpeople} people ({fname})")
                        else: 
                            doKML(self.gOptions, self.humans)
                            self.SayInfoMessage(f"KML file generated for {self.gOptions.totalpeople} people/points ({fname})")
                    else:
                        _log.info("not parsed")
                    _log.info("done draw")
                    

                _log.debug("=======================GOING TO IDLE %d", self.threadnum)
                self.do = 0
                self.readyToDo = True
                self.gOptions.stop()
                wx.PostEvent(self.win, UpdateBackgroundEvent(state='done'))
            else:
                time.sleep(0.3)
                # _log.info("background Do:%d  &  Running:%d  %d", self.do , self.gOptions.running, self.gOptions.counter)

        self.threadrunning = False

