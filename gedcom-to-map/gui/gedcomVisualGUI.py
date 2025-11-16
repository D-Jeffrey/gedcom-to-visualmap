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


from .visual_gedcom_ids import VisualGedcomIds

from .people_list_ctrl_panel import PeopleListCtrlPanel