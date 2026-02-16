"""Core GUI components: Main application window, frame, and service integration.

Provides the top-level GUI application interface and main window implementation.

Classes:
    - GedcomVisualGUI: Application wrapper providing start/stop interface
    - VisualMapFrame: Main application window (wx.Frame)
    - GuiHooks: Implements AppHooks protocol to bridge geo_gedcom callbacks to services

Usage:
    >>> from gui.core import GedcomVisualGUI
    >>> app = GedcomVisualGUI(parent=None, svc_config=config, svc_state=state,
    ...                       svc_progress=progress, title="GEDCOM to Visual Map")
    >>> app.start()
"""

# Best-effort lazy exports so this package can be imported in non-GUI
# environments (e.g. Ubuntu CI core lane without wxPython).
__all__ = []

try:
    from .gedcom_visual_gui import GedcomVisualGUI

    __all__.append("GedcomVisualGUI")
except ImportError:
    pass

try:
    from .visual_map_frame import VisualMapFrame

    __all__.append("VisualMapFrame")
except ImportError:
    pass

try:
    from .gui_hooks import GuiHooks

    __all__.append("GuiHooks")
except ImportError:
    pass
