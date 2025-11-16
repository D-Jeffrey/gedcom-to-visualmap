__all__ = ['AboutDialog', 'HelpDialog', 'ConfigDialog', 'PersonDialog', 'FindDialog', 'BackgroundActions']

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

# Import small dialog helper modules (package-aware). These modules are lightweight.
try:
    from .html_dialog import HTMLDialog
except Exception:
    try:
        from html_dialog import HTMLDialog
    except Exception:
        HTMLDialog = None

# Load dialog classes from their extracted modules (they are small). Keep fallbacks.
try:
    from .about_dialog import AboutDialog
except Exception:
    AboutDialog = None

try:
    from .help_dialog import HelpDialog
except Exception:
    HelpDialog = None

try:
    from .config_dialog import ConfigDialog
except Exception:
    ConfigDialog = None

try:
    from .family_panel import FamilyPanel
except Exception:
    FamilyPanel = None

try:
    from .person_dialog import PersonDialog
except Exception:
    PersonDialog = None

try:
    from .find_dialog import FindDialog
except Exception:
    FindDialog = None

# BackgroundActions has been moved and already does lazy imports internally.
try:
    from .background_actions import BackgroundActions
except Exception:
    BackgroundActions = None

