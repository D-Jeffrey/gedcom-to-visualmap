"""people_list_ctrl_panel.py

Contains PeopleListCtrlPanel, a composite wx.Panel that hosts the people list
control and a small multiline info box used to show messages/status to the user.

Responsibilities:
- Create and manage the PeopleListCtrl instance.
- Maintain a fixed number of StaticText lines for informational messages and
  re-wrap them when the panel resizes.
- Provide a thin adapter to locate the owning VisualMapPanel and to propagate
  gvOptions (gOp) to the inner list control.
"""
import logging
from typing import Any, Dict, Union
import wx
import wx.lib.mixins.listctrl as listmix
from .people_list_ctrl import PeopleListCtrl
from .font_manager import FontManager
from geo_gedcom.person import Person
from gedcom_options import gvOptions

_log = logging.getLogger(__name__.lower())

class PeopleListCtrlPanel(wx.Panel, listmix.ColumnSorterMixin):
    """Panel containing the people list and an information box.

    The info box is implemented as a fixed number of wx.StaticText lines whose
    raw text is kept in InfoBoxRaw so lines can be re-wrapped to the current
    width whenever the panel resizes.
    """

    def __init__(self, parent: wx.Window, people: Union[Dict[str, Person], Any], font_manager: FontManager, gOp=gvOptions, *args, **kw):
        """Initialize the PeopleListCtrlPanel.

        Args:
            parent: Parent wx window.
            people: Iterable of people to populate the initial list.
            font_manager: FontManager instance used by the PeopleListCtrl.
        """
        super().__init__(parent, *args, **kw)

        self.gOp = gOp
        self.font_manager = font_manager
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.messagelog = "*  Select a file, Load it and Create Files or change Result Type, Open Geo Table to edit addresses  *"
        self.InfoBox = []
        # store the raw (unwrapped) text for each line so we can re-wrap when width changes
        self.InfoBoxRaw = [''] * self.gOp.infoBoxLines
        for i in range(self.gOp.infoBoxLines):
            st = wx.StaticText(self, -1, ' ')
            self.InfoBox.append(st)
            sizer.Add(st, 0, wx.EXPAND | wx.LEFT, 5)
        self.Bind(wx.EVT_SIZE, self._on_size_wrap_info)
        tID = wx.NewIdRef()

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
        """Find and return the enclosing VisualMapPanel instance.

        Walks up the parent chain and finally checks the top-level parent.
        Returns:
            The found VisualMapPanel instance, or None if not found.
        """
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
        """Attach gvOptions (gOp) to this panel and propagate it to the inner list.

        Args:
            gOp: The options/state object used by the application.
        """
        self.gOp = gOp
        if getattr(self, "list", None):
            try:
                self.list.SetGOp(gOp)
            except Exception:
                _log.exception("PeopleListCtrlPanel.SetGOp failed")

    def _on_size_wrap_info(self, event):
        """Re-wrap info-box lines when the panel is resized.

        Uses the stored InfoBoxRaw lines to avoid re-wrapping already wrapped
        text. After updating each StaticText's label it calls Wrap(width) to
        perform line-breaking appropriate for the current client width.
        """
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
        """Append a message to the info box and reflow the visible lines.

        The message is combined with the previous message log, truncated to the
        configured infoBoxLines count, stored in InfoBoxRaw and then reflowed on
        the GUI thread (via CallAfter) so it respects current widths.

        Args:
            message: Multi-line string to prepend to the info log.
        """
        nlines = (message+'\n'+self.messagelog).split('\n')
        # update raw stored lines, then trigger wrapping to current width
        for i in range(self.gOp.infoBoxLines):
            if i >= (len(nlines)):
                self.InfoBoxRaw[i] = ''
            else:
                self.InfoBoxRaw[i] = nlines[i]
        self.messagelog = '\n'.join(nlines[:self.gOp.infoBoxLines])
        # reflow to current width on the GUI thread
        wx.CallAfter(self._on_size_wrap_info, None)

    def stop(self):
        """Called when the surrounding UI is shutting down.

        Attempts to notify the visual_map_panel to update its timer state.
        This is a best-effort helper used during teardown.
        """
        visual_map_panel = self.get_visual_map_panel()
        if visual_map_panel:
            try:
                visual_map_panel.UpdateTimer()
            except Exception:
                _log.exception("PeopleListCtrlPanel.stop failed")
