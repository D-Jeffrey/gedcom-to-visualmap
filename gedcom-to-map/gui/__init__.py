"""GUI package init — best-effort re-exports for refactored GUI modules.

Importing this package will not fail if individual modules have import-time errors;
callers can still import modules directly (e.g. `from gui.person_dialog import PersonDialog`).
"""

from .visual_map_frame import VisualMapFrame  # type: ignore
from .visual_map_panel import VisualMapPanel  # type: ignore
from .visual_gedcom_ids import VisualGedcomIds  # type: ignore
from .people_list_ctrl import PeopleListCtrl  # type: ignore
from .people_list_ctrl_panel import PeopleListCtrlPanel  # type: ignore
from .html_dialog import HTMLDialog  # type: ignore
from .about_dialog import AboutDialog  # type: ignore
from .help_dialog import HelpDialog  # type: ignore
from .config_dialog import ConfigDialog  # type: ignore
from .person_dialog import PersonDialog  # type: ignore
from .find_dialog import FindDialog  # type: ignore
from .family_panel import FamilyPanel  # type: ignore
from .background_actions import BackgroundActions  # type: ignore
from .font_manager import FontManager  # type: ignore
from .ged_rec_display import GedRecordDialog  # type: ignore

__all__ = [
    "VisualMapFrame",
    "VisualMapPanel",
    "VisualGedcomIds",
    "PeopleListCtrl",
    "PeopleListCtrlPanel",
    "HTMLDialog",
    "AboutDialog",
    "HelpDialog",
    "ConfigDialog",
    "PersonDialog",
    "FindDialog",
    "FamilyPanel",
    "BackgroundActions",
    "FontManager",
    "ged_rec_display",
]