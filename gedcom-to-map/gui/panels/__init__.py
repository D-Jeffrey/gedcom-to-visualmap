"""UI panels: Main visual components for the application window.

Provides panel components for displaying and interacting with genealogical data:
    - VisualMapPanel: Main panel with map, people list, and options
    - FamilyPanel: Family relationship visualization
    - PeopleListCtrlPanel: People list view and filtering
"""

# Best-effort lazy exports so this package can be imported in non-GUI
# environments (e.g. Ubuntu CI core lane without wxPython).
__all__ = []

try:
    from .visual_map_panel import VisualMapPanel

    __all__.append("VisualMapPanel")
except ImportError:
    pass

try:
    from .family_panel import FamilyPanel

    __all__.append("FamilyPanel")
except ImportError:
    pass

try:
    from .people_list_ctrl_panel import PeopleListCtrlPanel

    __all__.append("PeopleListCtrlPanel")
except ImportError:
    pass
