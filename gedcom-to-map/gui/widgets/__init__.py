"""
Custom widget components.

Reusable UI controls and displays.
"""
try:
    from .people_list_ctrl import PeopleListCtrl
    __all__ = ['PeopleListCtrl']
except ImportError:
    __all__ = []

try:
    from .ged_rec_display import GedRecordDialog
    __all__.append('GedRecordDialog')
except ImportError:
    pass
