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

_log = logging.getLogger(__name__.lower())

InfoBoxLines: int = 8


class GedcomVisualGUI:
    """Lightweight wrapper that constructs and controls the main VisualMapFrame.

    The wrapper keeps calling code simple: create an instance with the global
    options object (gOp) and a parent window (or None), then call start() to
    show the UI and stop() to request shutdown.

    Attributes:
        frame: The application's main frame (VisualMapFrame).
    """

    def __init__(self, gOp: Any, parent: wx.Window | None, title: str,
                 size: Tuple[int, int] = (1024, 800),
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
        self.frame: VisualMapFrame = VisualMapFrame(parent, title=title, size=size, style=style, gOp=gOp)

    def start(self) -> None:
        """Start the GUI by delegating to the main frame's start method."""
        self.frame.start()

    def stop(self) -> None:
        """Request shutdown by delegating to the main frame's stop method."""
        self.frame.stop()