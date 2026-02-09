# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
#
#
#    gv.py : main for gedcom-to-map
#    See https://github.com/D-Jeffrey/gedcom-to-visualmap
#
#
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
#!/usr/bin/env python

import logging
import logging.config
import os
import sys

# Configure GTK environment for Linux/WSL to prevent widget sizing warnings
if sys.platform.startswith('linux'):
    # Disable client-side decorations that can cause sizing issues
    os.environ.setdefault('GTK_CSD', '0')
    # Disable DPI scaling to prevent negative height calculations
    os.environ.setdefault('GDK_SCALE', '1')
    # Use a stable GTK theme if not already set
    os.environ.setdefault('GTK_THEME', 'Adwaita')

import wx
import wx.lib.mixins.inspection as wit
# pylint: disable=no-member


# Import constants and GUI components
from const import GUINAME, LOG_CONFIG, NAME, VERSION
from gui.core.gedcom_visual_gui import GedcomVisualGUI
from services.config_service import GVConfig
from services.state_service import GVState
from services.progress_service import GVProgress

# Define the path to gedcom_options.yaml as a constant (same directory as gv.py)
from pathlib import Path
GV_DIR = Path(__file__).resolve().parent
GEDCOM_OPTIONS_PATH = GV_DIR / 'gedcom_options.yaml'

# Initialize logger for the application
_log = logging.getLogger(__name__)

# Define a custom wx.App class with inspection capabilities for debugging
class MyWittedApp(wx.App, wit.InspectionMixin):
    def OnInit(self):
        # Initialize the inspection tool
        self.Init()
        return True

# Main entry point of the program
if __name__ == '__main__':
    # WITMODE is a flag for enabling debugging tools.  Normal is False
    WITMODE = False

    # Configure logging using the specified configuration
    logging.config.dictConfig(LOG_CONFIG)

    # Log the startup message with application name and version
    _log.info("Starting up %s %s", NAME, VERSION)

    # Create the application instance based on WITMODE
    if WITMODE:  # Debugging mode
        app = MyWittedApp(redirect=False)
    else:  # Normal mode
        app = wx.App(redirect=False)


    # Instantiate services with the options file constant
    svc_config = GVConfig(gedcom_options_path=GEDCOM_OPTIONS_PATH)
    svc_state = GVState()
    svc_progress = GVProgress()
    
    # Create app hooks to connect geo_gedcom progress to GUI services
    from gui.core import GuiHooks
    svc_config.app_hooks = GuiHooks(svc_progress, svc_state)

    # Create the main application frame and panel with explicit services
    frame = GedcomVisualGUI(parent=None, svc_config=svc_config, svc_state=svc_state, svc_progress=svc_progress, title=GUINAME)
    
    # Show the inspection tool if WITMODE is enabled
    if WITMODE:
        app.ShowInspectionTool()

    # Display the main frame
    frame.start()
    
    # Start the application's main event loop
    app.MainLoop()

    # Clean up and stop the application
    frame.stop()
    _log.info('Finished')

    # Exit the program
    exit(0)