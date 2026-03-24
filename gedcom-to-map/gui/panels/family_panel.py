import logging
import wx
import wx.grid as gridlib
from ..layout.font_manager import FontManager
from geo_gedcom.person import Person

_log = logging.getLogger(__name__.lower())


class FamilyPanel(wx.Panel):
    def __init__(
        self,
        parent: wx.Window,
        hertiageData: dict,
        font_manager: FontManager,
        color_manager=None,
        isLineage: bool = False,
        *args,
        **kwargs,
    ) -> None:
        """Initialize FamilyPanel to display family/lineage data in a grid."""
        super().__init__(parent, *args, **kwargs)

        self.hertiageData = hertiageData
        self.parent = parent
        self.font_manager = font_manager
        self.color_manager = color_manager
        self.isLineage = isLineage

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

        self.apply_grid_colors()

        self.populateGrid(isLineage=isLineage)

        self.update_fonts(self.font_manager)

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

    def apply_grid_colors(self) -> None:
        """Apply configured custom colors to the family grid and headers."""
        if not self.color_manager:
            return

        try:
            if self.color_manager.has_color("GRID_BACK"):
                grid_back = self.color_manager.get_color("GRID_BACK")
                self.grid.SetDefaultCellBackgroundColour(grid_back)
                self.grid.SetBackgroundColour(grid_back)
            if self.color_manager.has_color("GRID_TEXT"):
                grid_text = self.color_manager.get_color("GRID_TEXT")
                self.grid.SetDefaultCellTextColour(grid_text)
                self.grid.SetForegroundColour(grid_text)

            header_back_name = "GRID_HEADER_BACK" if self.color_manager.has_color("GRID_HEADER_BACK") else "GRID_BACK"
            header_text_name = "GRID_HEADER_TEXT" if self.color_manager.has_color("GRID_HEADER_TEXT") else "GRID_TEXT"

            if self.color_manager.has_color(header_back_name):
                self.grid.SetLabelBackgroundColour(self.color_manager.get_color(header_back_name))
            if self.color_manager.has_color(header_text_name):
                self.grid.SetLabelTextColour(self.color_manager.get_color(header_text_name))

            if self.color_manager.has_color("GRID_SELECTED_BACK"):
                self.grid.SetSelectionBackground(self.color_manager.get_color("GRID_SELECTED_BACK"))
            if self.color_manager.has_color("GRID_SELECTED_TEXT"):
                self.grid.SetSelectionForeground(self.color_manager.get_color("GRID_SELECTED_TEXT"))
        except Exception:
            _log.debug("FamilyPanel.apply_grid_colors failed", exc_info=True)

    def _get_warn_back(self) -> wx.Colour:
        if self.color_manager and self.color_manager.has_color("WARN_BACK"):
            return self.color_manager.get_color("WARN_BACK")
        return wx.RED

    def _get_warn_text(self) -> wx.Colour:
        if self.color_manager and self.color_manager.has_color("WARN_TEXT"):
            return self.color_manager.get_color("WARN_TEXT")
        return wx.WHITE

    def _get_warn_soft_back(self) -> wx.Colour:
        if self.color_manager and self.color_manager.has_color("WARN_SOFT_BACK"):
            return self.color_manager.get_color("WARN_SOFT_BACK")
        return wx.YELLOW

    def update_fonts(self, font_manager: FontManager) -> None:
        """Update the fonts of the grid based on the current font manager."""
        fm = font_manager if font_manager else self.font_manager
        if fm:
            grid_font = fm.get_font()
            if grid_font:
                self.grid.SetDefaultCellFont(grid_font)
                self.grid.SetLabelFont(grid_font)
                self.SetFont(grid_font)
                self.grid.ForceRefresh()

    def refresh_colors(self) -> None:
        """Refresh grid colors using current color manager settings."""
        self.apply_grid_colors()
        self.populateGrid(isLineage=self.isLineage)
        self.grid.ForceRefresh()

    def populateGrid(self, isLineage=False) -> None:
        """Populate the grid with family data and calculate the age dynamically.

        Args:
            isLineage: If True, calculates parent age at child birth.
                      If False, calculates lifespan age. Default: False.
        """
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
                    if age < 0 or age > Person.max_age:
                        self.grid.SetCellBackgroundColour(row, 4, self._get_warn_back())
                        self.grid.SetCellTextColour(row, 4, self._get_warn_text())
                    elif (age > 60 or age < 13) and isLineage:
                        self.grid.SetCellBackgroundColour(row, 4, self._get_warn_soft_back())
            except Exception:
                pass

            child_born_year = born_year

        self.grid.AutoSizeColumns()
        for r in range(self.grid.GetNumberRows()):
            self.grid.SetCellAlignment(r, 2, wx.ALIGN_RIGHT, wx.ALIGN_CENTER)
            self.grid.SetCellAlignment(r, 3, wx.ALIGN_RIGHT, wx.ALIGN_CENTER)
            self.grid.SetCellAlignment(r, 4, wx.ALIGN_RIGHT, wx.ALIGN_CENTER)

    def OnRowClick(self, event: wx.grid.GridEvent) -> None:
        """Open PersonDialog for the selected row (ID in column 7).

        Args:
            event: Grid event containing row information.
        """
        row = event.GetRow()
        person_id = self.grid.GetCellValue(row, 7)
        person = None
        try:
            # FamilyPanel parent is PersonDialog; prefer its in-memory people map
            if hasattr(self.parent, "people") and isinstance(self.parent.people, dict):
                person = self.parent.people.get(person_id)

            # Fall back to visual_map_panel service/state people
            if person is None and self.visual_map_panel is not None:
                svc_state = getattr(self.visual_map_panel, "svc_state", None)
                if svc_state is not None and hasattr(svc_state, "people") and isinstance(svc_state.people, dict):
                    person = svc_state.people.get(person_id)

            # Final fallback to background_process cache
            if person is None and self.visual_map_panel is not None:
                bp = getattr(self.visual_map_panel, "background_process", None)
                if bp is not None and hasattr(bp, "people") and isinstance(bp.people, dict):
                    person = bp.people.get(person_id)
        except Exception:
            person = None

        if person:
            # import PersonDialog lazily to avoid circular imports
            try:
                from ..dialogs.person_dialog import PersonDialog
            except Exception:
                try:
                    from person_dialog import PersonDialog
                except Exception:
                    PersonDialog = None

            fm = getattr(self.visual_map_panel, "font_manager", None) if self.visual_map_panel else None
            if PersonDialog:
                # Use self.font_manager if available, otherwise fall back to fm from visual_map_panel
                font_mgr = self.font_manager if self.font_manager else fm
                dlg = PersonDialog(
                    self,
                    person,
                    self.visual_map_panel,
                    font_manager=font_mgr,
                    color_manager=getattr(self.visual_map_panel, "color_manager", None),
                    svc_config=getattr(self.visual_map_panel, "svc_config", None),
                    svc_state=getattr(self.visual_map_panel, "svc_state", None),
                    svc_progress=getattr(self.visual_map_panel, "svc_progress", None),
                    showreferences=False,
                )
                dlg.Bind(wx.EVT_CLOSE, lambda evt: dlg.Destroy())
                dlg.Show(True)
        else:
            wx.MessageBox("Person not found.", "Error", wx.OK | wx.ICON_ERROR)
