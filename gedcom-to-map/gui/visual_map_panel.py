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
from datetime import datetime

from const import KMLMAPSURL

import wx

from .people_list_ctrl_panel import PeopleListCtrlPanel  # type: ignore
from .background_actions import BackgroundActions
from .layout_options import LayoutOptions
from .visual_gedcom_ids import VisualGedcomIds
from .visual_map_event_handlers import VisualMapEventHandler
from .visual_map_actions import VisualMapActions
from .font_manager import FontManager
from gedcom_options import gvOptions, ResultType  # type: ignore

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
        # action helpers handle commands that previously lived on this panel
        self.actions = VisualMapActions(self)

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
        self.id.TEXTResultFile.SetValue(self.gOp.get('ResultFile'))
        self.NeedReload()
        self.SetupButtonState()

    def SetResultTypeRadioBox(self):
        """Synchronize the result-type radio box selection with gOp.ResultType."""
        rType = self.gOp.get('ResultType')
        try:
            type_index = rType.index()
        except Exception:
            type_index = 0
            _log.error("SetResultTypeRadioBox: unknown ResultType %s", str(rType))

        self.id.RBResultType.SetSelection(type_index)

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

        # Enable/Disable marker-dependent controls if markers are off
        marks_on = self.gOp.get('MarksOn')
        for ctrl in LayoutOptions.get_marks_controls_list(self):
            if marks_on:
                ctrl.Enable()
            else:
                ctrl.Disable()

        self.optionHbox.Hide() # HTML options
        self.optionSbox.Hide() # Summary options
        self.optionKbox.Hide() # KML options
        self.optionK2box.Hide() # KML2 options
        # self.optionGbox.SetSize(self.optionGbox.GetBestSize())

        if ResultTypeSelect is ResultType.HTML:
            for ctrl in self.optionHbox.GetChildren():
                ctrl.Enable()
            
            # Handle heat map related controls
            self.id.CBMapTimeLine.Disable()
            self.id.LISTHeatMapTimeStep.Disable()
            
            if self.gOp.get('HeatMap'):
                self.id.CBMapTimeLine.Enable()
                # Only enable time step if timeline is enabled
                if self.gOp.get('MapTimeLine'):
                    self.id.LISTHeatMapTimeStep.Enable()
            for ctrl in self.optionKbox.GetChildren():
                ctrl.Disable()        
            self.optionHbox.Show()
            
        elif ResultTypeSelect is ResultType.SUM:
            self.optionSbox.Show()

        elif ResultTypeSelect is ResultType.KML:
            # In KML mode, disable HTML controls and enable KML controls
            for ctrl in self.optionHbox.GetChildren():
                ctrl.Disable()
            for ctrl in self.optionKbox.GetChildren():
                ctrl.Enable()
            # This timeline just works differently in KML mode vs embedded code for HTML
            self.id.CBMapTimeLine.Enable()
            self.optionKbox.Show()
        elif ResultTypeSelect is ResultType.KML2:
            self.optionK2box.Show()

       # Enable/disable trace button based on referenced data availability
        self.id.BTNTRACE.Enable(bool(self.gOp.Referenced and self.gOp.ResultFile and ResultTypeSelect))

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
            self.id.RBResultType.SetSelection(0)
        else:
            if self.id.RBResultType.GetSelection() not in [1,2]:
                self.id.RBResultType.SetSelection(1)
        
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

        self.id.LISTMapStyle.SetSelection(self.id.LISTMapStyle.FindString(self.gOp.get('MapStyle')))

        self.SetupButtonState()

        # Load file history into the panel's configuration
        self.frame.filehistory.Load(self.fileConfig)

    def updateOptions(self):
        pass

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

        for child in self.GetChildren():
            child.Destroy()
        for attr in ("peopleList", "panelA", "panelB", "optionSbox", "optionHbox", "optionKbox", "optionK2box", "id"):
            try:
                obj = getattr(self, attr, None)
                if obj and getattr(obj, "SetSizer", None):
                    try:
                        obj.SetSizer(None)
                    except Exception:
                        pass
                try:
                    setattr(self, attr, None)
                except Exception:
                    pass
            except Exception:
                _log.exception("OnCloseWindow: failed to delattr %s", attr)
        try:
            self.DestroyChildren()
        except Exception:
            _log.exception("OnCloseWindow: DestroyChildren failed")
        
        try:
            wx.CallAfter(self.Destroy)
        except Exception:
            _log.exception("OnCloseWindow: CallAfter Destroy failed")
        finally:
            try:
                del busy
            except Exception:
                pass
            if evt is not None:
                evt.Skip()

    def apply_controls_from_options(self, gOp: Any) -> None:
        """Apply values from gOp to wx controls using id metadata (clearer, helper-based)."""
        if not getattr(self, "id", None):
            return

        def resolve_value(gop_attr: str) -> Any:
            if not gop_attr:
                return None
            try:
                if hasattr(gOp, gop_attr):
                    return getattr(gOp, gop_attr)
                if hasattr(gOp, "get"):
                    return gOp.get(gop_attr, None)
            except Exception:
                _log.exception("resolve_value failed for %s", gop_attr)
            return None

        def set_text(control: wx.Window, name: str, value: Any) -> None:
            try:
                if name == "TEXTGEDCOMinput":
                    infile = gOp.get("GEDCOMinput", "") if hasattr(gOp, "get") else ""
                    _, filen = os.path.split(infile)
                    val = filen
                else:
                    val = "" if value is None else str(value)
                # Prefer ChangeValue (no EVT_TEXT) and fall back to SetValue/SetLabel
                try:
                    if getattr(control, "GetValue", None) and control.GetValue() != val:
                        if getattr(control, "ChangeValue", None):
                            control.ChangeValue(val)
                        else:
                            control.SetValue(val)
                except Exception:
                    try:
                        control.SetLabel(val)
                    except Exception:
                        _log.debug("Text set failed for %s", name)
            except Exception:
                _log.exception("set_text failed for %s", name)

        def set_checkbox(control: wx.Window, value: Any) -> None:
            try:
                control.SetValue(bool(value))
            except Exception:
                _log.debug("CheckBox set failed for %r", control)

        def set_selection(control: wx.Window, value: Any) -> None:
            try:
                control.SetSelection(int(value) if value is not None else 0)
            except Exception:
                _log.debug("Selection set failed for %r", control)

        def set_int(control: wx.Window, value: Any) -> None:
            try:
                control.SetValue(int(value))
            except Exception:
                _log.debug("Int/Slider set failed for %r", control)

        def set_button(control: wx.Window, value: Any) -> None:
            pass

        # dispatch mapping by wtype
        handlers = {
            "Text": set_text,
            "CheckBox": set_checkbox,
            "RadioButton": set_selection,
            "List": set_selection,
            "Slider": set_int,
            "Int": set_int,
            "SpinCtrl": set_int,
            "Button": set_button,
        }

        for name, idref, wtype, gop_attr, action in self.id.iter_controls():
            # resolve numeric id
            try:
                wid = int(idref)
            except Exception:
                try:
                    wid = idref.GetId()
                except Exception:
                    _log.debug("apply_controls_from_options: cannot resolve idref %r", idref)
                    continue

            control = wx.FindWindowById(wid, self)
            if control is None:
                continue

            value = resolve_value(gop_attr)

            try:
                # special controls
                if name == "LISTMapStyle":
                    ms = value or (gOp.get("MapStyle", "") if hasattr(gOp, "get") else value)
                    try:
                        idx = self.id.AllMapTypes.index(ms)
                    except Exception:
                        idx = 0
                    try:
                        control.SetSelection(idx)
                    except Exception:
                        _log.debug("LISTMapStyle: SetSelection failed for %r", control)
                    continue

                if name == "RBResultType":
                    order = ("HTML", "KML", "KML2", "SUM")
                    rt = getattr(gOp, "ResultType", None)
                    rt_name = getattr(rt, "value", str(rt) if rt is not None else "")
                    try:
                        idx = order.index(rt_name)
                    except ValueError:
                        idx = 0
                    try:
                        control.SetSelection(idx)
                    except Exception:
                        _log.debug("RBResultType: SetSelection failed for %r", control)
                    continue

                # generic handler dispatch
                handler = handlers.get(wtype)
                if handler:
                    handler(control, name, value) if handler is set_text else handler(control, value)
                else:
                    _log.debug("Unhandled control type %r for control %s", wtype, name)

            except Exception:
                _log.exception("apply_controls_from_options failed for control %s (id=%r)", name, idref)
