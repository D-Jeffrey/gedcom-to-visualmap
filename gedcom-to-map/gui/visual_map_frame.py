import logging
import os

import wx

from style.stylemanager import FontManager
from const import GUINAME, KMLMAPSURL

_log = logging.getLogger(__name__.lower())

from .config_dialog import ConfigDialog
from .about_dialog import AboutDialog
from .help_dialog import HelpDialog
from .visual_map_panel import VisualMapPanel
from .visual_gedcom_ids import VisualGedcomIds

class VisualMapFrame(wx.Frame):
    def __init__(self, *args, **kw):
        # ensure the parent's __init__ is called so the wx.frame is created
        super().__init__(*args, **kw)

        self.font_manager = FontManager()
        self.font_name, self.font_size = self.font_manager.get_font_name_size()

        self.set_current_font()

        self.SetMinSize((800, 800))
        self.StatusBar = self.CreateStatusBar()
        self.SetStatusText("This is the statusbar")
        # create a menu bar
        self.makeMenuBar()
        # and a status bar

        self.StatusBar.SetFieldsCount(number=2, widths=[-1, 28 * self.font_size])
        widthMax = self.font_manager.get_text_width(30)
        self.StatusBar.SetFieldsCount(number=2, widths=[-1, widthMax])
        self.SetStatusText("Visual Mapping ready", 0)
        self.inTimer = False

        # Create and set up the main panel within the frame
        self.visual_map_panel = VisualMapPanel(self, self.font_manager)  # pass the frame's FontManager into the panel
        # Configure panel options (panel exposes SetupOptions)
        try:
            self.visual_map_panel.SetupOptions()
        except Exception:
            _log.exception("VisualMapFrame: SetupOptions failed")

    def set_current_font(self):
        self.font = self.font_manager.get_font()
        wx.Frame.SetFont(self, self.font)

    def start(self):
        try:
            self.visual_map_panel.SetupButtonState()
        except Exception:
            _log.exception("start: SetupButtonState failed")
        self.Show()

    def stop(self):
        if self.visual_map_panel:
            try:
                self.visual_map_panel.OnCloseWindow()
            except Exception:
                _log.exception("stop: OnCloseWindow failed")

    def makeMenuBar(self):
        self.id = None

        self.id = VisualGedcomIds()
        self.menuBar = menuBar = wx.MenuBar()
        self.fileMenu = fileMenu = wx.Menu()
        fileMenu.Append(wx.ID_OPEN, "&Open...\tCtrl-O", "Select a GEDCOM file")
        fileMenu.Append(wx.ID_SAVEAS, "Save &as...")
        fileMenu.Append(wx.ID_CLOSE, "&Close")
        fileMenu.AppendSeparator()
        fileMenu.Append(wx.ID_EXIT)

        # file history
        self.filehistory = wx.FileHistory()
        self.filehistory.UseMenu(fileMenu)

        optionsMenu = wx.Menu()
        optionsMenu.Append(wx.ID_REVERT, "&Reset to Default")
        optionsMenu.Append(wx.ID_SETUP, "&Options Setup")

        self.ActionMenu = ActionMenu = wx.Menu()
        ActionMenu.Append(wx.ID_FIND, "&Find\tCtrl-F", "Find by name")
        ActionMenu.Append(wx.ID_INFO, "Statistics Sumary")
        ActionMenu.Append(self.id.IDs['ID_BTNBROWSER'], "Open Result in &Browser")
        ActionMenu.Append(self.id.IDs['ID_BTNCSV'], "Open &CSV")

        helpMenu = wx.Menu()
        helpMenu.Append(wx.ID_HELP, "Help")
        helpMenu.Append(wx.ID_ABOUT, "About")

        menuBar.Append(self.fileMenu, "&File")
        menuBar.Append(ActionMenu, "&Actions")
        menuBar.Append(optionsMenu, "&Options")
        menuBar.Append(helpMenu, "&Help")

        self.SetMenuBar(menuBar)

        # bind menu events
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
        self.Bind(wx.EVT_MENU, self.OnOpenCSV, id=self.id.IDs['ID_BTNCSV'])
        self.Bind(wx.EVT_MENU, self.OnOpenBrowser, id=self.id.IDs['ID_BTNBROWSER'])

        # Font submenu
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

    def set_gui_font(self, font_name, font_size):
        self.font_manager.apply_current_font_recursive(self)
        try:
            self.visual_map_panel.set_current_font()
        except Exception:
            _log.exception("set_gui_font: visual_map_panel.set_current_font failed")

        font = wx.Font(pointSize=font_size, family=wx.FONTFAMILY_DEFAULT,
                       style=wx.FONTSTYLE_NORMAL, weight=wx.FONTWEIGHT_NORMAL,
                       faceName=font_name)
        frame = self
        frame.SetFont(font)
        try:
            frame.GetMenuBar().SetFont(font)
        except Exception:
            pass
        try:
            frame.GetStatusBar().SetFont(font)
        except Exception:
            pass

        self.Layout()
        self.Refresh()

    def on_font_menu_item(self, event):
        mi = self.GetMenuBar().FindItemById(event.GetId())
        if mi is None:
            return
        face = mi.GetItemLabelText()
        success = self.font_manager.set_font(face)
        if success:
            self.font_name = face
            self.set_gui_font(self.font_name, self.font_size)

    def on_font_size_menu_item(self, event):
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
            self.font_size = size
            self.set_gui_font(self.font_name, self.font_size)

    def OnExit(self, event):
        try:
            self.visual_map_panel.myTimer.Stop()
        except Exception:
            pass
        try:
            self.Unbind(wx.EVT_TIMER, self)
        except Exception:
            pass
        try:
            self.visual_map_panel.gOp.savesettings()
        except Exception:
            pass

        if getattr(event, "GetEventType", None) and event.GetEventType() == wx.EVT_CLOSE.typeId:
            self.Destroy()
        else:
            self.Close(True)

    def OnOpenCSV(self, event):
        try:
            self.visual_map_panel.OpenCSV()
        except Exception:
            _log.exception("OnOpenCSV failed")

    def OnOpenBrowser(self, event):
        try:
            self.visual_map_panel.OpenBrowser()
        except Exception:
            _log.exception("OnOpenBrowser failed")

    def OnFileOpenDialog(self, evt):
        dDir = os.getcwd()
        filen = ""
        if self.visual_map_panel and getattr(self.visual_map_panel, "gOp", None):
            infile = self.visual_map_panel.gOp.get('GEDCOMinput')
            if infile:
                dDir, filen = os.path.split(infile)
        dlg = wx.FileDialog(self,
                            defaultDir=dDir,
                            defaultFile=filen,
                            wildcard="GEDCOM source (*.ged)|*.ged|All Files|*",
                            style=wx.FD_OPEN | wx.FD_CHANGE_DIR | wx.FD_FILE_MUST_EXIST)
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
                self.visual_map_panel.LoadGEDCOM()
            except Exception:
                _log.exception("LoadGEDCOM failed")

    def OnFileResultDialog(self, evt):
        dDir = os.getcwd()
        dFile = "visgedcom.html"
        if self.visual_map_panel and getattr(self.visual_map_panel, "gOp", None):
            resultfile = self.visual_map_panel.gOp.get('Result')
            if resultfile:
                dDir, dFile = os.path.split(resultfile)
            else:
                resultfile = self.visual_map_panel.gOp.get('GEDCOMinput')
                if resultfile:
                    dDir, dFile = os.path.split(resultfile)
        dFile = os.path.splitext(dFile)[0]

        dlg = wx.FileDialog(self,
                            defaultDir=dDir,
                            defaultFile=dFile,
                            wildcard="HTML Output Result (*.html)|*.html|Map KML (*.kml)|*.kml|All Files|*",
                            style=wx.FD_SAVE | wx.FD_CHANGE_DIR)

        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            _log.debug("Output selected %s", path)
            filetype = os.path.splitext(path)[1]
            isHTML = not (filetype.lower() in ['.kml'])
            try:
                self.visual_map_panel.gOp.setResults(path, isHTML)
                self.visual_map_panel.id.TEXTResult.SetValue(path)
                self.visual_map_panel.id.RBResultOutType.SetSelection(0 if isHTML else 1)
                self.visual_map_panel.SetupButtonState()
            except Exception:
                _log.exception("OnFileResultDialog: failed to set results")
        dlg.Destroy()
        wx.Yield()

    def Cleanup(self, *args):
        del self.filehistory
        try:
            if getattr(self, "menuBar", None):
                self.menuBar.Destroy()
        except Exception:
            _log.exception("Cleanup: failed to destroy menuBar")

    def OnFileHistory(self, evt):
        fileNum = evt.GetId() - wx.ID_FILE1
        path = self.filehistory.GetHistoryFile(fileNum)
        _log.debug("You selected %s", path)
        try:
            self.filehistory.AddFileToHistory(path)
            self.visual_map_panel.setInputFile(path)
            wx.Yield()
            self.visual_map_panel.LoadGEDCOM()
        except Exception:
            _log.exception("OnFileHistory failed")

    def OnAbout(self, event):
        try:
            if event.GetId() == wx.ID_ABOUT:
                dialog = AboutDialog(self, title=f"About {GUINAME} {self.font_manager.get_font_name_size()[1]}", font_manager=self.font_manager)
            else:
                dialog = HelpDialog(self, title=f"Help for {GUINAME}", font_manager=self.font_manager)
            dialog.ShowModal()
            dialog.Destroy()
        except Exception:
            _log.exception("OnAbout failed")

    def OnInfo(self, event):
        try:
            msg = "No people loaded yet\n"
            if getattr(self.visual_map_panel, "gOp", None) and getattr(self.visual_map_panel.gOp, 'people', None):
                self.visual_map_panel.gOp.totalGEDpeople = {len(self.visual_map_panel.gOp.people)}
                msg = f'Total People :{self.visual_map_panel.gOp.totalGEDpeople}\n'
                if self.visual_map_panel.gOp.timeframe:
                    msg += f"\nTimeframe : {self.visual_map_panel.gOp.timeframe.get('from','?')}-{self.visual_map_panel.gOp.timeframe.get('to','?')}\n"
                if getattr(self.visual_map_panel.gOp, "selectedpeople", 0) > 0:
                    msg += f"\nDirect  people {self.visual_map_panel.gOp.selectedpeople} in the heritage line\n"
                else:
                    msg += "\nSelect main person for heritage line\n"
            if hasattr(self.visual_map_panel.gOp, 'lookup') and getattr(self.visual_map_panel.gOp.lookup, 'address_book', None):
                stats = self.visual_map_panel.gOp.lookup.address_book.updatestats()
                msg += f'\nTotal cached addresses: {self.visual_map_panel.gOp.lookup.address_book.len()}\n{stats}'
            wx.MessageBox(msg, 'Statistics', wx.OK | wx.ICON_INFORMATION)
        except Exception:
            _log.exception("OnInfo failed")

    def OnFind(self, event):
        try:
            self.visual_map_panel.peopleList.list.OnFind(event)
        except Exception:
            _log.exception("OnFind failed")

    def onOptionsReset(self, event):
        try:
            if getattr(self.visual_map_panel, "gOp", None) and hasattr(self.visual_map_panel.gOp, "defaults"):
                self.visual_map_panel.gOp.defaults()
            self.visual_map_panel.SetupOptions()
            wx.MessageBox("Restored options to defaults", "Reset Options", wx.OK | wx.ICON_INFORMATION)
        except Exception:
            _log.exception("onOptionsReset failed")

    def onOptionsSetup(self, event):
        try:
            dialog = ConfigDialog(None, title='Configuration Options', gOp=getattr(self.visual_map_panel, "gOp", None))
            self.config_dialog = dialog
        except Exception:
            _log.exception("onOptionsSetup failed")