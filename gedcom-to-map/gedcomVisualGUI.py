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
import re
import subprocess
import sys
import time
from datetime import datetime
import webbrowser
from warnings import catch_warnings

import wx
# pylint: disable=no-member
import wx.lib.mixins.listctrl as listmix
import wx.lib.sized_controls as sc
import wx.lib.mixins.inspection as wit
import wx.lib.newevent
import wx.html
import wx.grid
import xyzservices.providers as xyz 


from const import GUINAME, GVFONT, KMLMAPSURL, LOG_CONFIG, NAME, VERSION, BackgroundProcess, panel
from gedcomoptions import gvOptions, AllPlaceType
from gedcomvisual import doTrace
from gedcomDialogs import *


_log = logging.getLogger(__name__.lower())


InfoBoxLines = 8
# This creates a new Event class and a EVT binder function

(UpdateBackgroundEvent, EVT_UPDATE_STATE) = wx.lib.newevent.NewEvent()
from wx.lib.embeddedimage import PyEmbeddedImage


class VisualGedcomIds():
    def __init__(self):
        
        self.ids = [
            'ID_CBMarksOn', 'ID_CBHeatMap', 'ID_CBBornMark', 'ID_CBDieMark', 'ID_LISTMapStyle',
            'ID_CBMarkStarOn', 'ID_RBGroupBy', 'ID_CBUseAntPath', 'ID_CBHeatMapTimeLine',
            'ID_CBHomeMarker', 'ID_LISTHeatMapTimeStep', 'ID_TEXTGEDCOMinput', 'ID_TEXTResult',
            'ID_RBResultHTML', 'ID_TEXTMain', 'ID_TEXTName', 'ID_INTMaxMissing', 'ID_INTMaxLineWeight',
            'ID_CBUseGPS', 'ID_CBCacheOnly', 'ID_CBAllEntities', 'ID_LISTPlaceType', 'ID_CBMapControl',
            'ID_CBMapMini', 'ID_BTNLoad', 'ID_BTNUpdate', 'ID_BTNCSV', 'ID_BTNTRACE', 'ID_BTNSTOP', 'ID_BTNBROWSER',
            'ID_CBGridView'
        ]
        self.IDs = {name: wx.NewIdRef() for name in self.ids}
        # ID = Attribute (in gOptions), Action impact
        self.IDtoAttr = {
            self.IDs['ID_CBMarksOn']: ('MarksOn', 'Redraw'),
            self.IDs['ID_CBHeatMap']: ('HeatMap', ''),
            self.IDs['ID_CBBornMark']: ('BornMark', 'Redraw'),
            self.IDs['ID_CBDieMark']: ('DieMark', 'Redraw'),
            self.IDs['ID_LISTMapStyle']: ('MapStyle', 'Redraw'),
            self.IDs['ID_CBMarkStarOn']: ('MarkStarOn', 'Redraw'),
            self.IDs['ID_RBGroupBy']: ('GroupBy', 'Redraw'),
            self.IDs['ID_CBUseAntPath']: ('UseAntPath', 'Redraw'),
            self.IDs['ID_CBHeatMapTimeLine']: ('HeatMapTimeLine', 'Redraw'),
            self.IDs['ID_CBHomeMarker']: ('HomeMarker', 'Redraw'),
            self.IDs['ID_LISTHeatMapTimeStep']: ('HeatMapTimeLine', 'Redraw'),
            self.IDs['ID_TEXTGEDCOMinput']: ('GEDCOMinput', 'Reload'),
            self.IDs['ID_TEXTResult']: ('Result', 'Redraw'),
            self.IDs['ID_RBResultHTML']: ('ResultHTML', 'Redraw'),
            self.IDs['ID_TEXTMain']: ('Main', 'Reload'),
            self.IDs['ID_TEXTName']: ('Name', ''),
            self.IDs['ID_INTMaxMissing']: ('MaxMissing', 'Reload'),
            self.IDs['ID_INTMaxLineWeight']: ('MaxLineWeight', 'Reload'),
            self.IDs['ID_CBUseGPS']: ('UseGPS', 'Reload'),
            self.IDs['ID_CBCacheOnly']: ('CacheOnly', 'Reload'),
            self.IDs['ID_CBAllEntities']: ('AllEntities', 'Redraw'),
            self.IDs['ID_LISTPlaceType']: ('PlaceType', 'Redraw'),
            self.IDs['ID_CBMapControl']: ('showLayerControl', 'Redraw'),
            self.IDs['ID_CBMapMini']: ('mapMini', 'Redraw'),
            self.IDs['ID_BTNLoad']: 'Load',
            self.IDs['ID_BTNUpdate']: 'Update',
            self.IDs['ID_BTNCSV']: 'OpenCSV',
            self.IDs['ID_BTNTRACE']: 'Trace',
            self.IDs['ID_BTNSTOP']: 'Stop',
            self.IDs['ID_BTNBROWSER']: 'OpenBrowser',
            self.IDs['ID_CBGridView']: ('GridView', 'Render')
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
            self.COLORs['BUSY_BACK']: ['KHAKI']

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
        super(VisualMapFrame, self).__init__(*args, **kw)

        self.SetMinSize((800,800))
        self.StatusBar = self.CreateStatusBar()
        self.SetStatusText("This is the statusbar")
        # create a menu bar
        self.makeMenuBar()
        # and a status bar
        
        self.StatusBar.SetFieldsCount(number=2, widths=[-1, 12*GVFONT[1]])
        self.SetStatusText("Visual Mapping ready",0)
        self.myFont = wx.Font(wx.FontInfo(GVFONT[1]).FaceName(GVFONT[0]))
        # TODO Check for Arial and change it
        if not self.myFont:
            self.myFont = wx.Font(wx.FontInfo(10).FaceName('Verdana'))
        wx.Frame.SetFont(self, self.myFont)
        self.inTimer = False


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
        self.Bind(wx.EVT_MENU_RANGE, self.OnFileHistory, id=wx.ID_FILE1, id2=wx.ID_FILE9)
        self.Bind(wx.EVT_MENU, self.onOptionsReset, id=wx.ID_REVERT)
        self.Bind(wx.EVT_MENU, self.OnFind, id=wx.ID_FIND)
        self.Bind(wx.EVT_MENU, self.onOptionsSetup, id=wx.ID_SETUP)
        self.Bind(wx.EVT_MENU, self.OnOpenCSV, id = self.id.IDs['ID_BTNCSV'])
        self.Bind(wx.EVT_MENU, self.OnOpenBrowser, id = self.id.IDs['ID_BTNBROWSER'])
        # More BIND below in main

    def OnExit(self, event):
        global panel
        panel.myTimer.Stop()
        self.Unbind(wx.EVT_TIMER, self)
        """Close the frame, terminating the application."""
        panel.gO.savesettings()
        if event.GetEventType() == wx.EVT_CLOSE.typeId:
            self.Destroy()
        else:
            self.Close(True)


        

    def OnOpenCSV(self, event):
        panel.OpenCSV()
    def OnOpenBrowser(self, event):
        panel.OpenBrowser()

    def OnFileOpenDialog(self, evt):
        global panel

        dDir = os.getcwd()
        if panel and panel.gO:
            infile = panel.gO.get('GEDCOMinput')
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
            panel.setInputFile(path)
            

            # add it to the history
            self.filehistory.AddFileToHistory(path)
            self.filehistory.Save(panel.fileConfig)

        dlg.Destroy()
        wx.Yield()
        if Proceed:
            panel.LoadGEDCOM()
    def OnFileResultDialog(self, evt):
        global panel

        dDir = os.getcwd()
        dFile = "visgedcom.html"
        if panel and panel.gO:
            resultfile = panel.gO.get('Result')
            if resultfile != '':
                dDir, dFile= os.path.split(resultfile)
            else:
                resultfile = panel.gO.get('GEDCOMinput')
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
            panel.gO.setResults(path, isHTML)
            panel.id.TEXTResult.SetValue(path)
            panel.id.RBResultHTML.SetSelection(0 if isHTML else 1)
            panel.SetupButtonState()
        dlg.Destroy()
        wx.Yield()
        

    def Cleanup(self, *args):
        # A little extra cleanup is required for the FileHistory control
        del self.filehistory
        self.menu.Destroy()

    def OnFileHistory(self, evt):
        global panel

        # get the file based on the menu ID
        fileNum = evt.GetId() - wx.ID_FILE1
        path = self.filehistory.GetHistoryFile(fileNum)
        _log.debug("You selected %s", path)

        # add it back to the history so it will be moved up the list
        self.filehistory.AddFileToHistory(path)
        panel.setInputFile(path)
        wx.Yield()
        panel.LoadGEDCOM()

    def OnAbout(self, event):
        dialog = AboutDialog(None, title=f"About {GUINAME} {VERSION}")
        dialog.ShowModal()
        dialog.Destroy()

    def OnInfo(self, event):
        global panel
        """Display an Staticis Info Dialog"""

        withoutaddr = 0
        msg = ""
        if hasattr(panel.gO, 'humans') and panel.gO.humans:
            # for xh in panel.gO.humans.keys():
            #    if (panel.gO.humans[xh].bestlocation() == ''): 
            #        withoutaddr += 1
            # msg = f'Total People :\t{len(panel.gO.humans)}\n People without any address {withoutaddr}'
            msg = f'Total People :{len(panel.gO.humans)}'
        else:
            msg = "No people loaded yet"
        msg = msg + '\n'
        if hasattr(panel.gO, 'lookup') and hasattr(panel.gO.lookup, 'addresses') and panel.gO.lookup.addresses:
            msg = msg + f'Total cached addresses :{len(panel.gO.lookup.addresses)}\n' +  panel.gO.lookup.stats
            
        else:
            msg = msg + "No address in cache"
            
        wx.MessageBox (msg, 'Statistics', wx.OK|wx.ICON_INFORMATION)
    def OnFind(self, event):
        global panel
        panel.peopleList.list.OnFind(event)

    def onOptionsReset(self, event):
        global panel
        panel.gO.defaults()
        panel.SetupOptions()
        wx.MessageBox("Rest options to defaults",
                      "Reset Options",
                      wx.OK|wx.ICON_INFORMATION)
        
    def onOptionsSetup(self, event):
        dialog = ConfigDialog(None, title='Configuration Options', gOptions=panel.gO)
        



#=============================================================
class PeopleListCtrl(wx.ListCtrl, listmix.ListCtrlAutoWidthMixin, listmix.ColumnSorterMixin):
    def __init__(self, parent, ID, pos=wx.DefaultPosition,
                 size=wx.DefaultSize, style=0, *args, **kw):
        super(PeopleListCtrl, self).__init__(*args, **kw)
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
        self.gO = None
        self.parent = parent

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
        self.gO = gOp

    def PopulateList(self, humans, mainperson, loading):
        global panel
        if self.active:
            return
        
        self.active = True

        if self.gO:
            wasrunning = self.gO.running
            self.gO.running = True
            self.GridOnlyFamily = self.gO.get('GridView')
        
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
        if (not humans):
            self.active = False
            return
        
        if (loading):
            index = 0
            for h in humans:
                if hasattr(humans[h], 'name'):
                    d, y = humans[h].refyear()
                    (location, where) = humans[h].bestlocation()
                        
                    self.popdata[index] = (humans[h].name, d, humans[h].xref_id, location , where, self.ParseDate(y))
                    index += 1
        if self.gO:
            items = self.popdata.items()
            self.gO.selectedpeople = 0
            self.gO.step("Gridload", resetCounter=False)
            self.itemDataMap = {data[0] : data for data in items} 
            index = -1
            for key, data in items:
                self.gO.counter = key
                if key % 2048 == 0:
                    wx.Yield()
                
                if self.GridOnlyFamily and self.gO.Referenced:
                    DisplayItem = self.gO.Referenced.exists(data[2])
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
                    
                    if self.gO.Referenced:
                        if self.gO.Referenced.exists(data[2]):
                            self.gO.selectedpeople = self.gO.selectedpeople + 1
                            if mainperson == data[2]:
                                self.SetItemBackgroundColour(index, self.id.GetColor('MAINPERSON'))
                            else:
                                self.SetItemBackgroundColour(index, self.id.GetColor('ANCESTOR'))
                        else:
                            self.SetItemBackgroundColour(index, self.id.GetColor('OTHERPERSON'))
            self.gO.counter = 0
            self.gO.state = ""

        self.SetColumnWidth(1, wx.LIST_AUTOSIZE_USEHEADER)
        self.SetColumnWidth(2, wx.LIST_AUTOSIZE_USEHEADER)
        self.SetColumnWidth(3, wx.LIST_AUTOSIZE_USEHEADER)
        self.SetColumnWidth(4, wx.LIST_AUTOSIZE_USEHEADER)
        self.SetColumnWidth(0, wx.LIST_AUTOSIZE_USEHEADER)
        # Sometimes the Name is too long
        if self.GetColumnWidth(0) > 300:
            self.SetColumnWidth(0, 300)

        # NOTE: self.list can be empty (the global value, m, is empty and passed as humans).
        if 0 <= selectperson < self.GetItemCount():
            self.SetItemState(selectperson, wx.LIST_STATE_SELECTED, wx.LIST_STATE_SELECTED)
        
        if mainperson and selectperson > 0 and loading:
            self.EnsureVisible(selectperson)
        wx.Yield()
        if self.gO and self.gO.running:
            # Hack race condition
            if not wasrunning:
                panel.StopTimer()
            self.gO.running = wasrunning
            
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
            match = pattern.search(datestring)
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
        global BackgroundProcess
        
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
            BackgroundProcess.SayInfoMessage(f"* Could not find '{self.LastSearch}' in the names", False)
  
    def OnItemRightClick(self, event):
        self.currentItem = event.Index
        _log.debug("%s, %s, %s, %s", 
                           self.currentItem,
                            self.GetItemText(self.currentItem),
                            self.GetItemText(self.currentItem, 1),
                            self.GetItemText(self.currentItem, 2))
        event.Skip()
        if BackgroundProcess.humans:
            itm = self.GetItemText(self.currentItem, 2)
            if itm in BackgroundProcess.humans:
                dialog = PersonDialog(None, BackgroundProcess.humans[itm], panel)
                dialog.ShowModal()
                dialog.Destroy()


    def OnItemActivated(self, event):
        global BackgroundProcess, panel
        self.currentItem = event.Index
        _log.debug("%s TopItem: %s", self.GetItemText(self.currentItem), self.GetTopItem())
        if self.gO:
            self.gO.setMain(self.GetItemText(self.currentItem, 2))
            if BackgroundProcess.updategridmain:
                BackgroundProcess.updategridmain = False
                doTrace(self.gO)
                self.PopulateList(self.gO.humans, self.gO.get('Main'), False)
                BackgroundProcess.SayInfoMessage(f"Using '{self.gO.get('Main')}' as starting person with {len(self.gO.Referenced)} direct ancestors", False)
                BackgroundProcess.updategridmain = True
                panel.SetupButtonState()
                

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
    def __init__(self, parent, humans,  *args, **kw):
        """    Initializes the PeopleListCtrlPanel.

    Args:
        parent: The parent window.
        humans: The list of humans.
        *args: Variable length argument list.
        **kw: Arbitrary keyword arguments.

    Returns:
        None

    Raises:
        None
        """
        super(PeopleListCtrlPanel, self).__init__(*args, **kw)
        wx.Panel.__init__(self, parent, -1, style=wx.WANTS_CHARS)
        # TODO This box defination still have a scroll overlap problem
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.messagelog = "*  Select a file, Load it and Draw Update or change Result Type, Open Geo Table to edit addresses  *"
        self.InfoBox = []
        for i in range(InfoBoxLines):
            self.InfoBox.append(wx.StaticText(parent, -1, ' '))
            sizer.Add(self.InfoBox[i], 0, wx.LEFT,5)
        tID = wx.NewIdRef()
        self.list = PeopleListCtrl(parent, tID,
                        style=wx.LC_REPORT | wx.BORDER_SUNKEN | wx.LC_SINGLE_SEL,
                        size=wx.Size(600,600))
        sizer.Add(self.list, -1, wx.EXPAND)

        self.list.PopulateList(humans, None, True)

        self.currentItem = 0
        parent.SetSizer(sizer)
        
    def setGOp(self, gOp):
        self.gO = gOp
        if self.list:
            self.list.SetGOp(gOp)


class VisualMapPanel(wx.Panel):
    """
    A Frame that says Visual Setup
    """

    def __init__(self,  *args, **kw):
        global panel
        # ensure the parent's __init__ is called so the wx.frame is created
        #
        super(VisualMapPanel, self).__init__(*args, **kw)

        panel = self
        self.SetMinSize((800,800))
        self.frame = self.TopLevelParent
        self.gO : gvOptions = None
        
        self.id = {}
        
        self.fileConfig = None
        self.busystate = 0
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


    def LayoutOptions(self, panel):
        """ Layout the panels in the proper nested manner """
        # Top of the Panel
        global BackgroundProcess
        box = wx.BoxSizer(wx.VERTICAL)
        titleFont = wx.Font(wx.FontInfo(GVFONT[2]).FaceName(GVFONT[0]).Bold())
        # TODO Check for Arial and change it
        if not titleFont:
            titleFont  = wx.Font(wx.FontInfo(16).FaceName('Verdana').Bold())
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
            
        
        self.id.txtinfile = wx.StaticText(panel, -1,  "Input file:   ") 
        self.id.txtinfile.SetBackgroundColour(self.id.GetColor('BTN_DIRECTORY'))
        self.id.TEXTGEDCOMinput = wx.TextCtrl(panel, self.id.IDs['ID_TEXTGEDCOMinput'], "", size=(250,20))
        self.id.TEXTGEDCOMinput.Enable(False) 
        self.id.txtoutfile = wx.StaticText(panel, -1, "Output file: ")
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
        self.id.RBResultHTML =  wx.RadioBox(panel, self.id.IDs['ID_RBResultHTML'], "Result Type", 
                                           choices = ['HTML', 'KML'] , majorDimension= 2)

        self.id.CBUseGPS = wx.CheckBox(panel, self.id.IDs['ID_CBUseGPS'], "Use GPS lookup (uncheck if GPS is in file)")#,  wx.NO_BORDER)
        self.id.CBCacheOnly = wx.CheckBox(panel, self.id.IDs['ID_CBCacheOnly'], "Cache Only, do not lookup addresses")#, , wx.NO_BORDER)
        self.id.CBAllEntities = wx.CheckBox(panel, self.id.IDs['ID_CBAllEntities'], "Map all people")#, wx.NO_BORDER)
        if False:
            txtMissing = wx.StaticText(panel, -1,  "Max generation missing: ") 
            self.id.INTMaxMissing = wx.TextCtrl(panel, self.id.IDs['ID_INTMaxMissing'], "", size=(20,20))
            txtLine = wx.StaticText(panel, -1,  "Line maximum weight: ") 
            self.id.INTMaxLineWeight = wx.TextCtrl(panel, self.id.IDs['ID_INTMaxLineWeight'], "", size=(20,20))
            l1 = wx.BoxSizer(wx.HORIZONTAL)
            l1.AddMany([txtMissing,      (0,20),     self.id.INTMaxMissing])
            l2 = wx.BoxSizer(wx.HORIZONTAL)
            l2.AddMany([txtLine,      (0,20),     self.id.INTMaxLineWeight])
            box.AddMany([l1, (4,4,), l2])
        # self.id.ID_INTMaxMissing  'MaxMissing'
        # self.id.ID_INTMaxLineWeight  'MaxLineWeight'
        
        self.id.busyIndicator = wx.ActivityIndicator(panel)

        self.id.busyIndicator.SetBackgroundColour(self.id.GetColor('BUSY_BACK'))
        
        box.AddMany([ self.id.RBResultHTML,
                       self.id.CBUseGPS,
                       self.id.CBCacheOnly,
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
        self.id.LISTMapType = wx.Choice(hbox, self.id.IDs['ID_LISTMapStyle'], name="MapStyle", choices=mapchoices)
        self.id.CBMapControl = wx.CheckBox(hbox, self.id.IDs['ID_CBMapControl'], "Open Map Controls",name='MapControl') 
        self.id.CBMapMini = wx.CheckBox(hbox, self.id.IDs['ID_CBMapMini'], "Add Mini Map",name='MapMini') 
        self.id.CBMarksOn = wx.CheckBox(hbox, self.id.IDs['ID_CBMarksOn'], "Markers",name='MarksOn')
        
        self.id.CBBornMark = wx.CheckBox(hbox, self.id.IDs['ID_CBBornMark'], "Marker for when Born")
        self.id.CBDieMark = wx.CheckBox(hbox, self.id.IDs['ID_CBDieMark'], "Marker for when Died")
        self.id.CBHomeMarker = wx.CheckBox(hbox, self.id.IDs['ID_CBHomeMarker'], "Marker point or homes")
        self.id.CBMarkStarOn = wx.CheckBox(hbox, self.id.IDs['ID_CBMarkStarOn'], "Marker starter with Star")
        
        self.id.CBHeatMap = wx.CheckBox(hbox, self.id.IDs['ID_CBHeatMap'], "Heatmap", style = wx.NO_BORDER)
        self.id.CBHeatMapTimeLine = wx.CheckBox(hbox, self.id.IDs['ID_CBHeatMapTimeLine'], "Heatmap Timeline Steps")
        self.id.CBUseAntPath = wx.CheckBox(hbox, self.id.IDs['ID_CBUseAntPath'], "Ant paths")
        
        TimeStepVal = 5
        self.id.LISTHeatMapTimeStep = wx.Slider(hbox, self.id.IDs['ID_LISTHeatMapTimeStep'], TimeStepVal,1, 100, size=(250, 45),
                style=wx.SL_HORIZONTAL | wx.SL_AUTOTICKS | wx.SL_LABELS )
        self.id.LISTHeatMapTimeStep.SetTickFreq(5)
        self.id.RBGroupBy  = wx.RadioBox(hbox, self.id.IDs['ID_RBGroupBy'], "Group by:", 
                                       choices = ['None', 'Last Name', 'Person'], majorDimension= 3)
        mapboxsizer.Add(self.id.LISTMapType)
        mapboxsizer.Add( mapStyleLabel)
        
        
        hboxIn.AddMany([
        
                        self.id.RBGroupBy, 
                        mapboxsizer,
                        self.id.CBMapControl,
                        self.id.CBMapMini,
                        self.id.CBMarksOn,
                        self.id.CBBornMark,
                        self.id.CBDieMark,
                        self.id.CBHomeMarker,
                        self.id.CBMarkStarOn,
                        self.id.CBUseAntPath,
                        self.id.CBHeatMap,
                        self.id.CBHeatMapTimeLine, 
                        (0,5),
                        self.id.LISTHeatMapTimeStep,
                        (0,5)
                        ])
        hsizer.Add( hboxIn, wx.LEFT, hOtherBorder+10)
        
        hbox.SetSizer(hsizer)
        self.hbox = hbox
        #
        # KML select controls in a Box
        #
        kbox = wx.StaticBox( panel, -1, "KML Options", size=(300,-1))
        kTopBorder, kOtherBorder = kbox.GetBordersForSizer()
        ksizer = wx.BoxSizer(wx.VERTICAL)
        ksizer.AddSpacer(kTopBorder)
        kboxIn = wx.BoxSizer(wx.VERTICAL)
        self.id.LISTPlaceType = wx.CheckListBox(kbox, self.id.IDs['ID_LISTPlaceType'],  choices=AllPlaceType)
        kboxIn.AddMany( [self.id.LISTPlaceType])
        ksizer.Add( kboxIn, wx.LEFT, kOtherBorder+10)
        kbox.SetSizer(ksizer)
        self.kbox = kbox


        #
        # Grid View Options
        #
        
        
        gbox = wx.StaticBox( panel, -1, "Grid View Options",size=(300,-1))
        gTopBorder, gOtherBorder = gbox.GetBordersForSizer()
        gsizer = wx.BoxSizer(wx.VERTICAL)
        gsizer.AddSpacer(gTopBorder)
        gboxIn = wx.BoxSizer(wx.VERTICAL)
        self.id.CBGridView = wx.CheckBox(gbox, self.id.IDs['ID_CBGridView'],  'View Only Direct Ancestors')
        gboxIn.AddMany( [self.id.CBGridView])
        gsizer.Add( gboxIn, wx.LEFT, kOtherBorder+10)
        
        gbox.SetSizer(gsizer)
        self.gbox = gbox
        
        box.Add(hbox, 1, wx.LEFT, 15)
        box.Add(kbox, 1, wx.LEFT, 15)
        box.Add(gbox, 1, wx.LEFT, 15)
        
        

        l1 = wx.BoxSizer(wx.HORIZONTAL)
        self.id.BTNLoad = wx.Button(panel, self.id.IDs['ID_BTNLoad'], "Load")
        self.id.BTNUpdate = wx.Button(panel, self.id.IDs['ID_BTNUpdate'], "Draw & Update")
        self.id.BTNCSV = wx.Button(panel, self.id.IDs['ID_BTNCSV'], "Geo Table")
        self.id.BTNTRACE = wx.Button(panel, self.id.IDs['ID_BTNTRACE'], "Trace")
        self.id.BTNSTOP = wx.Button(panel, self.id.IDs['ID_BTNSTOP'], "Stop")
        self.id.BTNBROWSER = wx.Button(panel, self.id.IDs['ID_BTNBROWSER'], "Browser")
        l1.Add (self.id.BTNLoad, 0, wx.EXPAND | wx.ALL, 5)
        l1.Add (self.id.BTNUpdate, 0, wx.EXPAND | wx.ALL, 5)
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
        
        self.Bind(wx.EVT_RADIOBOX, self.EvtRadioBox, id = self.id.IDs['ID_RBResultHTML'])
        self.Bind(wx.EVT_CHECKBOX, self.EvtCheckBox, id = self.id.IDs['ID_CBMapControl'])
        self.Bind(wx.EVT_CHECKBOX, self.EvtCheckBox, id = self.id.IDs['ID_CBMapMini'])
        self.Bind(wx.EVT_CHECKBOX, self.EvtCheckBox, id = self.id.IDs['ID_CBMarksOn'])
        self.Bind(wx.EVT_CHECKBOX, self.EvtCheckBox, id = self.id.IDs['ID_CBBornMark'])
        self.Bind(wx.EVT_CHECKBOX, self.EvtCheckBox, id = self.id.IDs['ID_CBDieMark'])
        self.Bind(wx.EVT_CHECKBOX, self.EvtCheckBox, id = self.id.IDs['ID_CBHomeMarker'])
        self.Bind(wx.EVT_CHECKBOX, self.EvtCheckBox, id = self.id.IDs['ID_CBMarkStarOn'])
        self.Bind(wx.EVT_CHECKBOX, self.EvtCheckBox, id = self.id.IDs['ID_CBHeatMap'])
        self.Bind(wx.EVT_CHECKBOX, self.EvtCheckBox, id = self.id.IDs['ID_CBHeatMapTimeLine'])
        self.Bind(wx.EVT_CHECKBOX, self.EvtCheckBox, id = self.id.IDs['ID_CBUseAntPath'])
        self.Bind(wx.EVT_CHECKBOX, self.EvtCheckBox, id = self.id.IDs['ID_CBUseGPS'])
        self.Bind(wx.EVT_CHECKBOX, self.EvtCheckBox, id = self.id.IDs['ID_CBCacheOnly'])
        self.Bind(wx.EVT_CHECKBOX, self.EvtCheckBox, id = self.id.IDs['ID_CBAllEntities'])
        self.Bind(wx.EVT_CHECKBOX, self.EvtCheckBox, id = self.id.IDs['ID_CBGridView'])
        self.Bind(wx.EVT_CHECKLISTBOX, self.EvtListBox, id = self.id.IDs['ID_LISTPlaceType'])
        self.Bind(wx.EVT_CHOICE, self.EvtListBox, id = self.id.IDs['ID_LISTMapStyle'])
        self.Bind(wx.EVT_BUTTON, self.EvtButton, id = self.id.IDs['ID_BTNLoad'])
        self.Bind(wx.EVT_BUTTON, self.EvtButton, id = self.id.IDs['ID_BTNUpdate'])
        self.Bind(wx.EVT_BUTTON, self.EvtButton, id = self.id.IDs['ID_BTNCSV'])
        self.Bind(wx.EVT_BUTTON, self.EvtButton, id = self.id.IDs['ID_BTNTRACE'])
        self.Bind(wx.EVT_BUTTON, self.EvtButton, id = self.id.IDs['ID_BTNSTOP'])
        self.Bind(wx.EVT_BUTTON, self.EvtButton, id = self.id.IDs['ID_BTNBROWSER'])
        self.Bind(wx.EVT_TEXT, self.EvtText, id = self.id.IDs['ID_TEXTResult'])
        self.OnBusyStop(-1)
        self.Bind(wx.EVT_RADIOBOX, self.EvtRadioBox, id = self.id.IDs['ID_RBGroupBy'])
        self.Bind(wx.EVT_SLIDER, self.EvtSlider, id = self.id.IDs['ID_LISTHeatMapTimeStep'])
        self.NeedReload()
        self.NeedRedraw()
        self.Bind(wx.EVT_CLOSE, self.OnCloseWindow)
        self.Bind(EVT_UPDATE_STATE, self.OnUpdate)
        self.threads = []
        BackgroundProcess = BackgroundActions(self, 0)
        self.threads.append(BackgroundProcess)
        for t in self.threads:
            t.Start()
        

        # Bind all EVT_TIMER events to self.OnMyTimer
        self.Bind(wx.EVT_TIMER, self.OnMyTimer)
        self.myTimer = wx.Timer(self)
        self.myTimer.Start(250)


    def NeedReload(self):
        if self.gO:
            self.gO.parsed= False
        self.id.BTNLoad.SetBackgroundColour(self.id.GetColor('BTN_PRESS'))
        self.NeedRedraw()

    def NeedRedraw(self):
        self.id.BTNUpdate.SetBackgroundColour(self.id.GetColor('BTN_PRESS'))

    def setInputFile(self, path):
        # set the state variables
        self.gO.setInput(path)
        _, filen = os.path.split(self.gO.get('GEDCOMinput'))
        # set the form field
        self.id.TEXTGEDCOMinput.SetValue(filen)
        self.fileConfig.Write("GEDCOMinput", path)
        #TODO Fix this
        #TODO Fix this
        self.id.TEXTResult.SetValue(self.gO.get('Result'))
        self.NeedReload()
        self.SetupButtonState()

    def EvtRadioBox(self, event):

        _log.debug('%d is %d',  event.GetId(), event.GetInt())
        if event.GetId() == self.id.IDs['ID_RBResultHTML']:
            self.gO.set('ResultHTML', event.GetInt() == 0)
            filename = self.gO.get('Result')
            newname = filename
            if self.gO.get('ResultHTML'):
                BackgroundProcess.updategridmain = True
                if '.kml' in filename.lower():
                    newname = self.gO.get('Result').replace('.kml', '.html', -1)
            else:
                if '.html' in filename.lower():
                    newname = self.gO.get('Result').replace('.html', '.kml', -1)
            if filename != newname:      
                self.gO.set('Result', newname)
                self.id.TEXTResult.SetValue(self.gO.get('Result'))

           
            self.SetupButtonState()
        elif event.GetId() ==  self.id.IDs['ID_RBGroupBy']:
            self.gO.GroupBy = event.GetSelection()
        else:
            _log.error('We have a Problem')
        

    def EvtText(self, event):

        if event.GetId() == self.id.IDs['ID_TEXTResult']:
            event.GetString()
            self.gO.set('Result', event.GetString())
            _log.debug("Result %s", self.gO.get('Result') )
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
        panel.gO.set( self.id.IDtoAttr[cbid][0], cb.GetValue())
        
        if cbid == self.id.IDs['ID_CBHeatMap'] or cbid == self.id.IDs['ID_CBHeatMapTimeLine'] or cbid == self.id.IDs['ID_CBMarksOn']:
            self.SetupButtonState()
        if ( self.id.IDtoAttr[cbid][1] == 'Redraw'):
            self.NeedRedraw()
        elif ( self.id.IDtoAttr[cbid][1] == 'Reload'):
            self.NeedReload()
        elif ( self.id.IDtoAttr[cbid][1] == 'Render'):
            BackgroundProcess.updategrid = True
        elif ( self.id.IDtoAttr[cbid][1] == ''):
            pass # Nothing to do for this one
        else:
            _log.error("uncontrolled CB %d with '%s'", cbid,   self.id.IDtoAttr[cbid][1])
        if cbid == self.id.IDs['ID_CBAllEntities'] and cb.GetValue():
            # TODO Fix this up
            if self.gO.get('ResultHTML'):
                dlg = None
                if hasattr(BackgroundProcess, 'humans') and BackgroundProcess.humans:
                    if len(BackgroundProcess.humans) > 200:
                        dlg = wx.MessageDialog(self, f'Caution, {len(BackgroundProcess.humans)} people in your tree\n it may create very large HTML files and may not open in the browser',
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
        self.SetupOptions()
        if myid == self.id.IDs['ID_BTNLoad']:
            self.LoadGEDCOM()
                
        elif myid == self.id.IDs['ID_BTNUpdate']:
            self.DrawGEDCOM()
                                
        elif myid == self.id.IDs['ID_BTNCSV']:
            self.OpenCSV()
        elif myid == self.id.IDs['ID_BTNTRACE']:
            self.SaveTrace()
        elif myid == self.id.IDs['ID_BTNSTOP']:
            self.gO.set('stopping', True)
            self.gO.set('parsed', False)
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
        if eventid == self.id.IDs['ID_LISTPlaceType']:
            places = {}
            for cstr in event.EventObject.CheckedStrings:
                places[cstr] = cstr
            if places == {}:
                places = {'native':'native'}
            panel.gO.PlaceType = places
        elif eventid == self.id.IDs['ID_LISTMapStyle']:
            
            panel.gO.MapStyle = sorted(self.id.AllMapTypes)[event.GetSelection()] 
            self.NeedRedraw()
        else:

            _log.error ("Uncontrol LISTbox")
    

    def EvtSlider(self, event):

        _log.debug('%s', event.GetSelection())
        panel.gO.HeatMapTimeStep = event.GetSelection()

    def OnMyTimer(self, evt):
        if self.inTimer:
            return
        self.inTimer = True
        status = ''
        if self.gO:
            if self.gO.ShouldStop() or not self.gO.running:
                if self.id.BTNSTOP.IsEnabled():
                    self.id.BTNSTOP.Disable()
            else:
                self.id.BTNSTOP.Enable()
            status = self.gO.state
            if self.gO.running:
                self.gO.runningLast = 0
                status = f"{status} - Processing"
                runtime = "Running {}".format(time.strftime('%H:%M:%S', time.gmtime(datetime.now().timestamp() - self.gO.runningSince)))
            else:
                runtime = "Last {}".format( time.strftime('%H:%M:%S', time.gmtime(self.gO.runningLast)))
            self.frame.SetStatusText(runtime,1) 
            if self.gO.counter > 0:
                if self.gO.countertarget > 0:
                    status = f"{status} : {panel.gO.counter/self.gO.countertarget*100:.0f}% ({panel.gO.counter}/{self.gO.countertarget})  "
                else:
                    status = f"{status} : {panel.gO.counter}"
                if panel.gO.stepinfo:
                    status = f"{status} ({panel.gO.stepinfo})"
            if self.gO.ShouldStop():
                self.id.BTNUpdate.Enable()
                status = f"{status} - please wait.. Stopping"

            _, filen = os.path.split(self.gO.get('GEDCOMinput'))
            if filen == "":
                self.id.BTNLoad.Disable()
                self.id.BTNUpdate.Disable()
            else:
                if not self.id.BTNLoad.IsEnabled():
                    self.id.BTNLoad.Enable()
                if not self.id.BTNLoad.IsEnabled():
                    self.id.BTNUpdate.Enable()
            if self.gO.get('gpsfile') == '':
                self.id.BTNCSV.Disable()
            else:
                if not self.id.BTNCSV.IsEnabled():
                    self.id.BTNCSV.Enable()
        if not status or status == '':
            if self.gO.selectedpeople and self.gO.ResultHTML:
                status = f'Ready - {panel.gO.selectedpeople} people selected'
            else:
                status = 'Ready'
            self.OnBusyStop(-1)
        if self.frame:
            self.frame.SetStatusText(status)
        if BackgroundProcess.updateinfo or BackgroundProcess.errorinfo or BackgroundProcess.updategrid:
            self.OnUpdate(evt)
        if self.busystate != self.gO.running:
            logging.info("Busy %d not Running %d", self.busystate, self.gO.running)
            if self.gO.running:
                self.gO.runningSince = datetime.now().timestamp()
                self.OnBusyStart(-1)
            else:
                self.OnBusyStop(-1)
                self.StopTimer()
        if not self.gO.running:
           self.gO.countertarget = 0
           self.gO.stepinfo = ""
           self.gO.runningSince = datetime.now().timestamp()
           self.busycounthack += 1
           if self.busycounthack > 40:
                self.OnBusyStop(-1)
                self.busycounthack = 0
        wx.Yield()
        self.inTimer = False
    def StopTimer(self):
        self.gO.runningLast = datetime.now().timestamp() - self.gO.runningSince
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

    def OnUpdate(self, evt):
        # proces evt state hand off
        if hasattr(evt, 'state'):
            if evt.state == 'busy': 
                self.OnBusyStart(evt)
            if evt.state == 'done': 
                self.OnBusyStop(evt)
                self.StopTimer()
        if BackgroundProcess.updategrid:
            BackgroundProcess.updategrid = False
            saveBusy = self.busystate
            self.OnBusyStart(evt)
            self.peopleList.list.PopulateList(BackgroundProcess.humans, self.gO.get('Main'), True)
            if saveBusy:
                self.OnBusyStop(evt)
        newinfo = None
        if BackgroundProcess.updateinfo:
            _log.debug("Infobox: %s", BackgroundProcess.updateinfo)
            newinfo = BackgroundProcess.updateinfo
            BackgroundProcess.updateinfo = None
        if BackgroundProcess.errorinfo:
            _log.debug("Infobox-Err: %s", BackgroundProcess.errorinfo)
            einfo = f"<span foreground='red'><b>{BackgroundProcess.errorinfo}</b></span>"
            newinfo = newinfo + '\n' + einfo if newinfo else einfo
            BackgroundProcess.errorinfo = None
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
        ResultTypeHTML = self.gO.get('ResultHTML')
        # Always enabled
            # self.id.CBUseGPS
            # self.id.CBAllEntities
            # self.id.CBCacheOnly
            
        # Define control groups for HTML and KML modes
        html_controls = [
            self.id.CBMarksOn,
            self.id.CBMapControl,
            self.id.LISTMapType, 
            self.id.CBMapMini,
            self.id.CBBornMark,
            self.id.CBDieMark,
            self.id.CBHomeMarker,
            self.id.CBMarkStarOn,
            self.id.CBHeatMap,
            self.id.CBUseAntPath,
            self.id.RBGroupBy
        ]
        kml_controls = [
            self.id.CBBornMark, 
            self.id.CBDieMark, 
            self.id.CBHomeMarker
            ]

        # Enable/disable controls based on result type (HTML vs KML)
        if ResultTypeHTML:
            # Enable HTML-specific controls
            for ctrl in html_controls:
                ctrl.Enable()
            
            # Disable KML-specific controls
            self.id.LISTPlaceType.Disable()
            
            # Handle heat map related controls
            self.id.CBHeatMapTimeLine.Disable()
            self.id.LISTHeatMapTimeStep.Disable()
            
            if self.gO.get('HeatMap'):
                self.id.CBHeatMapTimeLine.Enable()
                # Only enable time step if timeline is enabled
                if self.gO.get('HeatMapTimeLine'):
                    self.id.LISTHeatMapTimeStep.Enable()
                    
            # Disable marker-dependent controls if markers are off
            if not self.gO.get('MarksOn'):
                for ctrl in kml_controls:
                    ctrl.Disable()
        else:
            # In KML mode, disable HTML controls and enable KML controls
            for ctrl in html_controls + [
                self.id.CBHeatMapTimeLine,
                self.id.LISTHeatMapTimeStep
            ]:
                ctrl.Disable()
            self.id.LISTPlaceType.Enable()

        # Enable/disable trace button based on referenced data availability
        self.id.BTNTRACE.Enable(bool(self.gO.Referenced and self.gO.Result))

    def SetupOptions(self):

        if not self.fileConfig:
            self.fileConfig = wx.Config("gedcomVisualGUI")
        
        if not self.gO:
            self.gO = gvOptions()
            self.gO.panel = self
            self.gO.BackgroundProcess = BackgroundProcess
            self.gO.UpdateBackgroundEvent = UpdateBackgroundEvent
            self.peopleList.setGOp(self.gO)

        self.id.RBResultHTML.SetSelection(0 if self.gO.get('ResultHTML') else 1)
        
        self.id.CBMapControl.SetValue(self.gO.get('showLayerControl'))
        self.id.CBMapMini.SetValue(self.gO.get('mapMini'))
        self.id.CBMarksOn.SetValue(self.gO.get('MarksOn'))
        self.id.CBBornMark.SetValue(self.gO.get('BornMark'))
        self.id.CBDieMark.SetValue(self.gO.get('DieMark'))
        self.id.CBHomeMarker.SetValue(self.gO.get('HomeMarker'))
        self.id.CBMarkStarOn.SetValue(self.gO.get('MarkStarOn'))
        self.id.CBHeatMap.SetValue(self.gO.get('HeatMap'))
        self.id.CBHeatMapTimeLine.SetValue(self.gO.get('HeatMapTimeLine'))
        self.id.CBUseAntPath.SetValue(self.gO.get('UseAntPath'))
        self.id.CBUseGPS.SetValue(self.gO.get('UseGPS'))
        self.id.CBAllEntities.SetValue(self.gO.get('AllEntities'))
        self.id.CBCacheOnly.SetValue(self.gO.get('CacheOnly'))
        self.id.LISTHeatMapTimeStep.SetValue(self.gO.get('HeatMapTimeStep'))
        self.id.LISTMapType.SetSelection(self.id.LISTMapType.FindString(self.gO.get('MapStyle')))
                
        
        places = self.gO.get('PlaceType')
        self.id.LISTPlaceType.SetCheckedStrings(places)
        self.id.RBGroupBy.SetSelection(self.gO.get('GroupBy'))
        
        
        self.id.TEXTResult.SetValue(self.gO.get('Result'))

        _, filen = os.path.split(self.gO.get('GEDCOMinput')) if self.gO.get('GEDCOMinput') else ("", "first.ged")
        self.id.TEXTGEDCOMinput.SetValue(filen)
        self.id.LISTPlaceType.SetCheckedStrings(self.gO.PlaceType)
        self.SetupButtonState()

        for t in self.threads:
            t.DefgOps(self.gO)

        # Load file history into the panel's configuration
        self.frame.filehistory.Load(self.fileConfig)


    def updateOptions(self):
        pass

    def LoadGEDCOM(self):
        #TODO stop the previous actions and then do the load... need to be improved
        if BackgroundProcess.IsTriggered(): 
            self.gO.stopping = True
        else:
            self.OnBusyStart(-1)
            time.sleep(0.1)
        
            cachepath, _ = os.path.split(self.gO.get('GEDCOMinput'))
            if self.gO.get('gpsfile'):
                sourcepath, _ = os.path.split(self.gO.get('gpsfile'))
            else:
                sourcepath = None
            if self.gO.lookup and cachepath != sourcepath:
                del self.gO.lookup
                self.gO.lookup = None
            BackgroundProcess.Trigger(1)    
        
    def DrawGEDCOM(self):

        if not self.gO.get('Result') or self.gO.get('Result') == '':
            _log.error("Error: Not output file name set")
            BackgroundProcess.SayErrorMessage("Error: Please set the Output file name")
        else:
            self.OnBusyStart(-1)
            BackgroundProcess.Trigger(2 | 4)
        
    
    def OpenCSV(self):
        self.runCMDfile(self.gO.get('CSVcmdline'), self.gO.get('gpsfile'))

    def runCMDfile(self, cmdline, cmdfile, isHTML=False):
        cmdfile = self.gO.get('gpsfile')
        cmdline = self.gO.get('CSVcmdline')
        if cmdfile and cmdfile != '':
            if cmdline == '$n':
                if isHTML:
                    _log.info(f'browserstart {cmdfile}')
                    webbrowser.open(cmdfile, new = 0, autoraise = True)
                else:
                    _log.info(f'startfile {cmdfile}')
                    os.startfile(cmdfile)
                
            elif '$n' in cmdline:
                cmdline = cmdline.replace('$n','')
                if ' ' in cmdline:
                    cmdline = self.gO.get('CSVcmdline').replace('$n', f'{cmdfile}')
                    _log.info(f'shell run  `{cmdfile}`')
                    if gOp.cmdline.startswith('http'):
                        webbrowser.open(cmdline, new = 0, autoraise = True)
                    else:
                        subprocess.run(cmdline, shell=True)
                else:
                    _log.info(f'process run `{cmdline}` with `{cmdfile}`')
                    subprocess.run([cmdline, cmdfile], check=False)
                # TODO need a better command-line management than this
                # cmdline = f"column -s, -t < {csvfile} | less -#2 -N -S"
                # subprocess.run(cmdline, shell=True)
            else:
                _log.error("Error: runCMDfile-Unsupported platform, can not open cmdline file")
    
    def SaveTrace(self):
        if self.gO.Result and self.gO.Referenced:
            if not self.gO.lastlines:
                logging.error("No lastline values in SaveTrace (do draw first)")
                return 
            tracepath = os.path.splitext(self.gO.Result)[0] + ".trace.txt"
            # indentpath = os.path.splitext(self.gO.Result)[0] + ".indent.txt"
            trace = open(tracepath , 'w')
            # indent = open(indentpath , 'w')
            trace.write("id\tName\tYear\tWhere\tGPS\tPath\n")
            # indent.write("this is an indented file with the number of generations driven by the parents\nid\tName\tYear\tWhere\tGPS\n") 
            humans = BackgroundProcess.humans
            # Create a dictionary from the lines array with xid as the key
            for h in humans:
                if self.gO.Referenced.exists(humans[h].xref_id):
                    refyear, _ = humans[h].refyear()
                    (location, where) = humans[h].bestlocation()
                    humanpath = self.gO.lastlines[humans[h].xref_id].path
                    trace.write(f"{humans[h].xref_id}\t{humans[h].name}\t{refyear}\t{where}\t{location}\t" + "\t".join(humanpath) + "\n") 
                    # indent.write("\t".join(humanpath) + f",{humans[h].xref_id}\t{humans[h].name}\t{refyear}\t{where}\t{location}\n") 
            trace.close()
            # indent.close()
            _log.info(f"Trace file saved {tracepath}")
            # _log.info(f"Indent file saved {indentpath}")
            BackgroundProcess.SayInfoMessage(f"Trace file saved: {tracepath}",True)

    def OpenBrowser(self):
        if self.gO.get('ResultHTML'):
            self.runCMDfile(self.gO.get('KMLcmdline'), os.path.join(self.gO.resultpath, self.gO.Result), True)
            
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



