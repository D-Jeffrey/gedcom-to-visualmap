import wx
from ..layout.font_manager import FontManager

class FindDialog(wx.Dialog):
    def __init__(self, parent: wx.Window, font_manager: 'FontManager', title: str = "Find", LastSearch: str = "") -> None:
        """Initialize the Find/Search dialog.
        
        Args:
            parent: Parent wxPython window.
            font_manager: FontManager instance for font configuration.
            title: Dialog title (default: "Find").
            LastSearch: Previous search string to populate field with (default: "").
        """
        super().__init__(parent, title=title, size=(300, 150))

        self.font_manager: 'FontManager' = font_manager
        self.LastSearch: str = LastSearch

        # Layout
        Findpanel = wx.Panel(self, style=wx.SIMPLE_BORDER)
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

        self.font_manager.apply_current_font_recursive(self)

    def OnOk(self, event):
        self.LastSearch = self.SearchText.GetValue()
        self.EndModal(wx.ID_OK)

    def OnCancel(self, event):
        self.EndModal(wx.ID_CANCEL)

    def GetSearchString(self):
        return self.LastSearch
