import wx
import wx.lib.scrolledpanel as scrolled
from pathlib import Path
import logging
from typing import Any, List, Optional, Set, Tuple, Union
from ged4py.parser import GedcomReader

_log = logging.getLogger(__name__)

class GedRecordDialog(wx.Frame):
    """
    A dialog for displaying a flattened view of a GEDCOM record using wxPython.
    """

    def __init__(self, parent: Optional[wx.Window], record: Any, title: Optional[str] = None):
        """
        Initialize the dialog.

        Args:
            parent (wx.Window or None): The parent window.
            record (Any): The GEDCOM record to display.
            title (str, optional): The window title.
        """
        title = title or f"GED Record: {getattr(record, 'xref_id', getattr(record, 'tag', record.__class__.__name__))}"
        super().__init__(parent, title=title, size=(800, 600))

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        panel = scrolled.ScrolledPanel(self, -1)
        panel.SetupScrolling(scroll_x=False, scroll_y=True)
        pnl_sizer = wx.BoxSizer(wx.VERTICAL)

        self.list = wx.ListCtrl(panel, style=wx.LC_REPORT | wx.BORDER_SUNKEN | wx.LC_HRULES | wx.LC_VRULES)
        self.list.InsertColumn(0, "Field path")
        self.list.InsertColumn(1, "Value")

        flattened = self._flatten_ged_record(record) if record is not None else []
        flattened.sort(key=lambda x: x[0].lower())

        for path, val in flattened:
            if val and not path.endswith(".parser") and not path.endswith(".level"):
                idx = self.list.InsertItem(self.list.GetItemCount(), path.replace('INDI.',''))
                single_line_val = str(val).replace("\r", " ").replace("\n", " ")
                self.list.SetItem(idx, 1, single_line_val)

        self.list.SetColumnWidth(0, wx.COL_WIDTH_AUTOSIZE)
        full_width = self.GetSize()[0] - self.list.GetColumnWidth(0) - 40
        if full_width < 150:
            full_width = 300
        self.list.SetColumnWidth(1, full_width)

        pnl_sizer.Add(self.list, 1, wx.EXPAND | wx.ALL, 6)

        # Bottom row: copy button and close
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        copy_btn = wx.Button(panel, label="Copy selected value")
        copy_btn.Bind(wx.EVT_BUTTON, self.on_copy_selected)
        btn_sizer.Add(copy_btn, 0, wx.RIGHT, 6)

        close_btn = wx.Button(panel, label="Close")
        close_btn.Bind(wx.EVT_BUTTON, lambda evt: self.Close())
        btn_sizer.Add(close_btn, 0)

        pnl_sizer.Add(btn_sizer, 0, wx.ALIGN_RIGHT | wx.RIGHT | wx.BOTTOM, 8)

        panel.SetSizer(pnl_sizer)
        main_sizer.Add(panel, 1, wx.EXPAND)
        self.SetSizer(main_sizer)

        # Keyboard shortcut for copy
        accel_tbl = wx.AcceleratorTable([(wx.ACCEL_CTRL, ord('C'), copy_btn.GetId())])
        self.SetAcceleratorTable(accel_tbl)

        # Center and show
        self.Centre()
        self.Show()

    def on_copy_selected(self, event: wx.CommandEvent) -> None:
        """
        Copy the selected value from the list to the clipboard.
        """
        sel = self.list.GetFirstSelected()
        if sel == -1:
            wx.MessageBox("No row selected", "Info", wx.OK | wx.ICON_INFORMATION)
            return
        value = self.list.GetItemText(sel, 1)
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(value))
            wx.TheClipboard.Close()
            wx.MessageBox("Copied to clipboard", "Info", wx.OK | wx.ICON_INFORMATION)
        else:
            wx.MessageBox("Could not open clipboard", "Error", wx.OK | wx.ICON_ERROR)

    @staticmethod
    def _flatten_ged_record(
        record: Any, prefix: Optional[str] = None, seen: Optional[Set[int]] = None
    ) -> List[Tuple[str, str]]:
        """
        Recursively flatten a gedpy/gedcom record into list of (path, value) pairs.

        Args:
            record (Any): The record to flatten.
            prefix (str, optional): The path prefix.
            seen (set, optional): Set of seen object ids to avoid recursion.

        Returns:
            list of (str, str): Flattened field paths and values.
        """
        if seen is None:
            seen = set()
        if prefix is None:
            prefix = getattr(record, "tag", record.__class__.__name__)
        items: List[Tuple[str, str]] = []

        rid = id(record)
        if rid in seen:
            return [("", "")]
        seen.add(rid)

        def add_if(name: str, val: Any) -> None:
            if val is None:
                return
            if isinstance(val, (list, tuple, set)) and not val:
                return
            items.append((f"{prefix}.{name}", repr(val) if not isinstance(val, str) else val))

        for attr in ("tag", "xref_id", "pointer", "value", "text", "date", "placename", "place"):
            if hasattr(record, attr):
                add_if(attr, getattr(record, attr))

        for map_attr in ("sub_tag_map", "data", "fields", "attrs", "__dict__"):
            if hasattr(record, map_attr) and map_attr != "__dict__":
                mp = getattr(record, map_attr)
                if isinstance(mp, dict):
                    for k, v in mp.items():
                        if v is None or isinstance(v, (str, int, float, bool)):
                            items.append((f"{prefix}.{k}", str(v)))
                        else:
                            items.extend(GedRecordDialog._flatten_ged_record(v, f"{prefix}.{k}", seen))
                break

        for k, v in getattr(record, "__dict__", {}).items():
            if k.startswith("_"):
                continue
            if k in ("tag", "xref_id", "value", "text", "sub_records", "children"):
                continue
            if callable(v):
                continue
            if v is None or isinstance(v, (str, int, float, bool)):
                items.append((f"{prefix}.{k}", str(v)))
            elif isinstance(v, (list, tuple, set)):
                if all(isinstance(x, (str, int, float, bool)) for x in v):
                    items.append((f"{prefix}.{k}", ", ".join(map(str, v))))
                else:
                    for idx, element in enumerate(v):
                        items.extend(GedRecordDialog._flatten_ged_record(element, f"{prefix}.{k}[{idx}]", seen))
            elif isinstance(v, dict):
                for dk, dv in v.items():
                    if isinstance(dv, (str, int, float, bool)) or dv is None:
                        items.append((f"{prefix}.{k}.{dk}", str(dv)))
                    else:
                        items.extend(GedRecordDialog._flatten_ged_record(dv, f"{prefix}.{k}.{dk}", seen))
            else:
                items.extend(GedRecordDialog._flatten_ged_record(v, f"{prefix}.{k}", seen))

        for child_attr in ("sub_records", "children", "child_records", "subitems"):
            if hasattr(record, child_attr):
                children = getattr(record, child_attr) or []
                for idx, child in enumerate(children):
                    if isinstance(child, (str, int, float)):
                        items.append((f"{prefix}.{child_attr}[{idx}]", str(child)))
                    else:
                        child_tag = getattr(child, "tag", getattr(child, "__class__", type(child)).__name__)
                        items.extend(GedRecordDialog._flatten_ged_record(child, f"{prefix}.{child_tag}[{idx}]", seen))
                break

        for list_attr in ("events", "facts", "attributes", "notes", "media"):
            if hasattr(record, list_attr):
                lst = getattr(record, list_attr) or []
                for idx, element in enumerate(lst):
                    items.extend(GedRecordDialog._flatten_ged_record(element, f"{prefix}.{list_attr}[{idx}]", seen))

        if not items:
            try:
                s = str(record)
            except Exception:
                s = "<unprintable object>"
            items.append((prefix, s))

        return items

    @classmethod
    def show_gedpy_record_dialog(
        cls,
        parent: Optional[wx.Window],
        xref_id: str,
        title: Optional[str] = None,
        *,
        svc_config: Any = None,
    ) -> "GedRecordDialog":
        """
        Instantiate and show the GedRecordDialog for a given GEDCOM record.

        Args:
            parent (wx.Window or None): The parent window.
            xref_id (str): The GEDCOM xref_id to display.
            title (str, optional): The window title.
            svc_config (Any, optional): Configuration service (IConfig).
                Used to obtain the GEDCOM input path.

        Returns:
            GedRecordDialog: The dialog instance.
        """
        # Determine GEDCOM input path from service config
        input_value = None
        if svc_config is not None:
            try:
                input_value = getattr(svc_config, 'gedcom_input', None) or (
                    svc_config.get('GEDCOMinput') if hasattr(svc_config, 'get') else None
                )
            except Exception:
                input_value = None

        if not input_value:
            _log.error("Cannot determine GEDCOM input path from svc_config")
            input_value = ''

        input_path = Path(input_value)
        if not input_path.is_absolute():
            input_path = (Path.cwd() / input_path).resolve()
        input_file = str(input_path)
        try:
            with GedcomReader(input_file) as g:
                reference = g.xref0[xref_id]
                record = g.read_record(reference[0])
        except Exception as e:
            _log.error(f"Error looking up details in for person in  GEDCOM file '{input_file}': {e}")
            record = None

        dlg = cls(parent, record, title=title)
        return dlg
