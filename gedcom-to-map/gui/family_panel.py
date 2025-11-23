import logging
import wx
import wx.grid as gridlib
from gedcom.gedcomdate import maxage

_log = logging.getLogger(__name__.lower())


class FamilyPanel(wx.Panel):
    def __init__(self, parent, hertiageData, isLineage=False, *args, **kwargs) -> None:
        super().__init__(parent, *args, **kwargs)

        # Data structure: Family data with parent-child relationships
        # Example: {"parent_id": ("Name", "Mother/Father", BornYear, DeathYear, BornAddress, [children_born_years], id)}
        self.hertiageData = hertiageData
        self.gOp = getattr(parent, "gOp", None)

        # Create a grid
        rows = max(1, len(self.hertiageData))
        self.grid = gridlib.Grid(self)
        self.grid.CreateGrid(rows, 8)

        # Set column labels
        self.grid.SetColLabelValue(0, "Name")
        if isLineage:
            self.grid.SetColLabelValue(1, "Mom/Dad")
        self.grid.SetColLabelValue(2, "Born Yr")
        self.grid.SetColLabelValue(3, "Death Yr")
        if not isLineage:
            self.grid.SetColLabelValue(4, "Life Age")
        else:
            self.grid.SetColLabelValue(4, "Childbirth Age")
        self.grid.SetColLabelValue(5, "Born Address")
        self.grid.SetColLabelValue(6, "Description")
        self.grid.SetColLabelValue(7, "ID")

        self.populateGrid(isLineage=isLineage)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.grid, 1, wx.EXPAND | wx.ALL, 10)
        self.SetSizer(sizer)

        # Keep a reference to the visual map panel if present
        try:
            self.visual_map_panel = self.GetParent().GetParent()
        except Exception:
            self.visual_map_panel = None

        # Bind right-click handlers
        self.grid.Bind(wx.grid.EVT_GRID_CELL_RIGHT_CLICK, self.OnRowClick)
        self.grid.Bind(wx.grid.EVT_GRID_LABEL_RIGHT_CLICK, self.OnRowClick)

    def populateGrid(self, isLineage=False) -> None:
        """Populate the grid with family data and calculate the age dynamically."""
        child_born_year = None
        for row, (key, details) in enumerate(self.hertiageData.items()):
            name, mother_father, born_year, death_year, born_address, descrip, id_ = details

            if not isLineage:
                if born_year is not None and death_year is not None:
                    try:
                        age = int(death_year) - int(born_year)
                    except Exception:
                        age = "?"
                else:
                    age = "?"
            else:
                if child_born_year is not None and born_year is not None:
                    try:
                        age = int(child_born_year) - int(born_year)
                    except Exception:
                        age = "?"
                else:
                    age = "?"

            self.grid.SetCellValue(row, 0, str(name or ""))
            if isLineage:
                self.grid.SetCellValue(row, 1, str(mother_father or ""))
            self.grid.SetCellValue(row, 2, str(born_year) if born_year is not None else "?")
            self.grid.SetCellValue(row, 3, str(death_year) if death_year is not None else "?")
            self.grid.SetCellValue(row, 4, str(age))
            self.grid.SetCellValue(row, 5, str(born_address or ""))
            self.grid.SetCellValue(row, 6, str(descrip or ""))
            self.grid.SetCellValue(row, 7, str(id_ or ""))

            try:
                if age != "?" and isinstance(age, int):
                    if age < 0 or age > maxage:
                        self.grid.SetCellBackgroundColour(row, 4, wx.RED)
                        self.grid.SetCellTextColour(row, 4, wx.WHITE)
                    elif (age > 60 or age < 13) and isLineage:
                        self.grid.SetCellBackgroundColour(row, 4, wx.YELLOW)
            except Exception:
                pass

            child_born_year = born_year

        self.grid.AutoSizeColumns()
        for r in range(self.grid.GetNumberRows()):
            self.grid.SetCellAlignment(r, 2, wx.ALIGN_RIGHT, wx.ALIGN_CENTER)
            self.grid.SetCellAlignment(r, 3, wx.ALIGN_RIGHT, wx.ALIGN_CENTER)
            self.grid.SetCellAlignment(r, 4, wx.ALIGN_RIGHT, wx.ALIGN_CENTER)

    def OnRowClick(self, event: wx.grid.GridEvent) -> None:
        """Open PersonDialog for the selected row (ID in column 7)."""
        row = event.GetRow()
        person_id = self.grid.GetCellValue(row, 7)
        person = None
        try:
            person = self.gOp.BackgroundProcess.people.get(person_id) if self.gOp and getattr(self.gOp, "BackgroundProcess", None) else None
        except Exception:
            person = None

        if person:
            # import PersonDialog lazily to avoid circular imports
            try:
                from .person_dialog import PersonDialog
            except Exception:
                try:
                    from person_dialog import PersonDialog
                except Exception:
                    PersonDialog = None

            fm = getattr(self.gOp.panel, "font_manager", None) if self.gOp and getattr(self.gOp, "panel", None) else None
            if PersonDialog:
                dlg = PersonDialog(self, person, self.visual_map_panel, font_manager=fm, gOp=self.gOp, showreferences=False)
                dlg.Bind(wx.EVT_CLOSE, lambda evt: dlg.Destroy())
                dlg.Show(True)
        else:
            wx.MessageBox("Person not found.", "Error", wx.OK | wx.ICON_ERROR)