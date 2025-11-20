import wx
import wx.lib.scrolledpanel as scrolled
from pathlib import Path
import logging
from ged4py.parser import GedcomReader

_log = logging.getLogger(__name__)

def _flatten_ged_record(record, prefix=None, seen=None):
    """
    Recursively flatten a gedpy/gedcom record into list of (path, value) pairs.
    This function is intentionally generic to handle multiple record shapes:
    - attributes on object (tag, xref_id, value, text, pointer)
    - mapping-like attributes (dict fields)
    - iterable children (sub_records, children)
    """
    if seen is None:
        seen = set()
    if prefix is None:
        prefix = getattr(record, "tag", record.__class__.__name__)
    items = []

    # Avoid infinite recursion on self-references
    rid = id(record)
    if rid in seen:
        return [("", "")]
        return [(prefix, "<recursive reference>")]
    seen.add(rid)

    # Helper that adds a simple value if not None/empty
    def add_if(name, val):
        if val is None:
            return
        if isinstance(val, (list, tuple, set)) and not val:
            return
        items.append((f"{prefix}.{name}", repr(val) if not isinstance(val, str) else val))

    # Common simple attributes
    for attr in ("tag", "xref_id", "pointer", "value", "text", "date", "placename", "place"):
        if hasattr(record, attr):
            add_if(attr, getattr(record, attr))

    # If record looks like a mapping of fields (e.g. record.sub_tag_map or record.data)
    # check common attribute names used by parsers
    for map_attr in ("sub_tag_map", "data", "fields", "attrs", "__dict__"):
        if hasattr(record, map_attr) and map_attr != "__dict__":
            mp = getattr(record, map_attr)
            if isinstance(mp, dict):
                for k, v in mp.items():
                    # pretty print small scalars; otherwise recurse
                    if v is None or isinstance(v, (str, int, float, bool)):
                        items.append((f"{prefix}.{k}", str(v)))
                    else:
                        # recurse into nested object
                        items.extend(_flatten_ged_record(v, f"{prefix}.{k}", seen))
            break

    # Fallback: inspect __dict__ for additional attributes (avoid private and callables)
    for k, v in getattr(record, "__dict__", {}).items():
        if k.startswith("_"):
            continue
        if k in ("tag", "xref_id", "value", "text", "sub_records", "children"):
            # handled separately or earlier
            continue
        if callable(v):
            continue
        # small scalars printed inline
        if v is None or isinstance(v, (str, int, float, bool)):
            items.append((f"{prefix}.{k}", str(v)))
        elif isinstance(v, (list, tuple, set)):
            # list of scalars? flatten inline; else recurse each element
            if all(isinstance(x, (str, int, float, bool)) for x in v):
                items.append((f"{prefix}.{k}", ", ".join(map(str, v))))
            else:
                for idx, element in enumerate(v):
                    items.extend(_flatten_ged_record(element, f"{prefix}.{k}[{idx}]", seen))
        elif isinstance(v, dict):
            for dk, dv in v.items():
                if isinstance(dv, (str, int, float, bool)) or dv is None:
                    items.append((f"{prefix}.{k}.{dk}", str(dv)))
                else:
                    items.extend(_flatten_ged_record(dv, f"{prefix}.{k}.{dk}", seen))
        else:
            # nested object, recurse
            items.extend(_flatten_ged_record(v, f"{prefix}.{k}", seen))

    # Known child container names
    for child_attr in ("sub_records", "children", "child_records", "subitems"):
        if hasattr(record, child_attr):
            children = getattr(record, child_attr) or []
            for idx, child in enumerate(children):
                # child may be a simple tuple pair (tag,value)
                if isinstance(child, (str, int, float)):
                    items.append((f"{prefix}.{child_attr}[{idx}]", str(child)))
                else:
                    # determine child's tag or fallback to class name
                    child_tag = getattr(child, "tag", getattr(child, "__class__", type(child)).__name__)
                    items.extend(_flatten_ged_record(child, f"{prefix}.{child_tag}[{idx}]", seen))
            break

    # Many gedcom objects expose a list of events or facts
    for list_attr in ("events", "facts", "attributes", "notes", "media"):
        if hasattr(record, list_attr):
            lst = getattr(record, list_attr) or []
            for idx, element in enumerate(lst):
                items.extend(_flatten_ged_record(element, f"{prefix}.{list_attr}[{idx}]", seen))

    # If nothing collected so far, attempt to stringify the record
    if not items:
        try:
            s = str(record)
        except Exception:
            s = "<unprintable object>"
        items.append((prefix, s))

    return items


class GedRecordDialog(wx.Frame):
    def __init__(self, parent, record, title=None):
        title = title or f"GED Record: {getattr(record, 'xref_id', getattr(record, 'tag', record.__class__.__name__))}"
        super().__init__(parent, title=title, size=(800, 600))

        # Main sizer
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # Scrolled panel to contain the ListCtrl (works with large records)
        panel = scrolled.ScrolledPanel(self, -1)
        panel.SetupScrolling(scroll_x=False, scroll_y=True)
        pnl_sizer = wx.BoxSizer(wx.VERTICAL)

        # List control in report mode
        self.list = wx.ListCtrl(panel, style=wx.LC_REPORT | wx.BORDER_SUNKEN | wx.LC_HRULES | wx.LC_VRULES)
        self.list.InsertColumn(0, "Field path")
        self.list.InsertColumn(1, "Value")

        # Populate rows
        flattened = _flatten_ged_record(record)
        # Sort by path for consistent view
        flattened.sort(key=lambda x: x[0].lower())

        for path, val in flattened:
            if val and not path.endswith(".parser") and not path.endswith(".level"):
                idx = self.list.InsertItem(self.list.GetItemCount(), path.replace('INDI.',''))
                # Ensure value is a single-line string
                single_line_val = str(val).replace("\r", " ").replace("\n", " ")
                self.list.SetItem(idx, 1, single_line_val)

        # autosize columns (limit max width for value)
        self.list.SetColumnWidth(0, wx.COL_WIDTH_AUTOSIZE)
        # compute a reasonable width for value column
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

    def on_copy_selected(self, event):
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


def show_gedpy_record_dialog(parent, xref_id, gOp, title=None):
    """
    Convenience function to instantiate and show the GedRecordDialog.
    Example:
        show_gedpy_record_dialog(self, some_gedpy_record)
    """
    input_path = Path(gOp.GEDCOMinput)
    if not input_path.is_absolute():
        input_path = (Path.cwd() / input_path).resolve()
    input_file = str(input_path)
    try:
        
            # Single pass: build people and then addresses
        with GedcomReader(input_file) as g:
                reference = g.xref0[xref_id]
                record = g.read_record(reference[0])

    except Exception as e:
            _log.error(f"Error looking up details in for person in  GEDCOM file '{input_file}': {e}")

    # parent can be None or a wx.Window
    
    dlg = GedRecordDialog(parent, record, title=title)
    # The dialog is a Frame and shows itself; return the instance if caller wants to keep a handle
    return dlg