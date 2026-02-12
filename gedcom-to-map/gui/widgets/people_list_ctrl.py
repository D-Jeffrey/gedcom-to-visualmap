import logging
import re
from typing import Optional
import wx
import wx.lib.mixins.listctrl as listmix

from ..dialogs.find_dialog import FindDialog
from ..layout.visual_gedcom_ids import VisualGedcomIds
from ..layout.font_manager import FontManager
from ..layout.colour_manager import ColourManager

_log = logging.getLogger(__name__.lower())

class PeopleListData:
    """Data container for a person entry in the people list."""
    
    def __init__(self) -> None:
        """Initialize empty PeopleListData."""
        self.name: str = ""
        self.year_description: str = ""
        self.id: str = ""
        self.geocode: str = ""
        self.address: str = ""
        self.year_value: int = 0
        
    @classmethod
    def from_dict(cls, data: dict):
        instance = cls()
        instance.name = data.get('name', "")
        instance.year_description = data.get('year_description', "")
        instance.id = data.get('id', "")
        instance.geocode = data.get('geocode', "")
        instance.address = data.get('address', "")
        instance.year_value = data.get('year_value', 0)
        return instance
        
class PeopleListCtrl(wx.ListCtrl, listmix.ListCtrlAutoWidthMixin, listmix.ColumnSorterMixin):
    def __init__(
        self,
        parent: wx.Window,
        ID: int,
        pos: wx.Point = wx.DefaultPosition,
        size: wx.Size = wx.DefaultSize,
        style: int = 0,
        name: str = "PeopleList",
        font_manager: Optional['FontManager'] = None,
        color_manager: Optional['ColourManager'] = None,
        svc_config = None,
        *args,
        **kw
    ) -> None:
        """Initialize the people list control.
        
        Args:
            parent: Parent wxPython window.
            ID: Control ID.
            pos: Position (default: wx.DefaultPosition).
            size: Size (default: wx.DefaultSize).
            style: wxListCtrl style flags (default: 0).
            name: Control name (default: "PeopleList").
            font_manager: FontManager for text styling (optional).
            color_manager: ColourManager for colour management (optional).
            svc_config: Config service instance for accessing configuration.
            *args: Additional arguments for base class.
            **kw: Additional keyword arguments for base class.
        """
        wx.ListCtrl.__init__(self, parent, ID, pos, size, style)
        listmix.ListCtrlAutoWidthMixin.__init__(self)

        self.font_manager: Optional['FontManager'] = font_manager
        self.color_manager: Optional['ColourManager'] = color_manager
        self.svc_config = svc_config

        self.id = VisualGedcomIds(svc_config=self.svc_config) if VisualGedcomIds else type("IdStub", (), {"GetColor": lambda *_a, **_k: wx.WHITE, "SmallUpArrow": None, "SmallDnArrow": None})()
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
        # Service-architecture references (optional)
        self.svc_config = None
        self.svc_state = None
        self.svc_progress = None
        
        # Track item color types for refresh_colors()
        # Maps list index to color type: 'MAINPERSON', 'ANCESTOR', 'OTHERPERSON', 'YELLOW', or None
        self._item_color_types: dict[int, str] = {}

        self.SetImageList(self.il, wx.IMAGE_LIST_SMALL)
        try:
            if self.color_manager:
                self.SetTextColour(self.color_manager.get_color('GRID_TEXT'))
                self.SetBackgroundColour(self.color_manager.get_color('GRID_BACK'))
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

        parent.Bind(wx.EVT_FIND, self.OnFind, self)
        self.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self.OnItemRightClick, self)
        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnItemActivated, self)
        self.Bind(wx.EVT_LIST_COL_RIGHT_CLICK, self.OnColRightClick, self)

    def SetServices(self, svc_config=None, svc_state=None, svc_progress=None):
        """Bind configuration/state/progress services for this control.

        This control relies solely on service-architecture objects.
        """
        # Prefer explicit services if provided
        if svc_config is not None:
            self.svc_config = svc_config
        if svc_state is not None:
            self.svc_state = svc_state
        if svc_progress is not None:
            self.svc_progress = svc_progress

    def refresh_colors(self):
        """Refresh list colors after appearance mode change."""
        if self.color_manager:
            try:
                self.SetTextColour(self.color_manager.get_color('GRID_TEXT'))
                self.SetBackgroundColour(self.color_manager.get_color('GRID_BACK'))
                
                # Refresh individual item background colors
                for item_index, color_type in self._item_color_types.items():
                    if item_index < self.GetItemCount():
                        if color_type == 'YELLOW':
                            # Keep yellow for age issues (doesn't change with theme)
                            self.SetItemBackgroundColour(item_index, wx.YELLOW)
                        elif color_type in ('MAINPERSON', 'ANCESTOR', 'OTHERPERSON'):
                            # Update themed colors
                            self.SetItemBackgroundColour(item_index, self.color_manager.get_color(color_type))
                
                self.Refresh()
            except Exception:
                _log.exception("Failed to refresh colors in PeopleListCtrl")

    

    def PopulateList(self, people, mainperson, loading):
        if self.active:
            return

        self.active = True

        # Determine running state and grid mode using services if available
        wasrunning = getattr(self.svc_progress, "running", False) if self.svc_progress is not None else False
        if self.svc_progress is not None:
            try:
                self.svc_progress.running = True
            except Exception:
                pass
        try:
            self.GridOnlyFamily = self.svc_config.get('GridView') if (self.svc_config is not None and hasattr(self.svc_config, 'get')) else False
        except Exception:
            self.GridOnlyFamily = False

        if loading:
            self.RemoveSortIndicator() if hasattr(self, "RemoveSortIndicator") else None
            self.popdata: dict[int, PeopleListData] = {}

        if loading or (self._LastGridOnlyFamily != self.GridOnlyFamily):
            self.DeleteAllItems()
            self.itemDataMap = {}
            self.itemIndexMap = []
            self._item_color_types = {}  # Clear color type tracking
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
                    person = people[h]
                    description, year_num = person.ref_year()
                    (location, where) = person.bestlocation()
                    self.popdata[index] = PeopleListData.from_dict({
                        'name': person.name,
                        'year_description': description,
                        'id': person.xref_id,
                        'geocode': location,
                        'address': where,
                        'year_value': year_num if year_num is not None else 0
                    })
                    index += 1

        if self.svc_state is not None:
            items = self.popdata.items()
            try:
                self.svc_state.selectedpeople = 0
            except Exception:
                pass
            if not wasrunning:
                try:
                    if self.svc_progress is not None and hasattr(self.svc_progress, "step"):
                        self.svc_progress.step("Gridload", resetCounter=False, target=len(items))
                except Exception:
                    pass
            self.itemDataMap = {idx: pdata for idx, pdata in items}
            index = -1
            for key, pdata in items:
                try:
                    if self.svc_progress is not None:
                        self.svc_progress.counter = key
                except Exception:
                    pass
                if key % 2048 == 0:
                    wx.Yield()

                if self.GridOnlyFamily and getattr(self.svc_state, "Referenced", None):
                    ref = getattr(self.svc_state, "Referenced", None)
                    DisplayItem = ref.exists(pdata.id)
                else:
                    DisplayItem = True

                if DisplayItem:
                    if loading:
                        index = self.InsertItem(self.GetItemCount(), pdata.name, -1)
                        self.SetItem(index, 1, str(pdata.year_description))
                        self.SetItem(index, 2, pdata.id)
                        self.SetItem(index, 3, pdata.geocode)
                        self.SetItem(index, 4, pdata.address)
                        self.SetItemData(index, key)
                        if mainperson == pdata.id:
                            selectperson = index
                    else:
                        index += 1
                        if mainperson == self.GetItem(index, 2):
                            selectperson = index

                    ref = getattr(self.svc_state, "Referenced", None)
                    if ref is not None:
                        try:
                            if ref.exists(pdata.id):
                                if hasattr(self.svc_state, "selectedpeople"):
                                    self.svc_state.selectedpeople = getattr(self.svc_state, "selectedpeople", 0) + 1
                                if mainperson == pdata.id:
                                    if self.color_manager:
                                        self.SetItemBackgroundColour(index, self.color_manager.get_color('MAINPERSON'))
                                        self._item_color_types[index] = 'MAINPERSON'
                                else:
                                    person = people.get(pdata.id, None)
                                    issues = person.check_age_problems(people) if person else None
                                    if issues:
                                        self.SetItemBackgroundColour(index, wx.YELLOW)
                                        self._item_color_types[index] = 'YELLOW'
                                    else:
                                        if self.color_manager:
                                            self.SetItemBackgroundColour(index, self.color_manager.get_color('ANCESTOR'))
                                            self._item_color_types[index] = 'ANCESTOR'
                            else:
                                if self.color_manager:
                                    self.SetItemBackgroundColour(index, self.color_manager.get_color('OTHERPERSON'))
                                    self._item_color_types[index] = 'OTHERPERSON'
                        except Exception:
                            pass
            try:
                if self.svc_progress is not None:
                    self.svc_progress.counter = 0
                    self.svc_progress.state = ""
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

        if (self.svc_progress is not None and getattr(self.svc_progress, "running", False)):
            if not wasrunning:
                vis = self.get_visual_map_panel()
                if vis and getattr(vis, "UpdateTimer", None):
                    try:
                        vis.UpdateTimer()
                    except Exception:
                        _log.exception("UpdateTimer call failed on visual_map_panel")
            try:
                if self.svc_progress is not None:
                    self.svc_progress.running = wasrunning
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

    def GetColumnSorter(self):
        (col, ascending) = self.GetSortState()
        idsort = False
        if col == 2:
            checkid = self.popdata[1].id
            idsort = checkid.startswith("@I") and checkid.endswith("@")

        def cmp_func(item1, item2):
            person1 = self.popdata[item1]
            person2 = self.popdata[item2]
            if col == 1:
                year1 = person1.year_value
                year2 = person2.year_value
                return (year1 - year2) if ascending else (year2 - year1)
            elif col == 2 and idsort:
                # Assuming IDs are like "@I123@", extract the number
                data1 = int(person1.id[2:-1])
                data2 = int(person2.id[2:-1])
            else:
                # Map column index to attribute
                col_map = {0: "name", 1: "year_description", 2: "id", 3: "geocode", 4: "address"}
                attr = col_map.get(col, "name")
                data1 = getattr(person1, attr)
                data2 = getattr(person2, attr)
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
            self._say_info(f"* Could not find '{self.LastSearch}' in the names")

    def OnItemRightClick(self, event):
        self.currentItem = event.Index
        event.Skip()
        try:
            # Prefer service state people; fallback to panel.background_process.people
            people_src = None
            if self.svc_state is not None and getattr(self.svc_state, "people", None):
                people_src = self.svc_state.people
            else:
                vis = self.get_visual_map_panel()
                bp = getattr(vis, 'background_process', None) if vis is not None else None
                if bp is not None and getattr(bp, 'people', None):
                    people_src = bp.people

            if people_src:
                itm = self.GetItemText(self.currentItem, 2)
                if itm in people_src:
                    # Lazy import to avoid circular dependency
                    from ..dialogs.person_dialog import PersonDialog
                    parent_win = self.get_visual_map_panel() or self.GetTopLevelParent()
                    dialog = PersonDialog(
                        parent_win,
                        people_src[itm],
                        parent_win,
                        font_manager=self.font_manager,
                        svc_config=self.svc_config,
                        svc_state=self.svc_state,
                        svc_progress=self.svc_progress,
                    )
                    dialog.Bind(wx.EVT_CLOSE, lambda evt: dialog.Destroy())
                    dialog.Bind(wx.EVT_BUTTON, lambda evt: dialog.Destroy())
                    dialog.Show(True)
        except Exception:
            _log.exception("OnItemRightClick failed")

    def OnItemActivated(self, event):
        self.currentItem = event.Index
        self.ShowSelectedLinage(self.GetItemText(self.currentItem, 2))

    def ShowSelectedLinage(self, personid: str):
        # Set the main person via service config only
        try:
            if self.svc_config is not None and hasattr(self.svc_config, "set"):
                self.svc_config.set('Main', personid)
        except Exception:
            pass

        # Actions require access to panel and BackgroundProcess (via panel)
        vis = self.get_visual_map_panel()
        panel_actions = getattr(vis, "actions", None) if vis is not None else None
        vis = self.get_visual_map_panel()
        bp = getattr(vis, 'background_process', None) if vis is not None else None
        if getattr(bp, "updategridmain", False):
            _log.debug("Linage for: %s", personid)
            try:
                bp.updategridmain = False
            except Exception:
                pass
            if panel_actions and getattr(panel_actions, "doTrace", None):
                # Use service-architecture objects for lineage trace
                cfg = self.svc_config
                st = self.svc_state
                pr = self.svc_progress
                if cfg is not None and st is not None and pr is not None:
                    panel_actions.doTrace(cfg, st, pr)
                else:
                    _log.warning("ShowSelectedLinage: missing services; cannot perform trace")
            # mark newload using service state if present
            try:
                if self.svc_state is not None:
                    self.svc_state.newload = False
            except Exception:
                pass

            # refresh list using service state and config when available
            try:
                main_id = self.svc_config.get('Main') if self.svc_config is not None else None
            except Exception:
                main_id = None
            people_ref = self.svc_state.people if self.svc_state is not None else None
            self.PopulateList(people_ref, main_id, False)

            # Inform user using helper method and prefer service Referenced count
            ref = getattr(self.svc_state, 'Referenced', None) if self.svc_state is not None else None
            count = len(ref) if ref is not None else 0
            self._say_info(f"Using '{personid}' as starting person with {count} direct ancestors")

            people_non_null = (self.svc_state.people is not None) if self.svc_state is not None else False
            try:
                if bp is not None:
                    bp.updategridmain = people_non_null
            except Exception:
                pass
            vis = self.get_visual_map_panel()
            if vis and getattr(vis, "SetupButtonState", None):
                vis.SetupButtonState()

    def OnColClick(self, event):
        event.Skip()

    def OnColRightClick(self, event):
        event.Skip()

    def _say_info(self, message: str) -> None:
        """UI messaging helper.

        Prefer VisualMapPanel.background_process.SayInfoMessage (service-era UI hook).
        If unavailable, log the message.
        """
        try:
            vis = self.get_visual_map_panel()
            bg = getattr(vis, 'background_process', None) if vis is not None else None
            if bg is not None and hasattr(bg, 'SayInfoMessage'):
                bg.SayInfoMessage(message, False)
            else:
                _log.info(message)
        except Exception:
            _log.info(message)
