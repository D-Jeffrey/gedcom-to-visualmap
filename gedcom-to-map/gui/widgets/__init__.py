"""Custom widgets: Reusable wxPython UI controls and displays.

Provides custom widget implementations:
    - PeopleListCtrl: Advanced list control with people data and sorting
    - GedRecordDialog: Display raw GEDCOM record details
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
