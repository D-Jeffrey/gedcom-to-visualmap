"""
visual_map_panel.py

Main panel for the Visual Map GUI. Contains the control widgets, option panels,
and coordinates with the background worker to load GEDCOM data and produce
HTML/KML outputs.

This module uses wxPython for UI and provides a VisualMapPanel class which is a
wx.Panel hosting the primary user controls.

Types:
- gvOptions is the application options/state object (see gedcom_options.py).
- BackgroundActions is the background worker class.
"""
from typing import Optional, List, Dict, Any
import logging
import time
import math
import os
import sys
import subprocess
import webbrowser
from datetime import datetime

from const import KMLMAPSURL

import wx

from .visual_gedcom_ids import VisualGedcomIds  # type: ignore
from .people_list_ctrl_panel import PeopleListCtrlPanel  # type: ignore
from .person_dialog import PersonDialog  # type: ignore
from .find_dialog import FindDialog  # type: ignore
from gedcom_options import gvOptions, ResultsType  # type: ignore
from .background_actions import BackgroundActions

(UpdateBackgroundEvent, EVT_UPDATE_STATE) = wx.lib.newevent.NewEvent()

_log = logging.getLogger(__name__.lower())

class VisualMapPanel(wx.Panel):
    """
    Main panel used by the application's main frame.

    Responsibilities:
    - Build and manage the controls and option panels.
    - Start/stop background processing.
    - Reflect gvOptions state into the UI and vice-versa.
    """

    # Public attributes with types for static analysis and readability
    font_manager: Any
    font_name: str
    font_size: int
    frame: wx.Frame
    gOp: Optional['gvOptions']
    id: VisualGedcomIds
    peopleList: PeopleListCtrlPanel
    background_process: BackgroundActions
    threads: List[Any]
    myTimer: Optional[wx.Timer]
    busystate: bool

    def __init__(self, parent: wx.Window, font_manager: Any, gOp: Optional['gvOptions'],
                 *args: Any, **kw: Any) -> None:
        """
        Initialize the VisualMapPanel.

        Args:
            parent: wx parent window.
            font_manager: FontManager instance used to style controls.
            gOp: Optional global options/state object. If not provided the panel
                 will construct one in SetupOptions().
        """
        # parent must be the wx parent for this panel; call panel initializer with it
        super().__init__(parent, *args, **kw)

        self.font_manager = font_manager
        self.font_name, self.font_size = self.font_manager.get_font_name_size()

        self.SetMinSize((800,800))
        self.frame = self.TopLevelParent
        self.gOp : Optional['gvOptions'] = None

        self.id = {}
        
        self.fileConfig = None
        self.busystate = False
        self.busycounthack = 0
        self.inTimer = False
        self.timeformat = '%H hr %M'
        self.SetAutoLayout(True)
        self.id = VisualGedcomIds()
        
        # create a panel in the frame
        self.panelA = wx.Panel(self, -1, style=wx.SIMPLE_BORDER)
        self.panelB = wx.Panel(self, -1, style=wx.SIMPLE_BORDER)
        
        # https://docs.wxpython.org/wx.ColourDatabase.html#wx-colourdatabase
        self.panelA.SetBackgroundColour(self.id.GetColor('INFO_BOX_BACKGROUND'))
        self.panelB.SetBackgroundColour(wx.WHITE)

        main_hs = wx.BoxSizer(wx.HORIZONTAL)
        main_hs.Add(self.panelA, 1, wx.EXPAND | wx.ALL, 5)
        main_hs.Add(self.panelB, 0, wx.EXPAND | wx.ALL, 5)
        self.SetSizer(main_hs)
        self.Layout()

        # Add Data Grid on Left panel
        self.peopleList = PeopleListCtrlPanel(self.panelA, self.id.m, self.font_manager)
        
        # Add all the labels, button and radiobox to Right Panel
        self.LayoutOptions(self.panelB)

        pa_sizer = wx.BoxSizer(wx.VERTICAL)
        pa_sizer.Add(self.peopleList, 1, wx.EXPAND | wx.ALL, 5)
        self.panelA.SetSizer(pa_sizer)
        self.panelA.Layout()

        self._adjust_panelB_width()

        self.lastruninstance = 0.0
        self.remaintime = 0

        # Configure panel options
        self.SetupOptions()

    def start(self) -> None:
        """Perform any UI startup actions (enable/disable buttons etc.)."""
        try:
            self.SetupButtonState()
        except Exception:
            _log.exception("start: SetupButtonState failed")

    def stop(self):
        pass

    def stop_timer(self):
        if self.myTimer and self.myTimer.IsRunning():
            try:
                self.myTimer.Stop()
            except Exception:
                pass
            try:
                self.Unbind(wx.EVT_TIMER, self)
            except Exception:
                pass

    def _adjust_panelB_width(self):
        # Representative labels / longest control captions used in LayoutOptions
        sample_texts = [
            "Input file:   ", "Output file: ", "Default Country:   ",
            "Default Country:", "Map Style", "HTML Options", "Create Files", "Geo Table"
        ]
        # measure longest text in pixels
        max_text_len = max(len(s) for s in sample_texts)
        text_px = self.font_manager.get_text_width(max_text_len)
        # set panelB width with some padding
        extra_for_controls = int(220 + (self.font_size * 6))
        desired = max(300, text_px + extra_for_controls)
        # Apply as minimum width so sizer keeps panelB readable
        self.panelB.SetMinSize((desired, -1))
        # Apply layout update
        self.Layout()
        self.Refresh()

    def set_current_font(self) -> None:
        """Apply current font from the font manager to this panel and children."""
        self.font_manager.apply_current_font_recursive(self)
        self.font_manager.apply_current_font_recursive(self.peopleList)
        # adjust right-hand panel width to match new font metrics
        wx.CallAfter(self._adjust_panelB_width)
        self.Layout()
        self.Refresh()

    def LayoutOptions(self, panel: wx.Panel) -> None:
        """Create and layout the options controls on the provided panel."""
        # Top of the Panel
        box = wx.BoxSizer(wx.VERTICAL)
        titleFont = wx.Font(wx.FontInfo(self.font_size).FaceName(self.font_name).Bold())
        fh = titleFont.GetPixelSize()[1]
        titleArea = wx.Panel(panel, size=(-1, fh + 10))
        titleArea.SetBackgroundColour(self.id.GetColor('TITLE_BACK')) 
        title = wx.StaticText(titleArea, label="Visual Mapping Options",  style=wx.ALIGN_CENTER)
        title.SetFont(titleFont)
        # Center the title text in the title area
        titleSizer = wx.BoxSizer(wx.HORIZONTAL)
        titleSizer.Add(title, 1, wx.ALIGN_CENTER)
        titleArea.SetSizer(titleSizer)

        
        box.Add(titleArea, 0, wx.EXPAND | wx.BOTTOM, 0)

        
        
        box.Add(wx.StaticLine(panel), 0, wx.EXPAND)
            
        
        self.id.txtinfile = wx.Button(panel, -1,  "Input file:   ") 
        self.id.txtinfile.SetBackgroundColour(self.id.GetColor('BTN_DIRECTORY'))
        self.id.TEXTGEDCOMinput = wx.TextCtrl(panel, self.id.IDs['ID_TEXTGEDCOMinput'], "", size=(250,20))
        self.id.TEXTGEDCOMinput.Enable(False) 
        self.id.txtoutfile = wx.Button(panel, -1, "Output file: ")
        self.id.txtoutfile.SetBackgroundColour(self.id.GetColor('BTN_DIRECTORY'))
        self.id.TEXTResult = wx.TextCtrl(panel, self.id.IDs['ID_TEXTResult'], "", size=(250,20))
        self.id.txtinfile.Bind(wx.EVT_LEFT_DOWN, self.frame.OnFileOpenDialog)
        self.id.txtoutfile.Bind(wx.EVT_LEFT_DOWN, self.frame.OnFileResultDialog)

        l1 = wx.BoxSizer(wx.HORIZONTAL)
        l1.AddMany([self.id.txtinfile,      (6,20),     self.id.TEXTGEDCOMinput])
        l2 = wx.BoxSizer(wx.HORIZONTAL)
        l2.AddMany([self.id.txtoutfile,     (0,20), self.id.TEXTResult])
        box.AddMany([l1, (4,4,), l2])

        # First select controls

        self.id.CBUseGPS = wx.CheckBox(panel, self.id.IDs['ID_CBUseGPS'], "Use GPS lookup (uncheck if GPS is in file)")#,  wx.NO_BORDER)
        self.id.CBCacheOnly = wx.CheckBox(panel, self.id.IDs['ID_CBCacheOnly'], "Cache Only, do not lookup addresses")#, , wx.NO_BORDER)
        self.id.labelDefCountry = wx.StaticText(panel, -1,  "Default Country:   ") 
        self.id.TEXTDefaultCountry = wx.TextCtrl(panel, self.id.IDs['ID_TEXTDefaultCountry'], "", size=(250,20))
        defCounttryBox = wx.BoxSizer(wx.HORIZONTAL)
        defCounttryBox.AddMany([self.id.labelDefCountry,      (6,20),     self.id.TEXTDefaultCountry])
        self.id.CBAllEntities = wx.CheckBox(panel, self.id.IDs['ID_CBAllEntities'], "Map all people")#, wx.NO_BORDER)
        self.id.CBBornMark = wx.CheckBox(panel, self.id.IDs['ID_CBBornMark'], "Marker for when Born")
        self.id.CBDieMark = wx.CheckBox(panel, self.id.IDs['ID_CBDieMark'], "Marker for when Died")
        
        self.id.busyIndicator = wx.ActivityIndicator(panel)

        self.id.busyIndicator.SetBackgroundColour(self.id.GetColor('BUSY_BACK'))
        self.id.RBResultOutType =  wx.RadioBox(panel, self.id.IDs['ID_RBResultsType'], "Result Type", 
                                           choices = ['HTML', 'KML', 'KML2', 'SUM'] , majorDimension= 5)

        box.AddMany([  self.id.CBUseGPS,
                       self.id.CBCacheOnly,
                       defCounttryBox,
                       self.id.CBAllEntities,
                       self.id.CBBornMark,
                       self.id.CBDieMark
])
        """
          HTML select controls in a Box
        """
        hbox_container = wx.Panel(panel)
        hbox = wx.StaticBox( hbox_container, -1, "HTML Options")
        hsizer = wx.StaticBoxSizer(hbox, wx.VERTICAL)
        # Small inner sizer for the controls
        hboxIn = wx.BoxSizer(wx.VERTICAL)
        
        mapchoices =  sorted(self.id.AllMapTypes)
        mapboxsizer = wx.BoxSizer(wx.HORIZONTAL)
        mapStyleLabel = wx.StaticText(hbox, -1, " Map Style")
        self.id.CBMarksOn = wx.CheckBox(hbox_container, self.id.IDs['ID_CBMarksOn'], "Markers", name='MarksOn')

        self.id.CBHomeMarker = wx.CheckBox(hbox_container, self.id.IDs['ID_CBHomeMarker'], "Marker point or homes")
        self.id.CBMarkStarOn = wx.CheckBox(hbox_container, self.id.IDs['ID_CBMarkStarOn'], "Marker starter with Star")
        self.id.CBMapTimeLine = wx.CheckBox(hbox_container, self.id.IDs['ID_CBMapTimeLine'], "Add Timeline")
        self.id.LISTMapType = wx.Choice(hbox_container, self.id.IDs['ID_LISTMapStyle'], name="MapStyle", choices=mapchoices)
        self.id.CBMapControl = wx.CheckBox(hbox_container, self.id.IDs['ID_CBMapControl'], "Open Map Controls",name='MapControl') 
        self.id.CBMapMini = wx.CheckBox(hbox_container, self.id.IDs['ID_CBMapMini'], "Add Mini Map",name='MapMini') 
        
        
        
        self.id.CBHeatMap = wx.CheckBox(hbox_container, self.id.IDs['ID_CBHeatMap'], "Heatmap", style = wx.NO_BORDER)
        
        self.id.CBUseAntPath = wx.CheckBox(hbox_container, self.id.IDs['ID_CBUseAntPath'], "Ant paths")
        
        TimeStepVal = 5
        self.id.LISTHeatMapTimeStep = wx.Slider(hbox_container, self.id.IDs['ID_LISTHeatMapTimeStep'], TimeStepVal,1, 100, size=(250, 45),
                style=wx.SL_HORIZONTAL | wx.SL_AUTOTICKS | wx.SL_LABELS )
        self.id.LISTHeatMapTimeStep.SetTickFreq(5)
        self.id.RBGroupBy  = wx.RadioBox(hbox_container, self.id.IDs['ID_RBGroupBy'], "Group by:", 
                                       choices = ['None', 'Last Name', 'Last Name (Soundex)','Person'], majorDimension= 2)
        mapboxsizer.Add(self.id.LISTMapType)
        mapboxsizer.Add( mapStyleLabel)
        
        
        hboxIn.AddMany([
            (self.id.CBMarksOn, 0, wx.ALL, 2),
            (self.id.CBHomeMarker, 0, wx.ALL, 2),
            (self.id.CBMarkStarOn, 0, wx.ALL, 2),
            (self.id.CBMapTimeLine, 0, wx.ALL, 2),        
            (self.id.RBGroupBy, 0, wx.ALL, 2), 
            (mapboxsizer, 0, wx.EXPAND | wx.ALL, 4),
            (self.id.CBMapControl, 0, wx.ALL, 2),
            (self.id.CBMapMini, 0, wx.ALL, 2),
            (self.id.CBUseAntPath, 0, wx.ALL, 2),
            (self.id.CBHeatMap, 0, wx.ALL, 2),
            (self.id.LISTHeatMapTimeStep, 0, wx.EXPAND | wx.ALL, 4),
        ])
        hsizer.Add(hboxIn, 0, wx.EXPAND | wx.ALL, 4)
        hbox_container.SetSizer(hsizer)
        self.optionHbox = hbox_container
        #
        # KML select controls in a Box
        #
        kbox_container = wx.Panel(panel)
        kbox = wx.StaticBox( kbox_container, -1, "KML Options")
        ksizer = wx.StaticBoxSizer(kbox, wx.VERTICAL)
        kboxIn = wx.BoxSizer(wx.VERTICAL)
        if False:
            txtMissing = wx.StaticText(kboxIn, -1,  "Max generation missing: ") 
            self.id.INTMaxMissing = wx.TextCtrl(kboxIn, self.id.IDs['ID_INTMaxMissing'], "", size=(20,20))
            l1 = wx.BoxSizer(wx.HORIZONTAL)
            l1.AddMany([txtMissing,      (0,20),     self.id.INTMaxMissing])
            
            kboxIn.AddMany([l1, (4,4,), l2])
        # self.id.ID_INTMaxMissing  'MaxMissing'
        self.id.RBKMLMode  = wx.RadioBox(kbox, self.id.IDs['ID_RBKMLMode'], "Organize by:", 
                                       choices = ['None', 'Folder'], majorDimension= 2)
        
        kboxs = [self.id.RBKMLMode, wx.BoxSizer(wx.HORIZONTAL), (4,4), wx.BoxSizer(wx.HORIZONTAL)]
        self.id.CBFlyTo = wx.CheckBox(kbox, self.id.IDs['ID_CBFlyTo'], "FlyTo Balloon", style = wx.NO_BORDER)
        self.id.ID_INTMaxLineWeight = wx.SpinCtrl(kbox, self.id.IDs['ID_INTMaxLineWeight'], "", min=1, max=100, initial=20)
        
        kboxs[1].AddMany([wx.StaticText(kbox, -1, "        "), self.id.CBFlyTo])
        kboxs[3].AddMany([self.id.ID_INTMaxLineWeight, wx.StaticText(kbox, -1, " Max Line Weight")])
        kboxIn.AddMany(kboxs)

        ksizer.Add(kboxIn, 0, wx.EXPAND | wx.ALL, 4)
        kbox_container.SetSizer(ksizer)
        self.optionKbox = kbox_container
            #
        # KML select controls in a Box
        #
        k2box_container = wx.Panel(panel)
        k2box = wx.StaticBox(k2box_container, -1, "KML2 Options")
        k2sizer = wx.StaticBoxSizer(k2box, wx.VERTICAL)
        k2boxIn = wx.BoxSizer(wx.VERTICAL)
        
        k2sizer.Add(k2boxIn, 0, wx.EXPAND | wx.ALL, 4)
        k2box_container.SetSizer(k2sizer)
        self.optionK2box = k2box_container
        #
        # Summary select controls in a Box
        #
        sbox_container = wx.Panel(panel)
        sbox = wx.StaticBox( sbox_container, -1, "Summary Options")
        ssizer = wx.StaticBoxSizer(sbox, wx.VERTICAL)
        sboxIn = wx.BoxSizer(wx.VERTICAL)
        
        self.id.CBSummary = [wx.CheckBox(sbox, self.id.IDs['ID_CBSummary'], label="Open files after created", name="Open"),
                             wx.CheckBox(sbox, self.id.IDs['ID_CBSummary'], label="Places", name="Places"),
                             wx.CheckBox(sbox, self.id.IDs['ID_CBSummary'], label="People", name="People"),
                             wx.CheckBox(sbox, self.id.IDs['ID_CBSummary'], label="Countries", name="Countries"),
                             wx.CheckBox(sbox, self.id.IDs['ID_CBSummary'], label="Countries Grid", name="CountriesGrid"),
                             wx.CheckBox(sbox, self.id.IDs['ID_CBSummary'], label="Geocode", name="Geocode"),
                             wx.CheckBox(sbox, self.id.IDs['ID_CBSummary'], label="Alternate Places", name="AltPlaces")]
        
        sboxIn.AddMany(self.id.CBSummary)
        ssizer.Add(sboxIn, 0, wx.EXPAND | wx.ALL, 4)
        sbox_container.SetSizer(ssizer)
        self.optionSbox = sbox_container


        #
        # Grid View Options
        #
        
        
        gbox_min_height = max(40, int(fh * 4))
        gbox_container = wx.Panel(panel, size=(300, gbox_min_height))
        gbox = wx.StaticBox(gbox_container, -1, "Grid View Options")
        gsizer = wx.StaticBoxSizer(gbox, wx.VERTICAL)
        gboxIn = wx.BoxSizer(wx.VERTICAL)
        self.id.CBGridView = wx.CheckBox(gbox_container, self.id.IDs['ID_CBGridView'],  'View Only Direct Ancestors')
        gboxIn.AddMany( [self.id.CBGridView])
        gsizer.Add( gboxIn, 0, wx.EXPAND | wx.ALL, 4)
        
        gbox_container.SetSizer(gsizer)
        self.optionGbox = gbox_container
        
        self.optionsStack = wx.BoxSizer(wx.VERTICAL)
        # Add all option boxes to the same slot, but hide them initially
        self.optionsStack.Add(self.optionHbox, 1, wx.EXPAND)
        self.optionHbox.Hide()

        self.optionsStack.Add(self.optionKbox, 1, wx.EXPAND)
        self.optionKbox.Hide()

        self.optionsStack.Add(self.optionK2box, 1, wx.EXPAND)
        self.optionK2box.Hide()

        self.optionsStack.Add(self.optionSbox, 1, wx.EXPAND)
        self.optionSbox.Hide()

        box.Add(self.optionGbox, 0, wx.LEFT | wx.TOP, 5)
        box.AddMany([self.id.RBResultOutType])
        # Add the stack to the main layout
        box.Add(self.optionsStack, 1, wx.EXPAND | wx.ALL, 5)
        self.optionsStack.Layout()


        l1 = wx.BoxSizer(wx.HORIZONTAL)
        self.id.BTNLoad = wx.Button(panel, self.id.IDs['ID_BTNLoad'], "Load")
        self.id.BTNCreateFiles = wx.Button(panel, self.id.IDs['ID_BTNCreateFiles'], "Create Files")
        self.id.BTNCSV = wx.Button(panel, self.id.IDs['ID_BTNCSV'], "Geo Table")
        self.id.BTNTRACE = wx.Button(panel, self.id.IDs['ID_BTNTRACE'], "Trace")
        self.id.BTNSTOP = wx.Button(panel, self.id.IDs['ID_BTNSTOP'], "Stop")
        self.id.BTNBROWSER = wx.Button(panel, self.id.IDs['ID_BTNBROWSER'], "Browser")
        l1.Add (self.id.BTNLoad, 0, wx.EXPAND | wx.ALL, 5)
        l1.Add (self.id.BTNCreateFiles, 0, wx.EXPAND | wx.ALL, 5)
        l1.Add (self.id.BTNCSV, 0, wx.EXPAND | wx.ALL, 5)
        l1.Add (self.id.BTNTRACE, 0, wx.EXPAND | wx.ALL, 5)
        box.Add(l1, 0, wx.EXPAND | wx.ALL,0)
        l1 = wx.BoxSizer(wx.HORIZONTAL)
        l1.Add (self.id.busyIndicator, 0, wx.ALL | wx.RESERVE_SPACE_EVEN_IF_HIDDEN, 5)
        
        l1.Add (self.id.BTNSTOP, 0, wx.EXPAND | wx.LEFT, 20)
        l1.AddSpacer(20)
        l1.Add (self.id.BTNBROWSER, wx.EXPAND | wx.ALL, 5)
        l1.AddSpacer(20)
        box.Add((0,10))
        box.Add(l1, 0, wx.EXPAND | wx.ALL,0)
 
        """    
            self.id.ID_LISTMapStyle,
            self.id.ID_TEXTMain,
            self.id.ID_TEXTName,
        """
        
        # panel.SetSizeHints(box)
        panel.SetSizer(box)
        self.Bind(wx.EVT_RADIOBOX, self.EvtRadioBox, id = self.id.IDs['ID_RBResultsType'])
        self.Bind(wx.EVT_CHECKBOX, self.EvtCheckBox, id = self.id.IDs['ID_CBMapControl'])
        self.Bind(wx.EVT_CHECKBOX, self.EvtCheckBox, id = self.id.IDs['ID_CBMapMini'])
        self.Bind(wx.EVT_CHECKBOX, self.EvtCheckBox, id = self.id.IDs['ID_CBMarksOn'])
        self.Bind(wx.EVT_CHECKBOX, self.EvtCheckBox, id = self.id.IDs['ID_CBBornMark'])
        self.Bind(wx.EVT_CHECKBOX, self.EvtCheckBox, id = self.id.IDs['ID_CBDieMark'])
        self.Bind(wx.EVT_CHECKBOX, self.EvtCheckBox, id = self.id.IDs['ID_CBHomeMarker'])
        self.Bind(wx.EVT_CHECKBOX, self.EvtCheckBox, id = self.id.IDs['ID_CBMarkStarOn'])
        self.Bind(wx.EVT_CHECKBOX, self.EvtCheckBox, id = self.id.IDs['ID_CBHeatMap'])
        self.Bind(wx.EVT_CHECKBOX, self.EvtCheckBox, id = self.id.IDs['ID_CBFlyTo'])
        self.Bind(wx.EVT_CHECKBOX, self.EvtCheckBox, id = self.id.IDs['ID_CBMapTimeLine'])
        self.Bind(wx.EVT_CHECKBOX, self.EvtCheckBox, id = self.id.IDs['ID_CBUseAntPath'])
        self.Bind(wx.EVT_CHECKBOX, self.EvtCheckBox, id = self.id.IDs['ID_CBUseGPS'])
        self.Bind(wx.EVT_CHECKBOX, self.EvtCheckBox, id = self.id.IDs['ID_CBCacheOnly'])
        self.Bind(wx.EVT_CHECKBOX, self.EvtCheckBox, id = self.id.IDs['ID_CBAllEntities'])
        self.Bind(wx.EVT_CHECKBOX, self.EvtCheckBox, id = self.id.IDs['ID_CBGridView'])
        self.Bind(wx.EVT_CHECKBOX, self.EvtCheckBox, id = self.id.IDs['ID_CBSummary'])
        self.Bind(wx.EVT_RADIOBOX, self.EvtRadioBox, id = self.id.IDs['ID_RBKMLMode'])
        self.Bind(wx.EVT_SPINCTRL, self.EvtSpinCtrl, id = self.id.IDs['ID_INTMaxLineWeight'])
        self.Bind(wx.EVT_CHOICE, self.EvtListBox, id = self.id.IDs['ID_LISTMapStyle'])
        self.Bind(wx.EVT_BUTTON, self.EvtButton, id = self.id.IDs['ID_BTNLoad'])
        self.Bind(wx.EVT_BUTTON, self.EvtButton, id = self.id.IDs['ID_BTNCreateFiles'])
        self.Bind(wx.EVT_BUTTON, self.EvtButton, id = self.id.IDs['ID_BTNCSV'])
        self.Bind(wx.EVT_BUTTON, self.EvtButton, id = self.id.IDs['ID_BTNTRACE'])
        self.Bind(wx.EVT_BUTTON, self.EvtButton, id = self.id.IDs['ID_BTNSTOP'])
        self.Bind(wx.EVT_BUTTON, self.EvtButton, id = self.id.IDs['ID_BTNBROWSER'])
        self.Bind(wx.EVT_TEXT, self.EvtText, id = self.id.IDs['ID_TEXTResult'])
        self.Bind(wx.EVT_TEXT, self.EvtText, id = self.id.IDs['ID_TEXTDefaultCountry'])
        self.OnBusyStop(-1)
        self.Bind(wx.EVT_RADIOBOX, self.EvtRadioBox, id = self.id.IDs['ID_RBGroupBy'])
        self.Bind(wx.EVT_SLIDER, self.EvtSlider, id = self.id.IDs['ID_LISTHeatMapTimeStep'])
        self.NeedReload()
        self.NeedRedraw()
        self.Bind(wx.EVT_CLOSE, self.OnCloseWindow)
        self.Bind(EVT_UPDATE_STATE, self.OnCreateFiles)
        self.threads = []
        self.background_process = BackgroundActions(self, 0)
        self.threads.append(self.background_process)
        for t in self.threads:
            t.Start()
        

        # Bind all EVT_TIMER events to self.OnMyTimer
        self.Bind(wx.EVT_TIMER, self.OnMyTimer)
        self.myTimer = wx.Timer(self)
        self.myTimer.Start(500)
        self.Layout()
        self.Refresh()

    def NeedReload(self):
        if self.gOp:
            self.gOp.parsed= False
        self.id.BTNLoad.SetBackgroundColour(self.id.GetColor('BTN_PRESS'))
        self.NeedRedraw()

    def NeedRedraw(self):
        self.id.BTNCreateFiles.SetBackgroundColour(self.id.GetColor('BTN_PRESS'))

    def setInputFile(self, path):
        # set the state variables
        self.gOp.setInput(path)
        _, filen = os.path.split(self.gOp.get('GEDCOMinput'))
        # set the form field
        self.id.TEXTGEDCOMinput.SetValue(filen)
        self.fileConfig.Write("GEDCOMinput", path)
        #TODO Fix this
        #TODO Fix this
        self.id.TEXTResult.SetValue(self.gOp.get('Result'))
        self.NeedReload()
        self.SetupButtonState()

    def EvtRadioBox(self, event):

        _log.debug('%d is %d',  event.GetId(), event.GetInt())
        if event.GetId() == self.id.IDs['ID_RBResultsType']:
            if event.GetInt() == 0:
                outType = ResultsType.HTML
            elif event.GetInt() == 1:
                outType = ResultsType.KML
            elif event.GetInt() == 2:
                outType = ResultsType.KML2
            elif event.GetInt() == 3:
                outType = ResultsType.SUM
            self.gOp.setResults(self.gOp.get('Result'), outType)

#            BackgroundProcess.updategridmain = True

            self.id.TEXTResult.SetValue(self.gOp.get('Result'))
            self.SetupButtonState()

        elif event.GetId() ==  self.id.IDs['ID_RBGroupBy']:
            self.gOp.GroupBy = event.GetSelection()

        elif event.GetId() ==  self.id.IDs['ID_RBKMLMode']:
            self.gOp.KMLsort = event.GetSelection()
        else:
            _log.error('We have a Problem 81')
    def SetRestulTypeRadioBox(self):
        rType = self.gOp.get('ResultType')
        
        if rType is ResultsType.HTML:
            outType = 0
        elif rType is ResultsType.KML:
            outType = 1
        elif rType is ResultsType.KML2:
            outType = 2
        elif rType is ResultsType.SUM:
            outType = 3
        else:
            outType = 0
        self.id.RBResultOutType.SetSelection(outType)
    

    def EvtText(self, event):
        cbid = event.GetId()
        if event.GetId() == self.id.IDs['ID_TEXTResult'] or event.GetId() == self.id.IDs['ID_TEXTDefaultCountry']:
            self.gOp.set(self.id.IDtoAttr[cbid][2], event.GetString())
            _log.debug("TXT %s set value %s", self.id.IDtoAttr[cbid][0], self.id.IDtoAttr[cbid][2])
        else:
            _log.error("uncontrolled TEXT")
            self.SetupButtonState()

    def EvtCheckBox(self, event):

        _log.debug('%s for %i', event.IsChecked(), event.GetId() )
        cb = event.GetEventObject()
        if cb.Is3State():
            _log.debug("3StateValue: %s", cb.Get3StateValue())
        cbid = event.GetId()
        _log.debug('set %s to %s (%s)', self.id.IDtoAttr[cbid][0], cb.GetValue(), self.id.IDtoAttr[cbid][1] )
        if cbid == self.id.IDs['ID_CBSummary']:
            extra = cb.Name
        else:
            extra = ''
        self.gOp.set( self.id.IDtoAttr[cbid][0]+extra, cb.GetValue())
        
        if cbid == self.id.IDs['ID_CBHeatMap'] or cbid == self.id.IDs['ID_CBMapTimeLine'] or cbid == self.id.IDs['ID_CBMarksOn']:
            self.SetupButtonState()
        if ( self.id.IDtoAttr[cbid][1] == 'Redraw'):
            self.NeedRedraw()
        elif ( self.id.IDtoAttr[cbid][1] == 'Reload'):
            self.NeedReload()
        elif ( self.id.IDtoAttr[cbid][1] == 'Render'):
            self.background_process.updategrid = True
        elif ( self.id.IDtoAttr[cbid][1] == ''):
            pass # Nothing to do for this one
        else:
            _log.error("uncontrolled CB %d with '%s'", cbid,   self.id.IDtoAttr[cbid][1])
        if cbid == self.id.IDs['ID_CBAllEntities'] and cb.GetValue():
            # TODO Fix this up
            if self.gOp.get('ResultType'):
                dlg = None
                if getattr(self.background_process, 'people', None):
                    if len(self.background_process.people) > 200:
                        dlg = wx.MessageDialog(self, f'Caution, {len(self.background_process.people)} people in your tree\n it may create very large HTML files and may not open in the browser',
                                   'Warning', wx.OK | wx.ICON_WARNING)
                else:
                    dlg = wx.MessageDialog(self, 'Caution, if you load a GEDCOM with lots of people in your tree\n it may create very large HTML files and may not open in the browser',
                                   'Warning', wx.OK | wx.ICON_WARNING)

                if dlg:                    
                    dlg.ShowModal()
                    dlg.Destroy()
        

    def EvtButton(self, event):
        myid = event.GetId() 
        _log.debug("Click! (%d)", myid)
        # TODO HACK
    #    self.SetupOptions()
        if myid == self.id.IDs['ID_BTNLoad']:
            self.LoadGEDCOM()
                
        elif myid == self.id.IDs['ID_BTNCreateFiles']:
            self.DrawGEDCOM()
                                
        elif myid == self.id.IDs['ID_BTNCSV']:
            self.OpenCSV()
        elif myid == self.id.IDs['ID_BTNTRACE']:
            self.SaveTrace()
        elif myid == self.id.IDs['ID_BTNSTOP']:
            self.gOp.set('stopping', True)
            self.gOp.set('parsed', False)
            self.NeedRedraw()
            self.NeedReload()
        elif myid == self.id.IDs['ID_BTNBROWSER']:
            self.OpenBrowser()
        else:
            _log.error("uncontrolled ID : %d", myid)

    def EvtListBox(self, event):

        eventid = event.GetId()
        _log.debug('%s, %s, %s', event.GetString(), event.IsSelection(), event.GetSelection())                            
        _ = event.GetEventObject()
        # if eventid == self.id.IDs['ID_LISTPlaceType']:
        #     places = {}
        #     for cstr in event.EventObject.CheckedStrings:
        #         places[cstr] = cstr
        #     if places == {}:
        #         places = {'native':'native'}
        #     panel.gOp.PlaceType = places
        # el
        if eventid == self.id.IDs['ID_LISTMapStyle']:
            
            self.gOp.MapStyle = sorted(self.id.AllMapTypes)[event.GetSelection()] 
            self.NeedRedraw()
        else:

            _log.error ("Uncontrol LISTbox")
    

    def EvtSpinCtrl(self, event):
        eventid = event.GetId()
        _log.debug('%s, %s, %s', event.GetString(), event.IsSelection(), event.GetSelection())                            
        _ = event.GetEventObject()
        if eventid == self.id.IDs['ID_INTMaxLineWeight']:
            self.gOp.MaxLineWeight = event.GetSelection()
            self.NeedRedraw()
        else:
            _log.error ("Uncontrol SPINbox")

    def EvtSlider(self, event):

        _log.debug('%s', event.GetSelection())
        self.gOp.HeatMapTimeStep = event.GetSelection()

    def OnMyTimer(self, evt: wx.TimerEvent) -> None:
        """Periodic timer callback used to update UI state from background worker."""
        if self.inTimer:
            return
        self.inTimer = True
        status = ''
        if self.gOp:
            if self.gOp.ShouldStop() or not self.gOp.running:
                if self.id.BTNSTOP.IsEnabled():
                    self.id.BTNSTOP.Disable()
            else:
                self.id.BTNSTOP.Enable()
            status = self.gOp.state
            if self.gOp.running:
                self.gOp.runningLast = 0
                status = f"{status} - Processing"
                nowtime = datetime.now().timestamp()
                runningtime = nowtime - self.gOp.runningSince
                if runningtime < 86400:     # 1 day
                    runtime = f"Running {time.strftime('%H:%M:%S', time.gmtime(runningtime))}"
                else:
                    runtime = f"Running {time.strftime('%jD %H:%M', time.gmtime(runningtime - 86400))}" 
                
                if self.gOp.countertarget > 0 and self.gOp.counter > 0 and self.gOp.counter != self.gOp.countertarget:
                    if nowtime-1.0 > self.lastruninstance: 
                        self.timeformat = '%H:%M:%S'
                        stepsleft = self.gOp.countertarget-self.gOp.counter
                        scaler = math.log(stepsleft, 100) if stepsleft > 1 else 1
                        remaintimeInstant = (nowtime - self.gOp.runningSinceStep)/self.gOp.counter * stepsleft* scaler
                        remaintimeInstant = remaintimeInstant if remaintimeInstant > 0 else 0
                        # Smoothed runtime average over last 5 seconds
                        self.gOp.runavg.append(remaintimeInstant)
                        if len(self.gOp.runavg) > 5:
                            self.gOp.runavg.pop(0)
                        remaintime = sum(self.gOp.runavg)/len(self.gOp.runavg)
                        self.remaintime = remaintime
                        self.lastruninstance = nowtime
                        if self.remaintime> 3600: 
                            self.timeformat = '%H hr %M'
                            if self.remaintime > 86400:  # 1 day
                                self.timeformat = '%j %H hr %M'
                                self.remaintime -= 86400
                    runtime = f"{runtime} ({time.strftime(self.timeformat, time.gmtime(self.remaintime))})"
            else:
                runtime = "Last {}".format( time.strftime('%H:%M:%S', time.gmtime(self.gOp.runningLast)))
                # Rest the runtime average
                self.gOp.runavg = []
            self.frame.SetStatusText(runtime,1) 
            if self.gOp.counter > 0:
                if self.gOp.countertarget > 0:
                    status = f"{status} : {self.gOp.counter/self.gOp.countertarget*100:.0f}% ({self.gOp.counter}/{self.gOp.countertarget})  "
                else:
                    status = f"{status} : {self.gOp.counter}"
                if self.gOp.stepinfo:
                    status = f"{status} ({self.gOp.stepinfo})"
            if self.gOp.ShouldStop():
                self.id.BTNCreateFiles.Enable()
                status = f"{status} - please wait.. Stopping"

            _, filen = os.path.split(self.gOp.get('GEDCOMinput'))
            if filen == "":
                self.id.BTNLoad.Disable()
                self.id.BTNCreateFiles.Disable()
            else:
                if not self.id.BTNLoad.IsEnabled():
                    self.id.BTNLoad.Enable()
                if not self.id.BTNLoad.IsEnabled():
                    self.id.BTNCreateFiles.Enable()
            if self.gOp.get('gpsfile') == '':
                self.id.BTNCSV.Disable()
            else:
                if not self.id.BTNCSV.IsEnabled():
                    self.id.BTNCSV.Enable()
        if not status or status == '':
            if self.gOp.selectedpeople and self.gOp.ResultType:
                status = f'Ready - {self.gOp.selectedpeople} people selected'
            else:
                status = 'Ready'
            self.OnBusyStop(-1)
        if self.frame:
            self.frame.SetStatusText(status)
        if self.background_process:
            if self.background_process.updateinfo or self.background_process.errorinfo or self.background_process.updategrid:
                self.OnCreateFiles(evt)
        if self.busystate != self.gOp.running:
            logging.info("Busy %d not Running %d", self.busystate, self.gOp.running)
            if self.gOp.running:
                self.gOp.runningSince = datetime.now().timestamp()
                self.OnBusyStart(-1)
            else:
                self.OnBusyStop(-1)
                self.StopTimer()
        if not self.gOp.running:
           self.gOp.countertarget = 0
           self.gOp.stepinfo = ""
           self.gOp.runningSince = datetime.now().timestamp()
           self.busycounthack += 1
           if self.busycounthack > 40:
                self.OnBusyStop(-1)
                self.busycounthack = 0
        wx.Yield()
        self.inTimer = False
    def StopTimer(self):
        self.gOp.runningLast = datetime.now().timestamp() - self.gOp.runningSince
    def OnBusyStart(self, evt):
        """ show the spinning Busy graphic """
        self.busystate = True
        self.id.busyIndicator.Start()
        self.id.busyIndicator.Show()
        wx.Yield()
            
    def OnBusyStop(self, evt):
        """ remove the spinning Busy graphic """
        self.id.busyIndicator.Stop()
        self.id.busyIndicator.Hide()
        self.busystate = False
        self.busycounthack = 0
        wx.Yield()

    def OnCreateFiles(self, evt: Any) -> None:
        """Handle background updates: grid refresh, infobox messages, errors."""
        # proces evt state hand off
        if hasattr(evt, 'state'):
            if evt.state == 'busy': 
                self.OnBusyStart(evt)
            if evt.state == 'done': 
                self.OnBusyStop(evt)
                self.StopTimer()
        if self.background_process.updategrid:
            self.background_process.updategrid = False
            saveBusy = self.busystate
            self.OnBusyStart(evt)
            self.peopleList.list.PopulateList(self.background_process.people, self.gOp.get('Main'), True)
            if self.gOp.newload:
                self.peopleList.list.ShowSelectedLinage(self.gOp.get('Main'))
            if not saveBusy:
                self.OnBusyStop(evt)
        newinfo = None
        if self.background_process.updateinfo:
            _log.debug("Infobox: %s", self.background_process.updateinfo)
            newinfo = self.background_process.updateinfo
            self.background_process.updateinfo = None
        if self.background_process.errorinfo:
            _log.debug("Infobox-Err: %s", self.background_process.errorinfo)
            einfo = f"<span foreground='red'><b>{self.background_process.errorinfo}</b></span>"
            newinfo = newinfo + '\n' + einfo if newinfo else einfo
            self.background_process.errorinfo = None
        if (newinfo):
            self.peopleList.append_info_box(newinfo)

    def SetupButtonState(self):
        """ based on the type of file output, enable/disable the interface """
        ResultTypeSelect = self.gOp.get('ResultType')
        self.SetRestulTypeRadioBox()
        # Always enabled
            # self.id.CBUseGPS
            # self.id.CBAllEntities
            # self.id.CBCacheOnly
            
        # Define control groups for HTML and KML modes
        html_controls = [
            self.id.LISTMapType, 
            self.id.CBMapControl,
            self.id.CBMapMini,
            self.id.CBHeatMap,
            self.id.CBUseAntPath,
            self.id.RBGroupBy,
            self.id.LISTHeatMapTimeStep
        ]
        marks_controls = [
            self.id.CBBornMark,
            self.id.CBDieMark,
            self.id.CBHomeMarker,
            self.id.CBMarkStarOn,
            ]
        kml_controls = [
            self.id.RBKMLMode,
            self.id.CBFlyTo,
            self.id.ID_INTMaxLineWeight
                    
        ]

        # Enable/Disable marker-dependent controls if markers are off
        if self.gOp.get('MarksOn'):
            for ctrl in marks_controls:
                ctrl.Enable()
        else:
            for ctrl in marks_controls:
                ctrl.Disable()
        # layout the Summary box, and KML box in the same space as the HTML box (toggle them off and on to dsisplay)
        # also forward the boxes to be there maximinum size, they may ahve been made small when setup and rendering
        
        # self.optionKbox.SetPosition(wx.Point(self.optionKbox.GetPosition().x, self.optionHbox.GetPosition().y))
        # if self.optionKbox.GetSize() != self.optionKbox.GetBestSize():
        #     self.optionKbox.SetSize(self.optionKbox.GetBestSize())
        # self.optionK2box.SetPosition(wx.Point(self.optionK2box.GetPosition().x, self.optionHbox.GetPosition().y))
        # if self.optionK2box.GetSize() != self.optionK2box.GetBestSize():
        #     self.optionK2box.SetSize(self.optionK2box.GetBestSize())
        # self.optionSbox.SetPosition(wx.Point(self.optionSbox.GetPosition().x, self.optionHbox.GetPosition().y))
        # if self.optionSbox.GetSize() != self.optionSbox.GetBestSize():
        #     self.optionSbox.SetSize(self.optionSbox.GetBestSize())
        # self.optionHbox.SetPosition(wx.Point(self.optionKbox.GetPosition().x, self.optionHbox.GetPosition().y))
        # if self.optionHbox.GetSize() != self.optionHbox.GetBestSize():
        #     self.optionHbox.SetSize(self.optionHbox.GetBestSize())
        # Enable/disable controls based on result type (HTML vs KML vs Summary Mode )
        
        self.optionHbox.Hide()
        self.optionSbox.Hide()
        self.optionKbox.Hide()
        self.optionK2box.Hide()
        # self.optionGbox.SetSize(self.optionGbox.GetBestSize())

        if ResultTypeSelect is ResultsType.HTML:
            # Enable HTML-specific controls
            for ctrl in html_controls:
                ctrl.Enable()
            
            # Handle heat map related controls
            self.id.CBMapTimeLine.Disable()
            self.id.LISTHeatMapTimeStep.Disable()
            
            if self.gOp.get('HeatMap'):
                self.id.CBMapTimeLine.Enable()
                # Only enable time step if timeline is enabled
                if self.gOp.get('MapTimeLine'):
                    self.id.LISTHeatMapTimeStep.Enable()
            for ctrl in kml_controls:
                ctrl.Disable()        
            self.optionHbox.Show()
            
        elif ResultTypeSelect is ResultsType.SUM:
            self.optionSbox.Show()

        elif ResultTypeSelect is ResultsType.KML:
            # In KML mode, disable HTML controls and enable KML controls
            for ctrl in html_controls:
                ctrl.Disable()
            for ctrl in kml_controls:
                ctrl.Enable()
            # This timeline just works differently in KML mode vs embedded code for HTML
            self.id.CBMapTimeLine.Enable()
            self.optionKbox.Show()
        elif ResultTypeSelect is ResultsType.KML2:
            self.optionK2box.Show()

       # Enable/disable trace button based on referenced data availability
        self.id.BTNTRACE.Enable(bool(self.gOp.Referenced and self.gOp.Result and ResultTypeSelect))

        self.optionsStack.Layout()
        self.Layout()
        self.Refresh()


    def SetupOptions(self) -> None:
        """Ensure file config and gvOptions are created and populate UI from options."""
        if not self.fileConfig:
            self.fileConfig = wx.Config("gedcomVisualGUI")
        
        if not self.gOp:
            self.gOp = gvOptions()
            self.gOp.panel = self
            self.gOp.BackgroundProcess = self.background_process
            self.gOp.UpdateBackgroundEvent = UpdateBackgroundEvent
            # self.peopleList.setGOp(self.gOp)
            self.peopleList.SetGOp(self.gOp)

        if self.gOp.get('ResultType'):
            self.id.RBResultOutType.SetSelection(0)
        else:
            if self.id.RBResultOutType.GetSelection() not in [1,2]:
                self.id.RBResultOutType.SetSelection(1)
        
        self.id.CBMapControl.SetValue(self.gOp.get('showLayerControl'))
        self.id.CBMapMini.SetValue(self.gOp.get('mapMini'))
        self.id.CBMarksOn.SetValue(self.gOp.get('MarksOn'))
        self.id.CBBornMark.SetValue(self.gOp.get('BornMark'))
        self.id.CBDieMark.SetValue(self.gOp.get('DieMark'))
        self.id.CBHomeMarker.SetValue(self.gOp.get('HomeMarker'))
        self.id.CBMarkStarOn.SetValue(self.gOp.get('MarkStarOn'))
        self.id.CBHeatMap.SetValue(self.gOp.get('HeatMap'))
        self.id.CBFlyTo.SetValue(self.gOp.get('UseBalloonFlyto'))
        self.id.CBMapTimeLine.SetValue(self.gOp.get('MapTimeLine'))
        self.id.CBUseAntPath.SetValue(self.gOp.get('UseAntPath'))
        self.id.CBUseGPS.SetValue(self.gOp.get('UseGPS'))
        self.id.CBUseGPS.Disable()
        self.id.CBAllEntities.SetValue(self.gOp.get('AllEntities'))
        self.id.CBCacheOnly.SetValue(self.gOp.get('CacheOnly'))
        self.id.LISTHeatMapTimeStep.SetValue(self.gOp.get('HeatMapTimeStep'))
        self.id.LISTMapType.SetSelection(self.id.LISTMapType.FindString(self.gOp.get('MapStyle')))
        self.id.ID_INTMaxLineWeight.SetValue(self.gOp.get('MaxLineWeight'))
        self.id.RBGroupBy.SetSelection(self.gOp.get('GroupBy'))
        self.id.TEXTResult.SetValue(self.gOp.get('Result'))

        _, filen = os.path.split(self.gOp.get('GEDCOMinput', ifNone='first.ged')) 
        self.id.TEXTGEDCOMinput.SetValue(filen)
        self.id.CBSummary[0].SetValue(self.gOp.get('SummaryOpen'))
        self.id.CBSummary[1].SetValue(self.gOp.get('SummaryPlaces'))
        self.id.CBSummary[2].SetValue(self.gOp.get('SummaryPeople'))
        self.id.CBSummary[3].SetValue(self.gOp.get('SummaryCountries'))
        self.id.CBSummary[4].SetValue(self.gOp.get('SummaryCountriesGrid'))
        self.id.CBSummary[5].SetValue(self.gOp.get('SummaryGeocode'))
        self.id.CBSummary[6].SetValue(self.gOp.get('SummaryAltPlaces'))
        self.id.TEXTDefaultCountry.SetValue(self.gOp.get('defaultCountry', ifNone=""))
        self.SetupButtonState()

        for t in self.threads:
            t.DefgOps(self.gOp)

        # Load file history into the panel's configuration
        self.frame.filehistory.Load(self.fileConfig)


    def updateOptions(self):
        pass

    def LoadGEDCOM(self):
        #TODO stop the previous actions and then do the load... need to be improved
        if self.background_process.IsTriggered(): 
            self.gOp.stopping = True
        else:
            self.OnBusyStart(-1)
            time.sleep(0.1)
            self.gOp.set('GridView', False)
            self.id.CBGridView.SetValue(False)
        
            cachepath, _ = os.path.split(self.gOp.get('GEDCOMinput'))
            if self.gOp.get('gpsfile'):
                sourcepath, _ = os.path.split(self.gOp.get('gpsfile'))
            else:
                sourcepath = None
            if self.gOp.lookup and cachepath != sourcepath:
                del self.gOp.lookup
                self.gOp.lookup = None
            self.gOp.step('Loading GEDCOM')
            self.background_process.Trigger(1)
        
    def DrawGEDCOM(self):

        if not self.gOp.get('Result') or self.gOp.get('Result') == '':
            _log.error("Error: Not output file name set")
            self.background_process.SayErrorMessage("Error: Please set the Output file name")
        else:
            self.OnBusyStart(-1)
            self.background_process.Trigger(2 | 4)


    def OpenCSV(self):
        self.runCMDfile(self.gOp.get('CSVcmdline'), self.gOp.get('gpsfile'))

    def runCMDfile(self, cmdline, datafile, isHTML=False):
        orgcmdline = cmdline
        if datafile and datafile != '' and datafile != None:
            cmdline = cmdline.replace('$n', f'{datafile}')
            try:
                if isHTML:          # Force it to run in a browsers
                    _log.info(f'browserstart {cmdline}')
                    webbrowser.open(datafile, new = 0, autoraise = True)
                elif orgcmdline == '$n':
                    if sys.platform == "win32":
                        _log.info(f'startfile {datafile}')
                        os.startfile(datafile)          # Native Windows method
                    elif sys.platform == "darwin":
                        opener = "open"
                        _log.info(f'subprocess.Popen {datafile}')
                        subprocess.Popen([opener, datafile])
                    else:
                        opener ="xdg-open"
                        if not shutil.which(opener):
                            raise EnvironmentError(f"{opener} not found. Install it or use a different method.")
                        _log.info(f'subprocess.Popen {datafile}')
                        subprocess.Popen([opener, datafile])
                else:
                    # it is suggesting a web URL
                    if cmdline.startswith('http'):
                        _log.info(f'webbrowswer run  `{cmdline}`')
                        webbrowser.open(cmdline, new = 0, autoraise = True)
                    else:
                        # does the command line contain the $n placeholder
                        if '$n' in orgcmdline:
                            _log.info(f'subprocess.Popen file {cmdline}')
                            subprocess.Popen(cmdline, shell=True)
                        else:
                            _log.info(f'subprocess.Popen line {cmdline};{datafile}')
                            subprocess.Popen([cmdline, datafile], shell=True)

                        # TODO need a better command-line management than this
                        # cmdline = f"column -s, -t < {csvfile} | less -#2 -N -S"
            except Exception as e:
                _log.exception("Issues in runCMDfile")
                _log.error(f"Failed to open file: {e}")

        else:
            _log.error(f"Error: runCMDfile-unknwon cmdline {datafile}")
    
    def SaveTrace(self):
        if self.gOp.Result and self.gOp.Referenced:
            if not self.gOp.lastlines:
                logging.error("No lastline values in SaveTrace (do draw first using HTML Mode for this to work)")
                return 
            tracepath = os.path.splitext(self.gOp.Result)[0] + ".trace.txt"
            # indentpath = os.path.splitext(self.gOp.Result)[0] + ".indent.txt"
            try:
                trace = open(tracepath , 'w')
            except Exception as e:
                logging.error("Error: Could not open trace file %s for writing %s", tracepath, e)
                self.background_process.SayErrorMessage(f"Error: Could not open trace file {tracepath} for writing {e}")
                return
            # indent = open(indentpath , 'w')
            trace.write("id\tName\tYear\tWhere\tGPS\tPath\n")
            # indent.write("this is an indented file with the number of generations driven by the parents\nid\tName\tYear\tWhere\tGPS\n") 
            people = self.background_process.people
            # Create a dictionary from the lines array with xid as the key
            for h in people:
                if self.gOp.Referenced.exists(people[h].xref_id):
                    refyear, _ = people[h].refyear()
                    (location, where) = people[h].bestlocation()
                    personpath = self.gOp.lastlines[people[h].xref_id].path
                    trace.write(f"{people[h].xref_id}\t{people[h].name}\t{refyear}\t{where}\t{location}\t" + "\t".join(personpath) + "\n") 
                    # indent.write("\t".join(personpath) + f",{people[h].xref_id}\t{people[h].name}\t{refyear}\t{where}\t{location}\n") 
            trace.close()
            # indent.close()
            _log.info(f"Trace file saved {tracepath}")
            # _log.info(f"Indent file saved {indentpath}")
            withall = "with all people" if self.gOp.get('AllEntities') else ""
            self.background_process.SayInfoMessage(f"Trace file {withall} saved: {tracepath}",True)
            self.runCMDfile(self.gOp.get('Tracecmdline'), tracepath)


    def OpenBrowser(self):
        if self.gOp.get('ResultType'):
            self.runCMDfile(self.gOp.get('KMLcmdline'), os.path.join(self.gOp.resultpath, self.gOp.Result), True)
            
        else:
            self.runCMDfile('$n', KMLMAPSURL, True)
            
    #################################################
    #TODO FIX ME UP            

    def open_html_file(self, html_path):
        # Open the HTML file in a new tab and store the web browser instance
        browser = webbrowser.get()
        browser_tab = browser.open_new_tab(html_path)
    
        # Wait for the page to load
        time.sleep(1)
    
        # Find the browser window that contains the tab and activate it
        for window in browser.windows():
            for tab in window.tabs:
                if tab == browser_tab:
                    window.activate()
                    break
            else:
                continue
            break
    
        # Reload the tab
        browser_tab.reload()
    def OnCloseWindow(self, evt=None):
        busy = wx.BusyInfo("One moment please, waiting for threads to die...")
        wx.Yield()
        self.myTimer.Stop()
        for t in self.threads:
            t.Stop()

        running = 1

        while running:
            running = 0

            for t in self.threads:
                running = running + t.IsRunning()

            time.sleep(0.1)

        self.Destroy()
    #==============================================================