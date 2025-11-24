import _thread
import logging
import time
from pathlib import Path
from typing import Any, Optional

import wx

from .do_actions_type import DoActionsType

_log = logging.getLogger(__name__.lower())

class BackgroundActions:
    """Background worker thread for GEDCOM parsing, geocoding, and output generation.
    
    This class manages a background thread that performs time-consuming operations
    without blocking the UI. It uses DoActionsType flags to coordinate parse and
    generate operations, and communicates progress/results back to the UI via
    messages and events.
    
    The worker is designed to avoid circular imports by lazily importing heavy
    helper functions (ParseAndGPS, doHTML, doKML, etc.) inside the Run() method.
    
    Attributes:
        win: Parent wxPython window for posting events.
        gOp: Global options object (gedcom_options.gvOptions).
        people: Dictionary of Person objects keyed by xref_id (populated after parse).
        threadnum: Thread identifier for logging.
        updategrid: Flag indicating grid UI needs refresh.
        updategridmain: Flag for main grid update.
        updateinfo: Accumulated info messages to display to user.
        errorinfo: Accumulated error messages to display to user.
        keepGoing: Flag to control thread lifetime.
        threadrunning: Flag indicating if thread is currently running.
        doAction: Current action flags (DoActionsType).
        readyToDo: Flag indicating worker is ready to accept new work.
    
    Example:
        background = BackgroundActions(panel, threadnum=1, gOp=options)
        background.Start()
        background.Trigger(DoActionsType.PARSE | DoActionsType.GENERATE)
        # ... later ...
        background.Stop()
    """

    def __init__(self, win: wx.Window, threadnum: int, gOp):
        """Initialize background worker.
        
        Args:
            win: Parent wxPython window for posting events.
            threadnum: Unique thread identifier for logging.
            gOp: Global options object (gedcom_options.gvOptions).
        """
        self.win: wx.Window = win
        self.gOp = gOp  # Type depends on gedcom_options.gvOptions (avoid circular import)
        self.people: Optional[dict] = None
        self.threadnum: int = threadnum
        self.updategrid: bool = False
        self.updategridmain: bool = True
        self.updateinfo: str = ''  # This will prime the update
        self.errorinfo: Optional[str] = None
        self.keepGoing: bool = True
        self.threadrunning: bool = True
        self.doAction: DoActionsType = DoActionsType.NONE  # Initialize as DoActions instance with value NONE
        self.readyToDo: bool = True

    def Start(self) -> None:
        """Start the background worker thread.
        
        Resets state and spawns a new thread running the Run() method.
        """
        self.keepGoing = self.threadrunning = True
        self.doAction = DoActionsType.NONE
        _thread.start_new_thread(self.Run, ())

    def Stop(self) -> None:
        """Signal the background worker thread to stop.
        
        Sets the keepGoing flag to False, causing the Run() loop to exit.
        The thread will finish its current operation before stopping.
        """
        self.keepGoing = False

    def IsRunning(self) -> bool:
        """Check if the background worker thread is running.
        
        Returns:
            bool: True if thread is running, False otherwise.
        """
        return self.threadrunning

    def IsTriggered(self) -> bool:
        """Check if the worker has pending actions to perform.
        
        Returns:
            bool: True if any action flags are set (not NONE), False otherwise.
        """
        return self.doAction.doing_something()

    def _update_button_colours(self, dolevel: DoActionsType) -> None:
        """Update UI button colors based on pending actions.
        
        Sets button backgrounds to 'BTN_DONE' color for actions that will be performed.
        Used to provide visual feedback when operations are triggered.
        
        Args:
            dolevel: Action flags indicating which operations will be performed.
        """
        try:
            if dolevel.should_parse():
                self.gOp.panel.id.BTNLoad.SetBackgroundColour(self.gOp.panel.id.GetColor('BTN_DONE'))
            if dolevel.has_generate():
                self.gOp.panel.id.BTNCreateFiles.SetBackgroundColour(self.gOp.panel.id.GetColor('BTN_DONE'))
        except Exception:
            _log.exception("Update button colours: failed to update button colours")

    def Trigger(self, dolevel: DoActionsType) -> None:
        """Trigger background operations based on action flags.
        
        Sets the doAction flags to initiate background work. The Run() loop will
        detect the flags and execute the corresponding operations (parse/generate).
        Updates button colors to provide immediate visual feedback.
        
        Args:
            dolevel: Bit-flag combination specifying operations to perform
                    (e.g., DoActionsType.PARSE | DoActionsType.GENERATE).
        
        Example:
            # Trigger parse and generate
            background.Trigger(DoActionsType.PARSE | DoActionsType.GENERATE)
            
            # Trigger only parse
            background.Trigger(DoActionsType.PARSE)
        """
        _log.debug("Trigger: %s", dolevel)
        self._update_button_colours(dolevel)
        self.doAction = dolevel

    def SayInfoMessage(self, line: str, newline: bool = True) -> None:
        """Queue an informational message for display to the user.
        
        Messages are accumulated in updateinfo and displayed by the UI thread.
        
        Args:
            line: Message text to display.
            newline: If True, append newline before this message (default: True).
        """
        if newline and self.updateinfo and self.updateinfo != '':
            self.updateinfo = self.updateinfo + "\n"
        self.updateinfo = self.updateinfo + line if self.updateinfo else line

    def SayErrorMessage(self, line: str, newline: bool = True) -> None:
        """Queue an error message for display to the user.
        
        Messages are accumulated in errorinfo and displayed by the UI thread.
        
        Args:
            line: Error message text to display.
            newline: If True, append newline before this message (default: True).
        """
        if newline and self.errorinfo and self.errorinfo != '':
            self.errorinfo = self.errorinfo + "\n"
        self.errorinfo = self.errorinfo + line if self.errorinfo else line

    def _clear_people_data(self) -> None:
        """Clear people data from both instance and global options.
        
        Safely deletes the people dictionary and sets references to None.
        Used when starting a new parse operation or cleaning up after errors.
        """
        if hasattr(self, "people") and self.people:
            try:
                del self.people
            except Exception:
                pass
        self.gOp.people = None
        self.people = None

    def _report_parse_results(self) -> None:
        """Report parse operation results to the user via info/error messages.
        
        Displays success messages with person count and starting person info,
        or error messages if parsing failed or was aborted.
        Also sets the updategrid flag to trigger UI refresh.
        """
        if hasattr(self, "people") and self.people:
            _log.info("person count %d", len(self.people))
            self.updategrid = True
            if self.people:
                self.SayInfoMessage(f"Loaded {len(self.people)} people")
            else:
                self.SayInfoMessage(f"Cancelled loading people")
            if getattr(self.gOp, "Main", None):
                try:
                    self.SayInfoMessage(f" with '{self.gOp.Main}' as starting person from {Path(self.gOp.GEDCOMinput).name}", False)
                except Exception:
                    pass
        else:
            if getattr(self.gOp, "stopping", False):
                self.SayErrorMessage(f"Error: Aborted loading GEDCOM file", True)
            else:
                self.SayErrorMessage(f"Error: file could not read as a GEDCOM file", True)
                
    def _run_parse(self, panel_actions: Any, UpdateBackgroundEvent: Any = None) -> None:
        """Execute GEDCOM parsing and geocoding operation.
        
        Performs the following steps:
        1. Posts 'busy' event to UI
        2. Clears existing people data
        3. Calls ParseAndGPS to parse GEDCOM and geocode addresses
        4. Clears Referenced data (forces re-trace on next use)
        5. Reports results to user
        
        On error, clears people data, resets action flags, and reports error messages.
        
        Args:
            panel_actions: Panel actions object with ParseAndGPS method.
            UpdateBackgroundEvent: Optional event class for posting UI updates.
        """
        if UpdateBackgroundEvent:
            wx.PostEvent(self.win, UpdateBackgroundEvent(state='busy'))
        wx.Yield()
        _log.info("start ParseAndGPS")
        
        # Clear existing people data
        self._clear_people_data()
        
        _log.info("ParseAndGPS")
        try:
            if hasattr(panel_actions, "ParseAndGPS"):
                # ParseAndGPS may take time; ensure it can be interrupted by cooperative checks in that code
                self.people = panel_actions.ParseAndGPS(self.gOp, 1)
            else:
                _log.error("Run: panel_actions.ParseAndGPS not available")
                self.people = None
        except Exception as e:
            _log.exception("Issues in ParseAndGPS")
            self._clear_people_data()
            self.doAction = DoActionsType.NONE
            self.gOp.stopping = False
            _log.warning(str(e))
            self.SayErrorMessage('Failed to Parse', True)
            self.SayErrorMessage(str(e), True)
            return

        # Clear Referenced if parsing completed
        if self.doAction.has_parse() and getattr(self.gOp, "Referenced", None):
            try:
                del self.gOp.Referenced
                self.gOp.Referenced = None
            except Exception:
                pass

        # Report results
        self._report_parse_results()

    def _dispatch_generation(self, panel_actions: Any, result_type_name: str, fname: str) -> None:
        """Dispatch to appropriate output generation method based on result type.
        
        Calls the corresponding generation method (doHTML, doKML, doKML2, or doSUM)
        and displays a success message. Logs error if the required method is not available.
        
        Args:
            panel_actions: Panel actions object with generation methods
                          (doHTML, doKML, doKML2, doSUM).
            result_type_name: Name of the result type ("HTML", "KML", "KML2", or "SUM").
            fname: Output filename for display in success message.
        
        Raises:
            Logs error and displays error message for unknown result types.
        """
        if result_type_name == "HTML":
            if hasattr(panel_actions, "doHTML"):
                panel_actions.doHTML(self.gOp, self.people, True)
            else:
                _log.error("Run: panel_actions.doHTML not available")
            self.SayInfoMessage(f"HTML generated for {getattr(self.gOp, 'totalpeople', '?')} people ({fname})")
        elif result_type_name == "KML":
            if hasattr(panel_actions, "doKML"):
                panel_actions.doKML(self.gOp, self.people)
            else:
                _log.error("Run: panel_actions.doKML not available")
            self.SayInfoMessage(f"KML file generated for {getattr(self.gOp, 'totalpeople', '?')} people/points ({fname})")
        elif result_type_name == "KML2":
            if hasattr(panel_actions, "doKML2"):
                panel_actions.doKML2(self.gOp, self.people)
            else:
                _log.error("Run: panel_actions.doKML2 not available")
            self.SayInfoMessage(f"KML2 file generated for {getattr(self.gOp, 'totalpeople', '?')} people/points ({fname})")
        elif result_type_name == "SUM":
            if hasattr(panel_actions, "doSUM"):
                panel_actions.doSUM(self.gOp)
            else:
                _log.error("Run: panel_actions.doSUM not available")
            self.SayInfoMessage(f"Summary files generated ({fname})")
        else:
            self.SayErrorMessage(f"Error: Unknown Result Type {result_type_name}", True)

    def _run_generate(self, panel_actions: Any, UpdateBackgroundEvent: Any = None) -> None:
        """Execute output generation operation (HTML/KML/SUM).
        
        Validates that GEDCOM is parsed and result type is set, then dispatches
        to the appropriate generation method. Returns early if validation fails.
        
        Args:
            panel_actions: Panel actions object with generation methods
                          (doHTML, doKML, doKML2, doSUM).
            UpdateBackgroundEvent: Optional event class for posting UI updates.
        
        Returns:
            Returns early without generating output if:
            - GEDCOM is not parsed (gOp.parsed is False)
            - Result type is not set (gOp.ResultType is None)
        """
        _log.info("start do 2")
        if not getattr(self.gOp, "parsed", False):
            _log.info("not parsed")
            return
        
        fname = getattr(self.gOp, "ResultFile", None)
        if getattr(self.gOp, "ResultType", None) is None:
            _log.error("Run: ResultType not set")
            return
        
        # call appropriate generation function if available
        result_type_name = getattr(self.gOp, "ResultType", None).name
        try:
            self._dispatch_generation(panel_actions, result_type_name, fname)
        except Exception:
            _log.exception("Error while generating output")

    def _reset_button_colours(self) -> None:
        """Reset UI button background colors to default state.
        
        Resets both Load and CreateFiles buttons to 'BTN_DEFAULT' color.
        Called when operations complete or are cancelled.
        """
        try:
            default_color = self.gOp.panel.id.GetColor('BTN_DEFAULT')
            self.gOp.panel.id.BTNLoad.SetBackgroundColour(default_color)
            self.gOp.panel.id.BTNCreateFiles.SetBackgroundColour(default_color)
        except Exception:
            _log.exception("_reset_button_colours: failed to reset button colours")

    def _update_button_colours_done(self, dolevel: DoActionsType) -> None:
        """Update UI button colors to indicate completed operations.
        
        Sets button backgrounds to 'BTN_DONE' color for successfully completed actions.
        This provides visual feedback showing which operations finished.
        
        Args:
            dolevel: Action flags indicating which operations completed successfully.
        """
        try:
            if dolevel.should_parse():
                self.gOp.panel.id.BTNLoad.SetBackgroundColour(self.gOp.panel.id.GetColor('BTN_DONE'))
            if dolevel.has_generate():
                self.gOp.panel.id.BTNCreateFiles.SetBackgroundColour(self.gOp.panel.id.GetColor('BTN_DONE'))
        except Exception:
            _log.exception("_update_button_colours_done: failed to update button colours")

    def _transition_to_idle(self, UpdateBackgroundEvent: Optional[Any], completed_actions: DoActionsType) -> None:
        """Transition worker to idle state after completing or aborting operations.
        
        Performs cleanup and state reset:
        1. Updates button colors based on completed actions
        2. Resets action flags to NONE
        3. Sets readyToDo flag to accept new work
        4. Calls gOp.stop() to finalize state
        5. Posts 'done' event to UI
        
        Args:
            UpdateBackgroundEvent: Optional event class for posting UI updates.
            completed_actions: Flags indicating which operations completed successfully
                              (used to update button colors appropriately).
        """
        _log.debug("=======================GOING TO IDLE %d", self.threadnum)
        
        # Update button colors to show completion
        self._update_button_colours_done(completed_actions)
        
        # reset work flags
        self.doAction = DoActionsType.NONE
        self.readyToDo = True
        try:
            self.gOp.stop()
        except Exception:
            _log.exception("BackgroundActions: gOp.stop() failed")
        if UpdateBackgroundEvent:
            wx.PostEvent(self.win, UpdateBackgroundEvent(state='done'))

    def Run(self) -> None:
        """Main worker thread loop.
        
        Continuously monitors doAction flags and executes requested operations:
        - Parse/geocode GEDCOM if PARSE or REPARSE_IF_NEEDED flags are set
        - Generate output if GENERATE flag is set
        
        The loop runs until keepGoing is set to False. It sleeps when no work
        is pending to avoid busy-waiting.
        
        Heavy helper functions (ParseAndGPS, doHTML, etc.) are accessed via
        panel_actions to avoid circular imports at module load time.
        
        Thread lifecycle:
        1. Check for pending work (doAction flags set and readyToDo)
        2. Execute parse operation if requested
        3. Execute generation operation if requested
        4. Transition to idle state
        5. Sleep if no work pending
        6. Repeat until Stop() is called
        
        Error handling:
        - Individual operations handle their own exceptions
        - Top-level exception handler ensures transition to idle on unexpected errors
        """
        self.SayInfoMessage(' ', True)  # prime the InfoBox

        while self.keepGoing:
            if self.doAction.doing_something() and self.readyToDo:
                self.readyToDo = False  # Avoid a Race
                _log.info("triggered thread with %s (Thread# %d / %d)", self.doAction, self.threadnum, _thread.get_ident())
                self.gOp.stopping = False
                wx.Yield()
                # Obtain event type from gOp if available
                UpdateBackgroundEvent = getattr(self.gOp, "UpdateBackgroundEvent", None)
                panel_actions = getattr(getattr(self.gOp, "panel", None), "actions", None)
                
                if not panel_actions:
                    _log.error("Run: panel_actions not available")
                    self._transition_to_idle(UpdateBackgroundEvent, DoActionsType.NONE)
                    continue
                
                completed_actions = DoActionsType.NONE
                try:
                    if self.doAction.should_parse(getattr(self.gOp, "parsed", False)):
                        self._run_parse(panel_actions, UpdateBackgroundEvent)
                        if self.people:  # Only mark as completed if successful
                            completed_actions |= DoActionsType.PARSE

                    if self.doAction.has_generate():
                        self._run_generate(panel_actions, UpdateBackgroundEvent)
                        completed_actions |= DoActionsType.GENERATE
    
                    self._transition_to_idle(UpdateBackgroundEvent, completed_actions)
                    
                except Exception:
                    _log.exception("BackgroundActions.Run main loop failed")
                    self._transition_to_idle(UpdateBackgroundEvent, DoActionsType.NONE)
            else:
                time.sleep(0.3)
        self.threadrunning = False
        _log.info("BackgroundActions thread %d exiting", self.threadnum)