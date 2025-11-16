import logging
import wx
import wx.lib.mixins.listctrl as listmix

_log = logging.getLogger(__name__.lower())

# InfoBoxLines constant used by the original implementation.
InfoBoxLines = 8

class PeopleListCtrlPanel(wx.Panel, listmix.ColumnSorterMixin):
    def __init__(self, parent, people, font_manager, *args, **kw):
        """Initializes the PeopleListCtrlPanel.

        Args:
            parent: The parent window.
            people: The list of people.
            font_manager: FontManager instance.
        """
        super().__init__(parent, *args, **kw)

        self.font_manager = font_manager
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.messagelog = "*  Select a file, Load it and Create Files or change Result Type, Open Geo Table to edit addresses  *"
        self.InfoBox = []
        # store the raw (unwrapped) text for each line so we can re-wrap when width changes
        self.InfoBoxRaw = [''] * InfoBoxLines
        for i in range(InfoBoxLines):
            st = wx.StaticText(self, -1, ' ')
            self.InfoBox.append(st)
            sizer.Add(st, 0, wx.EXPAND | wx.LEFT, 5)
        self.Bind(wx.EVT_SIZE, self._on_size_wrap_info)
        tID = wx.NewIdRef()
        # The PeopleListCtrl class is provided by the main package module; import lazily to avoid cycles
        try:
            from .people_list_ctrl import PeopleListCtrl  # type: ignore
        except Exception:
            try:
                from people_list_ctrl import PeopleListCtrl  # type: ignore
            except Exception:
                PeopleListCtrl = wx.ListCtrl

        self.list = PeopleListCtrl(self, tID,
                        style=wx.LC_REPORT | wx.BORDER_SUNKEN | wx.LC_SINGLE_SEL,
                        size=wx.Size(600,600),
                        font_manager=font_manager)
        sizer.Add(self.list, 1, wx.EXPAND)

        # Populate initial list
        try:
            self.list.PopulateList(people, None, True)
        except Exception:
            pass

        self.currentItem = 0
        self.SetSizer(sizer)
        wx.CallAfter(self._on_size_wrap_info, None)

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

    def SetGOp(self, gOp):
        self.gOp = gOp
        if getattr(self, "list", None):
            try:
                self.list.SetGOp(gOp)
            except Exception:
                _log.exception("PeopleListCtrlPanel.SetGOp failed")

    def _on_size_wrap_info(self, event):
        """ Handle resizing of the info box area to wrap text appropriately. """
        width = self.GetClientSize().width
        wrap_width = max(10, width - 12)
        # Use the raw text for wrapping so previous wrapped linebreaks are not preserved.
        for i, info in enumerate(getattr(self, "InfoBox", [])):
            try:
                raw = self.InfoBoxRaw[i] if i < len(self.InfoBoxRaw) else ''
                # set the unwrapped text then wrap to the current width
                info.SetLabel(raw)
                info.Wrap(wrap_width)
            except Exception:
                pass
        self.Layout()
        if event:
            event.Skip()

    def append_info_box(self, message):
        nlines = (message+'\n'+self.messagelog).split('\n')
        # update raw stored lines, then trigger wrapping to current width
        for i in range(InfoBoxLines):
            if i >= (len(nlines)):
                self.InfoBoxRaw[i] = ''
            else:
                self.InfoBoxRaw[i] = nlines[i]
        self.messagelog = '\n'.join(nlines[:InfoBoxLines])
        # reflow to current width on the GUI thread
        wx.CallAfter(self._on_size_wrap_info, None)

    def stop(self):
        visual_map_panel = self.get_visual_map_panel()
        if visual_map_panel:
            try:
                visual_map_panel.StopTimer()
            except Exception:
                _log.exception("PeopleListCtrlPanel.stop failed")