import wx
from ..layout.font_manager import FontManager


class FindDialog(wx.Dialog):
    def __init__(
        self,
        parent: wx.Window,
        font_manager: "FontManager",
        title: str = "Find",
        LastSearch: str = "",
        color_manager=None,
    ) -> None:
        """Initialize the Find/Search dialog.

        Args:
            parent: Parent wxPython window.
            font_manager: FontManager instance for font configuration.
            title: Dialog title (default: "Find").
            LastSearch: Previous search string to populate field with (default: "").
        """
        super().__init__(parent, title=title, size=(300, 150))

        self.font_manager: "FontManager" = font_manager
        self.LastSearch: str = LastSearch
        self.color_manager = color_manager

        # Layout
        Findpanel = wx.Panel(self, style=wx.SIMPLE_BORDER)
        self.find_panel = Findpanel
        self.refresh_dialog_background()
        vbox = wx.BoxSizer(wx.VERTICAL)

        self.SearchLabel = wx.StaticText(Findpanel, label="Enter search string:")
        vbox.Add(self.SearchLabel, flag=wx.ALL, border=10)

        self.SearchText = wx.TextCtrl(Findpanel)
        self.SearchText.SetValue(self.LastSearch)
        vbox.Add(self.SearchText, flag=wx.EXPAND | wx.LEFT | wx.RIGHT, border=10)

        self.okButton = wx.Button(Findpanel, label="OK")
        self.cancelButton = wx.Button(Findpanel, label="Cancel")
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(self.okButton, flag=wx.RIGHT, border=10)
        hbox.Add(self.cancelButton, flag=wx.LEFT, border=10)
        vbox.Add(hbox, flag=wx.ALIGN_CENTER | wx.ALL, border=10)

        Findpanel.SetSizer(vbox)
        # Set OK button as default
        self.okButton.SetDefault()

        # Event bindings
        self.okButton.Bind(wx.EVT_BUTTON, self.OnOk)
        self.cancelButton.Bind(wx.EVT_BUTTON, self.OnCancel)
        self.Bind(wx.EVT_ACTIVATE, self.OnActivate)

        self.font_manager.apply_current_font_recursive(self)

        # Set focus on search field so user can start typing immediately
        wx.CallAfter(self.SearchText.SetFocus)

    def OnOk(self, event):
        self.LastSearch = self.SearchText.GetValue()
        self.EndModal(wx.ID_OK)

    def OnCancel(self, event):
        self.EndModal(wx.ID_CANCEL)

    def OnActivate(self, event: wx.ActivateEvent) -> None:
        if event.GetActive() and self.color_manager:
            if self.color_manager.refresh_colors():
                self.refresh_dialog_background()
        event.Skip()

    def refresh_dialog_background(self) -> None:
        if not self.color_manager:
            return
        if self.color_manager.has_color("DIALOG_BACKGROUND"):
            bg_color = self.color_manager.get_color("DIALOG_BACKGROUND")
            self.SetBackgroundColour(bg_color)
            if hasattr(self, "find_panel") and self.find_panel:
                self.find_panel.SetBackgroundColour(bg_color)
        if self.color_manager.has_color("DIALOG_TEXT"):
            text_color = self.color_manager.get_color("DIALOG_TEXT")
            self.SetForegroundColour(text_color)
            if hasattr(self, "find_panel") and self.find_panel:
                self.find_panel.SetForegroundColour(text_color)
                self._apply_foreground_recursive(self.find_panel, text_color)
        self.Refresh()

    def _apply_foreground_recursive(self, root: wx.Window, color: wx.Colour) -> None:
        try:
            root.SetForegroundColour(color)
            # Use SetOwnForegroundColour for Windows compatibility
            if hasattr(root, "SetOwnForegroundColour"):
                root.SetOwnForegroundColour(color)
        except Exception:
            pass
        # Apply background color to TextCtrl for Windows compatibility
        if isinstance(root, wx.TextCtrl):
            try:
                if self.color_manager and self.color_manager.has_color("DIALOG_BACKGROUND"):
                    bg_color = self.color_manager.get_color("DIALOG_BACKGROUND")
                    root.SetBackgroundColour(bg_color)
                    if hasattr(root, "SetOwnBackgroundColour"):
                        root.SetOwnBackgroundColour(bg_color)
            except Exception:
                pass
        for child in root.GetChildren():
            self._apply_foreground_recursive(child, color)

    def GetSearchString(self):
        return self.LastSearch
