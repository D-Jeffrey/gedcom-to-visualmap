# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
#
#
#  gedcom_visual_gui.py : GUI Interface  for gedcom-to-map
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
from ..layout.font_manager import FontManager
from ..layout.colour_manager import ColourManager
from services.interfaces import IConfig, IState, IProgressTracker

_log = logging.getLogger(__name__.lower())

class GedcomVisualGUI:
    """Lightweight wrapper that constructs and controls the main VisualMapFrame.

    The wrapper keeps calling code simple: create an instance with services
    and a parent window (or None), then call start() to show the UI and stop()
    to request shutdown.

    Attributes:
        font_manager: The FontManager instance used by the GUI.
        color_manager: The ColourManager instance used by the GUI.
        svc_config: Configuration service (IConfig).
        svc_state: Runtime state service (IState).
        svc_progress: Progress tracking service (IProgressTracker).
        frame: The application's main frame (VisualMapFrame).
    """
    # runtime attributes with basic type hints
    font_manager: FontManager
    color_manager: ColourManager
    svc_config: IConfig
    svc_state: IState
    svc_progress: IProgressTracker
    frame: VisualMapFrame

    def __init__(
        self,
        parent: wx.Window | None,
        svc_config: 'IConfig',
        svc_state: 'IState',
        svc_progress: 'IProgressTracker',
        title: str,
        style: int = wx.DEFAULT_FRAME_STYLE,
    ) -> None:
        """Create the main application frame.

        Args:
            parent: Parent wx window (or None).
            svc_config: Configuration service (IConfig).
            svc_state: Runtime state service (IState).
            svc_progress: Progress tracking service (IProgressTracker).
            title: Window title.
            style: wx frame style flags (default: wx.DEFAULT_FRAME_STYLE).
        """
        self.font_manager: 'FontManager' = FontManager()
        self.color_manager: 'ColourManager' = ColourManager(svc_config._gui_colors if hasattr(svc_config, '_gui_colors') else {})
        self.svc_config: 'IConfig' = svc_config
        self.svc_state: 'IState' = svc_state
        self.svc_progress: 'IProgressTracker' = svc_progress

        # Get window size from config
        size = svc_config.get('window_size', [1024, 800])
        self.frame: 'VisualMapFrame' = VisualMapFrame(
            parent, svc_config=svc_config, svc_state=svc_state, svc_progress=svc_progress,
            font_manager=self.font_manager, color_manager=self.color_manager, title=title, size=size, style=style)

    def start(self) -> None:
        """Start the GUI by delegating to the main frame's start method."""
        self.frame.start()

    def stop(self) -> None:
        """Request shutdown by delegating to the main frame's stop method."""
        self.frame.stop()
