import wx

class LayoutOptions(wx.Panel):
    def __init__(self, panel: wx.Panel) -> None:
        box = wx.BoxSizer(wx.VERTICAL)
        titleFont = self.font_manager.get_font(bold=True, size_delta=0)
        fh = titleFont.GetPixelSize()[1]
        titleArea = wx.Panel(panel, size=(-1, fh + 10))
        titleArea.SetBackgroundColour(self.id.GetColor('TITLE_BACK'))
        title = wx.StaticText(titleArea, label="Visual Mapping Options",  style=wx.ALIGN_CENTER)
        title.SetFont(titleFont)
        # Center the title text in the title area
        titleSizer = wx.BoxSizer(wx.HORIZONTAL)
        titleSizer.Add(title, 1, wx.ALIGN_CENTER)
        titleArea.SetSizer(titleSizer)

        box.Add(titleArea, 0, wx.EXPAND | wx.BOTTOM, 0)
        box.Add(wx.StaticLine(panel), 0, wx.EXPAND)