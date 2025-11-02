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

    def __init__(self):
        if self._current is None:
            self.load()

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
    def set_font_size(cls, size):
        if cls._current is None:
            cls.load()
        cls._current["size"] = int(size)
        cls.save()
        return True

    @classmethod
    def apply_font_recursive(self, win: wx.Window, font: wx.Font):
        """Set font on window and all children; ignore failures on native widgets."""
        try:
            win.SetFont(font)
        except Exception:
            pass
        # recurse to children (some objects may not implement GetChildren)
        for child in getattr(win, "GetChildren", lambda: [])():
            try:
                self.apply_font_recursive(child, font)
            except Exception:
                pass