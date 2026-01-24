"""GUI package init — best-effort re-exports for refactored GUI modules.

Importing this package will not fail if individual modules have import-time errors;
callers can still import modules directly (e.g. `from gui.person_dialog import PersonDialog`).
"""

# Try to import GUI components, but don't fail if there are errors
# This allows testing of individual modules without wxPython dependencies
__all__ = []

try:
    from .visual_map_frame import VisualMapFrame  # type: ignore
    __all__.append("VisualMapFrame")
except (ImportError, AttributeError):
    pass

try:
    from .visual_map_panel import VisualMapPanel  # type: ignore
    __all__.append("VisualMapPanel")
except (ImportError, AttributeError):
    pass

try:
    from .visual_gedcom_ids import VisualGedcomIds  # type: ignore
    __all__.append("VisualGedcomIds")
except (ImportError, AttributeError):
    pass

try:
    from .people_list_ctrl import PeopleListCtrl  # type: ignore
    __all__.append("PeopleListCtrl")
except (ImportError, AttributeError):
    pass

try:
    from .people_list_ctrl_panel import PeopleListCtrlPanel  # type: ignore
    __all__.append("PeopleListCtrlPanel")
except (ImportError, AttributeError):
    pass

try:
    from .html_dialog import HTMLDialog  # type: ignore
    __all__.append("HTMLDialog")
except (ImportError, AttributeError):
    pass

try:
    from .about_dialog import AboutDialog  # type: ignore
    __all__.append("AboutDialog")
except (ImportError, AttributeError):
    pass

try:
    from .help_dialog import HelpDialog  # type: ignore
    __all__.append("HelpDialog")
except (ImportError, AttributeError):
    pass

try:
    from .config_dialog import ConfigDialog  # type: ignore
    __all__.append("ConfigDialog")
except (ImportError, AttributeError):
    pass

try:
    from .person_dialog import PersonDialog  # type: ignore
    __all__.append("PersonDialog")
except (ImportError, AttributeError):
    pass

try:
    from .find_dialog import FindDialog  # type: ignore
    __all__.append("FindDialog")
except (ImportError, AttributeError):
    pass

try:
    from .family_panel import FamilyPanel  # type: ignore
    __all__.append("FamilyPanel")
except (ImportError, AttributeError):
    pass

try:
    from .background_actions import BackgroundActions  # type: ignore
    __all__.append("BackgroundActions")
except (ImportError, AttributeError):
    pass

try:
    from .font_manager import FontManager  # type: ignore
    __all__.append("FontManager")
except (ImportError, AttributeError):
    pass

try:
    from .ged_rec_display import GedRecordDialog  # type: ignore
    __all__.append("GedRecordDialog")
except (ImportError, AttributeError):
    pass

try:
    from .gedcomVisualGUI import GedcomVisualGUI  # type: ignore
    __all__.append("GedcomVisualGUI")
except (ImportError, AttributeError):
    pass

try:
    from .visual_map_actions import VisualMapActions, Geoheatmap, gedcom_to_map  # type: ignore
    __all__.extend(["VisualMapActions", "Geoheatmap", "gedcom_to_map"])
except (ImportError, AttributeError):
    pass

try:
    from .layout_options import LayoutOptions  # type: ignore
    __all__.append("LayoutOptions")
except (ImportError, AttributeError):
    pass