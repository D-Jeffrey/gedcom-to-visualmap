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

import wx
import wx.lib.mixins.inspection as wit
# pylint: disable=no-member

# Import constants and GUI components
from const import GUINAME, LOG_CONFIG, NAME, VERSION
from gui.core.gedcom_visual_gui import GedcomVisualGUI
from gedcom_options import gvOptions

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
        app = MyWittedApp()
    else:  # Normal mode
        app = wx.App()

    # Load gedcom options
    gOp = gvOptions()

    # Create the main application frame and panel
    frame = GedcomVisualGUI(gOp=gOp, parent=None, title=GUINAME)
    
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