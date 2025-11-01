# visualmap_style/style_manager.py
import wx
import json
import os


def ApproxTextWidth(numChars, sizePt=9, dpi=96.0, isMono=False, emRatio=None, marginPx=2):
    """
    Return approximate pixel width for numChars of text.
    - sizePt: font size in points
    - dpi: display DPI (use 96 for standard)
    - isMono: True for monospace fonts
    - emRatio: override default per-character em ratio (None uses defaults)
    - marginPx: small safety margin in pixels
    """
    if emRatio is None:
        emRatio = 1.0 if isMono else 0.55
    pxPerEm = sizePt * (dpi / 72.0)
    return int(round(numChars * pxPerEm * emRatio)) + marginPx


class FontManager:
    PREDEFINED_FONTS = [
        "Arial", "Calibri", "Corbel", "Consolas", "Courier New", "DejaVu Sans", "Georgia",  "Noto Sans", 
        "Segoe UI", "Tahoma", "Times New Roman", "Trebuchet MS", "Verdana"
    ]

    DEFAULT = {
        "face": "Segoe UI",
        "size": 9,
        "style": "normal"   # placeholder for future bold/italic
    }

    PREDEFINED_FONT_SIZES = [8, 9, 10, 11, 12, 14, 16, 18, 20, 22, 24]

    _current = None

    @classmethod
    def load(cls):
        sp = wx.StandardPaths.Get()
        _CONFIG_FILENAME = os.path.join(sp.GetUserDataDir(), "visualmap_style.json")
        
        try:
            os.makedirs(os.path.dirname(_CONFIG_FILENAME), exist_ok=True)
            if os.path.exists(_CONFIG_FILENAME):
                with open(_CONFIG_FILENAME, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                cls._current = {
                    "face": cfg.get("face", cls.DEFAULT["face"]),
                    "size": cfg.get("size", cls.DEFAULT["size"]),
                    "style": cfg.get("style", cls.DEFAULT["style"])
                }
                return
        except Exception:
            pass
        cls._current = dict(cls.DEFAULT)

    @classmethod
    def save(cls):
        sp = wx.StandardPaths.Get()
        _CONFIG_FILENAME = os.path.join(sp.GetUserDataDir(), "visualmap_style.json")

        try:
            cfg = dict(cls._current or cls.DEFAULT)
            with open(_CONFIG_FILENAME, "w", encoding="utf-8") as f:
                json.dump(cfg, f)
        except Exception:
            pass

    @classmethod
    def get_font(cls):
        if cls._current is None:
            cls.load()
        face = cls._current.get("face", cls.DEFAULT["face"])
        size = cls._current.get("size", cls.DEFAULT["size"])
        # wx.Font expects integer point sizes on Windows; cast safely
        return wx.Font(int(size), wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, False, face)

    @classmethod
    def set_font(cls, face, size=None):
        if cls._current is None:
            cls.load()
        if face not in cls.PREDEFINED_FONTS:
            return False
        cls._current["face"] = face
        if size:
            cls._current["size"] = int(size)
        cls.save()
        return True
    
    @classmethod
    def set_font_size(cls, size):
        if cls._current is None:
            cls.load()
        cls._current["size"] = int(size)
        cls.save()
        return True

    @classmethod
    def apply_to(cls, widget):
        """
        Apply the current font to a widget and its children where appropriate.
        For wx.Grid we set the default cell font and refresh.
        """
        font = cls.get_font()
        # If it's a wx.Grid, use its specific API
        try:
            import wx.grid as gridlib
        except Exception:
            gridlib = None

        # Apply to known grid types
        if gridlib and isinstance(widget, gridlib.Grid):
            # set label and cell fonts
            widget.SetDefaultCellFont(font)
            widget.SetLabelFont(font)
            widget.SetDefaultCellTextColour(widget.GetDefaultCellTextColour())
            widget.ForceRefresh()
            return

        wx.Frame.SetFont(widget, font)
        # Generic wx.Window and controls: propagate to children
        if isinstance(widget, wx.Window) or isinstance(widget, wx.Panel) or isinstance(widget, wx.Control):
            widget.SetFont(font)
            for child in widget.GetChildren():
                # avoid changing complex custom controls that manage fonts internally if needed
                try:
                    child.SetFont(font)
                except Exception:
                    pass
            print(f"Widget {type(widget)}")
        else:
            print(f"widget {type(widget)}")

    @classmethod
    def apply_to_all_controls(cls, top_window):
        cls.apply_to(top_window)
        # Walk children to try to apply where needed
        for c in top_window.GetChildren():
            cls.apply_to(c)

    @classmethod
    def apply_font_recursive(cls,win: wx.Window):
        font = cls.get_font()
        # ensure a wx.Font instance
        if not isinstance(font, wx.Font):
            font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)

        try:
            win.SetFont(font)
        except Exception:
            # some native controls may raise; ignore and continue
            pass
        for child in win.GetChildren():
            cls.apply_font_recursive(child)