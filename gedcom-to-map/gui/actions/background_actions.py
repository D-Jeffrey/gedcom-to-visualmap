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
        panel: Visual map panel reference for accessing UI state and actions.
        svc_config: Service for configuration access (IConfig).
        svc_state: Service for runtime state (IState).
        svc_progress: Service for progress tracking (IProgressTracker).
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
        background = BackgroundActions(panel, threadnum=1, svc_config, svc_state, svc_progress)
        background.Start()
        background.Trigger(DoActionsType.PARSE | DoActionsType.GENERATE)
        # ... later ...
        background.Stop()
    """

    def __init__(
        self,
        win: wx.Window,
        threadnum: int,
        panel: Any,
        svc_config: Optional["IConfig"] = None,
        svc_state: Optional["IState"] = None,
        svc_progress: Optional["IProgressTracker"] = None,
    ) -> None:
        """Initialize background worker thread.

        Args:
            win: Parent wxPython window for posting events.
            threadnum: Unique thread identifier for logging and diagnostics.
            panel: Visual map panel reference for UI actions and service access.
            svc_config: Configuration service (IConfig). Defaults to panel.svc_config.
            svc_state: Runtime state service (IState). Defaults to panel.svc_state.
            svc_progress: Progress tracker service (IProgressTracker). Defaults to panel.svc_progress.
        """
        self.win: wx.Window = win
        self.panel: Any = panel
        self.svc_config: "IConfig" = svc_config or panel.svc_config
        self.svc_state: "IState" = svc_state or panel.svc_state
        self.svc_progress: "IProgressTracker" = svc_progress or panel.svc_progress
        self.people: Optional[dict] = None
        self.threadnum: int = threadnum
        self.updategrid: bool = False
        self.updategridmain: bool = True
        self.updateinfo: str = ""  # Message to prime GUI updates
        self.errorinfo: Optional[str] = None
        self.keepGoing: bool = True
        self.threadrunning: bool = True
        self.doAction: DoActionsType = DoActionsType.NONE  # Current background operation
        self.readyToDo: bool = True  # Ready to accept new actions

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
                self.panel.id.BTNLoad.SetBackgroundColour(self.panel.color_manager.get_color("BTN_DONE"))
            if dolevel.has_generate():
                self.panel.id.BTNCreateFiles.SetBackgroundColour(self.panel.color_manager.get_color("BTN_DONE"))
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
        _log.debug(f"Trigger called with: {dolevel}, readyToDo={self.readyToDo}")

        if not self.readyToDo:
            _log.warning(f"Background worker busy, ignoring new Trigger request: {dolevel}")
            self.SayErrorMessage("Please wait for current operation to complete", False)
            return

        self._update_button_colours(dolevel)
        self.doAction = dolevel
        _log.debug(f"doAction set to: {self.doAction}")

    def SayInfoMessage(self, line: str, newline: bool = True) -> None:
        """Queue an informational message for display to the user.

        Messages are accumulated in updateinfo and displayed by the UI thread.

        Args:
            line: Message text to display.
            newline: If True, append newline before this message (default: True).
        """
        if newline and self.updateinfo and self.updateinfo != "":
            self.updateinfo = self.updateinfo + "\n"
        self.updateinfo = self.updateinfo + line if self.updateinfo else line

    def SayErrorMessage(self, line: str, newline: bool = True) -> None:
        """Queue an error message for display to the user.

        Messages are accumulated in errorinfo and displayed by the UI thread.

        Args:
            line: Error message text to display.
            newline: If True, append newline before this message (default: True).
        """
        if newline and self.errorinfo and self.errorinfo != "":
            self.errorinfo = self.errorinfo + "\n"
        self.errorinfo = self.errorinfo + line if self.errorinfo else line

    def _clear_people_data(self) -> None:
        """Clear people data from both instance and state service.

        Safely deletes the people dictionary and sets references to None.
        Used when starting a new parse operation or cleaning up after errors.
        """
        if hasattr(self, "people") and self.people:
            try:
                del self.people
            except Exception:
                pass
        try:
            self.svc_state.people = None
        except Exception:
            pass
        self.people = None

    def _report_parse_results(self) -> None:
        """Report parse operation results to the user via info/error messages.

        Displays success messages with person count and starting person info,
        or error messages if parsing failed or was aborted.
        Also sets the updategrid flag to trigger UI refresh.
        """
        if hasattr(self, "people") and self.people:
            _log.debug("person count %d", len(self.people))
            self.updategrid = True
            if self.people:
                self.SayInfoMessage(f"Loaded {len(self.people)} people")
            else:
                self.SayInfoMessage(f"Cancelled loading people")
            try:
                main_id = self.svc_config.get("Main")
                if main_id:
                    gedcom_input = self.svc_config.get("GEDCOMinput")
                    self.SayInfoMessage(f" with '{main_id}' as starting person from {Path(gedcom_input).name}", False)
            except Exception:
                pass
        else:
            if getattr(self.svc_progress, "stopping", False):
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
            wx.PostEvent(self.win, UpdateBackgroundEvent(state="busy"))
        wx.Yield()
        _log.debug("start ParseAndGPS")

        # Clear existing people data
        self._clear_people_data()

        _log.debug("ParseAndGPS")
        try:
            if hasattr(panel_actions, "ParseAndGPS"):
                # ParseAndGPS may take time; ensure it can be interrupted by cooperative checks in that code
                self.people = panel_actions.ParseAndGPS(self.svc_config, self.svc_state, self.svc_progress, 1)
            else:
                _log.error("Run: panel_actions.ParseAndGPS not available")
                self.people = None
        except Exception as e:
            _log.exception("Issues in ParseAndGPS")
            self._clear_people_data()
            self.doAction = DoActionsType.NONE
            try:
                self.svc_progress.stopping = False
            except Exception:
                pass
            _log.warning(str(e))
            self.SayErrorMessage("Failed to Parse", True)
            self.SayErrorMessage(str(e), True)
            return

        # Clear Referenced if parsing completed
        if self.doAction.has_parse():
            try:
                referenced = getattr(self.svc_state, "Referenced", None)
                if referenced:
                    del self.svc_state.Referenced
                    self.svc_state.Referenced = None
            except Exception:
                pass

        # Mark as successfully parsed if we have people data
        if self.people:
            try:
                self.svc_state.parsed = True
            except Exception:
                _log.exception("Failed to set parsed flag")

        # Report results
        self._report_parse_results()

    def _dispatch_generation(self, panel_actions: Any, result_type_name: str, fname: str) -> None:
        """Dispatch to appropriate output generation method based on result type.

        Calls the corresponding generation method (doHTML, doKML, doKML2, or doSUM),
        displays a success message, and opens the generated file if configured.
        Logs error if the required method is not available.

        Args:
            panel_actions: Panel actions object with generation methods
                          (doHTML, doKML, doKML2, doSUM).
            result_type_name: Name of the result type ("HTML", "KML", "KML2", or "SUM").
            fname: Output filename for display in success message.

        Raises:
            Logs error and displays error message for unknown result types.
        """
        result_file = None
        file_type = None
        # Use actual people count, not line count from totalpeople
        people_count = len(getattr(self.svc_state, "people", {})) if hasattr(self.svc_state, "people") else "?"
        total_people = getattr(self.svc_state, "totalpeople", "?")

        _log.info(f"Generating {result_type_name} output. File: {fname}")

        # Verify paths are set
        result_path = self.svc_config.get("resultpath", "")
        if not result_path:
            _log.error("resultpath not set in config")
            self.SayErrorMessage("Error: Output path not set. Load a GEDCOM file first.", True)
            return

        _log.info(f"Output path: {result_path}")

        try:
            if result_type_name == "HTML":
                if hasattr(panel_actions, "doHTML"):
                    _log.info(f"Calling doHTML for {people_count} people")
                    self.SayInfoMessage(f"Generating HTML map for {people_count} people...")

                    start_time = time.time()
                    try:
                        panel_actions.doHTML(
                            self.svc_config, self.svc_state, self.svc_progress, False
                        )  # Don't open in generator
                        elapsed = time.time() - start_time
                        _log.info(f"doHTML completed successfully in {elapsed:.1f} seconds")
                    except Exception as e:
                        elapsed = time.time() - start_time
                        _log.exception(f"doHTML failed after {elapsed:.1f} seconds")
                        raise
                else:
                    _log.error("Run: panel_actions.doHTML not available")
                    self.SayErrorMessage("Error: HTML generator not available", True)
                    return
                self.SayInfoMessage(f"HTML generated for {people_count} people ({fname})")
                file_type = "html"
            elif result_type_name == "KML":
                if hasattr(panel_actions, "doKML"):
                    _log.info(f"Calling doKML for {people_count} people - this may take several minutes")
                    self.SayInfoMessage(f"Generating KML for {people_count} people - please wait...")

                    # Check for cancellation periodically during long operation
                    start_time = time.time()
                    try:
                        panel_actions.doKML(self.svc_config, self.svc_state, self.svc_progress)
                        elapsed = time.time() - start_time
                        _log.info(f"doKML completed successfully in {elapsed:.1f} seconds")
                    except Exception as e:
                        elapsed = time.time() - start_time
                        _log.exception(f"doKML failed after {elapsed:.1f} seconds")
                        raise
                else:
                    _log.error("Run: panel_actions.doKML not available")
                    self.SayErrorMessage("Error: KML generator not available", True)
                    return
                self.SayInfoMessage(f"KML file generated for {people_count} people ({fname})")
                file_type = "kml"
            elif result_type_name == "KML2":
                if hasattr(panel_actions, "doKML2"):
                    _log.info(f"Calling doKML2 for {people_count} people")
                    self.SayInfoMessage(f"Generating KML2 for {people_count} people...")

                    start_time = time.time()
                    try:
                        panel_actions.doKML2(self.svc_config, self.svc_state, self.svc_progress)
                        elapsed = time.time() - start_time
                        _log.info(f"doKML2 completed successfully in {elapsed:.1f} seconds")
                    except Exception as e:
                        elapsed = time.time() - start_time
                        _log.exception(f"doKML2 failed after {elapsed:.1f} seconds")
                        raise
                else:
                    _log.error("Run: panel_actions.doKML2 not available")
                    self.SayErrorMessage("Error: KML2 generator not available", True)
                    return
                self.SayInfoMessage(f"KML2 generated for {people_count} people ({fname})")
                file_type = "kml2"
            elif result_type_name == "SUM":
                if hasattr(panel_actions, "doSUM"):
                    _log.info("Calling doSUM")
                    self.SayInfoMessage("Generating summary reports...")

                    start_time = time.time()
                    try:
                        panel_actions.doSUM(self.svc_config, self.svc_state, self.svc_progress)
                        elapsed = time.time() - start_time
                        _log.info(f"doSUM completed successfully in {elapsed:.1f} seconds")
                    except Exception as e:
                        elapsed = time.time() - start_time
                        _log.exception(f"doSUM failed after {elapsed:.1f} seconds")
                        raise
                else:
                    _log.error("Run: panel_actions.doSUM not available")
                    self.SayErrorMessage("Error: Summary generator not available", True)
                    return
                self.SayInfoMessage(f"Summary files generated ({fname})")
                # SUM doesn't auto-open files (it may generate multiple files)
            else:
                self.SayErrorMessage(f"Error: Unknown Result Type {result_type_name}", True)
                return
        except Exception as e:
            _log.exception(f"Error generating {result_type_name} output")
            self.SayErrorMessage(f"Error generating {result_type_name}: {str(e)}", True)
            return

        # Verify file was created and show full path
        result_path = self.svc_config.get("resultpath", "")
        result_file_path = Path(result_path) / fname if result_path else Path(fname)

        if result_file_path.exists():
            file_size = result_file_path.stat().st_size
            _log.info(f"Generated file verified: {result_file_path} ({file_size} bytes)")
            self.SayInfoMessage(f"File created: {result_file_path.name} ({file_size:,} bytes)")
        else:
            _log.warning(f"Generated file not found at expected location: {result_file_path}")
            self.SayErrorMessage(f"Warning: Generated file not found at {result_file_path}", False)

        # Open generated file if type is set and file exists
        if file_type and fname:
            try:
                _log.info(f"Attempting to open {file_type.upper()} file: {result_file_path}")
                if result_file_path.exists():
                    try:
                        from .file_operations import FileOpener

                        opener = FileOpener(self.svc_config)
                        opener.open_file(file_type, str(result_file_path))
                        _log.info(f"Successfully opened {file_type.upper()} file")
                    except Exception:
                        _log.exception(f"Failed to open {file_type.upper()} file with FileOpener")
                        self.SayErrorMessage(f"Failed to open {file_type.upper()} file. Check log for details.", False)
                else:
                    _log.warning(f"{file_type.upper()} file not found: {result_file_path}")
                    self.SayErrorMessage(f"{file_type.upper()} file not found: {fname}", False)
            except Exception as e:
                _log.exception(f"Error constructing result file path: {e}")
                self.SayErrorMessage(f"Error opening file: {e}", False)

    def _run_generate(self, panel_actions: Any, UpdateBackgroundEvent: Any = None) -> None:
        """Execute output generation operation (HTML/KML/SUM).

        Validates that GEDCOM is parsed and result type is set, then dispatches
        to the appropriate generation method. Returns early if validation fails.Args:
            panel_actions: Panel actions object with generation methods
                          (doHTML, doKML, doKML2, doSUM).
            UpdateBackgroundEvent: Optional event class for posting UI updates.

        Returns:
            Returns early without generating output if:
            - GEDCOM is not parsed (svc_state.parsed is False)
            - Result type is not set (svc_config.ResultType is None)
        """
        _log.info("start do 2")
        if not getattr(self.svc_state, "parsed", False):
            _log.info("not parsed - skipping generation")
            return

        fname = self.svc_config.get("ResultFile")
        result_type = self.svc_config.get("ResultType")
        if result_type is None:
            _log.error("Run: ResultType not set")
            return
        # call appropriate generation function if available
        result_type_name = result_type.name
        _log.debug(f"Starting generation dispatch for {result_type_name}")
        try:
            self._dispatch_generation(panel_actions, result_type_name, fname)
            _log.debug(f"Generation dispatch completed for {result_type_name}")
        except Exception:
            _log.exception("Error while generating output")
        _log.debug("_run_generate completed")

    def _reset_button_colours(self) -> None:
        """Reset UI button background colors to default state.

        Resets both Load and CreateFiles buttons to 'BTN_DEFAULT' color.
        Called when operations complete or are cancelled.
        """
        try:
            default_color = self.panel.color_manager.get_color("BTN_DEFAULT")
            self.panel.id.BTNLoad.SetBackgroundColour(default_color)
            self.panel.id.BTNCreateFiles.SetBackgroundColour(default_color)
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
                self.panel.id.BTNLoad.SetBackgroundColour(self.panel.color_manager.get_color("BTN_DONE"))
            if dolevel.has_generate():
                self.panel.id.BTNCreateFiles.SetBackgroundColour(self.panel.color_manager.get_color("BTN_DONE"))
        except Exception:
            _log.exception("_update_button_colours_done: failed to update button colours")

    def _transition_to_idle(self, UpdateBackgroundEvent: Optional[Any], completed_actions: DoActionsType) -> None:
        """Transition worker to idle state after completing or aborting operations.

        Performs cleanup and state reset:
        1. Updates button colors based on completed actions
        2. Resets action flags to NONE
        3. Sets readyToDo flag to accept new work
        4. Calls svc_progress.stop() to finalize state
        5. Posts 'done' event to UI

        Args:
            UpdateBackgroundEvent: Optional event class for posting UI updates.
            completed_actions: Flags indicating which operations completed successfully
                              (used to update button colors appropriately).
        """
        _log.debug("=======================GOING TO IDLE %d", self.threadnum)

        # CRITICAL: Reset work flags FIRST to ensure thread is always ready for new work
        # Do this before anything else that might fail
        self.doAction = DoActionsType.NONE
        self.readyToDo = True
        _log.debug(f"Transitioned to idle: doAction={self.doAction}, readyToDo={self.readyToDo}")

        # Update button colors (non-critical, don't let failures block readyToDo reset)
        try:
            self._update_button_colours_done(completed_actions)
        except Exception:
            _log.exception("Failed to update button colours - continuing anyway")

        # Stop progress tracking
        try:
            if hasattr(self.svc_progress, "stop"):
                self.svc_progress.stop()
                _log.debug(f"svc_progress.stop() called, running={self.svc_progress.running}")
        except Exception:
            _log.exception("BackgroundActions: svc_progress.stop() failed")

        # Post 'done' event to UI
        try:
            if UpdateBackgroundEvent:
                wx.PostEvent(self.win, UpdateBackgroundEvent(state="done"))
                _log.info("Posted 'done' event to UI")
        except Exception:
            _log.exception("Failed to post 'done' event")

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
        self.SayInfoMessage(" ", True)  # prime the InfoBox

        while self.keepGoing:
            if self.doAction.doing_something() and self.readyToDo:
                _log.debug(f"Run loop: detected work - doAction={self.doAction}, readyToDo={self.readyToDo}")
                self.readyToDo = False  # Avoid a Race
                _log.debug(
                    "triggered thread with %s (Thread# %d / %d)", self.doAction, self.threadnum, _thread.get_ident()
                )
                try:
                    self.svc_progress.stopping = False
                except Exception:
                    pass
                wx.Yield()
                # Obtain event type from panel if available
                UpdateBackgroundEvent = getattr(self.panel, "UpdateBackgroundEvent", None)
                panel_actions = getattr(self.panel, "actions", None)

                if not panel_actions:
                    _log.error("Run: panel_actions not available")
                    self._transition_to_idle(UpdateBackgroundEvent, DoActionsType.NONE)
                    continue

                completed_actions = DoActionsType.NONE
                try:
                    if self.doAction.should_parse(getattr(self.svc_state, "parsed", False)):
                        _log.debug("Running parse operation")
                        self._run_parse(panel_actions, UpdateBackgroundEvent)
                        if self.people:  # Only mark as completed if successful
                            completed_actions |= DoActionsType.PARSE
                            _log.debug("Parse completed successfully")
                        else:
                            _log.warning("Parse completed but no people data")

                    if self.doAction.has_generate():
                        _log.debug("Running generate operation")
                        self._run_generate(panel_actions, UpdateBackgroundEvent)
                        completed_actions |= DoActionsType.GENERATE
                        _log.debug("Generate operation completed")

                    _log.debug(f"Transitioning to idle with completed actions: {completed_actions}")
                    self._transition_to_idle(UpdateBackgroundEvent, completed_actions)

                except Exception:
                    _log.exception("BackgroundActions.Run main loop failed")
                    # CRITICAL: Always transition to idle to reset readyToDo flag
                    try:
                        self._transition_to_idle(UpdateBackgroundEvent, DoActionsType.NONE)
                    except Exception:
                        # Last resort: manually reset readyToDo if transition fails
                        _log.exception("CRITICAL: _transition_to_idle failed, manually resetting readyToDo")
                        self.doAction = DoActionsType.NONE
                        self.readyToDo = True
            else:
                time.sleep(0.3)
        self.threadrunning = False
        _log.info("BackgroundActions thread %d exiting", self.threadnum)
