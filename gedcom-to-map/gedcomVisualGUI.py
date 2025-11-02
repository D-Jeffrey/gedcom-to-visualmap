__all__ = ['VisualGedcomIds', 'VisualMapFrame', 'PeopleListCtrl', 'PeopleListCtrlPanel', 'VisualMapPanel']

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
#
#
#  gedcomVisualGUI.py : GUI Interface  for gedcom-to-map
#    See https://github.com/D-Jeffrey/gedcom-to-visualmap
#
#
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
#!/usr/bin/env python

import _thread
import logging
import logging.config
import os
import os.path
import platform
from pathlib import Path
import re
import subprocess
import shutil
import sys
import time
from datetime import datetime
import webbrowser
from warnings import catch_warnings
from models.Person import Person
from gedcom.GedcomParser import CheckAge 
from typing import Dict, Union

import wx
# pylint: disable=no-member
import wx.lib.mixins.listctrl as listmix
import wx.lib.sized_controls as sc
import wx.lib.mixins.inspection as wit
import wx.lib.newevent
import wx.html
import wx.grid
import xyzservices.providers as xyz 


from const import GUINAME, GVFONT, KMLMAPSURL, LOG_CONFIG, NAME, VERSION
from gedcomoptions import gvOptions, ResultsType 
from gedcomvisual import doTrace
from gedcomDialogs import *
from style.stylemanager import FontManager, ApproxTextWidth


_log = logging.getLogger(__name__.lower())


InfoBoxLines = 8
# This creates a new Event class and a EVT binder function

(UpdateBackgroundEvent, EVT_UPDATE_STATE) = wx.lib.newevent.NewEvent()
from wx.lib.embeddedimage import PyEmbeddedImage


class VisualGedcomIds():
    def __init__(self):
        
        self.ids = [
            'ID_CBMarksOn', 'ID_CBHeatMap', 'ID_CBFlyTo', 'ID_CBBornMark', 'ID_CBDieMark', 'ID_LISTMapStyle',
            'ID_CBMarkStarOn', 'ID_RBGroupBy', 'ID_CBUseAntPath', 'ID_CBMapTimeLine',
            'ID_CBHomeMarker', 'ID_LISTHeatMapTimeStep', 'ID_TEXTGEDCOMinput', 'ID_TEXTResult',
            'ID_RBResultsType', 'ID_TEXTMain', 'ID_TEXTName', 'ID_RBKMLMode', 'ID_INTMaxMissing', 'ID_INTMaxLineWeight',
            'ID_CBUseGPS', 'ID_CBCacheOnly', 'ID_CBAllEntities',  'ID_CBMapControl',
            'ID_CBMapMini', 'ID_BTNLoad', 'ID_BTNCreateFiles', 'ID_BTNCSV', 'ID_BTNTRACE', 'ID_BTNSTOP', 'ID_BTNBROWSER',
            'ID_CBGridView', 'CBYougeAge', 'ID_CBSummary', 'ID_TEXTDefaultCountry'
        ]
        self.IDs = {name: wx.NewIdRef() for name in self.ids}
        # ID = Attribute (in gOp), Action impact
        self.IDtoAttr = {
            self.IDs['ID_CBMarksOn']: ('MarksOn', 'Redraw'),
            self.IDs['ID_CBHeatMap']: ('HeatMap', ''),
            self.IDs['ID_CBBornMark']: ('BornMark', 'Redraw'),
            self.IDs['ID_CBDieMark']: ('DieMark', 'Redraw'),
            self.IDs['ID_LISTMapStyle']: ('MapStyle', 'Redraw'),
            self.IDs['ID_CBMarkStarOn']: ('MarkStarOn', 'Redraw'),
            self.IDs['ID_RBGroupBy']: ('GroupBy', 'Redraw'),
            self.IDs['ID_CBUseAntPath']: ('UseAntPath', 'Redraw'),
            self.IDs['ID_CBMapTimeLine']: ('MapTimeLine', 'Redraw'),
            self.IDs['ID_CBHomeMarker']: ('HomeMarker', 'Redraw'),
            self.IDs['ID_CBFlyTo']: ('UseBalloonFlyto', 'Redraw'),
            self.IDs['ID_LISTHeatMapTimeStep']: ('MapTimeLine', 'Redraw'),
            self.IDs['ID_TEXTGEDCOMinput']: ('GEDCOMinput', 'Reload'),
            self.IDs['ID_TEXTResult']: ('Result', 'Redraw', 'Result'),
            self.IDs['ID_RBResultsType']: ('ResultType', 'Redraw'),
            self.IDs['ID_TEXTMain']: ('Main', 'Reload'),
            self.IDs['ID_TEXTName']: ('Name', ''),
            self.IDs['ID_RBKMLMode']: ('KMLMode', 'Redraw'),
            self.IDs['ID_INTMaxMissing']: ('MaxMissing', 'Reload'),
            self.IDs['ID_INTMaxLineWeight']: ('MaxLineWeight', 'Reload'),
            self.IDs['ID_CBUseGPS']: ('UseGPS', 'Reload'),
            self.IDs['ID_CBCacheOnly']: ('CacheOnly', 'Reload'),
            self.IDs['ID_CBAllEntities']: ('AllEntities', 'Redraw'),
            self.IDs['ID_CBMapControl']: ('showLayerControl', 'Redraw'),
            self.IDs['ID_CBMapMini']: ('mapMini', 'Redraw'),
            self.IDs['ID_BTNLoad']: 'Load',
            self.IDs['ID_BTNCreateFiles']: 'CreateFiles',
            self.IDs['ID_BTNCSV']: 'OpenCSV',
            self.IDs['ID_BTNTRACE']: 'Trace',
            self.IDs['ID_BTNSTOP']: 'Stop',
            self.IDs['ID_BTNBROWSER']: 'OpenBrowser',
            self.IDs['ID_CBGridView']: ('GridView', 'Render'),
            self.IDs['ID_TEXTDefaultCountry']: ('defaultCountry', 'Reload', 'defaultCountry'),
            self.IDs['ID_CBSummary']: ('Summary','Redraw')
        }

        self.colors = [
            'BTN_PRESS', 'BTN_DIRECTORY', 'BTN_DONE', 'SELECTED', 'ANCESTOR', 'MAINPERSON', 'INFO_BOX_BACKGROUND', 'OTHERPERSON', 
            'GRID_TEXT', 'GRID_BACK', 'SELECTED_TEXT', 'TITLE_TEXT', 'TITLE_BACK', 'BUSY_BACK'
        ]
        self.COLORs = {name: wx.NewIdRef() for name in self.colors}
        # For color selections see https://docs.wxpython.org/wx.ColourDatabase.html#wx-colourdatabase
        self.COLORid = {
            self.COLORs['BTN_PRESS']: ['TAN'],              # Alternate WHITE or THISTLE
            self.COLORs['BTN_DIRECTORY']: ['WHEAT'],
            self.COLORs['BTN_DONE']: ['WHITE'],
            self.COLORs['SELECTED']: ['NAVY'],              # Does not currently work
            self.COLORs['SELECTED_TEXT']: ['BLACK'],        # Does not currently work
            self.COLORs['ANCESTOR']: ['MEDIUM GOLDENROD'],
            self.COLORs['MAINPERSON']: ['KHAKI'],
            self.COLORs['OTHERPERSON']: ['WHITE'],
            self.COLORs['INFO_BOX_BACKGROUND']: ['GOLDENROD'],
            self.COLORs['GRID_TEXT']: ['BLACK'],            # Alternate DIM GREY
            self.COLORs['GRID_BACK']: ['WHITE'],            # Alternate DARK SLATE GREY
            self.COLORs['TITLE_TEXT']: ['WHITE'],
            self.COLORs['TITLE_BACK']: ['KHAKI'],
            self.COLORs['BUSY_BACK']: ['YELLOW']

        }
        for colorToValue in self.colors:
            self.COLORid[self.COLORs[colorToValue]].append( wx.TheColourDatabase.FindColour(self.COLORid[self.COLORs[colorToValue]][0]))
        
        self.SmallUpArrow = PyEmbeddedImage(
            b"iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABHNCSVQICAgIfAhkiAAAADxJ"
            b"REFUOI1jZGRiZqAEMFGke2gY8P/f3/9kGwDTjM8QnAaga8JlCG3CAJdt2MQxDCAUaOjyjKMp"
            b"cRAYAABS2CPsss3BWQAAAABJRU5ErkJggg=="
        )
        self.SmallDnArrow = PyEmbeddedImage(
            b"iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABHNCSVQICAgIfAhkiAAAAEhJ"
            b"REFUOI1jZGRiZqAEMFGke9QABgYGBgYWdIH///7+J6SJkYmZEacLkCUJacZqAD5DsInTLhDR"
            b"bcPlKrwugGnCFy6Mo3mBAQChDgRlP4RC7wAAAABJRU5ErkJggg=="
        )
        
        self.m = {1: ()}
        # https://xyzservices.readthedocs.io/en/stable/gallery.html
        self.AllMapTypes = ["CartoDB.Voyager", 
            "OpenStreetMap.Mapnik", 
            "OpenStreetMap.HOT", 
            "Esri.WorldTerrain",
            "Esri.NatGeoWorldMap",
            "OpenTopoMap",
            "Esri.WorldStreetMap",
            "CartoDB.VoyagerNoLabels",
            "CartoDB.Positron",
            "CartoDB.PositronOnlyLabels",
            "CartoDB.VoyagerOnlyLabels",
            "CartoDB.DarkMatter"
            ]
        

    def GetColor(self, colorID):
        if colorID in self.colors:
            return self.COLORid[self.COLORs[colorID]][1]
        _log.error(f'Color not defined : {colorID}')
        raise ValueError(f'Color not defined : {colorID} Color to Attributer table error')


#=============================================================
class VisualMapFrame(wx.Frame):
    
    
    def __init__(self,  *args, **kw):


        # ensure the parent's __init__ is called so the wx.frame is created
        #
        super().__init__(*args, **kw)

        self.font_manager = FontManager()
        font = self.font_manager._current if self.font_manager._current else GVFONT[platform.system()]
        self.font_name = font.get("face", GVFONT[platform.system()]['family'])
        self.font_size = font.get("size", GVFONT[platform.system()]['sizePt'])

        self.SetMinSize((800,800))
        self.StatusBar = self.CreateStatusBar()
        self.SetStatusText("This is the statusbar")
        # create a menu bar
        self.makeMenuBar()
        # and a status bar
        
        self.StatusBar.SetFieldsCount(number=2, widths=[-1, 28*self.font_size])
        widthMax = ApproxTextWidth(30, self.font_size)
        self.StatusBar.SetFieldsCount(number=2, widths=[-1, widthMax])
        self.SetStatusText("Visual Mapping ready",0)
        self.myFont = wx.Font(wx.FontInfo(self.font_size).FaceName(self.font_name))
        if not self.myFont:
            _log.warning("Could not set font to %s, using default", self.font_name)
            self.myFont = wx.Font(wx.FontInfo(10).FaceName('Verdana'))
        wx.Frame.SetFont(self, self.myFont)
        self.inTimer = False
        
        # Create and set up the main panel within the frame
        self.visual_map_panel = VisualMapPanel(self)
        self.visual_map_panel.SetupOptions() # Configure panel options

    def start(self):
        self.visual_map_panel.SetupButtonState()
        self.Show()

    def stop(self):
        if self.visual_map_panel:
            self.visual_map_panel.OnCloseWindow()

    def makeMenuBar(self):
        """
        A menu bar is composed of menus, which are composed of menu items.
        This method builds a set of menus and binds handlers to be called
        when the menu item is selected.
        """
        
        # The "\t..." syntax defines an accelerator key that also triggers
        # Make the menu bar and add the two menus to it. The '&' defines
        # that the next letter is the "mnemonic" for the menu item. On the
        # platforms that support it those letters are underlined and can be
        # triggered from the keyboard.
        self.id = VisualGedcomIds()
        self.menuBar = menuBar = wx.MenuBar()
        self.fileMenu = fileMenu =  wx.Menu()
        fileMenu.Append(wx.ID_OPEN,    "&Open...\tCtrl-O", "Select a GEDCOM file")
        fileMenu.Append(wx.ID_SAVEAS,  "Save &as...")
        fileMenu.Append(wx.ID_CLOSE,   "&Close")
        # fileMenu.Append(wx.ID_SAVE,    "&Save")
        fileMenu.AppendSeparator()
        fileMenu.Append(wx.ID_EXIT)
        # and a file history
        self.filehistory = wx.FileHistory()
        self.filehistory.UseMenu(self.fileMenu)

        optionsMenu = wx.Menu()
        optionsMenu.Append(wx.ID_REVERT, "&Reset to Default")
        optionsMenu.Append(wx.ID_SETUP, "&Options Setup")
        
        self.ActionMenu = ActionMenu =  wx.Menu()
        ActionMenu.Append(wx.ID_FIND, '&Find\tCtrl-F', 'Find by name')
        ActionMenu.Append(wx.ID_INFO, "Statistics Sumary")
        ActionMenu.Append(self.id.IDs['ID_BTNBROWSER'],    "Open Result in &Browser")
        ActionMenu.Append(self.id.IDs['ID_BTNCSV'], "Open &CSV")

        # Now a help menu for the about item
        helpMenu = wx.Menu()
        helpMenu.Append(wx.ID_HELP, "Help")
        helpMenu.Append(wx.ID_ABOUT, "About")

        menuBar.Append(self.fileMenu, "&File")
        menuBar.Append(ActionMenu, "&Actions")
        menuBar.Append(optionsMenu, "&Options")
        menuBar.Append(helpMenu, "&Help")

        # Give the menu bar to the frame
        self.SetMenuBar(menuBar)

        # Finally, associate a handler function with the EVT_MENU event for
        # each of the menu items. That means that when that menu item is
        # activated then the associated handler function will be called.
        
        self.Bind(wx.EVT_MENU, self.OnFileOpenDialog, id=wx.ID_OPEN)
        self.Bind(wx.EVT_MENU, self.OnFileResultDialog, id=wx.ID_SAVEAS)
        self.Bind(wx.EVT_MENU, self.OnExit,   id=wx.ID_EXIT)
        self.Bind(wx.EVT_CLOSE, self.OnExit)
        self.Bind(wx.EVT_MENU, self.OnInfo, id=wx.ID_INFO)
        self.Bind(wx.EVT_MENU, self.OnAbout, id=wx.ID_ABOUT)
        self.Bind(wx.EVT_MENU, self.OnAbout, id=wx.ID_HELP)
        self.Bind(wx.EVT_MENU_RANGE, self.OnFileHistory, id=wx.ID_FILE1, id2=wx.ID_FILE9)
        self.Bind(wx.EVT_MENU, self.onOptionsReset, id=wx.ID_REVERT)
        self.Bind(wx.EVT_MENU, self.OnFind, id=wx.ID_FIND)
        self.Bind(wx.EVT_MENU, self.onOptionsSetup, id=wx.ID_SETUP)
        self.Bind(wx.EVT_MENU, self.OnOpenCSV, id = self.id.IDs['ID_BTNCSV'])
        self.Bind(wx.EVT_MENU, self.OnOpenBrowser, id = self.id.IDs['ID_BTNBROWSER'])
        # More BIND below in main
    
        # existing Option items...
        # Add Set Font submenu
        set_font_menu = wx.Menu()
        for fname in self.font_manager.PREDEFINED_FONTS:
            item = wx.MenuItem(set_font_menu, wx.ID_ANY, fname, kind=wx.ITEM_RADIO)
            set_font_menu.Append(item)
            # pre-check current selection
            current_face = self.font_manager._current.get("face") if self.font_manager._current else None
            if current_face == fname:
                item.Check(True)

        # optional: add font size submenu or a Font Size dialog entry
        set_font_sub = wx.MenuItem(optionsMenu, wx.ID_ANY, "Set Font")
        # optionsMenu.AppendSubMenu(set_font_menu, "Set People Grid Font")
        optionsMenu.AppendSubMenu(set_font_menu, "Set Font")
        # bind events
        for mi in set_font_menu.GetMenuItems():
            self.Bind(wx.EVT_MENU, self.on_font_menu_item, mi)

        # Add Set Font Size submenu
        set_font_size_menu = wx.Menu()
        for fsize in self.font_manager.PREDEFINED_FONT_SIZES:
            item = wx.MenuItem(set_font_size_menu, wx.ID_ANY, str(fsize), kind=wx.ITEM_RADIO)
            set_font_size_menu.Append(item)
            # pre-check current selection
            current_size = self.font_manager._current.get("size") if self.font_manager._current else None
            if current_size == fsize:
                item.Check(True)

        set_font_size_sub = wx.MenuItem(optionsMenu, wx.ID_ANY, "Set Font Size")
        optionsMenu.AppendSubMenu(set_font_size_menu, "Set Font Size")
        # bind events
        for mi in set_font_size_menu.GetMenuItems():
            self.Bind(wx.EVT_MENU, self.on_font_size_menu_item, mi)

    def set_font(self, font_name, font_size):
        success = self.font_manager.set_font(font_name, font_size)
        if not success:
            _log.error(f"Failed to set font to {font_name}")
        else:
            self.font_name = font_name
            self.font_size = font_size
            self.myFont = wx.Font(wx.FontInfo(font_size).FaceName(font_name))
            # Apply to VisualMapFrame
            self.font_manager.apply_font_recursive(self, self.myFont)
            # Apply to sub-panel: VisualMapPanel
            self.visual_map_panel.set_font(font_name, font_size)

        self.Layout()
        self.Refresh()

    #  event handler
    def on_font_menu_item(self, event):
        mi = self.GetMenuBar().FindItemById(event.GetId())
        if mi is None:
            return
        face = mi.GetItemLabelText()
        success = self.font_manager.set_font(face)
        if success:
            self.font_name = face
            self.set_font(self.font_name, self.font_size)

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
            self.set_font(self.font_name, self.font_size)

    def OnExit(self, event):
        self.visual_map_panel.myTimer.Stop()
        self.Unbind(wx.EVT_TIMER, self)
        """Close the frame, terminating the application."""
        self.visual_map_panel.gOp.savesettings()
        if event.GetEventType() == wx.EVT_CLOSE.typeId:
            self.Destroy()
        else:
            self.Close(True)


        

    def OnOpenCSV(self, event):
        self.visual_map_panel.OpenCSV()
    def OnOpenBrowser(self, event):
        self.visual_map_panel.OpenBrowser()

    def OnFileOpenDialog(self, evt):
        dDir = os.getcwd()
        if self.visual_map_panel and self.visual_map_panel.gOp:
            infile = self.visual_map_panel.gOp.get('GEDCOMinput')
            if infile != '':
                dDir, filen  = os.path.split(infile)
        dlg = wx.FileDialog(self,
                           defaultDir = dDir,
                           defaultFile= filen,
                           wildcard = "GEDCOM source (*.ged)|*.ged|" \
                                      "All Files|*",
                           style = wx.FD_OPEN | wx.FD_CHANGE_DIR | wx.FD_FILE_MUST_EXIST)
        Proceed = dlg.ShowModal() == wx.ID_OK
        if Proceed:
            path = dlg.GetPath()
            _log.debug("You selected %s", path)
            self.visual_map_panel.setInputFile(path)
            

            # add it to the history
            self.filehistory.AddFileToHistory(path)
            self.filehistory.Save(self.visual_map_panel.fileConfig)

        dlg.Destroy()
        wx.Yield()
        if Proceed:
            self.visual_map_panel.LoadGEDCOM()
    def OnFileResultDialog(self, evt):
        dDir = os.getcwd()
        dFile = "visgedcom.html"
        if self.visual_map_panel and self.visual_map_panel.gOp:
            resultfile = self.visual_map_panel.gOp.get('Result')
            if resultfile != '':
                dDir, dFile= os.path.split(resultfile)
            else:
                resultfile = self.visual_map_panel.gOp.get('GEDCOMinput')
                dDir, dFile  = os.path.split(resultfile)
        dFile = os.path.splitext(dFile)[0]

        dlg = wx.FileDialog(self,
                           defaultDir = dDir,
                           defaultFile= dFile,
                           wildcard = "HTML Output Result (*.html)|*.html|" \
                                    "Map KML (*.kml)|*.kml|" \
                                    "All Files|*",
                           style = wx.FD_SAVE | wx.FD_CHANGE_DIR )

        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            _log.debug("Output selected %s", path)
            filetype = os.path.splitext(path)[1]
            isHTML = not (filetype.lower() in ['.kml'])
            self.visual_map_panel.gOp.setResults(path, isHTML)
            self.visual_map_panel.id.TEXTResult.SetValue(path)
            self.visual_map_panel.id.RBResultOutType.SetSelection(0 if isHTML else 1)
            self.visual_map_panel.SetupButtonState()
        dlg.Destroy()
        wx.Yield()
        

    def Cleanup(self, *args):
        # A little extra cleanup is required for the FileHistory control
        del self.filehistory
        self.menu.Destroy()

    def OnFileHistory(self, evt):
        # get the file based on the menu ID
        fileNum = evt.GetId() - wx.ID_FILE1
        path = self.filehistory.GetHistoryFile(fileNum)
        _log.debug("You selected %s", path)

        # add it back to the history so it will be moved up the list
        self.filehistory.AddFileToHistory(path)
        self.visual_map_panel.setInputFile(path)
        wx.Yield()
        self.visual_map_panel.LoadGEDCOM()

    def OnAbout(self, event):
        if event.GetId() == wx.ID_ABOUT:
            dialog = AboutDialog(None, title=f"About {GUINAME} {VERSION}")
        else:
            dialog = HelpDialog(None, title=f"Help for {GUINAME} {VERSION}")    
        dialog.ShowModal()
        dialog.Destroy()

    def OnInfo(self, event):
        """Display an Staticis Info Dialog"""

        withoutaddr = 0
        msg = ""
        if getattr(self.visual_map_panel.gOp, 'people', None):
            # for xh in panel.gOp.people.keys():
            #    if (panel.gOp.people[xh].bestlocation() == ''): 
            #        withoutaddr += 1
            # msg = f'Total People :\t{len(panel.gOp.people)}\n People without any address {withoutaddr}'
            msg = f'Total People :{len(self.visual_map_panel.gOp.people)}\n'
            if self.visual_map_panel.gOp.timeframe:
                timeline = "-".join(map(str, self.visual_map_panel.gOp.timeframe))
                msg +=  f"\nTimeframe : {timeline}\n"
            if self.visual_map_panel.gOp.selectedpeople > 0:
                msg += f"\nDirect  people {self.visual_map_panel.gOp.selectedpeople} in the heritage line\n"
                
            else:
                msg += "\nSelect main person for heritage line\n"
            
        else:
            msg = "No people loaded yet\n"
        if hasattr(self.visual_map_panel.gOp, 'lookup') and getattr(self.visual_map_panel.gOp.lookup, 'address_book', None):
            stats = self.visual_map_panel.gOp.lookup.address_book.updatestats()
            msg += f'\nTotal cached addresses: {self.visual_map_panel.gOp.lookup.address_book.len()}\n{stats}'

        wx.MessageBox (msg, 'Statistics', wx.OK|wx.ICON_INFORMATION)
    def OnFind(self, event):
        self.visual_map_panel.peopleList.list.OnFind(event)

    def onOptionsReset(self, event):
        self.visual_map_panel.gOp.defaults()
        self.visual_map_panel.SetupOptions()
        wx.MessageBox("Rest options to defaults",
                      "Reset Options",
                      wx.OK|wx.ICON_INFORMATION)
        
    def onOptionsSetup(self, event):
        dialog = ConfigDialog(None, title='Configuration Options', gOp=self.visual_map_panel.gOp)
        self.config_dialog = dialog
        
#=============================================================
class PeopleListCtrl(wx.ListCtrl, listmix.ListCtrlAutoWidthMixin, listmix.ColumnSorterMixin):
    def __init__(self, parent, ID, pos=wx.DefaultPosition,
                 size=wx.DefaultSize, style=0, name="PeopleList", *args, **kw):
        super().__init__(*args, **kw)
        wx.ListCtrl.__init__(self, parent, ID, pos, size, style)
        listmix.ListCtrlAutoWidthMixin.__init__(self)

        self.id = VisualGedcomIds()
        self.active = False
        self.il = wx.ImageList(16, 16)
        self.sm_up = self.il.Add(self.id.SmallUpArrow.GetBitmap())
        self.sm_dn = self.il.Add(self.id.SmallDnArrow.GetBitmap())
        self.GridOnlyFamily = False
        self._LastGridOnlyFamily = self.GridOnlyFamily
        self.LastSearch = ""
        self.gOp = None
        self.visual_map_panel = self.GetParent().GetParent()

        self.SetImageList(self.il, wx.IMAGE_LIST_SMALL)
        self.SetTextColour(self.id.GetColor('GRID_TEXT'))
        self.SetBackgroundColour(self.id.GetColor('GRID_BACK'))

        # for normal, simple columns, you can add them like this:
        self.InsertColumn(0, "Name")
        self.InsertColumn(1, "Year", wx.LIST_FORMAT_RIGHT)
        self.InsertColumn(2, "ID")
        self.InsertColumn(3, "Geocode")
        self.InsertColumn(4, "Address")
        self.SetImageList(self.il, wx.IMAGE_LIST_SMALL)
        # see wx/lib/mixins/listctrl.py
        # Adjust Colums when adding colum
        # Now that the list exists we can init the other base class,
        listmix.ColumnSorterMixin.__init__(self, 5)

        self.itemDataMap = {}
        self.itemIndexMap = []
        self.patterns = [
            re.compile(r'(\d{1,6}) (B\.?C\.?)'),  # Matches "96 B.C." or "115 BC" or "109 BCE"
            re.compile(r'(\d{1,4})')              # Matches "1564", "1674", "922"
        ]

        parent.Bind(wx.EVT_FIND, self.OnFind, self)
        self.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self.OnItemRightClick, self)
        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnItemActivated, self)
        _log.debug("Register for SORTER")
        # parent.Bind(wx.EVT_LIST_COL_CLICK, self.OnColClick, self)
        # parent.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnItemSelected, self.list)
        # parent.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.OnItemDeselected, self.list)
        self.Bind(wx.EVT_LIST_COL_RIGHT_CLICK, self.OnColRightClick, self)
        # parent.Bind(wx.EVT_LIST_COL_BEGIN_DRAG, self.OnColBeginDrag, self.list)
        # parent.Bind(wx.EVT_LIST_COL_DRAGGING, self.OnColDragging, self.list)
        # parent.Bind(wx.EVT_LIST_COL_END_DRAG, self.OnColEndDrag, self.list)
        # parent.Bind(wx.EVT_LIST_BEGIN_LABEL_EDIT, self.OnBeginEdit, self.list)
        # parent.Bind(wx.EVT_LIST_END_LABEL_EDIT, self.OnEndEdit, self.list)
        

    def SetGOp(self, gOp):
        self.gOp = gOp

    def PopulateList(self, people, mainperson, loading):
        if self.active:
            return
        
        self.active = True

        if self.gOp:
            wasrunning = self.gOp.running
            self.gOp.running = True
            self.GridOnlyFamily = self.gOp.get('GridView')
        
        if (loading):
            # BUG this does not work
            self.RemoveSortIndicator()
            self.popdata = {}
                            
        if loading or (self._LastGridOnlyFamily != self.GridOnlyFamily):
            self.DeleteAllItems()
            self.itemDataMap = {}
            self.itemIndexMap = []
            loading = True
            self._LastGridOnlyFamily = self.GridOnlyFamily
            # TODO BUG neithe of these clear the sort indicator
            
        selectperson = 0
        if (not people):
            self.active = False
            return
        
        if (loading):
            index = 0
            for h in people:
                if hasattr(people[h], 'name'):
                    d, y = people[h].refyear()
                    (location, where) = people[h].bestlocation()
                        
                    self.popdata[index] = (people[h].name, d, people[h].xref_id, location , where, self.ParseDate(y))
                    index += 1
        if self.gOp:
            items = self.popdata.items()
            self.gOp.selectedpeople = 0
            if not wasrunning:
                self.gOp.step("Gridload", resetCounter=False, target=len(items))
            self.itemDataMap = {data[0] : data for data in items} 
            index = -1
            for key, data in items:
                self.gOp.counter = key
                if key % 2048 == 0:
                    wx.Yield()
                
                if self.GridOnlyFamily and self.gOp.Referenced:
                    DisplayItem = self.gOp.Referenced.exists(data[2])
                else:
                    DisplayItem = True
                if DisplayItem:
                    if (loading):
                        index = self.InsertItem(self.GetItemCount(), data[0], -1) # Name
                        self.SetItem(index, 1, data[1]) # Year
                        self.SetItem(index, 2, data[2]) # ID
                        self.SetItem(index, 3, data[3]) # GeoCode
                        self.SetItem(index, 4, data[4]) # Location
                        # self.itemDataMap[data] = data
                        # self.itemIndexMap.append(index)
                        self.SetItemData(index, key)
                        if mainperson == data[2]:
                            selectperson = index                    
                    else:
                        index += 1
                        if mainperson == self.GetItem(index,2):
                            selectperson = index
                    
                    if self.gOp.Referenced:
                        if self.gOp.Referenced.exists(data[2]):
                            self.gOp.selectedpeople = self.gOp.selectedpeople + 1
                            if mainperson == data[2]:
                                self.SetItemBackgroundColour(index, self.id.GetColor('MAINPERSON'))
                            else:
                                issues = CheckAge(people, data[2])
                                if issues:
                                    self.SetItemBackgroundColour(index, wx.YELLOW)
                                else:
                                    self.SetItemBackgroundColour(index, self.id.GetColor('ANCESTOR'))
                        else:
                            self.SetItemBackgroundColour(index, self.id.GetColor('OTHERPERSON'))
            self.gOp.counter = 0
            self.gOp.state = ""

        self.SetColumnWidth(1, 112)
        self.SetColumnWidth(2, 85)
        self.SetColumnWidth(3, 220)
        self.SetColumnWidth(4, 375)
        self.SetColumnWidth(0, wx.LIST_AUTOSIZE_USEHEADER)
        # Sometimes the Name is too long
        if self.GetColumnWidth(0) > 300:
            self.SetColumnWidth(0, 300)

        # NOTE: self.list can be empty (the global value, m, is empty and passed as people).
        if 0 <= selectperson < self.GetItemCount():
            self.SetItemState(selectperson, wx.LIST_STATE_SELECTED, wx.LIST_STATE_SELECTED)
        
        if mainperson and selectperson > 0 and loading:
            self.EnsureVisible(selectperson)
        wx.Yield()
        if self.gOp and self.gOp.running:
            # Hack race condition
            if not wasrunning:
                self.visual_map_panel.StopTimer()
            self.gOp.running = wasrunning
            
        self.active = False

   
    # Used by the ColumnSorterMixin, see wx/lib/mixins/listctrl.py
    def GetListCtrl(self):
        # print("GetListCtrl {} {}".format(self.GetSortState(), self.itemDataMap[1]))
        return self.list


    # Specifically designed to deal with the 2nd return value from refyear
    def ParseDate(self, datestring):
        if datestring == None:
            return 0
        for pattern in self.patterns:
            match = pattern.search(str(datestring))
            if match:
                if pattern ==self.patterns[0]:
                    # BC year found, convert to negative
                    return -int(match.group(1))
                else:
                    # Year with slash found, choose the first year
                    return int(match.group(1))
        
        # If no valid year found, return 0
        return 0
        
    def GetColumnSorter(self):
        (col, ascending) = self.GetSortState()
        idsort = False
        if col == 2:
            checkid = self.popdata[1][2]
            idsort = checkid[0:2] == "@I" and checkid[-1] == "@"
        # _log.debug(f"Sorter called col:{col} ascending:{ascending} first time of popdata is {self.popdata[0][0]}")

        def cmp_func(item1, item2):
            if col == 1:  # Year column
                year1 = self.popdata[item1][5] 
                year2 = self.popdata[item2][5] 
                return (year1 - year2) if ascending else (year2 - year1)
            elif col == 2 and idsort:
                data1 = int(self.popdata[item1][col][2:-1])
                data2 = int(self.popdata[item2][col][2:-1])
            else:
                data1 = self.popdata[item1][col]
                data2 = self.popdata[item2][col]
            return (data1 > data2) - (data1 < data2) if ascending else (data2 > data1) - (data2 < data1)

        return cmp_func

    # Used by the ColumnSorterMixin, see wx/lib/mixins/listctrl.py
    def GetSortImages(self):
        return (self.sm_dn, self.sm_up)
        # Used by the ColumnSorterMixin, see wx/lib/mixins/listctrl.py
    def GetListCtrl(self):
        # _log.debug(f"GetListCtrl {self.GetSortState()} {self.itemDataMap[1]}")
        return self

    def OnFind(self, event):
        find_dialog = FindDialog(None, "Find", LastSearch=self.LastSearch)
        if find_dialog.ShowModal() == wx.ID_OK:
            self.LastSearch = find_dialog.GetSearchString()
            if self.GetItemCount() > 1:
                findperson = self.LastSearch.lower() 
                for checknames in range(self.GetFirstSelected()+1,self.GetItemCount()):
                    if findperson in self.GetItemText(checknames, 0).lower():
                        self.SetItemState(checknames, wx.LIST_STATE_SELECTED, wx.LIST_STATE_SELECTED)
                        self.EnsureVisible(checknames)
                        return
            self.gOp.BackgroundProcess.SayInfoMessage(f"* Could not find '{self.LastSearch}' in the names", False)
  
    def OnItemRightClick(self, event):
        self.currentItem = event.Index
        _log.debug("%s, %s, %s, %s", 
                           self.currentItem,
                            self.GetItemText(self.currentItem),
                            self.GetItemText(self.currentItem, 1),
                            self.GetItemText(self.currentItem, 2))
        event.Skip()
        if self.gOp.BackgroundProcess.people:
            itm = self.GetItemText(self.currentItem, 2)
            if itm in self.gOp.BackgroundProcess.people:
                dialog = PersonDialog(None, self.gOp.BackgroundProcess.people[itm], self.visual_map_panel)
                dialog.Bind(wx.EVT_CLOSE, lambda evt: dialog.Destroy())
                dialog.Bind(wx.EVT_BUTTON, lambda evt: dialog.Destroy())
                dialog.Show(True)
                
                #dialog.Destroy()


    def OnItemActivated(self, event):
        self.currentItem = event.Index
        _log.debug("%s TopItem: %s", self.GetItemText(self.currentItem), self.GetTopItem())
        self.ShowSelectedLinage(self.GetItemText(self.currentItem, 2))
                
    def ShowSelectedLinage(self, personid: str):
        if self.gOp:
            self.gOp.setMain(personid)
            if self.gOp.BackgroundProcess.updategridmain:
                _log.debug("Linage for: %s", personid)
                self.gOp.BackgroundProcess.updategridmain = False
                doTrace(self.gOp)
                self.gOp.newload = False
                self.PopulateList(self.gOp.people, self.gOp.get('Main'), False)
                self.gOp.BackgroundProcess.SayInfoMessage(f"Using '{personid}' as starting person with {len(self.gOp.Referenced)} direct ancestors", False)
                self.gOp.BackgroundProcess.updategridmain = True
                self.visual_map_panel.SetupButtonState()


    def OnColClick(self, event):
        item = self.GetColumn(event.GetColumn())
        _log.debug("%s %s", event.GetColumn(), (item.GetText(), item.GetAlign(), item.GetWidth(), item.GetImage()))
        if self.HasColumnOrderSupport():
            _log.debug("column order: %s", self.GetColumnOrder(event.GetColumn()))

        # event.Skip()
    def OnColRightClick(self, event):
        item = self.GetColumn(event.GetColumn())
        _log.debug("%s %s", event.GetColumn(), (item.GetText(), item.GetAlign(), item.GetWidth(), item.GetImage()))
        if self.HasColumnOrderSupport():
            _log.debug("column order: %s", self.GetColumnOrder(event.GetColumn()))


    #  The following Events types are not needed

    # def OnItemSelected(self, event):
    #     item = event.GetIndex()
    #     self.list.SetItemBackgroundColour(item, self.id.GetColor('SELECTED'))  
    #     self.list.SetItemTextColour(item, self.id.GetColor('SELECTED_TEXT'))  
    #     event.Skip()

    # def OnItemDeselected(self, event):
    #     item = event.GetIndex()
    #     self.list.SetItemBackgroundColour(item, wx.NullColour)             # Default background
    #     self.list.SetItemTextColour(item, wx.NullColour)                   # Default text color

    # def OnGetItemsChecked(self, event):

    #     itemcount = self.list.GetItemCount()
    #     itemschecked = [i for i in range(itemcount) if self.list.IsItemChecked(item=i)]
    #     _log.debug("%s ",  itemschecked)



        
class PeopleListCtrlPanel(wx.Panel, listmix.ColumnSorterMixin):
    def __init__(self, parent, people,  *args, **kw):
        """    Initializes the PeopleListCtrlPanel.

    Args:
        parent: The parent window.
        people: The list of people.
        *args: Variable length argument list.
        **kw: Arbitrary keyword arguments.

    Returns:
        None

    Raises:
        None
        """
        super().__init__(*args, **kw)
        wx.Panel.__init__(self, parent, -1, style=wx.WANTS_CHARS, name="PeoplePanel")
        # TODO This box defination still have a scroll overlap problem
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.messagelog = "*  Select a file, Load it and Create Files or change Result Type, Open Geo Table to edit addresses  *"
        self.InfoBox = []
        for i in range(InfoBoxLines):
            self.InfoBox.append(wx.StaticText(parent, -1, ' '))
            sizer.Add(self.InfoBox[i], 0, wx.LEFT,5)
        tID = wx.NewIdRef()
        self.visual_map_panel = self.GetParent()
        self.list = PeopleListCtrl(parent, tID,
                        style=wx.LC_REPORT | wx.BORDER_SUNKEN | wx.LC_SINGLE_SEL,
                        size=wx.Size(600,600))
        sizer.Add(self.list, -1, wx.EXPAND)

        self.list.PopulateList(people, None, True)

        self.currentItem = 0
        parent.SetSizer(sizer)
        
    def setGOp(self, gOp):
        self.gOp = gOp
        if self.list:
            self.list.SetGOp(gOp)


class VisualMapPanel(wx.Panel):
    """
    A Frame that says Visual Setup
    """

    def __init__(self, *args, **kw):
        # ensure the parent's __init__ is called so the wx.frame is created
        #
        super().__init__(*args, **kw)

        self.font_manager = FontManager()
        font = self.font_manager._current if self.font_manager._current else GVFONT[platform.system()]
        self.font_name = font.get("face", GVFONT[platform.system()]['family'])
        self.font_size = font.get("size", GVFONT[platform.system()]['sizePt'])
        self.myFont = wx.Font(wx.FontInfo(self.font_size).FaceName(self.font_name))

        self.SetMinSize((800,800))
        self.frame = self.TopLevelParent
        self.gOp : gvOptions = None

        self.id = {}
        
        self.fileConfig = None
        self.busystate = False
        self.busycounthack = 0
        self.inTimer = False
        self.SetAutoLayout(True)
        self.id = VisualGedcomIds()
        
        # create a panel in the frame
        self.panelA = wx.Panel(self, -1, size=(760,420),style=wx.SIMPLE_BORDER  )
        self.panelB = wx.Panel(self, -1, size=(300,420),style=wx.SIMPLE_BORDER  )
        
        # https://docs.wxpython.org/wx.ColourDatabase.html#wx-colourdatabase
        self.panelA.SetBackgroundColour(self.id.GetColor('INFO_BOX_BACKGROUND'))
        self.panelB.SetBackgroundColour(wx.WHITE)

        # Data Grid side
        lcA = wx.LayoutConstraints()
        lcA.top.SameAs( self, wx.Top, 5)
        lcA.left.SameAs( self, wx.Left, 5)
        lcA.bottom.SameAs( self, wx.Bottom, 5)
        lcA.right.LeftOf( self.panelB, 5)
        self.panelA.SetConstraints(lcA)

        # TODO make the Controls side fixed in width and resize the Data Grid side
        # Controls Side        
        lc = wx.LayoutConstraints()
        lc.top.SameAs( self, wx.Top, 5)
        lc.right.SameAs( self, wx.Right, 5)
        lc.bottom.SameAs( self, wx.Bottom, 5)
        lc.left.PercentOf( self, wx.Right, 60)
        self.panelB.SetConstraints(lc)
        

        # Add Data Grid on Left panel
        self.peopleList = PeopleListCtrlPanel(self.panelA, self.id.m)
        
        # Add all the labels, button and radiobox to Right Panel
        self.LayoutOptions(self.panelB)

        self.Layout()
        self.lastruninstance = 0.0
        self.remaintime = 0

    def set_font(self, font_name, font_size):
        self.font_name = font_name
        self.font_size = font_size
        self.myFont = wx.Font(wx.FontInfo(self.font_size).FaceName(self.font_name))

        self.font_manager.apply_font_recursive(self, self.myFont)

        self.Layout()
        self.Refresh()

    def LayoutOptions(self, panel):
        """ Layout the panels in the proper nested manner """
        # Top of the Panel
        box = wx.BoxSizer(wx.VERTICAL)
        titleFont = wx.Font(wx.FontInfo(self.font_size).FaceName(self.font_name).Bold())
        # TODO Check for Arial and change it
        if not titleFont:
            _log.warning("Could not load font %s, using ", self.font_name)
            titleFont  = wx.Font(wx.FontInfo(GVFONT[platform.system()]['sizePt']).FaceName(GVFONT[platform.system()]['family']).Bold())
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
        
        self.id.busyIndicator = wx.ActivityIndicator(panel)

        self.id.busyIndicator.SetBackgroundColour(self.id.GetColor('BUSY_BACK'))
        self.id.RBResultOutType =  wx.RadioBox(panel, self.id.IDs['ID_RBResultsType'], "Result Type", 
                                           choices = ['HTML', 'KML', 'KML2', 'SUM'] , majorDimension= 5)

        box.AddMany([  self.id.CBUseGPS,
                       self.id.CBCacheOnly,
                       defCounttryBox,
                       self.id.CBAllEntities])
        """
          HTML select controls in a Box
        """
        hbox = wx.StaticBox( panel, -1, "HTML Options", size=(300,-1))
        hTopBorder, hOtherBorder = hbox.GetBordersForSizer()
        hsizer = wx.BoxSizer(wx.VERTICAL)
        hsizer.AddSpacer(hTopBorder)
        hboxIn = wx.BoxSizer(wx.VERTICAL)
        mapchoices =  sorted(self.id.AllMapTypes)
        mapboxsizer = wx.BoxSizer(wx.HORIZONTAL)
        mapStyleLabel = wx.StaticText(hbox, -1, " Map Style")
        self.id.CBMarksOn = wx.CheckBox(hbox, self.id.IDs['ID_CBMarksOn'], "Markers",name='MarksOn')

        self.id.CBBornMark = wx.CheckBox(hbox, self.id.IDs['ID_CBBornMark'], "Marker for when Born")
        self.id.CBDieMark = wx.CheckBox(hbox, self.id.IDs['ID_CBDieMark'], "Marker for when Died")
        self.id.CBHomeMarker = wx.CheckBox(hbox, self.id.IDs['ID_CBHomeMarker'], "Marker point or homes")
        self.id.CBMarkStarOn = wx.CheckBox(hbox, self.id.IDs['ID_CBMarkStarOn'], "Marker starter with Star")
        self.id.CBMapTimeLine = wx.CheckBox(hbox, self.id.IDs['ID_CBMapTimeLine'], "Add Timeline")

        self.id.LISTMapType = wx.Choice(hbox, self.id.IDs['ID_LISTMapStyle'], name="MapStyle", choices=mapchoices)
        self.id.CBMapControl = wx.CheckBox(hbox, self.id.IDs['ID_CBMapControl'], "Open Map Controls",name='MapControl') 
        self.id.CBMapMini = wx.CheckBox(hbox, self.id.IDs['ID_CBMapMini'], "Add Mini Map",name='MapMini') 
        
        
        
        self.id.CBHeatMap = wx.CheckBox(hbox, self.id.IDs['ID_CBHeatMap'], "Heatmap", style = wx.NO_BORDER)
        
        self.id.CBUseAntPath = wx.CheckBox(hbox, self.id.IDs['ID_CBUseAntPath'], "Ant paths")
        
        TimeStepVal = 5
        self.id.LISTHeatMapTimeStep = wx.Slider(hbox, self.id.IDs['ID_LISTHeatMapTimeStep'], TimeStepVal,1, 100, size=(250, 45),
                style=wx.SL_HORIZONTAL | wx.SL_AUTOTICKS | wx.SL_LABELS )
        self.id.LISTHeatMapTimeStep.SetTickFreq(5)
        self.id.RBGroupBy  = wx.RadioBox(hbox, self.id.IDs['ID_RBGroupBy'], "Group by:", 
                                       choices = ['None', 'Last Name', 'Last Name (Soundex)','Person'], majorDimension= 2)
        mapboxsizer.Add(self.id.LISTMapType)
        mapboxsizer.Add( mapStyleLabel)
        
        
        hboxIn.AddMany([
            self.id.CBMarksOn,
            self.id.CBBornMark,
            self.id.CBDieMark,
            self.id.CBHomeMarker,
            self.id.CBMarkStarOn,
            self.id.CBMapTimeLine,        
            self.id.RBGroupBy, 
            mapboxsizer,
            self.id.CBMapControl,
            self.id.CBMapMini,
            self.id.CBUseAntPath,
            self.id.CBHeatMap,
            (0,5),
            self.id.LISTHeatMapTimeStep,
            (0,5)
            ])
        hsizer.Add( hboxIn, wx.LEFT, hOtherBorder+5)
        
        hbox.SetSizer(hsizer)
        self.optionHbox = hbox
        #
        # KML select controls in a Box
        #
        kbox = wx.StaticBox( panel, -1, "KML Options", size=(300,-1))
        kTopBorder, kOtherBorder = kbox.GetBordersForSizer()
        ksizer = wx.BoxSizer(wx.VERTICAL)
        ksizer.AddSpacer(kTopBorder)
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

        ksizer.Add( kboxIn, wx.LEFT, kOtherBorder+5)
        kbox.SetSizer(ksizer)
        self.optionKbox = kbox
            #
        # KML select controls in a Box
        #
        k2box = wx.StaticBox( panel, -1, "KML2 Options", size=(300,-1))
        k2TopBorder, k2OtherBorder = k2box.GetBordersForSizer()
        k2sizer = wx.BoxSizer(wx.VERTICAL)
        k2sizer.AddSpacer(k2TopBorder)
        k2boxIn = wx.BoxSizer(wx.VERTICAL)
        
        k2sizer.Add( k2boxIn, wx.LEFT, k2OtherBorder+5)
        k2box.SetSizer(k2sizer)
        self.optionK2box = k2box
        #
        # Summary select controls in a Box
        #
        sbox = wx.StaticBox( panel, -1, "Summary Options", size=(300,-1))
        sTopBorder, sOtherBorder = sbox.GetBordersForSizer()
        ssizer = wx.BoxSizer(wx.VERTICAL)
        ssizer.AddSpacer(sTopBorder)
        sboxIn = wx.BoxSizer(wx.VERTICAL)
        
        self.id.CBSummary = [wx.CheckBox(sbox, self.id.IDs['ID_CBSummary'], label="Open files after created", name="Open"),
                             wx.CheckBox(sbox, self.id.IDs['ID_CBSummary'], label="Places", name="Places"),
                             wx.CheckBox(sbox, self.id.IDs['ID_CBSummary'], label="People", name="People"),
                             wx.CheckBox(sbox, self.id.IDs['ID_CBSummary'], label="Countries", name="Countries"),
                             wx.CheckBox(sbox, self.id.IDs['ID_CBSummary'], label="Countries Grid", name="CountriesGrid"),
                             wx.CheckBox(sbox, self.id.IDs['ID_CBSummary'], label="Geocode", name="Geocode"),
                             wx.CheckBox(sbox, self.id.IDs['ID_CBSummary'], label="Alternate Places", name="AltPlaces")]
        
        sboxIn.AddMany(self.id.CBSummary)
        ssizer.Add( sboxIn, wx.LEFT, sOtherBorder+5)
        sbox.SetSizer(ssizer)
        self.optionSbox = sbox


        #
        # Grid View Options
        #
        
        
        gbox = wx.StaticBox( panel, -1, "Grid View Options",size=(300,40))
        gTopBorder, gOtherBorder = gbox.GetBordersForSizer()
        gsizer = wx.BoxSizer(wx.VERTICAL)
        gsizer.AddSpacer(gTopBorder)
        gboxIn = wx.BoxSizer(wx.VERTICAL)
        self.id.CBGridView = wx.CheckBox(gbox, self.id.IDs['ID_CBGridView'],  'View Only Direct Ancestors')
        gboxIn.AddMany( [self.id.CBGridView])
        gsizer.Add( gboxIn, wx.LEFT, gOtherBorder+5)
        
        gbox.SetSizer(gsizer)
        self.optionGbox = gbox
        
        box.Add(gbox, 1, wx.LEFT, 5)
        box.AddMany([self.id.RBResultOutType])
        box.Add(hbox, 1, wx.LEFT, 5)
        box.Add(kbox, 1, wx.LEFT, 5)
        box.Add(sbox, 1, wx.LEFT, 5)
        box.Add(k2box, 1, wx.LEFT, 5)

        self._needLayoutSet = True
        

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
        self.myTimer.Start(250)


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

    def OnMyTimer(self, evt):
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
                runningtime = datetime.now().timestamp() - self.gOp.runningSince
                runtime = f"Running {time.strftime('%H:%M:%S', time.gmtime(runningtime))}"
                if self.gOp.countertarget > 0 and self.gOp.counter > 0 and self.gOp.counter != self.gOp.countertarget:
                    if runningtime-1.5 > self.lastruninstance: 
                        remaintimeInstant = runningtime * (self.gOp.countertarget/ self.gOp.counter)- runningtime
                        # Smoothed runtime average over last 10 seconds
                        self.gOp.runavg.append(remaintimeInstant)
                        if len(self.gOp.runavg) > 20:
                            self.gOp.runavg.pop(0)
                        remaintime = sum(self.gOp.runavg)/len(self.gOp.runavg)
                        self.remaintime = runningtime * (self.gOp.countertarget/ self.gOp.counter)- runningtime
                        self.lastruninstance = runningtime
                    runtime = f"{runtime} ({time.strftime('%H:%M:%S', time.gmtime(self.remaintime))})"
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

    def OnCreateFiles(self, evt):
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
            nlines = (newinfo+'\n'+self.peopleList.messagelog).split("\n")
            for i in range(InfoBoxLines):
                if i >= len(nlines):
                    self.peopleList.InfoBox[i].SetLabelMarkup('')
                else:
                    self.peopleList.InfoBox[i].SetLabelMarkup(nlines[i])  
            self.peopleList.messagelog = "\n".join(nlines[:InfoBoxLines])

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
        
        self.optionKbox.SetPosition(wx.Point(self.optionKbox.GetPosition().x, self.optionHbox.GetPosition().y))
        if self.optionKbox.GetSize() != self.optionKbox.GetBestSize():
            self.optionKbox.SetSize(self.optionKbox.GetBestSize())
        self.optionK2box.SetPosition(wx.Point(self.optionK2box.GetPosition().x, self.optionHbox.GetPosition().y))
        if self.optionK2box.GetSize() != self.optionK2box.GetBestSize():
            self.optionK2box.SetSize(self.optionK2box.GetBestSize())
        self.optionSbox.SetPosition(wx.Point(self.optionSbox.GetPosition().x, self.optionHbox.GetPosition().y))
        if self.optionSbox.GetSize() != self.optionSbox.GetBestSize():
            self.optionSbox.SetSize(self.optionSbox.GetBestSize())
        self.optionHbox.SetPosition(wx.Point(self.optionKbox.GetPosition().x, self.optionHbox.GetPosition().y))
        if self.optionHbox.GetSize() != self.optionHbox.GetBestSize():
            self.optionHbox.SetSize(self.optionHbox.GetBestSize())
        # Enable/disable controls based on result type (HTML vs KML vs Summary Mode )
        if not self._needLayoutSet:
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
            if self._needLayoutSet:
                self._needLayoutSet = False
            else:
                self.optionHbox.Show()
            
        elif ResultTypeSelect is ResultsType.SUM:
            if self._needLayoutSet:
                self._needLayoutSet = False
            else:
                self.optionSbox.Show()

        elif ResultTypeSelect is ResultsType.KML:
            # In KML mode, disable HTML controls and enable KML controls
            for ctrl in html_controls:
                ctrl.Disable()
            for ctrl in kml_controls:
                ctrl.Enable()
            # This timeline just works differently in KML mode vs embedded code for HTML
            self.id.CBMapTimeLine.Enable()
            if self._needLayoutSet:
                self._needLayoutSet = False
            else:
                self.optionKbox.Show()
        elif ResultTypeSelect is ResultsType.KML2:
            if self._needLayoutSet:
                self._needLayoutSet = False
            else:
                self.optionK2box.Show()

       # Enable/disable trace button based on referenced data availability
        self.id.BTNTRACE.Enable(bool(self.gOp.Referenced and self.gOp.Result and ResultTypeSelect))

    def SetupOptions(self):

        if not self.fileConfig:
            self.fileConfig = wx.Config("gedcomVisualGUI")
        
        if not self.gOp:
            self.gOp = gvOptions()
            self.gOp.panel = self
            self.gOp.BackgroundProcess = self.background_process
            self.gOp.UpdateBackgroundEvent = UpdateBackgroundEvent
            self.peopleList.setGOp(self.gOp)

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
    def OnCloseWindow(self, evt):
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



