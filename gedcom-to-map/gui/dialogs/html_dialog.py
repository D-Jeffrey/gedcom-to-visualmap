import logging
from io import BytesIO
import wx
import wx.html
import yaml
from pathlib import Path

from gui.layout.font_manager import FontManager
from const import GUINAME, VERSION, ABOUTLINK, NAME

_log = logging.getLogger(__name__.lower())


class HTMLDialog(wx.Dialog):
    @staticmethod
    def load_dialog_content(dialog_key: str) -> str:
        """Load dialog HTML content from YAML file.

        Args:
            dialog_key: Key identifying the dialog content (e.g., 'about_dialog', 'help_dialog').

        Returns:
            HTML content string.

        Raises:
            FileNotFoundError: If dialog_content.yaml is not found.
            KeyError: If dialog_key is not found in the YAML file.
        """
        content_file = Path(__file__).parent / "dialog_content.yaml"
        try:
            with open(content_file, "r", encoding="utf-8") as f:
                content = yaml.safe_load(f)
            return content[dialog_key]
        except FileNotFoundError:
            _log.error(f"Dialog content file not found: {content_file}")
            raise
        except KeyError:
            _log.error(f"Dialog key '{dialog_key}' not found in {content_file}")
            raise
        except Exception as e:
            _log.exception(f"Failed to load dialog content for '{dialog_key}'")
            raise

    def __init__(
        self,
        parent: wx.Window,
        title: str,
        icontype: str,
        htmlbody: str,
        width: int,
        font_manager: "FontManager",
        color_manager=None,
    ) -> None:
        """Initialize the HTML content dialog.

        Args:
            parent: Parent wxPython window.
            title: Dialog title.
            icontype: wx.ArtID for the dialog icon (e.g., wx.ART_INFORMATION).
            htmlbody: HTML content to display in the dialog.
            width: Width multiplier for dialog sizing (based on font size).
            font_manager: FontManager instance for font configuration.
        """
        # font_manager is required; caller must pass a valid FontManager instance
        self.font_manager: "FontManager" = font_manager
        self.font_name: str
        self.font_size: int
        self.font_name, self.font_size = self.font_manager.get_font_name_size()
        self.color_manager = color_manager

        # Ensure color_manager has loaded current system appearance colors
        if self.color_manager and hasattr(self.color_manager, "refresh_colors"):
            try:
                self.color_manager.refresh_colors()
            except Exception:
                _log.debug("HTMLDialog init: refresh_colors() failed", exc_info=True)

        super().__init__(parent, title=title, size=(self.font_size * width, self.font_size * 45))

        self.icon: wx.Bitmap = wx.ArtProvider.GetBitmap(icontype, wx.ART_OTHER, (32, 32))
        self.icon_ctrl: wx.StaticBitmap = wx.StaticBitmap(self, bitmap=self.icon)
        self.html: wx.html.HtmlWindow = wx.html.HtmlWindow(self)
        self.set_current_font()
        # Store the raw body content for later re-rendering with theme colors
        self.htmlbody = htmlbody
        self._set_html_content()

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

        self.refresh_dialog_background()

        self.Bind(wx.html.EVT_HTML_LINK_CLICKED, self.on_link_clicked, self.html)
        self.Bind(wx.EVT_ACTIVATE, self.OnActivate)

    def _set_html_content(self) -> None:
        """Render HTML content with theme-appropriate CSS styling."""
        # Detect system dark mode as fallback
        is_dark_system = False
        try:
            if hasattr(wx, "SystemSettings") and hasattr(wx.SystemSettings, "GetAppearance"):
                appearance = wx.SystemSettings.GetAppearance()
                is_dark_system = appearance.IsDark()
        except Exception:
            pass

        # Set defaults based on system appearance
        if is_dark_system:
            text_color = "#FFFFFF"  # White text for dark mode
            bg_color = "#2A2A2A"  # Dark gray background
            link_color = "#87CEEB"  # Sky blue for links
        else:
            text_color = "#000000"  # Black text for light mode
            bg_color = "#FFFFFF"  # White background
            link_color = "#0000EE"  # Blue for links

        if self.color_manager:
            try:
                if self.color_manager.has_color("DIALOG_TEXT"):
                    color_obj = self.color_manager.get_color("DIALOG_TEXT")
                    if color_obj and color_obj.IsOk():
                        text_color = f"#{color_obj.Red():02X}{color_obj.Green():02X}{color_obj.Blue():02X}"

                if self.color_manager.has_color("DIALOG_BACKGROUND"):
                    color_obj = self.color_manager.get_color("DIALOG_BACKGROUND")
                    if color_obj and color_obj.IsOk():
                        bg_color = f"#{color_obj.Red():02X}{color_obj.Green():02X}{color_obj.Blue():02X}"

                if self.color_manager.has_color("DIALOG_LINK_TEXT"):
                    color_obj = self.color_manager.get_color("DIALOG_LINK_TEXT")
                    if color_obj and color_obj.IsOk():
                        link_color = f"#{color_obj.Red():02X}{color_obj.Green():02X}{color_obj.Blue():02X}"
            except Exception:
                _log.debug("Failed to get theme colors for HTML dialog", exc_info=True)

        # Inject inline color into links since wx.html.HtmlWindow ignores CSS for <a> tags
        # Replace <a href="..." with <a style="color: {link_color}" href="..."
        import re

        modified_body = re.sub(
            r"<a\s+href=", f'<a style="color: {link_color};" href=', self.htmlbody, flags=re.IGNORECASE
        )

        # Inject CSS AND inline styles to style the HTML content
        # wx.html.HtmlWindow on macOS doesn't fully respect CSS, so we also use font tags and inline styles
        styled_html = f"""<html>
<head>
<style>
body {{
    color: {text_color} !important;
    background-color: {bg_color} !important;
}}
a {{
    color: {link_color} !important;
}}
a:visited {{
    color: {link_color} !important;
}}
</style>
</head>
<body style="color: {text_color}; background-color: {bg_color};">
<font color="{text_color}">
{modified_body}
</font>
</body>
</html>""".replace(
            "VERVER", f"{GUINAME} {VERSION}"
        ).replace(
            "PROJECTLINK", f"{ABOUTLINK}{NAME}"
        )

        # Load HTML content first
        try:
            self.html.SetPage(styled_html)
        except Exception:
            _log.exception("Failed to set HTML page content")

        # AFTER loading HTML, set widget colors to override any defaults
        # This is needed because wxPython's HtmlWindow on macOS may not fully respect CSS colors
        try:
            # Convert hex colors back to wx.Colour for widget methods
            bg_r = int(bg_color[1:3], 16)
            bg_g = int(bg_color[3:5], 16)
            bg_b = int(bg_color[5:7], 16)
            widget_bg = wx.Colour(bg_r, bg_g, bg_b)

            text_r = int(text_color[1:3], 16)
            text_g = int(text_color[3:5], 16)
            text_b = int(text_color[5:7], 16)
            widget_fg = wx.Colour(text_r, text_g, text_b)

            self.html.SetBackgroundColour(widget_bg)
            self.html.SetForegroundColour(widget_fg)
            self.html.Refresh()
        except Exception as e:
            _log.debug(f"Failed to set HtmlWindow colors: {e}")

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

    def OnActivate(self, event: wx.ActivateEvent) -> None:
        if event.GetActive() and self.color_manager:
            if self.color_manager.refresh_colors():
                self.refresh_dialog_background()
        event.Skip()

    def refresh_dialog_background(self) -> None:
        if not self.color_manager:
            return

        # Set background color for the dialog container only
        if self.color_manager.has_color("DIALOG_BACKGROUND"):
            bg_color = self.color_manager.get_color("DIALOG_BACKGROUND")
            self.SetBackgroundColour(bg_color)
            # Don't set colors on HtmlWindow widget - it's styled via CSS in _set_html_content()

        # Set text color for the dialog container and OK button
        if self.color_manager.has_color("DIALOG_TEXT"):
            text_color = self.color_manager.get_color("DIALOG_TEXT")
            self.SetForegroundColour(text_color)
            # Apply to OK button and other non-HTML widgets
            if hasattr(self, "okButton"):
                self.okButton.SetForegroundColour(text_color)
                if hasattr(self.okButton, "SetOwnForegroundColour"):
                    self.okButton.SetOwnForegroundColour(text_color)

        # Re-render HTML content with updated theme colors via CSS
        self._set_html_content()
        self.Refresh()

    def _apply_foreground_recursive(self, root: wx.Window, color: wx.Colour) -> None:
        try:
            root.SetForegroundColour(color)
            # Use SetOwnForegroundColour for Windows compatibility
            if hasattr(root, "SetOwnForegroundColour"):
                root.SetOwnForegroundColour(color)
        except Exception:
            pass
        for child in root.GetChildren():
            self._apply_foreground_recursive(child, color)
