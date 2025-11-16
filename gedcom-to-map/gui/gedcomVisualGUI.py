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

import _thread
import logging
import logging.config
import os
import math
import os.path
from pathlib import Path
import re
import subprocess
import shutil
import sys
import time
from datetime import datetime
import webbrowser
from warnings import catch_warnings
from models.Person import Person
from gedcom.gedcomdate import CheckAge 
from typing import Dict, Union

import wx
# pylint: disable=no-member
import wx.lib.mixins.listctrl as listmix
import wx.lib.sized_controls as sc
import wx.lib.mixins.inspection as wit
import wx.lib.newevent
import wx.html
import wx.grid
import xyzservices.providers as xyz 


from const import GUINAME, KMLMAPSURL, LOG_CONFIG, NAME, VERSION
from gedcomoptions import gvOptions, ResultsType 
from gui.visual_map_frame import VisualMapFrame
from gui.visual_map_panel import VisualMapPanel
from gui.gedcomvisual import doTrace
from gui.gedcomDialogs import *
from style.stylemanager import FontManager


_log = logging.getLogger(__name__.lower())


InfoBoxLines = 8

from wx.lib.embeddedimage import PyEmbeddedImage


# Use the moved VisualGedcomIds implementation
try:
    from .visual_gedcom_ids import VisualGedcomIds
except Exception:
    try:
        from visual_gedcom_ids import VisualGedcomIds
    except Exception:
        # Minimal fallback so module import still succeeds in degraded environments
        class VisualGedcomIds:
            def __init__(self):
                self.m = {}
                self.ids = []
                self.IDs = {}
            def GetColor(self, _name, default=wx.WHITE):
                return default

# Use the moved PeopleListCtrlPanel implementation
try:
    from .people_list_ctrl_panel import PeopleListCtrlPanel
except Exception:
    try:
        from people_list_ctrl_panel import PeopleListCtrlPanel
    except Exception:
        # fallback stub to avoid import-time failure
        class PeopleListCtrlPanel(wx.Panel):
            def __init__(self, parent, people, font_manager, *args, **kw):
                super().__init__(parent, *args, **kw)
                wx.StaticText(self, -1, "PeopleListCtrlPanel unavailable")
