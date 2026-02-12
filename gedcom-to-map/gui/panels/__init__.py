"""UI panels: Main visual components for the application window.

Provides panel components for displaying and interacting with genealogical data:
    - VisualMapPanel: Main panel with map, people list, and options
    - FamilyPanel: Family relationship visualization
    - PeopleListCtrlPanel: People list view and filtering
"""

from .visual_map_panel import VisualMapPanel
from .family_panel import FamilyPanel
from .people_list_ctrl_panel import PeopleListCtrlPanel

__all__ = ["VisualMapPanel", "FamilyPanel", "PeopleListCtrlPanel"]
