__all__ = ['AboutDialog', 'HelpDialog', 'ConfigDialog', 'PersonDialog', 'FindDialog', 'BackgroundActions']

import _thread
import logging
import logging.config
import time

import requests
from io import BytesIO
from pathlib import Path
import os
import platform
import wx
import wx.lib.newevent
import wx.html
import wx.grid as gridlib
from models.LatLon import LatLon
from models.Person import Person, LifeEvent
from gedcom.gedcomdate import CheckAge, maxage
from gedcomoptions import gvOptions, ResultsType
from style.stylemanager import FontManager

from const import VERSION, GUINAME, ABOUTLINK, NAME
from gui.gedcomvisual import ParseAndGPS, doHTML, doKML, doKML2, doSUM, doTraceTo

maxPhotoWidth = 400  # Maximum width for photos in the PersonDialog
maxPhotoHeight = 500  # Maximum Height for photos in the PersonDialog

_log = logging.getLogger(__name__.lower())

UpdateBackgroundEvent = None

# Import HTMLDialog from the new module (package-aware fallback)
try:
    from .html_dialog import HTMLDialog
except Exception:
    try:
        from html_dialog import HTMLDialog
    except Exception:
        HTMLDialog = None

try:
    from .about_dialog import AboutDialog
except Exception:
    try:
        from about_dialog import AboutDialog
    except Exception:
        AboutDialog = None

try:
    from .help_dialog import HelpDialog
except Exception:
    try:
        from help_dialog import HelpDialog
    except Exception:
        HelpDialog = None

try:
    from .config_dialog import ConfigDialog
except Exception:
    try:
        from config_dialog import ConfigDialog
    except Exception:
        ConfigDialog = None
try:
    from .family_panel import FamilyPanel
except Exception:
    try:
        from family_panel import FamilyPanel
    except Exception:
        FamilyPanel = None

try:
    from .person_dialog import PersonDialog
except Exception:
    try:
        from person_dialog import PersonDialog
    except Exception:
        PersonDialog = None
        
try:
    from .find_dialog import FindDialog
except Exception:
    try:
        from find_dialog import FindDialog
    except Exception:
        FindDialog = None

try:
    from .background_actions import BackgroundActions
except Exception:
    try:
        from background_actions import BackgroundActions
    except Exception:
        BackgroundActions = None

