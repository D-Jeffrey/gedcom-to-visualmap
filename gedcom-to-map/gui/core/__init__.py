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

from .gedcom_visual_gui import GedcomVisualGUI
from .visual_map_frame import VisualMapFrame
from .gui_hooks import GuiHooks

__all__ = ['GedcomVisualGUI', 'VisualMapFrame', 'GuiHooks']
