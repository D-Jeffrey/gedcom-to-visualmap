from render.result_type import ResultType

"""
visual_map_frame.py

Main application Frame for gedcom-to-visualmap.

Provides the VisualMapFrame which hosts the primary VisualMapPanel, menu bar,
status bar and various menu command handlers. Designed to be lightweight and
delegate most functionality to the contained panel and helper dialogs.
"""
from typing import Any, Optional
import logging
import os

import wx

from const import GUINAME
from services.interfaces import IConfig, IState, IProgressTracker

_log = logging.getLogger(__name__.lower())

# UI Constants
STATUS_BAR_RIGHT_FIELD_CHARS = 30  # Width of right status bar field in characters

from ..dialogs.config_dialog import ConfigDialog
from ..dialogs.about_dialog import AboutDialog
from ..dialogs.help_dialog import HelpDialog
from ..panels.visual_map_panel import VisualMapPanel
from ..layout.visual_gedcom_ids import VisualGedcomIds
from ..layout.font_manager import FontManager
from ..layout.colour_manager import ColourManager


class VisualMapFrame(wx.Frame):
    """Main application window/frame.

    Responsible for creating the top-level frame, menu bar, status bar and the
    primary VisualMapPanel. Menu event handlers are implemented here and delegate
    detailed behaviour to the panel, dialogs or services where appropriate.
    """

    # runtime attributes with basic type hints
    font_manager: FontManager  # Initialized in __init__
    color_manager: ColourManager  # Initialized in __init__
    svc_config: IConfig  # Initialized in __init__
    svc_state: IState  # Initialized in __init__
    svc_progress: IProgressTracker  # Initialized in __init__
    StatusBar: wx.StatusBar  # Created in makeStatusBar()
    menuBar: wx.MenuBar  # Created in makeMenuBar()
    visual_map_panel: VisualMapPanel  # Created in __init__
    filehistory: wx.FileHistory  # Created in makeMenuBar()
    id: VisualGedcomIds  # Created in makeMenuBar()
    fileMenu: wx.Menu  # Created in makeMenuBar()
    ActionMenu: wx.Menu  # Created in makeMenuBar()
    font: wx.Font  # Set in set_current_font()

    def __init__(
        self,
        parent: wx.Window,
        svc_config: IConfig,
        svc_state: IState,
        svc_progress: IProgressTracker,
        font_manager: FontManager,
        color_manager: ColourManager,
        *args: Any,
        **kw: Any,
    ) -> None:
        """Construct the frame.

        Args:
            parent: wx parent window (or None).
            svc_config: Configuration service (IConfig).
            svc_state: Runtime state service (IState).
            svc_progress: Progress tracking service (IProgressTracker).
            font_manager: Font manager instance.
            color_manager: Colour manager instance.
            *args/**kw: forwarded to wx.Frame constructor (title, size, style).
        """
        # ensure the parent's __init__ is called so the wx.frame is created
        super().__init__(parent, *args, **kw)

        self.svc_config = svc_config
        self.svc_state = svc_state
        self.svc_progress = svc_progress
        self.font_manager = font_manager
        self.color_manager = color_manager
        self.set_current_font()

        self.SetMinSize((800, 800))

        self.makeStatusBar()
        self.makeMenuBar()

        # Create and set up the main panel within the frame
        # Pass services to VisualMapPanel
        self.visual_map_panel = VisualMapPanel(
            self, self.font_manager, self.color_manager, self.svc_config, self.svc_state, self.svc_progress
        )

    def set_current_font(self) -> None:
        """Ensure the frame uses the current font from the FontManager."""
        self.font = self.font_manager.get_font()
        wx.Frame.SetFont(self, self.font)

    def start(self) -> None:
        """Start the UI by starting the contained panel and showing the frame."""
        self.visual_map_panel.start()
        self.Show()

    def stop(self) -> None:
        """Request clean shutdown of the UI by delegating to the panel."""
        self.visual_map_panel.stop()

    def makeStatusBar(self):
        """Create and configure the status bar for the frame."""
        self.StatusBar = self.CreateStatusBar()
        self.SetStatusText("This is the statusbar")
        # Compute field widths once (use font manager to determine a sensible width)
        widthMax = self.font_manager.get_text_width(STATUS_BAR_RIGHT_FIELD_CHARS)
        self.StatusBar.SetFieldsCount(number=2, widths=[-1, widthMax])
        self.SetStatusText("Visual Mapping ready", 0)

    def bind_menu_events(self) -> None:
        """Bind menu and window events to their handlers."""
        self.Bind(wx.EVT_MENU, self.OnFileOpenDialog, id=wx.ID_OPEN)
        self.Bind(wx.EVT_MENU, self.OnFileResultDialog, id=wx.ID_SAVEAS)
        self.Bind(wx.EVT_MENU, self.OnExit, id=wx.ID_EXIT)
        self.Bind(wx.EVT_CLOSE, self.OnExit)
        self.Bind(wx.EVT_MENU, self.OnInfo, id=wx.ID_INFO)
        self.Bind(wx.EVT_MENU, self.OnAbout, id=wx.ID_ABOUT)
        self.Bind(wx.EVT_MENU, self.OnAbout, id=wx.ID_HELP)
        self.Bind(wx.EVT_MENU_RANGE, self.OnFileHistory, id=wx.ID_FILE1, id2=wx.ID_FILE9)
        self.Bind(wx.EVT_MENU, self.onOptionsReset, id=wx.ID_REVERT)
        self.Bind(wx.EVT_MENU, self.OnFind, id=wx.ID_FIND)
        self.Bind(wx.EVT_MENU, self.onOptionsSetup, id=wx.ID_SETUP)
        self.Bind(wx.EVT_MENU, self.OnOpenCSV, id=self.id.IDs["BTNCSV"])
        self.Bind(wx.EVT_MENU, self.OnOpenBrowser, id=self.id.IDs["BTNBROWSER"])
        # Bind window activation to check for appearance changes
        self.Bind(wx.EVT_ACTIVATE, self.OnActivate)

    def populate_font_menus(self, optionsMenu: wx.Menu) -> None:
        """Populate optionsMenu with font face and size submenus.

        Creates two radio submenus (font face and font size) and binds their
        items to handlers that update the application's FontManager.
        """
        set_font_menu = wx.Menu()
        for fname in self.font_manager.PREDEFINED_FONTS:
            item = wx.MenuItem(set_font_menu, wx.ID_ANY, fname, kind=wx.ITEM_RADIO)
            set_font_menu.Append(item)
            current_face = self.font_manager._current.get("face") if self.font_manager._current else None
            if current_face == fname:
                item.Check(True)
        optionsMenu.AppendSubMenu(set_font_menu, "Set Font")
        for mi in set_font_menu.GetMenuItems():
            self.Bind(wx.EVT_MENU, self.on_font_menu_item, mi)

        """Create and bind the font-size submenu under optionsMenu."""
        set_font_size_menu = wx.Menu()
        for fsize in self.font_manager.PREDEFINED_FONT_SIZES:
            item = wx.MenuItem(set_font_size_menu, wx.ID_ANY, str(fsize), kind=wx.ITEM_RADIO)
            set_font_size_menu.Append(item)
            current_size = self.font_manager._current.get("size") if self.font_manager._current else None
            if current_size == fsize:
                item.Check(True)
        optionsMenu.AppendSubMenu(set_font_size_menu, "Set Font Size")
        for mi in set_font_size_menu.GetMenuItems():
            self.Bind(wx.EVT_MENU, self.on_font_size_menu_item, mi)

    def makeMenuBar(self) -> None:
        """Build and attach the application's menu bar."""
        self.id = VisualGedcomIds(svc_config=self.svc_config)
        self.menuBar = menuBar = wx.MenuBar()
        self.fileMenu = fileMenu = wx.Menu()
        fileMenu.Append(wx.ID_OPEN, "&Open...\tCtrl-O", "Select a GEDCOM file")
        fileMenu.Append(wx.ID_SAVEAS, "Save &as...")
        fileMenu.Append(wx.ID_CLOSE, "&Close")
        fileMenu.AppendSeparator()
        fileMenu.Append(wx.ID_EXIT)

        self.filehistory = wx.FileHistory()
        self.filehistory.UseMenu(fileMenu)

        optionsMenu = wx.Menu()
        optionsMenu.Append(wx.ID_REVERT, "&Reset to Default")
        optionsMenu.Append(wx.ID_SETUP, "&Options Setup")

        self.ActionMenu = ActionMenu = wx.Menu()
        ActionMenu.Append(wx.ID_FIND, "&Find\tCtrl-F", "Find by name")
        ActionMenu.Append(wx.ID_INFO, "Statistics Summary")
        ActionMenu.Append(self.id.IDs["BTNBROWSER"], "Open Result in &Browser")
        ActionMenu.Append(self.id.IDs["BTNCSV"], "Open &CSV")

        helpMenu = wx.Menu()
        helpMenu.Append(wx.ID_HELP, "Help")
        helpMenu.Append(wx.ID_ABOUT, "About")

        menuBar.Append(self.fileMenu, "&File")
        menuBar.Append(ActionMenu, "&Actions")
        menuBar.Append(optionsMenu, "&Options")
        menuBar.Append(helpMenu, "&Help")

        self.SetMenuBar(menuBar)

        self.bind_menu_events()

        self.populate_font_menus(optionsMenu)

    def set_gui_font(self) -> None:
        """Apply a new GUI font (propagate to frame, menus, statusbar and panel)."""
        # Apply recursively to frame (includes menu bar and status bar)
        self.font_manager.apply_current_font_recursive(self)

        # Explicitly update panel (may have special font handling)
        self.visual_map_panel.set_current_font()

        # Notify any registered dialogs/panels of the font change
        self.font_manager.notify_font_change()

        self.Layout()
        self.Refresh()

    def on_font_menu_item(self, event: wx.CommandEvent) -> None:
        """Handle selection of a font-face menu item.

        Updates the FontManager and applies the new face across the UI.
        """
        mi = self.GetMenuBar().FindItemById(event.GetId())
        if mi is None:
            return
        face = mi.GetItemLabelText()
        success = self.font_manager.set_font(face)
        if success:
            self.set_gui_font()

    def on_font_size_menu_item(self, event: wx.CommandEvent) -> None:
        """Handle selection of a font-size menu item.

        Parses the selected size and applies it via the FontManager.
        """
        mi = self.GetMenuBar().FindItemById(event.GetId())
        if mi is None:
            return
        size_str = mi.GetItemLabelText()
        try:
            size = int(size_str)
        except ValueError:
            _log.error(f"Invalid font size selected: '{size_str}'")
            return
        success = self.font_manager.set_font_size(size)
        if success:
            self.set_gui_font()

    def OnExit(self, event: wx.Event) -> None:
        """Handle application exit: stop timers, save settings and close the window."""
        self.visual_map_panel.stop_timer()
        try:
            self.svc_config.savesettings()
        except Exception:
            _log.exception("OnExit: failed to save settings")

        if getattr(event, "GetEventType", None) and event.GetEventType() == wx.EVT_CLOSE.typeId:
            self.Destroy()
        else:
            self.Close(True)

    def OnActivate(self, event: wx.ActivateEvent) -> None:
        """Handle window activation: check for system appearance changes."""
        if event.GetActive():
            # Window is being activated - check if appearance mode changed
            if self.color_manager.refresh_colors():
                # Colors changed, need to refresh the UI
                _log.info("Appearance mode changed, refreshing UI colors")
                # Refresh the panel colors
                self.visual_map_panel.refresh_colors()
        event.Skip()  # Allow event to propagate

    def OnOpenCSV(self, event: wx.Event) -> None:
        """Menu handler: open CSV/geo table using the panel helper."""
        try:
            self.visual_map_panel.actions.OpenCSV()
        except Exception:
            _log.exception("OnOpenCSV failed")

    def OnOpenBrowser(self, event: wx.Event) -> None:
        """Menu handler: open the generated result in a browser or KML viewer."""
        try:
            self.visual_map_panel.actions.OpenBrowser()
        except Exception:
            _log.exception("OnOpenBrowser failed")

    def OnFileOpenDialog(self, evt: wx.Event) -> None:
        """Show a file-open dialog for selecting a GEDCOM and load it if chosen.

        Adds the selected file to the recent-file history and triggers LoadGEDCOM.
        """
        dDir = os.getcwd()
        filen = ""
        infile = self.svc_config.get("GEDCOMinput")
        if infile:
            dDir, filen = os.path.split(infile)
        dlg = wx.FileDialog(
            self,
            defaultDir=dDir,
            defaultFile=filen,
            wildcard="GEDCOM source (*.ged)|*.ged|All Files|*",
            style=wx.FD_OPEN | wx.FD_CHANGE_DIR | wx.FD_FILE_MUST_EXIST,
        )
        Proceed = dlg.ShowModal() == wx.ID_OK
        if Proceed:
            path = dlg.GetPath()
            _log.debug("You selected %s", path)
            try:
                self.visual_map_panel.setInputFile(path)
            except Exception:
                _log.exception("Failed to set input file")

            # add it to the history
            try:
                self.filehistory.AddFileToHistory(path)
                self.filehistory.Save(self.visual_map_panel.fileConfig)
            except Exception:
                pass

        dlg.Destroy()
        wx.Yield()
        if Proceed:
            try:
                self.visual_map_panel.actions.LoadGEDCOM()
            except Exception:
                _log.exception("LoadGEDCOM failed")

    def OnFileResultDialog(self, evt: wx.Event) -> None:
        """Show a save dialog to select an output result path (HTML or KML).

        Updates configuration with the chosen result path and refreshes the radio selection.
        """
        dDir = os.getcwd()
        dFile = "visgedcom.html"
        resultfile = self.svc_config.get("ResultFile")
        if resultfile:
            dDir, dFile = os.path.split(resultfile)
        else:
            resultfile = self.svc_config.get("GEDCOMinput")
            if resultfile:
                dDir, dFile = os.path.split(resultfile)
        dFile = os.path.splitext(dFile)[0]

        dlg = wx.FileDialog(
            self,
            defaultDir=dDir,
            defaultFile=dFile,
            wildcard="HTML Output Result (*.html)|*.html|Map KML (*.kml)|*.kml|All Files|*",
            style=wx.FD_SAVE | wx.FD_CHANGE_DIR,
        )

        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            _log.debug("Output selected %s", path)
            try:
                result_type = self.svc_config.get("ResultType")
            except Exception:
                result_type = ResultType.HTML
            isHTML = result_type == ResultType.HTML
            _, fname = os.path.split(path or "")
            try:
                # Update ResultFile and ResultType via services
                enforced = ResultType.ResultTypeEnforce(result_type)
                ext = ResultType.file_extension(enforced)
                base, _ = os.path.splitext(fname or "")
                result_file = (base or "output") + "." + ext
                if hasattr(self.svc_config, "set"):
                    self.svc_config.set("ResultType", enforced)
                    self.svc_config.set("ResultFile", result_file)
                self.visual_map_panel.id.TEXTResultFile.SetValue(result_file)
                self.visual_map_panel.id.RBResultType.SetSelection(0 if isHTML else 1)
                self.visual_map_panel.SetupButtonState()
            except Exception:
                _log.exception("OnFileResultDialog: failed to set results")
        dlg.Destroy()
        wx.Yield()

    def Cleanup(self, *args: Any) -> None:
        """Tidy up frame resources (menu, history) before exit."""
        del self.filehistory
        try:
            if getattr(self, "menuBar", None):
                self.menuBar.Destroy()
        except Exception:
            _log.exception("Cleanup: failed to destroy menuBar")

    def OnFileHistory(self, evt: wx.Event) -> None:
        """Handle selection from the recent-file history and load the chosen file."""
        fileNum = evt.GetId() - wx.ID_FILE1
        path = self.filehistory.GetHistoryFile(fileNum)
        _log.debug("You selected %s", path)
        try:
            self.filehistory.AddFileToHistory(path)
            self.visual_map_panel.setInputFile(path)
            wx.Yield()
            self.visual_map_panel.actions.LoadGEDCOM()
        except Exception:
            _log.exception("OnFileHistory failed")

    def OnAbout(self, event: wx.Event) -> None:
        """Show About or Help dialog depending on the menu id."""
        try:
            if event.GetId() == wx.ID_ABOUT:
                dialog = AboutDialog(
                    self,
                    title=f"About {GUINAME} {self.font_manager.get_font_name_size()[1]}",
                    font_manager=self.font_manager,
                )
            else:
                dialog = HelpDialog(self, title=f"Help for {GUINAME}", font_manager=self.font_manager)
            dialog.ShowModal()
            dialog.Destroy()
        except Exception:
            _log.exception("OnAbout failed")

    def OnInfo(self, event: wx.Event) -> None:
        """Display summary statistics about the currently loaded GEDCOM data."""
        try:
            msg = "No people loaded yet\n"
            if self.svc_state.people:
                total_ged_people = len(self.svc_state.people)
                msg = f"Total People: {total_ged_people}\n"
                try:
                    timeframe = self.svc_config.get("timeframe")
                    if timeframe:
                        msg += f"\nTimeframe: {timeframe.get('from', '?')}-{timeframe.get('to', '?')}\n"
                except Exception:
                    pass
                selected = self.svc_state.selectedpeople
                if selected > 0:
                    msg += f"\nDirect people: {selected} in the heritage line\n"
                else:
                    msg += "\nSelect main person for heritage line\n"
            if (
                self.svc_state.lookup
                and hasattr(self.svc_state.lookup, "address_book")
                and self.svc_state.lookup.address_book
            ):
                try:
                    stats = self.visual_map_panel.actions.updatestats()
                    msg += f"\nTotal cached addresses: {self.svc_state.lookup.address_book.len()}\n{stats}"
                except Exception:
                    pass
            wx.MessageBox(msg, "Statistics", wx.OK | wx.ICON_INFORMATION)
        except Exception:
            _log.exception("OnInfo failed")

    def OnFind(self, event: wx.Event) -> None:
        """Delegate the Find action to the people list widget."""
        try:
            self.visual_map_panel.peopleList.list.OnFind(event)
        except Exception:
            _log.exception("OnFind failed")

    def onOptionsReset(self, event: wx.Event) -> None:
        """Reset application options to defaults and refresh the UI."""
        try:
            if hasattr(self.svc_config, "defaults"):
                self.svc_config.defaults()
            self.visual_map_panel.SetupOptions()
            wx.MessageBox("Restored options to defaults", "Reset Options", wx.OK | wx.ICON_INFORMATION)
        except Exception:
            _log.exception("onOptionsReset failed")

    def onOptionsSetup(self, event: wx.Event) -> None:
        """Open the configuration dialog for editing application options."""
        try:
            svc_config = self.svc_config

            # Get logger names from logging_defaults (dict) or logging_keys (list) for backwards compatibility
            logging_defaults = svc_config.options.get("logging_defaults", {})
            logger_names = (
                list(logging_defaults.keys()) if logging_defaults else svc_config.options.get("logging_keys", [])
            )

            dialog = ConfigDialog(
                None,
                title="Configuration Options",
                svc_config=svc_config,
                file_open_commands=svc_config.file_open_commands,
                logging_keys=logger_names,
                color_manager=self.color_manager,
                parent_refresh_callback=lambda: self.visual_map_panel.refresh_colors(),
            )
            dialog.ShowModal()
            dialog.Destroy()
        except Exception:
            _log.exception("onOptionsSetup failed")

    def OnCloseWindow(self, event):
        try:
            if getattr(self, "visual_map_panel", None):
                try:
                    self.visual_map_panel._shutdown_background()
                except Exception:
                    _log.exception("visual_map_panel._shutdown_background failed")
        finally:
            # then allow normal close/destroy
            event.Skip()
