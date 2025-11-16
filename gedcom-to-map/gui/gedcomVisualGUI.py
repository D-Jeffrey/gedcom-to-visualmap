__all__ = ['VisualGedcomIds', 'VisualMapFrame', 'PeopleListCtrl', 'PeopleListCtrlPanel', 'VisualMapPanel']

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
#
#
#  gedcomVisualGUI.py : GUI Interface  for gedcom-to-map
#    See https://github.com/D-Jeffrey/gedcom-to-visualmap
#
#
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
#!/usr/bin/env python

import logging

from gui.visual_map_frame import VisualMapFrame

_log = logging.getLogger(__name__.lower())

InfoBoxLines = 8

class GedcomVisualGUI:
    def __init__(self, parent, title, size=(1024, 800), style=None):
        self.frame = VisualMapFrame(parent, title=title, size=size, style=style)

    def start(self):
        self.frame.start()

    def stop(self):
        self.frame.stop()