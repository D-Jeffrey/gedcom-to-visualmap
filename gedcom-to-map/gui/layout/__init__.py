"""Layout helpers: UI construction, styling, event handling, and utilities.

Provides utilities for building the UI:
    - LayoutOptions: Options panel construction
    - LayoutHelpers: Common layout and widget helpers
    - VisualMapEventHandler: Main event handler for user interactions
    - VisualGedcomIds: ID constants for UI elements
    - FontManager: Font configuration and management
    - ColourManager: GUI colour management
"""

# Best-effort lazy exports so this package can be imported in non-GUI
# environments (e.g. Ubuntu CI core lane without wxPython).
__all__ = []

try:
    from .layout_options import LayoutOptions

    __all__.append("LayoutOptions")
except ImportError:
    pass

try:
    from .layout_helpers import LayoutHelpers

    __all__.append("LayoutHelpers")
except ImportError:
    pass

try:
    from .visual_map_event_handlers import VisualMapEventHandler

    __all__.append("VisualMapEventHandler")
except ImportError:
    pass

try:
    from .visual_gedcom_ids import VisualGedcomIds

    __all__.append("VisualGedcomIds")
except ImportError:
    pass

try:
    from .font_manager import FontManager

    __all__.append("FontManager")
except ImportError:
    pass

try:
    from .colour_manager import ColourManager

    __all__.append("ColourManager")
except ImportError:
    pass
