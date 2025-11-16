# __all__ = ['AboutDialog', 'HelpDialog', 'ConfigDialog', 'PersonDialog', 'FindDialog', 'BackgroundActions']

import _thread
import logging
import logging.config
import time
from io import BytesIO
from pathlib import Path
import os
import platform
from typing import TYPE_CHECKING, Optional

import requests
import wx
import wx.lib.newevent
import wx.html
import wx.grid as gridlib

# Lightweight model imports ok at module import time
from models.LatLon import LatLon
from models.Person import Person, LifeEvent
from gedcom.gedcomdate import CheckAge, maxage

# Type-only imports to avoid import-time circular dependencies / heavy modules
if TYPE_CHECKING:
    from gedcomoptions import gvOptions, ResultsType
    from style.stylemanager import FontManager
    # If you need to reference these names for typing elsewhere, keep them in TYPE_CHECKING

# Defer heavy or cross-package imports (like gui.gedcomvisual) to where they're used.
# This file should not import ParseAndGPS/doHTML/doKML at module level.

from const import VERSION, GUINAME, ABOUTLINK, NAME

maxPhotoWidth = 400  # Maximum width for photos in the PersonDialog
maxPhotoHeight = 500  # Maximum Height for photos in the PersonDialog

_log = logging.getLogger(__name__.lower())

UpdateBackgroundEvent = None