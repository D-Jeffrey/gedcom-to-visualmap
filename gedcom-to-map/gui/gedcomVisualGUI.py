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
import math
import os.path
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
from gedcom.gedcomdate import CheckAge 
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


from const import GUINAME, KMLMAPSURL, LOG_CONFIG, NAME, VERSION
from gedcomoptions import gvOptions, ResultsType 
from gui.visual_map_frame import VisualMapFrame
from gui.visual_map_panel import VisualMapPanel
from gui.gedcomvisual import doTrace
from gui.gedcomDialogs import *
from style.stylemanager import FontManager


_log = logging.getLogger(__name__.lower())


InfoBoxLines = 8

from wx.lib.embeddedimage import PyEmbeddedImage


# Use the moved VisualGedcomIds implementation
try:
    from .visual_gedcom_ids import VisualGedcomIds
except Exception:
    try:
        from visual_gedcom_ids import VisualGedcomIds
    except Exception:
        # Minimal fallback so module import still succeeds in degraded environments
        class VisualGedcomIds:
            def __init__(self):
                self.m = {}
                self.ids = []
                self.IDs = {}
            def GetColor(self, _name, default=wx.WHITE):
                return default
#=============================================================
class PeopleListCtrl(wx.ListCtrl, listmix.ListCtrlAutoWidthMixin, listmix.ColumnSorterMixin):
    def __init__(self, parent, ID, pos=wx.DefaultPosition,
                 size=wx.DefaultSize, style=0, name="PeopleList",
                 font_manager=None, *args, **kw):
        super().__init__(*args, **kw)
        wx.ListCtrl.__init__(self, parent, ID, pos, size, style)
        listmix.ListCtrlAutoWidthMixin.__init__(self)

        self.font_manager = font_manager

        self.id = VisualGedcomIds()
        self.active = False
        self.il = wx.ImageList(16, 16)
        self.sm_up = self.il.Add(self.id.SmallUpArrow.GetBitmap())
        self.sm_dn = self.il.Add(self.id.SmallDnArrow.GetBitmap())
        self.GridOnlyFamily = False
        self._LastGridOnlyFamily = self.GridOnlyFamily
        self.LastSearch = ""
        self.gOp = None

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
                vis = self.get_visual_map_panel()
                if vis and getattr(vis, "StopTimer", None):
                    try:
                        vis.StopTimer()
                    except Exception:
                        _log.exception("StopTimer call failed on visual_map_panel")
            self.gOp.running = wasrunning
            
        self.active = False

    def get_visual_map_panel(self):
        vis = getattr(self, 'visual_map_panel', None)
        if vis is None:
            ancestor = self.GetParent()
            while ancestor is not None:
                vis = getattr(ancestor, 'visual_map_panel', None)
                if vis is not None:
                    break
                ancestor = ancestor.GetParent()
        if vis is None:
            top = self.GetTopLevelParent()
            vis = getattr(top, 'visual_map_panel', None)
        return vis

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
        parent_win = self.get_visual_map_panel() or self.GetTopLevelParent()
        find_dialog = FindDialog(parent_win, "Find", LastSearch=self.LastSearch)
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
                parent_win = self.get_visual_map_panel() or self.GetTopLevelParent()
                dialog = PersonDialog(parent_win, self.gOp.BackgroundProcess.people[itm], parent_win, font_manager=self.font_manager, gOp=self.gOp)
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
                self.gOp.BackgroundProcess.updategridmain = self.gOp.people is not None
                vis = self.get_visual_map_panel()
                if vis and getattr(vis, "SetupButtonState", None):
                    vis.SetupButtonState()


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




# Use the moved PeopleListCtrlPanel implementation
try:
    from .people_list_ctrl_panel import PeopleListCtrlPanel
except Exception:
    try:
        from people_list_ctrl_panel import PeopleListCtrlPanel
    except Exception:
        # fallback stub to avoid import-time failure
        class PeopleListCtrlPanel(wx.Panel):
            def __init__(self, parent, people, font_manager, *args, **kw):
                super().__init__(parent, *args, **kw)
                wx.StaticText(self, -1, "PeopleListCtrlPanel unavailable")
#=============================================================
