import logging
import os
from pathlib import Path
import wx
import wx.grid as gridlib

_log = logging.getLogger(__name__.lower())


class ConfigDialog(wx.Dialog):
    def __init__(
        self,
        parent: wx.Window,
        title: str,
        svc_config,
        file_open_commands: dict,
        logging_keys: list[str] | None = None,
        color_manager=None,
        parent_refresh_callback=None,
    ) -> None:
        """Initialize the Configuration dialog.

        Args:
            parent: Parent wxPython window.
            title: Dialog title.
            svc_config: Configuration service (IConfig).
            file_open_commands: Dictionary mapping file types to open commands.
            logging_keys: List of logger names to configure (optional).
            color_manager: ColourManager for dark mode support (optional).
            parent_refresh_callback: Callback to refresh parent window colors (optional).
        """
        super().__init__(parent, title=title, size=(600, 950))

        includeNOTSET = True
        # Configuration service for logic-backed settings
        self.svc_config = svc_config
        self.file_open_commands: dict = file_open_commands
        self.logging_keys: list[str] = logging_keys or []
        self.color_manager = color_manager
        self.parent_refresh_callback = parent_refresh_callback

        all_loggers = list(logging.root.manager.loggerDict.keys())
        self.loggerNames: list[str] = (
            [name for name in all_loggers if name in self.logging_keys] if self.logging_keys else all_loggers
        )
        cfgpanel = wx.Panel(self, style=wx.SIMPLE_BORDER)
        self.cfgpanel = cfgpanel
        self.refresh_dialog_background()

        TEXTkmlcmdlinelbl = wx.StaticText(cfgpanel, -1, " KML Editor Command line:   ")
        self.TEXTkmlcmdline = wx.TextCtrl(cfgpanel, wx.ID_FILE1, "", size=(250, 20))
        if file_open_commands:
            kml_cmd = file_open_commands.get_command_for_file_type("kml")
            if kml_cmd:
                self.TEXTkmlcmdline.SetValue(kml_cmd)

        TEXTcsvcmdlinelbl = wx.StaticText(cfgpanel, -1, " CSV Table Editor Command line:   ")
        self.TEXTcsvcmdline = wx.TextCtrl(cfgpanel, wx.ID_FILE1, "", size=(250, 20))
        if file_open_commands:
            csv_cmd = file_open_commands.get_command_for_file_type("csv")
            if csv_cmd:
                self.TEXTcsvcmdline.SetValue(csv_cmd)

        TEXTtracecmdlinelbl = wx.StaticText(cfgpanel, -1, " Trace Table Editor Command line:   ")
        self.TEXTtracecmdline = wx.TextCtrl(cfgpanel, wx.ID_FILE1, "", size=(250, 20))
        if file_open_commands:
            trace_cmd = file_open_commands.get_command_for_file_type("trace")
            if trace_cmd:
                self.TEXTtracecmdline.SetValue(trace_cmd)

        self.CBBadAge = wx.CheckBox(cfgpanel, -1, "Flag if age is off")
        # Get badAge from service config
        bad_age = svc_config.get("badAge")
        self.CBBadAge.SetValue(bool(bad_age))
        self.badAge = True

        self.CBEnableTracemalloc = wx.CheckBox(cfgpanel, -1, "Enable detailed memory tracking (15% overhead)")
        enable_tracemalloc = svc_config.get("EnableTracemalloc", False)
        self.CBEnableTracemalloc.SetValue(bool(enable_tracemalloc))

        # Processing options
        self.CBEnableEnrichment = wx.CheckBox(cfgpanel, -1, "Enable enrichment processing during GEDCOM load")
        enable_enrichment = svc_config.get("EnableEnrichment", True)
        self.CBEnableEnrichment.SetValue(bool(enable_enrichment))

        self.CBEnableStatistics = wx.CheckBox(cfgpanel, -1, "Enable statistics processing during GEDCOM load")
        enable_statistics = svc_config.get("EnableStatistics", True)
        self.CBEnableStatistics.SetValue(bool(enable_statistics))

        self.CBUseCustomColors = wx.CheckBox(cfgpanel, -1, "Use CustomColours (disable for platform defaults)")
        use_custom_colors = svc_config.get("UseCustomColors", True)
        self.CBUseCustomColors.SetValue(bool(use_custom_colors))

        # Statistics options
        self.birth_year_spinner = wx.SpinCtrl(cfgpanel, value="1000", min=1, max=2100, initial=1000, size=(80, 20))
        earliest_year = svc_config.get("earliest_credible_birth_year", 1000)
        self.birth_year_spinner.SetValue(int(earliest_year))

        GRIDctl = gridlib.Grid(cfgpanel)
        # Only show loggers explicitly configured in logging_keys
        gridlen = len(self.logging_keys)

        GRIDctl.CreateGrid(gridlen, 2)
        GRIDctl.SetColLabelValue(0, "Logger Name")
        GRIDctl.SetColLabelValue(1, "Log Level")

        self.logging_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

        # Populate grid with only configured loggers
        # Get appropriate readonly background color for dark mode support
        readonly_bg = wx.LIGHT_GREY
        if self.color_manager and self.color_manager.has_color("GRID_READONLY_BACK"):
            readonly_bg = self.color_manager.get_color("GRID_READONLY_BACK")

        for row, loggerName in enumerate(self.logging_keys):
            updatelog = logging.getLogger(loggerName)
            GRIDctl.SetCellValue(row, 0, loggerName)
            GRIDctl.SetCellBackgroundColour(row, 0, readonly_bg)
            GRIDctl.SetCellValue(row, 1, logging.getLevelName(updatelog.level))
            GRIDctl.SetCellEditor(row, 1, gridlib.GridCellChoiceEditor(self.logging_levels))
            GRIDctl.SetReadOnly(row, 0)

        GRIDctl.AutoSizeColumn(0, True)
        GRIDctl.AutoSizeColumn(1, True)
        GRIDctl.SetMinSize((400, 300))

        saveBTN = wx.Button(cfgpanel, label="Save Changes")
        saveBTN.Bind(wx.EVT_BUTTON, self.onSave)
        cancelBTN = wx.Button(cfgpanel, label="Cancel")
        cancelBTN.Bind(wx.EVT_BUTTON, self.onCancel)

        sizer = wx.BoxSizer(wx.VERTICAL)

        # Geocoding Options section (moved to top)
        sizer.Add(wx.StaticText(cfgpanel, -1, " Geocoding Options:"))

        # Radio buttons for geocoding mode (mutually exclusive)
        self.rb_normal = wx.RadioButton(cfgpanel, -1, "   Normal (use cache and geocode)", style=wx.RB_GROUP)
        self.rb_geocode_only = wx.RadioButton(cfgpanel, -1, "   Geocode only (ignore cache)")
        self.rb_cache_only = wx.RadioButton(cfgpanel, -1, "   Cache only (no geocode)")

        # Determine which radio button should be selected
        geocode_only = svc_config.get("geocode_only", False)
        cache_only = svc_config.get("cache_only", False)

        if geocode_only:
            self.rb_geocode_only.SetValue(True)
        elif cache_only:
            self.rb_cache_only.SetValue(True)
        else:
            self.rb_normal.SetValue(True)

        sizer.Add(self.rb_normal, 0, wx.ALL, 5)
        sizer.Add(self.rb_geocode_only, 0, wx.ALL, 5)
        sizer.Add(self.rb_cache_only, 0, wx.ALL, 5)

        # Default country
        default_country_sizer = wx.BoxSizer(wx.HORIZONTAL)
        default_country_label = wx.StaticText(cfgpanel, -1, "   Default country (full name or empty):")
        self.default_country_text = wx.TextCtrl(cfgpanel, value="", size=(150, 20))
        default_country = svc_config.get("defaultCountry")
        if default_country:
            self.default_country_text.SetValue(str(default_country))
        default_country_sizer.Add(default_country_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        default_country_sizer.Add(self.default_country_text, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(default_country_sizer, 0, wx.ALL, 5)

        # Days between retrying failed lookups
        retry_days_sizer = wx.BoxSizer(wx.HORIZONTAL)
        retry_days_label = wx.StaticText(cfgpanel, -1, "   Days between retrying failed lookups:")
        self.retry_days_spinner = wx.SpinCtrl(cfgpanel, value="7", min=1, max=365, initial=7, size=(80, 20))
        retry_days = svc_config.get("days_between_retrying_failed_lookups", 7)
        self.retry_days_spinner.SetValue(int(retry_days))
        retry_days_sizer.Add(retry_days_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        retry_days_sizer.Add(self.retry_days_spinner, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(retry_days_sizer, 0, wx.ALL, 5)
        sizer.AddSpacer(20)

        # File Command Options section
        sizer.Add(wx.StaticText(cfgpanel, -1, " File Command Options:"))
        sizer.AddSpacer(5)

        # KML command line
        kml_sizer = wx.BoxSizer(wx.HORIZONTAL)
        kml_sizer.Add(TEXTkmlcmdlinelbl, 0, wx.ALIGN_CENTER_VERTICAL)
        kml_sizer.Add((3, 20), 0)
        kml_sizer.Add(self.TEXTkmlcmdline, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(kml_sizer, 0, wx.ALL, 5)

        # CSV command line
        csv_sizer = wx.BoxSizer(wx.HORIZONTAL)
        csv_sizer.Add(TEXTcsvcmdlinelbl, 0, wx.ALIGN_CENTER_VERTICAL)
        csv_sizer.Add((3, 20), 0)
        csv_sizer.Add(self.TEXTcsvcmdline, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(csv_sizer, 0, wx.ALL, 5)

        # Trace command line
        trace_sizer = wx.BoxSizer(wx.HORIZONTAL)
        trace_sizer.Add(TEXTtracecmdlinelbl, 0, wx.ALIGN_CENTER_VERTICAL)
        trace_sizer.Add((3, 20), 0)
        trace_sizer.Add(self.TEXTtracecmdline, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(trace_sizer, 0, wx.ALL, 5)

        # Help text for file commands
        sizer.Add(
            wx.StaticText(
                cfgpanel, -1, "Use   $n  for the name of the file within a command line - such as    notepad $n"
            ),
            0,
            wx.LEFT,
            10,
        )
        sizer.Add(
            wx.StaticText(cfgpanel, -1, "Use   $n  without any command to open default application for that file type"),
            0,
            wx.LEFT,
            10,
        )

        # Bad Age checkbox
        sizer.Add(self.CBBadAge, 0, wx.ALL, 5)

        # Processing Options section
        sizer.AddSpacer(10)
        sizer.Add(wx.StaticText(cfgpanel, -1, " Processing Options:"))
        sizer.Add(self.CBEnableEnrichment, 0, wx.ALL, 5)
        sizer.Add(self.CBEnableStatistics, 0, wx.ALL, 5)
        sizer.AddSpacer(10)

        # Appearance Options section
        sizer.Add(wx.StaticText(cfgpanel, -1, " Appearance Options:"))
        sizer.Add(self.CBUseCustomColors, 0, wx.ALL, 5)
        sizer.AddSpacer(20)

        # Performance Options section
        sizer.Add(wx.StaticText(cfgpanel, -1, " Performance Options:"))
        sizer.Add(self.CBEnableTracemalloc, 0, wx.ALL, 5)
        sizer.AddSpacer(20)

        # Statistics Options section
        sizer.Add(wx.StaticText(cfgpanel, -1, " Statistics Options:"))
        birth_year_sizer = wx.BoxSizer(wx.HORIZONTAL)
        birth_year_label = wx.StaticText(cfgpanel, -1, "   Earliest credible birth year:")
        birth_year_sizer.Add(birth_year_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        birth_year_sizer.Add(self.birth_year_spinner, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(birth_year_sizer, 0, wx.ALL, 5)
        sizer.AddSpacer(20)

        sizer.Add(wx.StaticText(cfgpanel, -1, " Logging Options:"))

        # Add "Set All Levels" control
        setAllSizer = wx.BoxSizer(wx.HORIZONTAL)
        setAllSizer.Add(
            wx.StaticText(cfgpanel, -1, "Set all logging levels to:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5
        )
        self.setAllChoice = wx.Choice(cfgpanel, choices=self.logging_levels)
        self.setAllChoice.SetSelection(1)  # Default to INFO
        self._apply_choice_colors(self.setAllChoice, selected=False)
        self.setAllChoice.Bind(wx.EVT_SET_FOCUS, self.onSetAllChoiceFocus)
        self.setAllChoice.Bind(wx.EVT_KILL_FOCUS, self.onSetAllChoiceBlur)
        self.setAllChoice.Bind(wx.EVT_CHOICE, self.onSetAllChoiceChanged)
        setAllSizer.Add(self.setAllChoice, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        setAllButton = wx.Button(cfgpanel, label="Apply to All")
        setAllButton.Bind(wx.EVT_BUTTON, self.onSetAllLevels)
        setAllSizer.Add(setAllButton, 0, wx.ALIGN_CENTER_VERTICAL)

        # Add Clear Log File button
        clearLogButton = wx.Button(cfgpanel, label="Clear Log File")
        clearLogButton.Bind(wx.EVT_BUTTON, self.onClearLogFile)
        setAllSizer.Add(clearLogButton, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 20)

        sizer.Add(setAllSizer, 0, wx.ALL, 10)

        sizer.Add(GRIDctl, 1, wx.EXPAND | wx.ALL, 20)

        buttonsizer = wx.BoxSizer(wx.HORIZONTAL)
        buttonsizer.Add(saveBTN, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        buttonsizer.Add(cancelBTN, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        sizer.Add(buttonsizer, 0, wx.ALIGN_CENTER | wx.ALL, 5)

        cfgpanel.SetSizer(sizer)
        self.GRIDctl = GRIDctl
        self.saveBTN = saveBTN
        self.cancelBTN = cancelBTN
        self.setAllButton = setAllButton
        self.clearLogButton = clearLogButton

        # Apply colors to all controls (critical for Windows)
        self._apply_control_colors()

        # Bind to activation event to detect color scheme changes
        self.Bind(wx.EVT_ACTIVATE, self.OnActivate)

        self.Show(True)

    def OnActivate(self, event: wx.ActivateEvent) -> None:
        """Handle dialog activation: check for system appearance changes."""
        if event.GetActive() and self.color_manager:
            # Dialog is being activated - check if appearance mode changed
            if self.color_manager.refresh_colors():
                # Colors changed, need to refresh the grid colors
                _log.info("Appearance mode changed in ConfigDialog, refreshing grid colors")
                self.refresh_dialog_background()
                self.refresh_grid_colors()
                # Also notify parent to refresh its colors
                if self.parent_refresh_callback:
                    try:
                        self.parent_refresh_callback()
                    except Exception:
                        _log.exception("Failed to call parent_refresh_callback")
        event.Skip()  # Allow event to propagate

    def refresh_dialog_background(self) -> None:
        """Update dialog and panel backgrounds from configured colors."""
        if not self.color_manager:
            return

        if self.color_manager.has_color("DIALOG_BACKGROUND"):
            bg_color = self.color_manager.get_color("DIALOG_BACKGROUND")
            self.SetBackgroundColour(bg_color)
            if hasattr(self, "cfgpanel") and self.cfgpanel:
                self.cfgpanel.SetBackgroundColour(bg_color)
        if self.color_manager.has_color("DIALOG_TEXT"):
            text_color = self.color_manager.get_color("DIALOG_TEXT")
            self.SetForegroundColour(text_color)
            if hasattr(self, "cfgpanel") and self.cfgpanel:
                self.cfgpanel.SetForegroundColour(text_color)
                self._apply_foreground_recursive(self.cfgpanel, text_color)
        if hasattr(self, "setAllChoice") and self.setAllChoice:
            self._apply_choice_colors(self.setAllChoice, selected=False)
        # Apply colors to all controls
        self._apply_control_colors()
        self.Refresh()

    def _apply_foreground_recursive(self, root: wx.Window, color: wx.Colour) -> None:
        try:
            root.SetForegroundColour(color)
        except Exception:
            pass
        for child in root.GetChildren():
            self._apply_foreground_recursive(child, color)

    def _apply_choice_colors(self, choice_ctrl: wx.Choice, selected: bool = False) -> None:
        if not self.color_manager or not choice_ctrl:
            return

        if selected:
            if self.color_manager.has_color("GRID_SELECTED_BACK"):
                choice_ctrl.SetBackgroundColour(self.color_manager.get_color("GRID_SELECTED_BACK"))
            elif self.color_manager.has_color("DIALOG_BACKGROUND"):
                choice_ctrl.SetBackgroundColour(self.color_manager.get_color("DIALOG_BACKGROUND"))

            if self.color_manager.has_color("GRID_SELECTED_TEXT"):
                choice_ctrl.SetForegroundColour(self.color_manager.get_color("GRID_SELECTED_TEXT"))
            elif self.color_manager.has_color("DIALOG_TEXT"):
                choice_ctrl.SetForegroundColour(self.color_manager.get_color("DIALOG_TEXT"))
            return

        if self.color_manager.has_color("DIALOG_BACKGROUND"):
            choice_ctrl.SetBackgroundColour(self.color_manager.get_color("DIALOG_BACKGROUND"))
        if self.color_manager.has_color("DIALOG_TEXT"):
            choice_ctrl.SetForegroundColour(self.color_manager.get_color("DIALOG_TEXT"))

    def onSetAllChoiceFocus(self, event: wx.FocusEvent) -> None:
        self._apply_choice_colors(self.setAllChoice, selected=True)
        event.Skip()

    def onSetAllChoiceBlur(self, event: wx.FocusEvent) -> None:
        self._apply_choice_colors(self.setAllChoice, selected=False)
        event.Skip()

    def onSetAllChoiceChanged(self, event: wx.CommandEvent) -> None:
        self._apply_choice_colors(self.setAllChoice, selected=True)
        event.Skip()

    def _apply_control_colors(self) -> None:
        """Apply colors explicitly to all controls for Windows compatibility."""
        if not self.color_manager:
            return

        # Get colors
        dialog_bg = None
        dialog_text = None
        if self.color_manager.has_color("DIALOG_BACKGROUND"):
            dialog_bg = self.color_manager.get_color("DIALOG_BACKGROUND")
        if self.color_manager.has_color("DIALOG_TEXT"):
            dialog_text = self.color_manager.get_color("DIALOG_TEXT")

        # Apply to text fields (check if they exist first)
        text_field_names = [
            "TEXTkmlcmdline",
            "TEXTcsvcmdline",
            "TEXTtracecmdline",
            "default_country_text",
        ]
        for field_name in text_field_names:
            if not hasattr(self, field_name):
                continue
            txt = getattr(self, field_name)
            if dialog_bg:
                txt.SetBackgroundColour(dialog_bg)
                txt.SetOwnBackgroundColour(dialog_bg)
            if dialog_text:
                txt.SetForegroundColour(dialog_text)
                txt.SetOwnForegroundColour(dialog_text)

        # Apply to spin controls (check if they exist first)
        spin_ctrl_names = ["birth_year_spinner", "retry_days_spinner"]
        for spin_name in spin_ctrl_names:
            if not hasattr(self, spin_name):
                continue
            spin = getattr(self, spin_name)
            if dialog_bg:
                spin.SetBackgroundColour(dialog_bg)
                if hasattr(spin, "SetOwnBackgroundColour"):
                    spin.SetOwnBackgroundColour(dialog_bg)
            if dialog_text:
                spin.SetForegroundColour(dialog_text)
                if hasattr(spin, "SetOwnForegroundColour"):
                    spin.SetOwnForegroundColour(dialog_text)

        # Apply to buttons (check if they exist first)
        button_names = ["saveBTN", "cancelBTN", "setAllButton", "clearLogButton"]
        for btn_name in button_names:
            if not hasattr(self, btn_name):
                continue
            btn = getattr(self, btn_name)
            # Let buttons use platform defaults for better appearance
            btn.Refresh()

        # Apply to grid
        self._apply_grid_colors()

    def _apply_grid_colors(self) -> None:
        """Apply colors to all grid cells and labels."""
        if not self.color_manager:
            return

        # Check if grid exists yet
        if not hasattr(self, "GRIDctl"):
            return

        # Get colors
        grid_bg = wx.WHITE
        grid_text = wx.BLACK
        header_bg = wx.LIGHT_GREY
        header_text = wx.BLACK
        readonly_bg = wx.LIGHT_GREY

        if self.color_manager.has_color("GRID_BACK"):
            grid_bg = self.color_manager.get_color("GRID_BACK")
        if self.color_manager.has_color("GRID_TEXT"):
            grid_text = self.color_manager.get_color("GRID_TEXT")
        if self.color_manager.has_color("GRID_HEADER_BACK"):
            header_bg = self.color_manager.get_color("GRID_HEADER_BACK")
        if self.color_manager.has_color("GRID_HEADER_TEXT"):
            header_text = self.color_manager.get_color("GRID_HEADER_TEXT")
        if self.color_manager.has_color("GRID_READONLY_BACK"):
            readonly_bg = self.color_manager.get_color("GRID_READONLY_BACK")

        # Set default cell colors
        self.GRIDctl.SetDefaultCellBackgroundColour(grid_bg)
        self.GRIDctl.SetDefaultCellTextColour(grid_text)

        # Set label (header) colors
        self.GRIDctl.SetLabelBackgroundColour(header_bg)
        self.GRIDctl.SetLabelTextColour(header_text)

        # Set individual cell colors
        for row in range(self.GRIDctl.GetNumberRows()):
            # Column 0 (Logger Name) - readonly
            self.GRIDctl.SetCellBackgroundColour(row, 0, readonly_bg)
            self.GRIDctl.SetCellTextColour(row, 0, grid_text)
            # Column 1 (Log Level) - editable
            self.GRIDctl.SetCellBackgroundColour(row, 1, grid_bg)
            self.GRIDctl.SetCellTextColour(row, 1, grid_text)

        self.GRIDctl.ForceRefresh()

    def refresh_grid_colors(self) -> None:
        """Update grid colors based on current color scheme."""
        self._apply_grid_colors()

    def onSetAllLevels(self, event):
        """Apply the selected logging level to all configured loggers in the grid."""
        selected_level = self.setAllChoice.GetStringSelection()
        if not selected_level:
            return

        for row in range(self.GRIDctl.GetNumberRows()):
            loggerName = self.GRIDctl.GetCellValue(row, 0)
            # Only update loggers that are in logging_keys (configured in yaml/INI)
            if loggerName in self.logging_keys:
                self.GRIDctl.SetCellValue(row, 1, selected_level)

        self.GRIDctl.ForceRefresh()

    def onClearLogFile(self, event):
        """Clear the log file (reset to empty file)."""
        from const import NAME

        log_file_path = Path(f"{NAME}.log")

        try:
            if log_file_path.exists():
                # Close all file handlers writing to this log file to avoid file position issues
                root_logger = logging.getLogger()
                file_handlers_to_reopen = []

                for handler in root_logger.handlers[:]:
                    if isinstance(handler, logging.FileHandler):
                        if Path(handler.baseFilename).resolve() == log_file_path.resolve():
                            handler.close()
                            file_handlers_to_reopen.append((handler, root_logger))
                            root_logger.removeHandler(handler)

                # Also check all other loggers
                for logger_name in logging.Logger.manager.loggerDict:
                    logger = logging.getLogger(logger_name)
                    if hasattr(logger, "handlers"):
                        for handler in logger.handlers[:]:
                            if isinstance(handler, logging.FileHandler):
                                if Path(handler.baseFilename).resolve() == log_file_path.resolve():
                                    handler.close()
                                    file_handlers_to_reopen.append((handler, logger))
                                    logger.removeHandler(handler)

                # Clear the file
                with open(log_file_path, "w", encoding="utf-8") as f:
                    pass

                # Recreate and reattach the file handlers
                from const import LOG_CONFIG

                formatter = logging.Formatter(LOG_CONFIG["formatters"]["standard"]["format"])

                for old_handler, parent_logger in file_handlers_to_reopen:
                    new_handler = logging.FileHandler(
                        filename=old_handler.baseFilename,
                        mode="a",  # Append mode since file now exists and is empty
                        encoding="utf-8",
                    )
                    new_handler.setLevel(old_handler.level)
                    new_handler.setFormatter(formatter)
                    parent_logger.addHandler(new_handler)

                _log.info("Log file cleared by user via Configuration dialog")
            else:
                wx.MessageBox(
                    f"Log file does not exist:\n\n{log_file_path.absolute()}",
                    "File Not Found",
                    wx.OK | wx.ICON_INFORMATION,
                )
        except Exception as e:
            _log.exception("Failed to clear log file")
            wx.MessageBox(f"Failed to clear log file:\n\n{str(e)}", "Error", wx.OK | wx.ICON_ERROR)

    def onSave(self, event):
        # Collect all logging level changes
        logging_config = {}
        for row in range(self.GRIDctl.GetNumberRows()):
            loggerName = self.GRIDctl.GetCellValue(row, 0)
            logLevel = self.GRIDctl.GetCellValue(row, 1)
            if logLevel:
                level_value = logging.getLevelName(logLevel)
                if isinstance(level_value, int):
                    logging_config[loggerName] = logLevel
                else:
                    _log.warning("ConfigDialog.onSave: invalid log level '%s' for '%s'", logLevel, loggerName)

        # Apply logging levels hierarchically (parent levels propagate to children)
        if logging_config:
            try:
                from services.config_loader import LoggingConfigApplicator

                LoggingConfigApplicator.apply_hierarchically(logging_config)
            except Exception:
                _log.exception("ConfigDialog.onSave: failed to apply hierarchical logging defaults")

        # Update file open commands
        self.file_open_commands.add_file_type_command("kml", self.TEXTkmlcmdline.GetValue())
        self.file_open_commands.add_file_type_command("csv", self.TEXTcsvcmdline.GetValue())
        self.file_open_commands.add_file_type_command("trace", self.TEXTtracecmdline.GetValue())

        # Update service config
        try:
            if hasattr(self.svc_config, "set"):
                self.svc_config.set("badAge", bool(self.CBBadAge.GetValue()))
                self.svc_config.set("EnableEnrichment", bool(self.CBEnableEnrichment.GetValue()))
                self.svc_config.set("EnableStatistics", bool(self.CBEnableStatistics.GetValue()))
                self.svc_config.set("EnableTracemalloc", bool(self.CBEnableTracemalloc.GetValue()))
                self.svc_config.set("UseCustomColors", bool(self.CBUseCustomColors.GetValue()))
                self.svc_config.set("earliest_credible_birth_year", self.birth_year_spinner.GetValue())
                # Set geocoding mode based on radio button selection
                if self.rb_geocode_only.GetValue():
                    self.svc_config.set("geocode_only", True)
                    self.svc_config.set("cache_only", False)
                elif self.rb_cache_only.GetValue():
                    self.svc_config.set("geocode_only", False)
                    self.svc_config.set("cache_only", True)
                else:  # Normal mode (rb_normal)
                    self.svc_config.set("geocode_only", False)
                    self.svc_config.set("cache_only", False)
                self.svc_config.set("days_between_retrying_failed_lookups", self.retry_days_spinner.GetValue())
                # Set default country - convert empty string or "none" (case insensitive) to None
                default_country_value = self.default_country_text.GetValue().strip()
                if not default_country_value or default_country_value.lower() == "none":
                    default_country_value = None
                self.svc_config.set("defaultCountry", default_country_value)
        except Exception:
            _log.exception("ConfigDialog.onSave: failed to set config values in svc_config")

        # Persist settings if available
        try:
            if hasattr(self.svc_config, "savesettings"):
                self.svc_config.savesettings()
        except Exception:
            _log.exception("ConfigDialog.onSave: savesettings failed")

        # Refresh parent panel to update UI based on changed settings
        try:
            if self.color_manager and hasattr(self.color_manager, "set_use_custom_colors"):
                self.color_manager.set_use_custom_colors(bool(self.CBUseCustomColors.GetValue()))
                self.refresh_dialog_background()
                self.refresh_grid_colors()
        except Exception:
            _log.exception("ConfigDialog.onSave: failed to apply UseCustomColors to color_manager")

        if self.parent_refresh_callback:
            try:
                self.parent_refresh_callback()
            except Exception:
                _log.exception("ConfigDialog.onSave: parent_refresh_callback failed")

        self.Close()
        self.DestroyLater()

    def onCancel(self, event):
        self.Close()
        self.DestroyLater()
