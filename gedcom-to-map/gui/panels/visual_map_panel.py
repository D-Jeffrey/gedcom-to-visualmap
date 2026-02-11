from render.result_type import ResultType
"""
visual_map_panel.py

Main panel for the Visual Map GUI.

This module provides VisualMapPanel, a wx.Panel subclass that builds the UI
controls, coordinates with the BackgroundActions worker, and reflects services
state into the UI.

Notes:
- Event handling has been delegated to visual_map_event_handlers.VisualMapEventHandler.
- Layout construction has been delegated to layout_options.LayoutOptions.
- This file contains only panel-level behaviour and lifecycle management.
"""
from typing import Optional, List, Any, TYPE_CHECKING
import logging
import time
import math
import os
from datetime import datetime

from const import KMLMAPSURL

import wx

from .people_list_ctrl_panel import PeopleListCtrlPanel  # type: ignore
from ..actions.background_actions import BackgroundActions
from ..layout.layout_options import LayoutOptions
from ..layout.visual_gedcom_ids import VisualGedcomIds
from ..layout.visual_map_event_handlers import VisualMapEventHandler
from ..actions.visual_map_actions import VisualMapActions
from ..layout.font_manager import FontManager
from ..layout.colour_manager import ColourManager

if TYPE_CHECKING:
    from services.interfaces import IConfig, IState, IProgressTracker

(UpdateBackgroundEvent, EVT_UPDATE_STATE) = wx.lib.newevent.NewEvent()

_log = logging.getLogger(__name__.lower())

class VisualMapPanel(wx.Panel):
    """
    Panel hosting primary controls and coordinating background processing.

    Responsibilities:
    - Construct and layout widgets (delegates layout to LayoutOptions).
    - Start/stop background worker threads and a periodic timer.
    - Mirror services state into UI controls and propagate UI changes back.
    - Provide UI-safe helpers for status, busy indicators and file/command launching.

    The heavy event logic is implemented in VisualMapEventHandler to keep this
    class focused on layout/state and lifecycle management.
    """

    # Public attributes with types for static analysis and readability
    font_manager: FontManager
    color_manager: ColourManager
    frame: wx.Frame
    svc_config: Any
    svc_state: Any
    svc_progress: Any
    id: VisualGedcomIds
    peopleList: PeopleListCtrlPanel
    background_process: BackgroundActions
    threads: List[Any]
    myTimer: Optional[wx.Timer]
    busystate: bool

    def __init__(
        self,
        parent: wx.Window,
        font_manager: 'FontManager',
        color_manager: 'ColourManager',
        svc_config: 'IConfig',
        svc_state: 'IState',
        svc_progress: 'IProgressTracker',
        *args: Any,
        **kw: Any,
    ) -> None:
        """Initialize the VisualMapPanel.

        Args:
            parent: Parent wxPython window.
            font_manager: FontManager instance for font management and styling.
            color_manager: ColourManager instance for colour management.
            svc_config: IConfig service for configuration storage.
            svc_state: IState service for runtime state access.
            svc_progress: IProgressTracker service for progress tracking and control.
            *args: Additional arguments for wx.Panel.
            **kw: Additional keyword arguments for wx.Panel.
            
        Side-effects:
            - Builds left/right sub-panels and people list view.
            - Constructs the options UI via LayoutOptions.build.
            - Instantiates event handler and starts background threads/timer.
        """
        # parent must be the wx parent for this panel; call panel initializer with it
        super().__init__(parent, *args, **kw)

        # Service-architecture references
        self.svc_config: 'IConfig' = svc_config
        self.svc_state: 'IState' = svc_state
        self.svc_progress: 'IProgressTracker' = svc_progress
        self.font_manager: 'FontManager' = font_manager
        self.color_manager: 'ColourManager' = color_manager

        self.SetMinSize((800,800))
        self.frame = self.TopLevelParent

        self.fileConfig = None
        self.busystate = False
        self.busycounthack = 0
        self.inTimer = False
        self.timeformat = '%H hr %M'
        self.SetAutoLayout(True)
        self.id = VisualGedcomIds(svc_config=self.svc_config)
        
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
        self.panelA.SetBackgroundColour(self.color_manager.get_color('INFO_BOX_BACKGROUND'))
        # Use system default for panelB to support dark mode
        if not self.color_manager.is_dark_mode():
            self.panelB.SetBackgroundColour(wx.WHITE)
        # In dark mode, let system handle the background color

        main_hs = wx.BoxSizer(wx.HORIZONTAL)
        main_hs.Add(self.panelA, 1, wx.EXPAND | wx.ALL, 5)
        main_hs.Add(self.panelB, 0, wx.EXPAND | wx.ALL, 5)
        self.SetSizer(main_hs)
        self.Layout()

        # Add Data Grid on Left panel
        self.peopleList = PeopleListCtrlPanel(self.panelA, self.id.m, self.font_manager, self.color_manager, svc_config=self.svc_config, svc_state=self.svc_state, svc_progress=self.svc_progress)
        
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
    
    def refresh_colors(self) -> None:
        """Refresh all UI colors after appearance mode change."""
        # Update panel backgrounds
        self.panelA.SetBackgroundColour(self.color_manager.get_color('INFO_BOX_BACKGROUND'))
        if not self.color_manager.is_dark_mode():
            self.panelB.SetBackgroundColour(wx.WHITE)
        else:
            # In dark mode, reset to system default
            self.panelB.SetBackgroundColour(wx.NullColour)
        
        # Note: Input File, Output File, and Configuration Options buttons use system defaults
        # (color=None) and automatically adapt to appearance changes. No manual color refresh needed.
        
        # Refresh people list colors
        if hasattr(self, 'peopleList') and self.peopleList:
            self.peopleList.refresh_colors()
        
        # Force repaint
        self.Layout()
        self.Refresh()
        self.Update()
 
    def start_threads_and_timer(self) -> None:
         """Start background worker thread(s) and the periodic UI timer.

         This binds EVT_TIMER to OnMyTimer and EVT_UPDATE_STATE to the handler's
         OnCreateFiles method so background updates can be applied to the UI.
         """
         self.threads = []
         self.background_process = BackgroundActions(self, 0, self, self.svc_config, self.svc_state, self.svc_progress)
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
        self.svc_state.parsed = False
        self.id.BTNLoad.SetBackgroundColour(self.color_manager.get_color('BTN_PRESS'))
        self.NeedRedraw()

    def NeedRedraw(self):
        """Mark options that a redraw is required and update button visuals."""
        self.id.BTNCreateFiles.SetBackgroundColour(self.color_manager.get_color('BTN_PRESS'))

    def setInputFile(self, path):
        """Set GEDCOM input path via services, update UI text and persist."""
        # Normalize input to ensure .ged extension
        try:
            base, ext = os.path.splitext(path or "")
            normalized_input = path if ext else (path + ".ged" if path else "")
        except Exception:
            normalized_input = path

        # Use setInput to ensure ResultFile is updated correctly
        try:
            self.svc_config.setInput(normalized_input, generalRequest=True)
            _log.debug("After setInput: ResultFile=%s", self.svc_config.get('ResultFile', 'NOT SET'))
        except Exception:
            _log.exception("Failed to set GEDCOMinput on svc_config")

        # Update the input filename field
        _, filen = os.path.split(normalized_input or "")
        try:
            self.id.TEXTGEDCOMinput.SetValue(filen)
        except Exception:
            _log.debug("Failed to set TEXTGEDCOMinput")

        # Update the output filename field from config (setInput already set ResultFile)
        try:
            result_file = self.svc_config.get('ResultFile', '')
            _log.debug("Setting TEXTResultFile to: %s", result_file)
            self.id.TEXTResultFile.SetValue(result_file)
        except Exception:
            _log.exception("Failed to update TEXTResultFile")

        # Persist to user config storage
        try:
            self.fileConfig.Write("GEDCOMinput", normalized_input)
        except Exception:
            _log.debug("Failed to write GEDCOMinput to fileConfig")

        # Mark UI for reload and refresh button states
        self.NeedReload()
        self.SetupButtonState()

    def SetResultTypeRadioBox(self):
        """Synchronize the result-type radio box selection with ResultType from services."""
        try:
            rType = self.svc_config.get('ResultType')
        except Exception:
            rType = None
        try:
            type_index = rType.index()
        except Exception:
            type_index = 0
            _log.error("SetResultTypeRadioBox: unknown ResultType %s", str(rType))

        self.id.RBResultType.SetSelection(type_index)

    def get_runtime_string(self) -> str:
        """Return a formatted running/ETA string based on services timing and counters.

        The string is suitable for display in a status pane and does not touch UI.
        """

        nowtime = datetime.now().timestamp()
        running_since = getattr(self.svc_progress, "running_since", nowtime)
        runningtime = nowtime - running_since

        # Base running label
        if runningtime < 86400:     # 1 day
            runtime = f"Running {time.strftime('%H:%M:%S', time.gmtime(runningtime))}"
        else:
            runtime = f"Running {time.strftime('%jD %H:%M', time.gmtime(runningtime - 86400))}" 
        
        # ETA calculation if counters available
        countertarget = getattr(self.svc_progress, "target", 0)
        counter = getattr(self.svc_progress, "counter", 0)
        if countertarget > 0 and counter > 0 and counter != countertarget:
            # update ETA display every second
            if nowtime-1.0 > self.lastruninstance: 
                self.timeformat = '%H:%M:%S'
                stepsleft = countertarget - counter
                scaler = math.log(stepsleft, 100) if stepsleft > 1 else 1
                running_since_step = getattr(self.svc_progress, "running_since_step", nowtime)
                remaintimeInstant = (nowtime - running_since_step)/max(counter, 1) * stepsleft* scaler
                remaintimeInstant = remaintimeInstant if remaintimeInstant > 0 else 0
                # Smoothed runtime average over last 5 seconds
                runavg = getattr(self.svc_state, "runavg", [])
                try:
                    runavg.append(remaintimeInstant)
                    if len(runavg) > 5:
                        runavg.pop(0)
                except Exception:
                    pass
                try:
                    remaintime = sum(runavg)/len(runavg) if runavg else 0
                except Exception:
                    remaintime = 0
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
        status = getattr(self.svc_progress, "state", "")
        if running:
            try:
                self.svc_progress.running_last = 0
            except Exception:
                pass
            status = f"{status} - Processing"
            runtime = self.get_runtime_string()
        else:
            running_last = getattr(self.svc_progress, "running_last", 0)
            runtime = "Last {}".format( time.strftime('%H:%M:%S', time.gmtime(running_last)))
            try:
                self.svc_state.runavg = []
            except Exception:
                pass
        return status, runtime
    
    def get_status_progress_string(self, status: str) -> str:
        """Append counter/progress information to the provided status string."""
        counter = getattr(self.svc_progress, "counter", 0)
        countertarget = getattr(self.svc_progress, "target", 0)
        stepinfo = getattr(self.svc_progress, "step_info", "")
        
        # Show progress if we have a target (even when counter is 0) or if counter > 0
        if countertarget > 0 or counter > 0:
            if countertarget > 0:
                pct = counter/countertarget*100 if countertarget else 0
                status = f"{status} : {pct:.0f}% ({counter}/{countertarget})  "
            else:
                status = f"{status} : {counter}"
            if stepinfo:
                status = f"{status} ({stepinfo})"
        return status
    
    def check_if_should_stop(self, status) -> str:
        """Return an updated status string if the background worker is stopping."""
        should_stop = False
        try:
            if hasattr(self.svc_progress, "should_stop"):
                should_stop = self.svc_progress.should_stop()
        except Exception:
            should_stop = False
        if should_stop:
            self.id.BTNCreateFiles.Enable()
            status = f"{status} - please wait.. Stopping"
        return status
    
    def update_load_create_buttons_display(self) -> None:
        """Enable/disable Load/Create buttons depending on whether input is set."""
        infile = self.svc_config.get('GEDCOMinput', "")
        _, filen = os.path.split(infile or "")
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
        gpsfile = self.svc_config.get('gpsfile', '')
        if (gpsfile or '') == '':
            self.id.BTNCSV.Disable()
        else:
            if not self.id.BTNCSV.IsEnabled():
                self.id.BTNCSV.Enable()

    def get_status_if_ready(self, status: str) -> str:
        """Return a 'Ready' status string when no work is in progress."""
        if not status or status == '':
            selectedpeople = getattr(self.svc_state, 'selectedpeople', 0)
            result_type = self.svc_config.get('ResultType')
            if selectedpeople and result_type:
                status = f'Ready - {selectedpeople} people selected'
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
        running = getattr(self.svc_progress, 'running', False)
        if self.busystate != running:
            _log.info("Busy %d not Running %d", self.busystate, running)
            if running:
                try:
                    self.svc_progress.running_since = datetime.now().timestamp()
                except Exception:
                    pass
                self.OnBusyStart(-1)
            else:
                self.OnBusyStop(-1)
                self.UpdateTimer()

        if not running:
           try:
               self.svc_progress.target = 0
               self.svc_progress.step_info = ""
               self.svc_progress.running_since = datetime.now().timestamp()
           except Exception:
               pass
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
    
        # Enable/disable Stop button based on running state
        should_stop = False
        running = getattr(self.svc_progress, 'running', False)
        try:
            if hasattr(self.svc_progress, 'should_stop'):
                should_stop = self.svc_progress.should_stop()
        except Exception:
            should_stop = False
        self.update_stop_button_display(should_stop, running)
        self.update_load_create_buttons_display()
        self.update_csv_button_display()

        # Update status bar text
        status, runtime = self.get_status_runtime_string(running)
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
        """Update the running_last elapsed time computed from running_since."""
        now = datetime.now().timestamp()
        running_since = getattr(self.svc_progress, 'running_since', now)
        try:
            self.svc_progress.running_last = now - running_since
        except Exception:
            pass

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
            try:
                main_id = self.svc_config.get('Main')
            except Exception:
                main_id = None
            self.peopleList.list.PopulateList(self.background_process.people, main_id, True)
            newload_flag = getattr(self.svc_state, 'newload', False)
            if newload_flag:
                self.peopleList.list.ShowSelectedLinage(main_id)
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
        ResultTypeSelect = self.svc_config.get('ResultType')
        self.SetResultTypeRadioBox()
        # Always enabled
            # self.id.CBUseGPS
            # self.id.CBAllEntities
            # self.id.CBCacheOnly

        # Enable/Disable marker-dependent controls if markers are off
        marks_on = self.svc_config.get('MarksOn', False)
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
            
            try:
                heatmap_on = self.svc_config.get('HeatMap')
            except Exception:
                heatmap_on = False
            if heatmap_on:
                self.id.CBMapTimeLine.Enable()
                # Only enable time step if timeline is enabled
                try:
                    timeline_on = self.svc_config.get('MapTimeLine')
                except Exception:
                    timeline_on = False
                if timeline_on:
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
        referenced = getattr(self.svc_state, 'Referenced', None)
        result_file = self.svc_config.get('ResultFile')
        self.id.BTNTRACE.Enable(bool(referenced and result_file and ResultTypeSelect))

        self.optionsStack.Layout()
        self.Layout()
        self.Refresh()

    def SetupOptions(self) -> None:
        """Populate UI controls from stored options.

        Also binds services to background threads and restores file history.
        """
        if not self.fileConfig:
            self.fileConfig = wx.Config("gedcomVisualGUI")
        
        # UI wiring: set references in services for backward compatibility with background process
        # Removed direct assignment to svc_config.panel for config purity
        try:
            if hasattr(self.svc_progress, 'BackgroundProcess'):
                self.svc_progress.BackgroundProcess = self.background_process
        except Exception:
            pass
        try:
            if hasattr(self.svc_progress, 'UpdateBackgroundEvent'):
                self.svc_progress.UpdateBackgroundEvent = UpdateBackgroundEvent
        except Exception:
            pass
        
        # propagate services to the people list control
        self.peopleList.SetServices(self.svc_config, self.svc_state, self.svc_progress)

        result_type = self.svc_config.get('ResultType')
        if result_type:
            self.id.RBResultType.SetSelection(0)
        else:
            if self.id.RBResultType.GetSelection() not in [1,2]:
                self.id.RBResultType.SetSelection(1)
        
        # Populate UI widgets from services
        try:
            self.apply_controls_from_options()
        except Exception:
            _log.exception("SetupOptions: apply_controls_from_options failed")

        self.id.CBSummary[0].SetValue(self.svc_config.get('SummaryOpen'))
        self.id.CBSummary[1].SetValue(self.svc_config.get('SummaryPlaces'))
        self.id.CBSummary[2].SetValue(self.svc_config.get('SummaryPeople'))
        self.id.CBSummary[3].SetValue(self.svc_config.get('SummaryCountries'))
        self.id.CBSummary[4].SetValue(self.svc_config.get('SummaryCountriesGrid'))
        self.id.CBSummary[5].SetValue(self.svc_config.get('SummaryGeocode'))
        self.id.CBSummary[6].SetValue(self.svc_config.get('SummaryAltPlaces'))
        self.id.CBSummary[7].SetValue(self.svc_config.get('SummaryEnrichmentIssues'))
        self.id.CBSummary[8].SetValue(self.svc_config.get('SummaryStatistics'))

        mark_star_on = self.svc_config.get('MarkStarOn')
        self.id.CBMarkStarOn.SetValue(mark_star_on)

        map_style = self.svc_config.get('MapStyle')
        self.id.LISTMapStyle.SetSelection(self.id.LISTMapStyle.FindString(map_style))

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

    def apply_controls_from_options(self) -> None:
        """Apply values from services to wx controls using id metadata."""
        if not getattr(self, "id", None):
            return

        def resolve_value(attr: str) -> Any:
            if not attr:
                return None
            try:
                return self.svc_config.get(attr)
            except Exception:
                return None

        def set_text(control: wx.Window, name: str, value: Any) -> None:
            try:
                if name == "TEXTGEDCOMinput":
                    try:
                        infile = self.svc_config.get("GEDCOMinput", "")
                    except Exception:
                        infile = ""
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

        for name, idref, wtype, config_attr, action in self.id.iter_controls():
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

            value = resolve_value(config_attr)

            try:
                # special controls
                if name == "LISTMapStyle":
                    ms = self.svc_config.get("MapStyle", "")
                    try:
                        idx = self.svc_config.map_types.index(ms)
                    except Exception:
                        idx = 0
                    try:
                        control.SetSelection(idx)
                    except Exception:
                        _log.debug("LISTMapStyle: SetSelection failed for %r", control)
                    continue

                if name == "RBResultType":
                    order = ("HTML", "KML", "KML2", "SUM")
                    try:
                        rt = self.svc_config.get("ResultType")
                        # ResultType.get() now ensures proper Enum with uppercase .value
                        rt_name = rt.value if rt else ""
                    except Exception as e:
                        _log.debug("RBResultType: Failed to get ResultType: %s", e)
                        rt_name = ""
                    
                    # Find index in order tuple, default to 0 if not found
                    if not rt_name:
                        idx = 0
                    else:
                        try:
                            idx = order.index(rt_name)
                        except ValueError:
                            _log.debug("RBResultType: rt_name '%s' not in order tuple, defaulting to 0", rt_name)
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
