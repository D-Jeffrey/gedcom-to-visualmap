import logging
import wx

from ..layout.font_manager import FontManager
from const import VERSION, GUINAME, ABOUTLINK, NAME

_log = logging.getLogger(__name__.lower())

from .html_dialog import HTMLDialog


class AboutDialog(HTMLDialog):
    def __init__(self, parent: wx.Window, title: str, font_manager: "FontManager", color_manager=None) -> None:
        """Initialize the About dialog.

        Args:
            parent: Parent wxPython window.
            title: Dialog title.
            font_manager: FontManager instance for font configuration.
        """
        abouttype = HTMLDialog.load_dialog_content("about_dialog")
        super().__init__(
            parent,
            title=title,
            icontype=wx.ART_INFORMATION,
            htmlbody=abouttype,
            width=55,
            font_manager=font_manager,
            color_manager=color_manager,
        )
        try:
            if font_manager:
                font_manager.apply_current_font_recursive(self)
        except Exception:
            _log.exception("AboutDialog: failed to apply font to dialog")
