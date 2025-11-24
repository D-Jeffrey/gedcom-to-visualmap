import logging
import re
import wx
import wx.lib.mixins.listctrl as listmix

from gedcom.gedcomdate import CheckAge
from .person_dialog import PersonDialog
from .find_dialog import FindDialog
from .visual_gedcom_ids import VisualGedcomIds
from style.stylemanager import FontManager

_log = logging.getLogger(__name__.lower())

class PeopleListCtrl(wx.ListCtrl, listmix.ListCtrlAutoWidthMixin, listmix.ColumnSorterMixin):
    def __init__(self, parent, ID, pos=wx.DefaultPosition,
                 size=wx.DefaultSize, style=0, name="PeopleList",
                 font_manager=None, *args, **kw):
        wx.ListCtrl.__init__(self, parent, ID, pos, size, style)
        listmix.ListCtrlAutoWidthMixin.__init__(self)

        self.font_manager = font_manager

        self.id = VisualGedcomIds() if VisualGedcomIds else type("IdStub", (), {"GetColor": lambda *_a, **_k: wx.WHITE, "SmallUpArrow": None, "SmallDnArrow": None})()
        self.active = False
        self.il = wx.ImageList(16, 16)
        try:
            if getattr(self.id, "SmallUpArrow", None):
                self.sm_up = self.il.Add(self.id.SmallUpArrow.GetBitmap())
            else:
                self.sm_up = -1
            if getattr(self.id, "SmallDnArrow", None):
                self.sm_dn = self.il.Add(self.id.SmallDnArrow.GetBitmap())
            else:
                self.sm_dn = -1
        except Exception:
            self.sm_up = self.sm_dn = -1

        self.GridOnlyFamily = False
        self._LastGridOnlyFamily = self.GridOnlyFamily
        self.LastSearch = ""
        self.gOp = None

        self.SetImageList(self.il, wx.IMAGE_LIST_SMALL)
        try:
            self.SetTextColour(self.id.GetColor('GRID_TEXT'))
            self.SetBackgroundColour(self.id.GetColor('GRID_BACK'))
        except Exception:
            pass

        # columns
        self.InsertColumn(0, "Name")
        self.InsertColumn(1, "Year", wx.LIST_FORMAT_RIGHT)
        self.InsertColumn(2, "ID")
        self.InsertColumn(3, "Geocode")
        self.InsertColumn(4, "Address")
        self.SetImageList(self.il, wx.IMAGE_LIST_SMALL)
        listmix.ColumnSorterMixin.__init__(self, 5)

        self.itemDataMap = {}
        self.itemIndexMap = []
        self.patterns = [
            re.compile(r'(\d{1,6}) (B\.?C\.?)'),
            re.compile(r'(\d{1,4})')
        ]

        parent.Bind(wx.EVT_FIND, self.OnFind, self)
        self.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self.OnItemRightClick, self)
        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnItemActivated, self)
        self.Bind(wx.EVT_LIST_COL_RIGHT_CLICK, self.OnColRightClick, self)

    def SetGOp(self, gOp):
        self.gOp = gOp

    def PopulateList(self, people, mainperson, loading):
        if self.active:
            return

        self.active = True

        if self.gOp:
            wasrunning = getattr(self.gOp, "running", False)
            setattr(self.gOp, "running", True)
            self.GridOnlyFamily = self.gOp.get('GridView') if hasattr(self.gOp, "get") else False
        else:
            wasrunning = False

        if loading:
            self.RemoveSortIndicator() if hasattr(self, "RemoveSortIndicator") else None
            self.popdata = {}

        if loading or (self._LastGridOnlyFamily != self.GridOnlyFamily):
            self.DeleteAllItems()
            self.itemDataMap = {}
            self.itemIndexMap = []
            loading = True
            self._LastGridOnlyFamily = self.GridOnlyFamily

        selectperson = 0
        if not people:
            self.active = False
            return

        if loading:
            index = 0
            for h in people:
                if hasattr(people[h], 'name'):
                    d, y = people[h].refyear()
                    (location, where) = people[h].bestlocation()
                    self.popdata[index] = (people[h].name, d, people[h].xref_id, location, where, self.ParseDate(y))
                    index += 1

        if self.gOp:
            items = self.popdata.items()
            self.gOp.selectedpeople = 0
            if not wasrunning and hasattr(self.gOp, "step"):
                try:
                    self.gOp.step("Gridload", resetCounter=False, target=len(items))
                except Exception:
                    pass
            self.itemDataMap = {data[0]: data for data in items}
            index = -1
            for key, data in items:
                try:
                    self.gOp.counter = key
                except Exception:
                    pass
                if key % 2048 == 0:
                    wx.Yield()

                if self.GridOnlyFamily and getattr(self.gOp, "Referenced", None):
                    DisplayItem = self.gOp.Referenced.exists(data[2])
                else:
                    DisplayItem = True

                if DisplayItem:
                    if loading:
                        index = self.InsertItem(self.GetItemCount(), data[0], -1)
                        self.SetItem(index, 1, data[1])
                        self.SetItem(index, 2, data[2])
                        self.SetItem(index, 3, data[3])
                        self.SetItem(index, 4, data[4])
                        self.SetItemData(index, key)
                        if mainperson == data[2]:
                            selectperson = index
                    else:
                        index += 1
                        if mainperson == self.GetItem(index, 2):
                            selectperson = index

                    if getattr(self.gOp, "Referenced", None):
                        try:
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
                        except Exception:
                            pass
            try:
                self.gOp.counter = 0
                self.gOp.state = ""
            except Exception:
                pass

        self.SetColumnWidth(1, 112)
        self.SetColumnWidth(2, 85)
        self.SetColumnWidth(3, 220)
        self.SetColumnWidth(4, 375)
        self.SetColumnWidth(0, wx.LIST_AUTOSIZE_USEHEADER)
        if self.GetColumnWidth(0) > 300:
            self.SetColumnWidth(0, 300)

        if 0 <= selectperson < self.GetItemCount():
            self.SetItemState(selectperson, wx.LIST_STATE_SELECTED, wx.LIST_STATE_SELECTED)

        if mainperson and selectperson > 0 and loading:
            self.EnsureVisible(selectperson)
        wx.Yield()

        if self.gOp and getattr(self.gOp, "running", False):
            if not wasrunning:
                vis = self.get_visual_map_panel()
                if vis and getattr(vis, "UpdateTimer", None):
                    try:
                        vis.UpdateTimer()
                    except Exception:
                        _log.exception("UpdateTimer call failed on visual_map_panel")
            try:
                self.gOp.running = wasrunning
            except Exception:
                pass

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

    def ParseDate(self, datestring):
        if datestring is None:
            return 0
        for pattern in self.patterns:
            match = pattern.search(str(datestring))
            if match:
                if pattern == self.patterns[0]:
                    return -int(match.group(1))
                else:
                    return int(match.group(1))
        return 0

    def GetColumnSorter(self):
        (col, ascending) = self.GetSortState()
        idsort = False
        if col == 2:
            checkid = self.popdata[1][2]
            idsort = checkid[0:2] == "@I" and checkid[-1] == "@"

        def cmp_func(item1, item2):
            if col == 1:
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

    def GetSortImages(self):
        return (self.sm_dn, self.sm_up)

    def GetListCtrl(self):
        return self

    def OnFind(self, event):
        parent_win = self.get_visual_map_panel() or self.GetTopLevelParent()
        find_dialog = FindDialog(parent_win, font_manager=self.font_manager, title ="Find", LastSearch=self.LastSearch)
        if find_dialog.ShowModal() == wx.ID_OK:
            self.LastSearch = find_dialog.GetSearchString()
            if self.GetItemCount() > 1:
                findperson = self.LastSearch.lower()
                for checknames in range(self.GetFirstSelected()+1, self.GetItemCount()):
                    if findperson in self.GetItemText(checknames, 0).lower():
                        self.SetItemState(checknames, wx.LIST_STATE_SELECTED, wx.LIST_STATE_SELECTED)
                        self.EnsureVisible(checknames)
                        return
            try:
                self.gOp.BackgroundProcess.SayInfoMessage(f"* Could not find '{self.LastSearch}' in the names", False)
            except Exception:
                pass

    def OnItemRightClick(self, event):
        self.currentItem = event.Index
        event.Skip()
        try:
            if getattr(self.gOp.BackgroundProcess, "people", None):
                itm = self.GetItemText(self.currentItem, 2)
                if itm in self.gOp.BackgroundProcess.people:
                    parent_win = self.get_visual_map_panel() or self.GetTopLevelParent()
                    dialog = PersonDialog(parent_win, self.gOp.BackgroundProcess.people[itm], parent_win, font_manager=self.font_manager, gOp=self.gOp)
                    dialog.Bind(wx.EVT_CLOSE, lambda evt: dialog.Destroy())
                    dialog.Bind(wx.EVT_BUTTON, lambda evt: dialog.Destroy())
                    dialog.Show(True)
        except Exception:
            _log.exception("OnItemRightClick failed")

    def OnItemActivated(self, event):
        self.currentItem = event.Index
        self.ShowSelectedLinage(self.GetItemText(self.currentItem, 2))

    def ShowSelectedLinage(self, personid: str):
        if self.gOp:
            self.gOp.setMain(personid)
            panel_actions = getattr(getattr(self.gOp, "panel", None), "actions", None)
            if getattr(self.gOp.BackgroundProcess, "updategridmain", False):
                _log.debug("Linage for: %s", personid)
                self.gOp.BackgroundProcess.updategridmain = False
                if panel_actions and getattr(panel_actions, "doTrace", None):
                    panel_actions.doTrace(self.gOp)
                self.gOp.newload = False
                self.PopulateList(self.gOp.people, self.gOp.get('Main'), False)
                try:
                    self.gOp.BackgroundProcess.SayInfoMessage(f"Using '{personid}' as starting person with {len(self.gOp.Referenced)} direct ancestors", False)
                except Exception:
                    pass
                self.gOp.BackgroundProcess.updategridmain = self.gOp.people is not None
                vis = self.get_visual_map_panel()
                if vis and getattr(vis, "SetupButtonState", None):
                    vis.SetupButtonState()

    def OnColClick(self, event):
        event.Skip()

    def OnColRightClick(self, event):
        event.Skip()