import logging
from io import BytesIO
import wx
import wx.html

from const import GUINAME, VERSION, ABOUTLINK, NAME

_log = logging.getLogger(__name__.lower())


class HTMLDialog(wx.Dialog):
    def __init__(self, parent, title, icontype, htmlbody, width: int, font_manager):
        # font_manager is required; caller must pass a valid FontManager instance
        self.font_manager = font_manager
        self.font_name, self.font_size = self.font_manager.get_font_name_size()
        super().__init__(parent, title=title, size=(self.font_size * width, self.font_size * 45))

        self.icon = wx.ArtProvider.GetBitmap(icontype, wx.ART_OTHER, (32, 32))
        self.icon_ctrl = wx.StaticBitmap(self, bitmap=self.icon)
        self.html = wx.html.HtmlWindow(self)
        self.set_current_font()
        self.html.SetPage(
            f"<html><body>{htmlbody}</body></html>"
            .replace('VERVER', f"{GUINAME} {VERSION}")
            .replace('PROJECTLINK', f"{ABOUTLINK}{NAME}")
        )

        self.okButton = wx.Button(self, wx.ID_OK, "OK")
        # ensure OK ends the modal loop cleanly
        self.okButton.Bind(wx.EVT_BUTTON, lambda evt: self.EndModal(wx.ID_OK))

        sizer = wx.BoxSizer(wx.VERTICAL)
        icon_sizer = wx.BoxSizer(wx.HORIZONTAL)

        icon_sizer.Add(self.icon_ctrl, 0, wx.ALL, 10)
        icon_sizer.Add(self.html, 1, wx.EXPAND | wx.ALL, 7)

        sizer.Add(icon_sizer, 1, wx.EXPAND)
        sizer.Add(self.okButton, 0, wx.ALIGN_CENTER | wx.ALL, 5)

        self.SetSizer(sizer)

        self.Bind(wx.html.EVT_HTML_LINK_CLICKED, self.on_link_clicked, self.html)

    def set_current_font(self):
        try:
            # HtmlWindow.SetFonts requires three font names; pass same face and repeated sizes
            self.html.SetFonts(self.font_name, self.font_name, [self.font_size] * 7)
        except Exception:
            _log.exception("set_current_font failed in HTMLDialog")

    def on_link_clicked(self, event):
        try:
            wx.LaunchDefaultBrowser(event.GetLinkInfo().GetHref())
        except Exception:
            _log.exception("on_link_clicked failed")

    def on_ok(self, event):
        # Defensive: end modal loop; caller will Destroy() after ShowModal returns
        try:
            if self.IsModal():
                self.EndModal(wx.ID_OK)
            else:
                self.Close()
        except Exception:
            # fallback: ensure dialog is closed
            self.Destroy()
