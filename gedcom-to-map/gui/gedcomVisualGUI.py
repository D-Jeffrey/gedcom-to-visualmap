__all__ = ['VisualGedcomIds', 'VisualMapFrame', 'PeopleListCtrl', 'PeopleListCtrlPanel', 'VisualMapPanel']

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
#
#
#  gedcomVisualGUI.py : GUI Interface  for gedcom-to-map
#    See https://github.com/D-Jeffrey/gedcom-to-visualmap
#
#
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
"""
GUI package facade for the gedcom-to-visualmap application.

This module exposes a small wrapper class (GedcomVisualGUI) used by the
application entrypoint to create and manage the main frame. It intentionally
keeps responsibilities minimal: construct the VisualMapFrame and forward
start/stop lifecycle calls.
"""
#!/usr/bin/env python

import logging
from typing import Any, Tuple

import wx
from .visual_map_frame import VisualMapFrame
from style.stylemanager import FontManager
from gedcom_options import gvOptions

_log = logging.getLogger(__name__.lower())

class GedcomVisualGUI:
    """Lightweight wrapper that constructs and controls the main VisualMapFrame.

    The wrapper keeps calling code simple: create an instance with the global
    options object (gOp) and a parent window (or None), then call start() to
    show the UI and stop() to request shutdown.

    Attributes:
        font_manager: The FontManager instance used by the GUI.
        gOp: The global options / state object.
        frame: The application's main frame (VisualMapFrame).
    """
    # runtime attributes with basic type hints
    font_manager: FontManager
    gOp: gvOptions
    frame: VisualMapFrame

    def __init__(self, gOp: Any, parent: wx.Window | None, title: str,
                 style: int = wx.DEFAULT_FRAME_STYLE) -> None:
        """
        Create the main application frame.

        Args:
            gOp: Global options / state object (implementation-specific).
            parent: Parent wx window (or None).
            title: Window title.
            size: Initial window size as (width, height).
            style: wx frame style flags.
        """
        self.font_manager = FontManager()
        self.gOp = gOp

        size: Tuple[int, int] = gOp.get('window_size', None)
        self.frame: VisualMapFrame = VisualMapFrame(
            parent, gOp=self.gOp, font_manager=self.font_manager,
            title=title, size=size, style=style)

    def start(self) -> None:
        """Start the GUI by delegating to the main frame's start method."""
        self.frame.start()

    def stop(self) -> None:
        """Request shutdown by delegating to the main frame's stop method."""
        self.frame.stop()