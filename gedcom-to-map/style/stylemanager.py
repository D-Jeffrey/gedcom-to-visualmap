# visualmap_style/style_manager.py
import wx
import json
import os


class FontManager:
    PREDEFINED_FONTS = [
        "Arial", "Calibri", "Consolas", "Courier New", "Georgia",
        "Segoe UI", "Tahoma", "Times New Roman", "Trebuchet MS", "Verdana"
    ]

    DEFAULT = {
        "face": "Segoe UI",
        "size": 9,
        "style": "normal"   # placeholder for future bold/italic
    }

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

        # Generic wx.Window and controls: propagate to children
        if isinstance(widget, wx.Window):
            widget.SetFont(font)
            for child in widget.GetChildren():
                # avoid changing complex custom controls that manage fonts internally if needed
                try:
                    child.SetFont(font)
                except Exception:
                    pass

    @classmethod
    def apply_to_all_controls(cls, top_window):
        cls.apply_to(top_window)
        # Walk children to try to apply where needed
        for c in top_window.GetChildren():
            cls.apply_to(c)