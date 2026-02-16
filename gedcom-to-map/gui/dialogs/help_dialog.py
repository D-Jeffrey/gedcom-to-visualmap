import logging
import wx

from ..layout.font_manager import FontManager

_log = logging.getLogger(__name__.lower())

from .html_dialog import HTMLDialog


class HelpDialog(HTMLDialog):
    def __init__(self, parent: wx.Window, title: str, font_manager: "FontManager") -> None:
        """Initialize the Help dialog.

        Args:
            parent: Parent wxPython window.
            title: Dialog title.
            font_manager: FontManager instance for font configuration.
        """
        helppage = HTMLDialog.load_dialog_content("help_dialog")
        super().__init__(
            parent, title=title, icontype=wx.ART_INFORMATION, htmlbody=helppage, width=55, font_manager=font_manager
        )
        try:
            if font_manager:
                font_manager.apply_current_font_recursive(self)
        except Exception:
            _log.exception("HelpDialog: failed to apply font to dialog")
