"""
visual_map_panel.py

Main panel for the Visual Map GUI.

This module provides VisualMapPanel, a wx.Panel subclass that builds the UI
controls, coordinates with the BackgroundActions worker, and reflects gvOptions
state into the UI.

Notes:
- Event handling has been delegated to visual_map_event_handlers.VisualMapEventHandler.
- Layout construction has been delegated to layout_options.LayoutOptions.
- This file contains only panel-level behaviour and lifecycle management.
"""
from typing import Optional, List, Any
import logging
import time
import math
import os
import sys
import subprocess
import webbrowser
import shutil
from datetime import datetime

from const import KMLMAPSURL

import wx

from .people_list_ctrl_panel import PeopleListCtrlPanel  # type: ignore
from .background_actions import BackgroundActions
from .layout_options import LayoutOptions
from .visual_gedcom_ids import VisualGedcomIds
from .visual_map_event_handlers import VisualMapEventHandler
from gedcom_options import gvOptions, ResultsType  # type: ignore
from style.stylemanager import FontManager

(UpdateBackgroundEvent, EVT_UPDATE_STATE) = wx.lib.newevent.NewEvent()

_log = logging.getLogger(__name__.lower())

class VisualMapPanel(wx.Panel):
    """
    Panel hosting primary controls and coordinating background processing.

    Responsibilities:
    - Construct and layout widgets (delegates layout to LayoutOptions).
    - Start/stop background worker threads and a periodic timer.
    - Mirror gvOptions state into UI controls and propagate UI changes back.
    - Provide UI-safe helpers for status, busy indicators and file/command launching.

    The heavy event logic is implemented in VisualMapEventHandler to keep this
    class focused on layout/state and lifecycle management.
    """

    # Public attributes with types for static analysis and readability
    font_manager: FontManager
    frame: wx.Frame
    gOp: gvOptions
    id: VisualGedcomIds
    peopleList: PeopleListCtrlPanel
    background_process: BackgroundActions
    threads: List[Any]
    myTimer: Optional[wx.Timer]
    busystate: bool

    def __init__(self, parent: wx.Window, font_manager: FontManager, gOp: gvOptions,
                 *args: Any, **kw: Any) -> None:
        """
        Initialize the VisualMapPanel.

        Args:
            parent: WX parent window.
            font_manager: FontManager instance used to compute and apply fonts.
            gOp: Optional gvOptions instance; if not supplied a new gvOptions will be
                 created during SetupOptions().
        Side-effects:
            - Builds left/right sub-panels and people list.
            - Constructs the options UI via LayoutOptions.build.
            - Instantiates event handler and starts background threads/timer.
        """
        # parent must be the wx parent for this panel; call panel initializer with it
        super().__init__(parent, *args, **kw)

        self.gOp = gOp
        self.font_manager = font_manager

        self.SetMinSize((800,800))
        self.frame = self.TopLevelParent

        self.fileConfig = None
        self.busystate = False
        self.busycounthack = 0
        self.inTimer = False
        self.timeformat = '%H hr %M'
        self.SetAutoLayout(True)
        self.id = VisualGedcomIds()
        
        self.make_panels()

        # wire event bindings via the handler and start background threads/timer
        self.handlers.bind()
        self.start_threads_and_timer()

        self.lastruninstance = 0.0
        self.remaintime = 0

        # Configure panel options
        self.SetupOptions()

    def make_panels(self) -> None:
        """Construct left/right sub-panels and people list."""
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
        self.peopleList = PeopleListCtrlPanel(self.panelA, self.id.m, self.font_manager, self.gOp)
        
        # create handler first so LayoutOptions.build (which no longer binds)
        # can safely be used; handler will be used to wire event bindings next
        self.handlers = VisualMapEventHandler(self)

        # Add all the labels, button and radiobox to Right Panel using LayoutOptions helper
        LayoutOptions.build(self, self.panelB)

        pa_sizer = wx.BoxSizer(wx.VERTICAL)
        pa_sizer.Add(self.peopleList, 1, wx.EXPAND | wx.ALL, 5)
        self.panelA.SetSizer(pa_sizer)
        self.panelA.Layout()

        # compute a sensible width for the right-hand options panel
        LayoutOptions.adjust_panel_width(self)

    def start(self) -> None:
        """Perform UI startup actions (currently triggers SetupButtonState)."""

    def stop(self):
        """Placeholder for panel shutdown logic (not implemented)."""

    def stop_timer(self):
        """Stop the periodic wx.Timer if running and unbind associated handler."""
        if self.myTimer and self.myTimer.IsRunning():
            try:
                self.myTimer.Stop()
            except Exception:
                pass
            try:
                self.Unbind(wx.EVT_TIMER, handler=self.OnMyTimer)
            except Exception:
                pass

    def set_current_font(self) -> None:
        """Apply current font to panel and children and adjust layout accordingly."""
        self.font_manager.apply_current_font_recursive(self)
        self.font_manager.apply_current_font_recursive(self.peopleList)
        # adjust right-hand panel width to match new font metrics
        wx.CallAfter(LayoutOptions.adjust_panel_width, self)
        self.Layout()
        self.Refresh()
 
    def start_threads_and_timer(self) -> None:
         """Start background worker thread(s) and the periodic UI timer.

         This binds EVT_TIMER to OnMyTimer and EVT_UPDATE_STATE to the handler's
         OnCreateFiles method so background updates can be applied to the UI.
         """
         self.threads = []
         self.background_process = BackgroundActions(self, 0, self.gOp)
         self.threads.append(self.background_process)
         for t in self.threads:
             t.Start()
         # Bind timer events and the custom update event to the handler
         self.Bind(wx.EVT_TIMER, self.OnMyTimer)
         # Bind the background update event to the handler (EVT_UPDATE_STATE is module-level in this file)
         self.Bind(EVT_UPDATE_STATE, self.handlers.OnCreateFiles)
         self.myTimer = wx.Timer(self)
         self.myTimer.Start(500)
    
    def NeedReload(self):
        """Mark options that a reload is required and update button visuals."""
        if self.gOp:
            self.gOp.parsed= False
        self.id.BTNLoad.SetBackgroundColour(self.id.GetColor('BTN_PRESS'))
        self.NeedRedraw()

    def NeedRedraw(self):
        """Mark options that a redraw is required and update button visuals."""
        self.id.BTNCreateFiles.SetBackgroundColour(self.id.GetColor('BTN_PRESS'))

    def setInputFile(self, path):
        """Set GEDCOM input path, update UI text and persist to config."""
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

    def SetResultTypeRadioBox(self):
        """Synchronize the result-type radio box selection with gOp.ResultType."""
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

    def get_runtime_string(self) -> str:
        """Return a formatted running/ETA string based on gOp timing and counters.

        The string is suitable for display in a status pane and does not touch UI.
        """

        nowtime = datetime.now().timestamp()
        runningtime = nowtime - self.gOp.runningSince

        # Base running label
        if runningtime < 86400:     # 1 day
            runtime = f"Running {time.strftime('%H:%M:%S', time.gmtime(runningtime))}"
        else:
            runtime = f"Running {time.strftime('%jD %H:%M', time.gmtime(runningtime - 86400))}" 
        
        # ETA calculation if counters available
        if self.gOp.countertarget > 0 and self.gOp.counter > 0 and self.gOp.counter != self.gOp.countertarget:
            # update ETA display every second
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
            # append ETA to runtime display
            runtime = f"{runtime} ({time.strftime(self.timeformat, time.gmtime(self.remaintime))})"
        return runtime
    
    def update_stop_button_display(self, should_stop: bool, running: bool) -> None:
        """Enable or disable the Stop button based on worker state flags."""
        if should_stop or not running:
            if self.id.BTNSTOP.IsEnabled():
                self.id.BTNSTOP.Disable()
        else:
            self.id.BTNSTOP.Enable()

    def get_status_runtime_string(self, running: bool) -> str:
        """Compose main status and short runtime string for the status bar."""
        status = self.gOp.state
        if running:
            self.gOp.runningLast = 0
            status = f"{status} - Processing"
            runtime = self.get_runtime_string()
        else:
            runtime = "Last {}".format( time.strftime('%H:%M:%S', time.gmtime(self.gOp.runningLast)))
            self.gOp.runavg = []
        return status, runtime
    
    def get_status_progress_string(self, status: str) -> str:
        """Append counter/progress information to the provided status string."""
        if self.gOp.counter > 0:
            if self.gOp.countertarget > 0:
                status = f"{status} : {self.gOp.counter/self.gOp.countertarget*100:.0f}% ({self.gOp.counter}/{self.gOp.countertarget})  "
            else:
                status = f"{status} : {self.gOp.counter}"
            if self.gOp.stepinfo:
                status = f"{status} ({self.gOp.stepinfo})"
        return status
    
    def check_if_should_stop(self, status) -> str:
        """Return an updated status string if the background worker is stopping."""
        if self.gOp.ShouldStop():
            self.id.BTNCreateFiles.Enable()
            status = f"{status} - please wait.. Stopping"
        return status
    
    def update_load_create_buttons_display(self) -> None:
        """Enable/disable Load/Create buttons depending on whether input is set."""
        _, filen = os.path.split(self.gOp.get('GEDCOMinput'))
        if filen == "":
            self.id.BTNLoad.Disable()
            self.id.BTNCreateFiles.Disable()
        else:
            if not self.id.BTNLoad.IsEnabled():
                self.id.BTNLoad.Enable()
            if not self.id.BTNCreateFiles.IsEnabled():
                self.id.BTNCreateFiles.Enable()

    def update_csv_button_display(self) -> None:
        """Enable/disable CSV button depending on whether a GPS file is configured."""
        if self.gOp.get('gpsfile') == '':
            self.id.BTNCSV.Disable()
        else:
            if not self.id.BTNCSV.IsEnabled():
                self.id.BTNCSV.Enable()

    def get_status_if_ready(self, status: str) -> str:
        """Return a 'Ready' status string when no work is in progress."""
        if not status or status == '':
            if self.gOp.selectedpeople and self.gOp.ResultType:
                status = f'Ready - {self.gOp.selectedpeople} people selected'
            else:
                status = 'Ready'
            self.OnBusyStop(-1)
        return status
    
    def check_background_process(self, evt) -> None:
        """Dispatch background-process update flags to OnCreateFiles when present."""
        if self.background_process:
            if self.background_process.updateinfo or self.background_process.errorinfo or self.background_process.updategrid:
                self.OnCreateFiles(evt)

    def check_update_running_state(self) -> None:
        """Synchronize busy/ running state and trigger busy indicator transitions."""
        if self.busystate != self.gOp.running:
            _log.info("Busy %d not Running %d", self.busystate, self.gOp.running)
            if self.gOp.running:
                self.gOp.runningSince = datetime.now().timestamp()
                self.OnBusyStart(-1)
            else:
                self.OnBusyStop(-1)
                self.UpdateTimer()

        if not self.gOp.running:
           self.gOp.countertarget = 0
           self.gOp.stepinfo = ""
           self.gOp.runningSince = datetime.now().timestamp()
           self.busycounthack += 1
           if self.busycounthack > 40:
                self.OnBusyStop(-1)
                self.busycounthack = 0

    def OnMyTimer(self, evt: wx.TimerEvent) -> None:
        """Periodic timer callback to refresh status, enable/disable controls and
        dispatch background updates to the UI.

        This method is intentionally lightweight and defers complex logic to
        helper methods so it remains robust when called frequently.
        """
        if self.inTimer:
            return
        self.inTimer = True

        # if no gOp, nothing to do
        if not getattr(self, "gOp", None):
            self.inTimer = False
            return
    
        # Enable/disable Stop button based on running state
        self.update_stop_button_display(self.gOp.ShouldStop(), self.gOp.running)
        self.update_load_create_buttons_display()
        self.update_csv_button_display()

        # Update status bar text
        status, runtime = self.get_status_runtime_string(self.gOp.running)
        self.frame.SetStatusText(runtime, 1)

        # progress / counter text augmentation
        status = self.get_status_progress_string(status)
        status = self.check_if_should_stop(status)
        status = self.get_status_if_ready(status)

        if self.frame:
            self.frame.SetStatusText(status)

        self.check_background_process(evt)

        self.check_update_running_state()

        wx.Yield()
        self.inTimer = False

    def UpdateTimer(self):
        """Update the runningLast elapsed time computed from runningSince."""
        self.gOp.runningLast = datetime.now().timestamp() - self.gOp.runningSince

    def OnBusyStart(self, evt):
        """Show and start the busy indicator (spinner)."""
        self.busystate = True
        self.id.busyIndicator.Start()
        self.id.busyIndicator.Show()
        wx.Yield()
            
    def OnBusyStop(self, evt):
        """Stop and hide the busy indicator and reset temporary counters."""
        self.id.busyIndicator.Stop()
        self.id.busyIndicator.Hide()
        self.busystate = False
        self.busycounthack = 0
        wx.Yield()

    def OnCreateFiles(self, evt: Any) -> None:
        """Apply updates coming from the background worker to the UI.

        Handles:
        - busy/done state transitions from the event `state` attribute.
        - grid/list population when updategrid is set.
        - appending info and error messages into the people list infobox.
        """
        # proces evt state hand off
        if hasattr(evt, 'state'):
            if evt.state == 'busy': 
                self.OnBusyStart(evt)
            if evt.state == 'done': 
                self.OnBusyStop(evt)
                self.UpdateTimer()

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
        """Enable/disable controls according to selected ResultType and options.

        This method lays out which groups of controls are active in HTML, KML,
        KML2 and Summary modes and refreshes the options stack visibility.
        """
        ResultTypeSelect = self.gOp.get('ResultType')
        self.SetResultTypeRadioBox()
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
            self.id.INTMaxLineWeight
        ]

        # Enable/Disable marker-dependent controls if markers are off
        if self.gOp.get('MarksOn'):
            for ctrl in marks_controls:
                ctrl.Enable()
        else:
            for ctrl in marks_controls:
                ctrl.Disable()

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
        """Create/configure gvOptions and populate UI controls from stored options.

        Also binds gvOptions to background threads and restores file history.
        """
        if not self.fileConfig:
            self.fileConfig = wx.Config("gedcomVisualGUI")
        
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
        
        # Populate UI widgets from gOp using the panel method (VisualGedcomIds is metadata-only)
        try:
            self.apply_controls_from_options(self.gOp)
        except Exception:
            _log.exception("SetupOptions: apply_controls_from_options failed")

        self.id.CBSummary[0].SetValue(self.gOp.get('SummaryOpen'))
        self.id.CBSummary[1].SetValue(self.gOp.get('SummaryPlaces'))
        self.id.CBSummary[2].SetValue(self.gOp.get('SummaryPeople'))
        self.id.CBSummary[3].SetValue(self.gOp.get('SummaryCountries'))
        self.id.CBSummary[4].SetValue(self.gOp.get('SummaryCountriesGrid'))
        self.id.CBSummary[5].SetValue(self.gOp.get('SummaryGeocode'))
        self.id.CBSummary[6].SetValue(self.gOp.get('SummaryAltPlaces'))

        self.id.TEXTDefaultCountry.SetValue(self.gOp.get('defaultCountry', ifNone=""))

        self.id.CBMarkStarOn.SetValue(self.gOp.get('MarkStarOn'))

        self.id.LISTMapType.SetSelection(self.id.LISTMapType.FindString(self.gOp.get('MapStyle')))

        self.SetupButtonState()

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
        """Run an external command or open a file/URL suggested by application options.

        - If isHTML then open datafile in a browser.
        - If cmdline == '$n' attempt to open the datafile with the platform default.
        - If cmdline contains '$n' substitute the datafile and shell-execute the result.
        - Otherwise try to launch the command with datafile as an argument.

        Exceptions are logged rather than raised to keep the UI responsive.
        """
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
        """Dump a trace file describing each referenced person and optionally open it."""

        if self.gOp.Result and self.gOp.Referenced:
            if not self.gOp.lastlines:
                _log.error("No lastline values in SaveTrace (do draw first using HTML Mode for this to work)")
                return 
            tracepath = os.path.splitext(self.gOp.Result)[0] + ".trace.txt"
            # indentpath = os.path.splitext(self.gOp.Result)[0] + ".indent.txt"
            try:
                trace = open(tracepath , 'w')
            except Exception as e:
                _log.error("Error: Could not open trace file %s for writing %s", tracepath, e)
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
        """Open the generated result in a browser or the default KML viewer."""
        if self.gOp.get('ResultType'):
            self.runCMDfile(self.gOp.get('KMLcmdline'), os.path.join(self.gOp.resultpath, self.gOp.Result), True)
            
        else:
            self.runCMDfile('$n', KMLMAPSURL, True)
            
    #################################################
    #TODO FIX ME UP            

    def open_html_file(self, html_path):
        """(Deprecated) older helper to attempt activation/reload of a browser tab.

        Kept for reference but not used; prefer runCMDfile / webbrowser.open instead.
        """
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
        """Gracefully stop worker threads and schedule safe destruction of the panel.

        This method performs a best-effort shutdown and then calls Destroy once
        background threads have terminated. It tolerates partially-initialised
        state when called during application teardown.
        """
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

    def apply_controls_from_options(self, gOp: Any) -> None:
        """Apply values from gOp to actual wx controls using id metadata.

        This keeps UI updates on the panel (where we have window context)
        while VisualGedcomIds remains a metadata-only helper.
        """
        if not getattr(self, "id", None):
            return
        for name, idref, wtype, gop_attr, action in self.id.iter_controls():
            # resolve numeric id
            try:
                wid = int(idref)
            except Exception:
                try:
                    wid = idref.GetId()  # fallback for other idref types
                except Exception:
                    _log.debug("apply_controls_from_options: cannot resolve idref %r", idref)
                    continue

            # find the control within this panel/window hierarchy
            control = wx.FindWindowById(wid, self)
            # read the value from gOp
            try:
                if gop_attr:
                    if hasattr(gOp, gop_attr):
                        value = getattr(gOp, gop_attr)
                    elif hasattr(gOp, "get"):
                        # fallback to get(key, default)
                        value = gOp.get(gop_attr, None)
                    else:
                        value = None
                else:
                    value = None
            except Exception:
                _log.exception("apply_controls_from_options: failed to read %s from gOp", gop_attr)
                value = None

            if control is None:
                # control not created yet (or not a child of this panel) — skip
                continue

            try:
                # handle special named controls first
                if name == "LISTMapStyle":
                    ms = value or gOp.get("MapStyle", "") if hasattr(gOp, "get") else value
                    try:
                        idx = self.id.AllMapTypes.index(ms)
                    except Exception:
                        idx = 0
                    try:
                        control.SetSelection(idx)
                    except Exception:
                        _log.debug("LISTMapStyle: SetSelection failed for %r", control)
                    continue

                if name == "RBResultsType":
                    order = ("HTML", "KML", "KML2", "SUM")
                    rt = getattr(gOp, "ResultType", None)
                    if hasattr(rt, "value"):
                        rt_name = rt.value
                    else:
                        rt_name = str(rt) if rt is not None else ""
                    try:
                        idx = order.index(rt_name)
                    except ValueError:
                        idx = 0
                    try:
                        control.SetSelection(idx)
                    except Exception:
                        _log.debug("RBResultsType: SetSelection failed for %r", control)
                    continue

                # generic handlers by widget type
                if wtype == "Text":
                    # TEXTGEDCOMinput should show filename only
                    if name == "TEXTGEDCOMinput":
                        infile = gOp.get("GEDCOMinput", "") if hasattr(gOp, "get") else ""
                        _, filen = os.path.split(infile)
                        val = filen
                    else:
                        val = "" if value is None else str(value)
                    try:
                        control.SetValue(val)
                    except Exception:
                        try:
                            control.SetLabel(val)
                        except Exception:
                            _log.debug("Text set failed for %s", name)

                elif wtype == "CheckBox":
                    try:
                        control.SetValue(bool(value))
                    except Exception:
                        _log.debug("CheckBox set failed for %s", name)

                elif wtype in ("RadioButton", "List"):
                    try:
                        control.SetSelection(int(value) if value is not None else 0)
                    except Exception:
                        _log.debug("Radio/List set failed for %s", name)

                elif wtype in ("Slider", "Int", "SpinCtrl"):
                    try:
                        control.SetValue(int(value))
                    except Exception:
                        _log.debug("Slider/Int set failed for %s", name)

                else:
                    _log.debug("Unhandled control type %r for control %s", wtype, name)

            except Exception:
                _log.exception("apply_controls_from_options failed for control %s (id=%r)", name, idref)