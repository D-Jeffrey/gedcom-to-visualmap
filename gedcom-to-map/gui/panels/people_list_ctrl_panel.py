"""people_list_ctrl_panel.py

Contains PeopleListCtrlPanel, a composite wx.Panel that hosts the people list
control and a small multiline info box used to show messages/status to the user.

Responsibilities:
- Create and manage the PeopleListCtrl instance.
- Maintain a fixed number of StaticText lines for informational messages and
  re-wrap them when the panel resizes.
- Provide a thin adapter to locate the owning VisualMapPanel and to propagate
  services to the inner list control.
"""

import logging
from typing import Any, Dict, Union
import wx
import wx.lib.mixins.listctrl as listmix
from ..widgets.people_list_ctrl import PeopleListCtrl
from ..layout.font_manager import FontManager
from ..layout.colour_manager import ColourManager
from geo_gedcom.person import Person

_log = logging.getLogger(__name__.lower())


class PeopleListCtrlPanel(wx.Panel, listmix.ColumnSorterMixin):
    """Panel containing the people list and an information box.

    The info box is implemented as a fixed number of wx.StaticText lines whose
    raw text is kept in InfoBoxRaw so lines can be re-wrapped to the current
    width whenever the panel resizes.
    """

    def __init__(
        self,
        parent: wx.Window,
        people: Union[Dict[str, Person], Any],
        font_manager: FontManager,
        color_manager: ColourManager,
        svc_config: Any = None,
        svc_state: Any = None,
        svc_progress: Any = None,
        *args,
        **kw
    ):
        """Initialize the PeopleListCtrlPanel.

        Args:
            parent: Parent wx window.
            people: Iterable of people to populate the initial list.
            font_manager: FontManager instance used by the PeopleListCtrl.
            color_manager: ColourManager instance used by the PeopleListCtrl.
            svc_config: IConfig service for configuration storage.
            svc_state: IState service for runtime state access.
            svc_progress: IProgressTracker service for progress and control.
        """
        super().__init__(parent, *args, **kw)

        self.svc_config = svc_config
        self.svc_state = svc_state
        self.svc_progress = svc_progress
        self.font_manager = font_manager
        self.color_manager = color_manager
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.messagelog = (
            "*  Select a file, Load it and Create Files or change Result Type, Open Geo Table to edit addresses  *"
        )
        self.InfoBox = []
        # dedicated sizer for the info box lines to support dynamic rebuilds
        self.info_sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.info_sizer, 0, wx.EXPAND)
        # store the raw (unwrapped) text for each line so we can re-wrap when width changes
        init_lines = self.svc_config.get("infoBoxLines", 5) if self.svc_config else 5
        self.InfoBoxRaw = [""] * init_lines
        for i in range(init_lines):
            st = wx.StaticText(self, -1, " ")
            self.InfoBox.append(st)
            self.info_sizer.Add(st, 0, wx.EXPAND | wx.LEFT, 5)
        self._update_info_box_colors()
        self.Bind(wx.EVT_SIZE, self._on_size_wrap_info)
        tID = wx.NewIdRef()

        self._header_titles = ["Name", "Year", "ID", "Geocode", "Address"]
        self.header_panel = wx.Panel(self, style=wx.SIMPLE_BORDER)
        self.header_labels: list[wx.StaticText] = []
        self.header_sizer = wx.BoxSizer(wx.HORIZONTAL)
        for title in self._header_titles:
            lbl = wx.StaticText(self.header_panel, label=title)
            self.header_labels.append(lbl)
            self.header_sizer.Add(lbl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 3)
        self.header_panel.SetSizer(self.header_sizer)
        self._update_custom_header_colors()
        sizer.Add(self.header_panel, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 0)

        self.list = PeopleListCtrl(
            self,
            tID,
            style=wx.LC_REPORT | wx.BORDER_SUNKEN | wx.LC_SINGLE_SEL | wx.LC_NO_HEADER,
            size=wx.Size(600, 600),
            font_manager=font_manager,
            color_manager=color_manager,
            svc_config=svc_config,
        )
        sizer.Add(self.list, 1, wx.EXPAND)

        # Populate initial list
        try:
            self.list.PopulateList(people, None, True)
        except Exception:
            pass

        self.currentItem = 0
        self.SetSizer(sizer)
        wx.CallAfter(self._on_size_wrap_info, None)
        wx.CallAfter(self.sync_custom_header_widths)

    def get_visual_map_panel(self):
        """Find and return the enclosing VisualMapPanel instance.

        Walks up the parent chain and finally checks the top-level parent.
        Returns:
            The found VisualMapPanel instance, or None if not found.
        """
        vis = getattr(self, "visual_map_panel", None)
        if vis is None:
            ancestor = self.GetParent()
            while ancestor is not None:
                vis = getattr(ancestor, "visual_map_panel", None)
                if vis is not None:
                    break
                ancestor = ancestor.GetParent()
        if vis is None:
            top = self.GetTopLevelParent()
            vis = getattr(top, "visual_map_panel", None)
        return vis

    def SetServices(self, svc_config=None, svc_state=None, svc_progress=None):
        """Attach service-architecture objects to this panel and propagate to the list.

        Args:
            svc_config/state/progress: Service-architecture objects (optional).
        """
        # retain services locally for UI preferences (e.g., InfoBoxLines)
        if svc_config is not None:
            self.svc_config = svc_config
        if svc_state is not None:
            self.svc_state = svc_state
        if svc_progress is not None:
            self.svc_progress = svc_progress

        if getattr(self, "list", None):
            try:
                self.list.SetServices(svc_config=svc_config, svc_state=svc_state, svc_progress=svc_progress)
            except Exception:
                _log.exception("PeopleListCtrlPanel.SetServices failed")

        # After services attach, prefer svc_config for info box line count and rebuild if needed
        try:
            new_lines = self._get_info_box_lines()
            if new_lines != len(self.InfoBox):
                # preserve existing raw text up to the new size
                preserved = (self.InfoBoxRaw + [""] * new_lines)[:new_lines]
                # clear existing controls
                try:
                    self.info_sizer.Clear(delete_windows=True)
                except Exception:
                    pass
                self.InfoBox = []
                self.InfoBoxRaw = preserved
                for i in range(new_lines):
                    st = wx.StaticText(self, -1, " ")
                    self.InfoBox.append(st)
                    self.info_sizer.Add(st, 0, wx.EXPAND | wx.LEFT, 5)
                self._update_info_box_colors()
                self.Layout()
                wx.CallAfter(self._on_size_wrap_info, None)
        except Exception:
            pass

    def _update_info_box_colors(self) -> None:
        """Apply configured colors to the top-left info text area."""
        if not self.color_manager:
            return
        try:
            if self.color_manager.has_color("INFO_BOX_BACKGROUND"):
                back = self.color_manager.get_color("INFO_BOX_BACKGROUND")
                self.SetBackgroundColour(back)
                for info in self.InfoBox:
                    info.SetBackgroundColour(back)
            if self.color_manager.has_color("DIALOG_TEXT"):
                text = self.color_manager.get_color("DIALOG_TEXT")
                self.SetForegroundColour(text)
                for info in self.InfoBox:
                    info.SetForegroundColour(text)
            self.Refresh()
        except Exception:
            _log.debug("_update_info_box_colors failed", exc_info=True)

    def _get_info_box_lines(self) -> int:
        """Resolve the info box line count.

        Prefer `svc_config` key 'InfoBoxLines' (or 'infoBoxLines'); default 5.
        """
        # try service config
        try:
            if getattr(self, "svc_config", None) is not None:
                get = getattr(self.svc_config, "get", None)
                if callable(get):
                    val = get("InfoBoxLines")
                    if val is None:
                        val = get("infoBoxLines")
                    if isinstance(val, int) and val > 0:
                        return val
        except Exception:
            pass
        return 5

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
                raw = self.InfoBoxRaw[i] if i < len(self.InfoBoxRaw) else ""
                # set the unwrapped text then wrap to the current width
                info.SetLabel(raw)
                info.Wrap(wrap_width)
            except Exception:
                pass
        self.Layout()
        self.sync_custom_header_widths()
        if event:
            event.Skip()

    def sync_custom_header_widths(self) -> None:
        """Keep custom header label widths aligned with list column widths."""
        if not hasattr(self, "list") or not self.list or not getattr(self, "header_labels", None):
            return
        try:
            for i, lbl in enumerate(self.header_labels):
                width = self.list.GetColumnWidth(i)
                if width <= 0:
                    continue
                lbl.SetMinSize((width, -1))
                lbl.SetMaxSize((width, -1))
            self.header_panel.Layout()
        except Exception:
            _log.debug("sync_custom_header_widths failed", exc_info=True)

    def _update_custom_header_colors(self) -> None:
        """Apply GRID colors to custom header background and text."""
        if not self.color_manager:
            return
        try:
            back_name = "GRID_HEADER_BACK" if self.color_manager.has_color("GRID_HEADER_BACK") else "GRID_BACK"
            text_name = "GRID_HEADER_TEXT" if self.color_manager.has_color("GRID_HEADER_TEXT") else "GRID_TEXT"
            back = self.color_manager.get_color(back_name)
            text = self.color_manager.get_color(text_name)
            self.header_panel.SetBackgroundColour(back)
            self.header_panel.SetForegroundColour(text)
            for lbl in self.header_labels:
                lbl.SetBackgroundColour(back)
                lbl.SetForegroundColour(text)
            self.header_panel.Refresh()
        except Exception:
            _log.debug("_update_custom_header_colors failed", exc_info=True)

    def append_info_box(self, message):
        """Append a message to the info box and reflow the visible lines.

        The message is combined with the previous message log, truncated to the
        configured infoBoxLines count, stored in InfoBoxRaw and then reflowed on
        the GUI thread (via CallAfter) so it respects current widths.

        Args:
            message: Multi-line string to prepend to the info log.
        """
        nlines = (message + "\n" + self.messagelog).split("\n")
        # update raw stored lines, then trigger wrapping to current width
        for i in range(len(self.InfoBox)):
            if i >= (len(nlines)):
                self.InfoBoxRaw[i] = ""
            else:
                self.InfoBoxRaw[i] = nlines[i]
        self.messagelog = "\n".join(nlines[: len(self.InfoBox)])
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

    def refresh_colors(self):
        """Refresh colors in the people list control after appearance mode change."""
        self._update_info_box_colors()
        self._update_custom_header_colors()
        self.sync_custom_header_widths()
        if hasattr(self, "list") and self.list:
            try:
                self.list.refresh_colors()
            except Exception:
                _log.exception("PeopleListCtrlPanel.refresh_colors failed")
