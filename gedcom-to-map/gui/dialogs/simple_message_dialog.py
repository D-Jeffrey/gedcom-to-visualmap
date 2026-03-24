"""Simple themed message dialog to replace wx.MessageBox for dark mode compatibility."""

import logging
import wx

_log = logging.getLogger(__name__.lower())


class SimpleMessageDialog(wx.Dialog):
    """A simple message dialog that properly supports dark mode colors on all platforms.

    This replaces wx.MessageBox which doesn't respect custom colors on Windows.
    """

    def __init__(
        self,
        parent: wx.Window,
        message: str,
        title: str = "Information",
        color_manager=None,
    ) -> None:
        """Initialize the simple message dialog.

        Args:
            parent: Parent wxPython window.
            message: Message text to display.
            title: Dialog title.
            color_manager: Optional ColorManager instance for theming.
        """
        self.color_manager = color_manager

        # Ensure color_manager has loaded current system appearance colors
        if self.color_manager and hasattr(self.color_manager, "refresh_colors"):
            try:
                self.color_manager.refresh_colors()
            except Exception:
                _log.debug("SimpleMessageDialog init: refresh_colors() failed", exc_info=True)

        super().__init__(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE)

        # Create a multiline text control to display the message
        self.text_ctrl = wx.TextCtrl(
            self,
            value=message,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_NO_VSCROLL | wx.BORDER_NONE,
        )

        # Size the text control based on content
        lines = message.split("\n")
        max_line_length = max(len(line) for line in lines) if lines else 40
        num_lines = len(lines)

        # Approximate sizing (7 pixels per char, 20 pixels per line)
        width = min(max_line_length * 7 + 40, 600)
        height = min(num_lines * 20 + 40, 400)
        self.text_ctrl.SetMinSize((width, height))

        # OK button - use wx.ID_ANY to allow custom background colors on macOS
        self.okButton = wx.Button(self, wx.ID_ANY, "OK")
        self.okButton.Bind(wx.EVT_BUTTON, lambda evt: self.EndModal(wx.ID_OK))

        # Layout
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.text_ctrl, 1, wx.EXPAND | wx.ALL, 10)
        sizer.Add(self.okButton, 0, wx.ALIGN_CENTER | wx.ALL, 10)
        self.SetSizer(sizer)

        # Apply colors
        self.refresh_dialog_colors()

        # Fit to content
        self.Fit()
        self.CenterOnParent()

        # Bind Enter key to close dialog
        self.Bind(wx.EVT_CHAR_HOOK, self.on_char_hook)

    def on_char_hook(self, event: wx.KeyEvent) -> None:
        """Handle key events to allow Enter to close the dialog."""
        if event.GetKeyCode() in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            self.EndModal(wx.ID_OK)
        else:
            event.Skip()

    def refresh_dialog_colors(self) -> None:
        """Apply theme colors to the dialog and controls."""
        if not self.color_manager:
            return

        try:
            # Set dialog background
            if self.color_manager.has_color("DIALOG_BACKGROUND"):
                bg_color = self.color_manager.get_color("DIALOG_BACKGROUND")
                self.SetBackgroundColour(bg_color)
                self.text_ctrl.SetBackgroundColour(bg_color)
                # Use SetOwnBackgroundColour for Windows compatibility
                if hasattr(self.text_ctrl, "SetOwnBackgroundColour"):
                    self.text_ctrl.SetOwnBackgroundColour(bg_color)

            # Set text color
            if self.color_manager.has_color("DIALOG_TEXT"):
                text_color = self.color_manager.get_color("DIALOG_TEXT")
                self.SetForegroundColour(text_color)
                self.text_ctrl.SetForegroundColour(text_color)
                # Use SetOwnForegroundColour for Windows compatibility
                if hasattr(self.text_ctrl, "SetOwnForegroundColour"):
                    self.text_ctrl.SetOwnForegroundColour(text_color)
                # Apply to OK button
                if hasattr(self, "okButton"):
                    self.okButton.SetForegroundColour(text_color)
                    if hasattr(self.okButton, "SetOwnForegroundColour"):
                        self.okButton.SetOwnForegroundColour(text_color)

            # Set OK button background color
            if hasattr(self, "okButton") and self.color_manager.has_color("BTN_BACK"):
                btn_color = self.color_manager.get_color("BTN_BACK")
                self.okButton.SetBackgroundColour(btn_color)
                if hasattr(self.okButton, "SetOwnBackgroundColour"):
                    self.okButton.SetOwnBackgroundColour(btn_color)

            self.Refresh()
        except Exception as e:
            _log.debug(f"Failed to apply dialog colors: {e}")
