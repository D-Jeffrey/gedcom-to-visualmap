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
    ) -> None:
        """Initialize the Configuration dialog.
        
        Args:
            parent: Parent wxPython window.
            title: Dialog title.
            svc_config: Configuration service (IConfig).
            file_open_commands: Dictionary mapping file types to open commands.
            logging_keys: List of logger names to configure (optional).
        """
        super().__init__(parent, title=title, size=(500, 650))

        includeNOTSET = True
        # Configuration service for logic-backed settings
        self.svc_config = svc_config
        self.file_open_commands: dict = file_open_commands
        self.logging_keys: list[str] = logging_keys or []
        all_loggers = list(logging.root.manager.loggerDict.keys())
        self.loggerNames: list[str] = (
            [name for name in all_loggers if name in self.logging_keys]
            if self.logging_keys
            else all_loggers
        )
        cfgpanel = wx.Panel(self, style=wx.SIMPLE_BORDER)

        TEXTkmlcmdlinelbl = wx.StaticText(cfgpanel, -1, " KML Editor Command line:   ")
        self.TEXTkmlcmdline = wx.TextCtrl(cfgpanel, wx.ID_FILE1, "", size=(250, 20))
        if file_open_commands:
            kml_cmd = file_open_commands.get_command_for_file_type('kml')
            if kml_cmd:
                self.TEXTkmlcmdline.SetValue(kml_cmd)

        TEXTcsvcmdlinelbl = wx.StaticText(cfgpanel, -1, " CSV Table Editor Command line:   ")
        self.TEXTcsvcmdline = wx.TextCtrl(cfgpanel, wx.ID_FILE1, "", size=(250, 20))
        if file_open_commands:
            csv_cmd = file_open_commands.get_command_for_file_type('csv')
            if csv_cmd:
                self.TEXTcsvcmdline.SetValue(csv_cmd)

        TEXTtracecmdlinelbl = wx.StaticText(cfgpanel, -1, " Trace Table Editor Command line:   ")
        self.TEXTtracecmdline = wx.TextCtrl(cfgpanel, wx.ID_FILE1, "", size=(250, 20))
        if file_open_commands:
            trace_cmd = file_open_commands.get_command_for_file_type('trace')
            if trace_cmd:
                self.TEXTtracecmdline.SetValue(trace_cmd)

        self.CBBadAge = wx.CheckBox(cfgpanel, -1, 'Flag if age is off')
        # Get badAge from service config
        bad_age = svc_config.get('badAge')
        self.CBBadAge.SetValue(bool(bad_age))
        self.badAge = True

        GRIDctl = gridlib.Grid(cfgpanel)
        # Only show loggers explicitly configured in logging_keys
        gridlen = len(self.logging_keys)

        GRIDctl.CreateGrid(gridlen, 2)
        GRIDctl.SetColLabelValue(0, "Logger Name")
        GRIDctl.SetColLabelValue(1, "Log Level")

        self.logging_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']

        # Populate grid with only configured loggers
        for row, loggerName in enumerate(self.logging_keys):
            updatelog = logging.getLogger(loggerName)
            GRIDctl.SetCellValue(row, 0, loggerName)
            GRIDctl.SetCellBackgroundColour(row, 0, wx.LIGHT_GREY)
            GRIDctl.SetCellValue(row, 1, logging.getLevelName(updatelog.level))
            GRIDctl.SetCellEditor(row, 1, gridlib.GridCellChoiceEditor(self.logging_levels))
            GRIDctl.SetReadOnly(row, 0)

        GRIDctl.AutoSizeColumn(0, True)
        GRIDctl.AutoSizeColumn(1, True)

        saveBTN = wx.Button(cfgpanel, label="Save Changes")
        saveBTN.Bind(wx.EVT_BUTTON, self.onSave)
        cancelBTN = wx.Button(cfgpanel, label="Cancel")
        cancelBTN.Bind(wx.EVT_BUTTON, self.onCancel)

        sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Geocoding Options section (moved to top)
        sizer.Add(wx.StaticText(cfgpanel, -1, " Geocoding Options:"))
        
        # Geocode only (ignore cache)
        self.cb_geocode_only = wx.CheckBox(cfgpanel, -1, "   Geocode only (ignore cache)")
        geocode_only = svc_config.get('geocode_only', True)
        self.cb_geocode_only.SetValue(bool(geocode_only))
        sizer.Add(self.cb_geocode_only, 0, wx.ALL, 5)
        
        # Cache only (no geocode)
        self.cb_cache_only = wx.CheckBox(cfgpanel, -1, "   Cache only (no geocode)")
        cache_only = svc_config.get('cache_only', False)
        self.cb_cache_only.SetValue(bool(cache_only))
        sizer.Add(self.cb_cache_only, 0, wx.ALL, 5)
        
        # Default country
        default_country_sizer = wx.BoxSizer(wx.HORIZONTAL)
        default_country_label = wx.StaticText(cfgpanel, -1, "   Default country (full name or empty):")
        self.default_country_text = wx.TextCtrl(cfgpanel, value="", size=(150, 20))
        default_country = svc_config.get('defaultCountry')
        if default_country:
            self.default_country_text.SetValue(str(default_country))
        default_country_sizer.Add(default_country_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        default_country_sizer.Add(self.default_country_text, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(default_country_sizer, 0, wx.ALL, 5)
        
        # Days between retrying failed lookups
        retry_days_sizer = wx.BoxSizer(wx.HORIZONTAL)
        retry_days_label = wx.StaticText(cfgpanel, -1, "   Days between retrying failed lookups:")
        self.retry_days_spinner = wx.SpinCtrl(cfgpanel, value="7", min=1, max=365, initial=7, size=(80, 20))
        retry_days = svc_config.get('days_between_retrying_failed_lookups', 7)
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
        sizer.Add(wx.StaticText(cfgpanel, -1, "Use   $n  for the name of the file within a command line - such as    notepad $n"), 0, wx.LEFT, 10)
        sizer.Add(wx.StaticText(cfgpanel, -1, "Use   $n  without any command to open default application for that file type"), 0, wx.LEFT, 10)
        
        # Bad Age checkbox
        sizer.Add(self.CBBadAge, 0, wx.ALL, 5)
        sizer.AddSpacer(20)
        
        sizer.Add(wx.StaticText(cfgpanel, -1, " Logging Options:"))
        
        # Add "Set All Levels" control
        setAllSizer = wx.BoxSizer(wx.HORIZONTAL)
        setAllSizer.Add(wx.StaticText(cfgpanel, -1, "Set all logging levels to:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        self.setAllChoice = wx.Choice(cfgpanel, choices=self.logging_levels)
        self.setAllChoice.SetSelection(1)  # Default to INFO
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
        self.Show(True)

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
                    if hasattr(logger, 'handlers'):
                        for handler in logger.handlers[:]:
                            if isinstance(handler, logging.FileHandler):
                                if Path(handler.baseFilename).resolve() == log_file_path.resolve():
                                    handler.close()
                                    file_handlers_to_reopen.append((handler, logger))
                                    logger.removeHandler(handler)
                
                # Clear the file
                with open(log_file_path, 'w', encoding='utf-8') as f:
                    pass
                
                # Recreate and reattach the file handlers
                from const import LOG_CONFIG
                formatter = logging.Formatter(LOG_CONFIG['formatters']['standard']['format'])
                
                for old_handler, parent_logger in file_handlers_to_reopen:
                    new_handler = logging.FileHandler(
                        filename=old_handler.baseFilename,
                        mode='a',  # Append mode since file now exists and is empty
                        encoding='utf-8'
                    )
                    new_handler.setLevel(old_handler.level)
                    new_handler.setFormatter(formatter)
                    parent_logger.addHandler(new_handler)
                
                _log.info("Log file cleared by user via Configuration dialog")
            else:
                wx.MessageBox(
                    f"Log file does not exist:\n\n{log_file_path.absolute()}",
                    "File Not Found",
                    wx.OK | wx.ICON_INFORMATION
                )
        except Exception as e:
            _log.exception("Failed to clear log file")
            wx.MessageBox(
                f"Failed to clear log file:\n\n{str(e)}",
                "Error",
                wx.OK | wx.ICON_ERROR
            )

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
        self.file_open_commands.add_file_type_command('kml', self.TEXTkmlcmdline.GetValue())
        self.file_open_commands.add_file_type_command('csv', self.TEXTcsvcmdline.GetValue())
        self.file_open_commands.add_file_type_command('trace', self.TEXTtracecmdline.GetValue())
        
        # Update service config
        try:
            if hasattr(self.svc_config, 'set'):
                self.svc_config.set('badAge', bool(self.CBBadAge.GetValue()))
                self.svc_config.set('geocode_only', bool(self.cb_geocode_only.GetValue()))
                self.svc_config.set('cache_only', bool(self.cb_cache_only.GetValue()))
                self.svc_config.set('days_between_retrying_failed_lookups', self.retry_days_spinner.GetValue())
                # Set default country - convert empty string or "none" (case insensitive) to None
                default_country_value = self.default_country_text.GetValue().strip()
                if not default_country_value or default_country_value.lower() == 'none':
                    default_country_value = None
                self.svc_config.set('defaultCountry', default_country_value)
        except Exception:
            _log.exception("ConfigDialog.onSave: failed to set config values in svc_config")
        
        # Persist settings if available
        try:
            if hasattr(self.svc_config, 'savesettings'):
                self.svc_config.savesettings()
        except Exception:
            _log.exception("ConfigDialog.onSave: savesettings failed")
        
        self.Close()
        self.DestroyLater()

    def onCancel(self, event):
        self.Close()
        self.DestroyLater()
