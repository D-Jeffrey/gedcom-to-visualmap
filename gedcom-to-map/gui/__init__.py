"""GUI package init — best-effort re-exports for refactored GUI modules.

Importing this package will not fail if individual modules have import-time errors;
callers can still import modules directly (e.g. `from gui.dialogs import PersonDialog`).

The GUI package is now organized into subpackages:
- core: Main application components (GedcomVisualGUI, VisualMapFrame, GuiHooks)
- panels: UI panels (VisualMapPanel, FamilyPanel, PeopleListCtrlPanel)
- processors: Data processors (GedcomLoader, MapGenerator, ReportGenerator, LineageTracer)
- actions: Action handlers (VisualMapActions, BackgroundActions, FileOpener, DoActionsType)
- dialogs: Dialog windows (AboutDialog, ConfigDialog, FindDialog, etc.)
- widgets: Custom controls (PeopleListCtrl, GedRecDisplay)
- layout: Layout helpers (LayoutOptions, LayoutHelpers, EventHandlers, FontManager, ColourManager, etc.)
"""

# Try to import GUI components, but don't fail if there are errors
# This allows testing of individual modules without wxPython dependencies
__all__ = []

# Core components
try:
    from .core import GedcomVisualGUI, VisualMapFrame, GuiHooks  # type: ignore
    __all__.extend(["GedcomVisualGUI", "VisualMapFrame", "GuiHooks"])
except (ImportError, AttributeError):
    pass

# Panels
try:
    from .panels import VisualMapPanel, FamilyPanel, PeopleListCtrlPanel  # type: ignore
    __all__.extend(["VisualMapPanel", "FamilyPanel", "PeopleListCtrlPanel"])
except (ImportError, AttributeError):
    pass

# Processors
try:
    from .processors import GedcomLoader, MapGenerator, ReportGenerator, LineageTracer  # type: ignore
    __all__.extend(["GedcomLoader", "MapGenerator", "ReportGenerator", "LineageTracer"])
except (ImportError, AttributeError):
    pass

# Actions
try:
    from .actions import VisualMapActions, Geoheatmap, gedcom_to_map, BackgroundActions, FileOpener, DoActionsType  # type: ignore
    __all__.extend(["VisualMapActions", "Geoheatmap", "gedcom_to_map", "BackgroundActions", "FileOpener", "DoActionsType"])
except (ImportError, AttributeError):
    pass

# Dialogs
try:
    from .dialogs import AboutDialog, ConfigDialog, FindDialog, HelpDialog, PersonDialog  # type: ignore
    __all__.extend(["AboutDialog", "ConfigDialog", "FindDialog", "HelpDialog", "PersonDialog"])
except (ImportError, AttributeError):
    pass

try:
    from .dialogs import HTMLDialog  # type: ignore
    __all__.append("HTMLDialog")
except (ImportError, AttributeError):
    pass

# Widgets
try:
    from .widgets import PeopleListCtrl, GedRecordDialog  # type: ignore
    __all__.extend(["PeopleListCtrl", "GedRecordDialog"])
except (ImportError, AttributeError):
    pass

# Layout
try:
    from .layout import LayoutOptions, LayoutHelpers, VisualMapEventHandler, VisualGedcomIds, FontManager, ColourManager  # type: ignore
    __all__.extend(["LayoutOptions", "LayoutHelpers", "VisualMapEventHandler", "VisualGedcomIds", "FontManager", "ColourManager"])
except (ImportError, AttributeError):
    pass
