"""GUI package init — best-effort re-exports for refactored GUI modules.

Importing this package will not fail if individual modules have import-time errors;
callers can still import modules directly (e.g. `from gui.person_dialog import PersonDialog`).
"""
__all__ = []

# Frames / Panels / Controls
try:
    from .visual_map_frame import VisualMapFrame  # type: ignore
    __all__.append("VisualMapFrame")
except Exception:
    pass

try:
    from .gedcomVisualGUI import VisualMapPanel  # type: ignore
    __all__.append("VisualMapPanel")
except Exception:
    pass

try:
    from .gedcomVisualGUI import VisualGedcomIds  # type: ignore
    __all__.append("VisualGedcomIds")
except Exception:
    pass

try:
    from .people_list_ctrl import PeopleListCtrl  # type: ignore
    __all__.append("PeopleListCtrl")
except Exception:
    pass

try:
    from .gedcomVisualGUI import PeopleListCtrlPanel  # type: ignore
    __all__.append("PeopleListCtrlPanel")
except Exception:
    pass

# Dialogs & helpers
try:
    from .gedcomDialogs import HTMLDialog  # type: ignore
    __all__.append("HTMLDialog")
except Exception:
    pass

try:
    from .gedcomDialogs import AboutDialog  # type: ignore
    __all__.append("AboutDialog")
except Exception:
    pass

try:
    from .gedcomDialogs import HelpDialog  # type: ignore
    __all__.append("HelpDialog")
except Exception:
    pass

try:
    from .gedcomDialogs import ConfigDialog  # type: ignore
    __all__.append("ConfigDialog")
except Exception:
    pass

try:
    from .gedcomDialogs import PersonDialog  # type: ignore
    __all__.append("PersonDialog")
except Exception:
    pass

try:
    from .gedcomDialogs import FindDialog  # type: ignore
    __all__.append("FindDialog")
except Exception:
    pass

# Panels and background actions
try:
    from .gedcomDialogs import FamilyPanel  # type: ignore
    __all__.append("FamilyPanel")
except Exception:
    pass

try:
    from .gedcomDialogs import BackgroundActions  # type: ignore
    __all__.append("BackgroundActions")
except Exception:
    pass

# Utility: keep this file lightweight; import modules directly if you need full traceback.