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
from const import GUINAME, LOG_CONFIG, NAME, VERSION, panel
from gedcomVisualGUI import VisualMapFrame, VisualMapPanel

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

    # Create the main application frame
    visualFrame = VisualMapFrame(None, title=GUINAME, size=(1024, 800), style=wx.DEFAULT_FRAME_STYLE)

    # Create and set up the main panel within the frame
    panel = VisualMapPanel(visualFrame)
    visualFrame.panel = panel
    panel.SetupOptions()  # Configure panel options
    
    
    # Show the inspection tool if WITMODE is enabled
    if WITMODE:
        app.ShowInspectionTool()

    # Display the main frame
    visualFrame.Show()

    # Start the application's main event loop
    app.MainLoop()
    if panel:
        panel.OnCloseWindow()
    # Log the shutdown message
    _log.info('Finished')

    # Exit the program
    exit(0)