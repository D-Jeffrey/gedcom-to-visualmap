"""GUI package init — best-effort re-exports for refactored GUI modules.

Importing this package will not fail if individual modules have import-time errors;
callers can still import modules directly (e.g. `from gui.person_dialog import PersonDialog`).
"""
__all__ = []

from .visual_map_frame import VisualMapFrame  # type: ignore
__all__.append("VisualMapFrame")

from .gedcomVisualGUI import VisualMapPanel  # type: ignore
__all__.append("VisualMapPanel")

from .gedcomVisualGUI import VisualGedcomIds  # type: ignore
__all__.append("VisualGedcomIds")

from .people_list_ctrl import PeopleListCtrl  # type: ignore
__all__.append("PeopleListCtrl")

from .gedcomVisualGUI import PeopleListCtrlPanel  # type: ignore
__all__.append("PeopleListCtrlPanel")

from .html_dialog import HTMLDialog  # type: ignore
__all__.append("HTMLDialog")

from .about_dialog import AboutDialog  # type: ignore
__all__.append("AboutDialog")

from .help_dialog import HelpDialog  # type: ignore
__all__.append("HelpDialog")

from .config_dialog import ConfigDialog  # type: ignore
__all__.append("ConfigDialog")

from .person_dialog import PersonDialog  # type: ignore
__all__.append("PersonDialog")

from .find_dialog import FindDialog  # type: ignore
__all__.append("FindDialog")

from .family_panel import FamilyPanel  # type: ignore
__all__.append("FamilyPanel")

from .background_actions import BackgroundActions  # type: ignore
__all__.append("BackgroundActions")