"""
Dialog windows.

Various dialog windows for configuration, help, search, and data display.
"""
try:
    from .about_dialog import AboutDialog
    __all__ = ['AboutDialog']
except ImportError:
    __all__ = []

try:
    from .config_dialog import ConfigDialog
    __all__.append('ConfigDialog')
except ImportError:
    pass

try:
    from .find_dialog import FindDialog
    __all__.append('FindDialog')
except ImportError:
    pass

try:
    from .help_dialog import HelpDialog
    __all__.append('HelpDialog')
except ImportError:
    pass

try:
    from .html_dialog import HTMLDialog
    __all__.append('HTMLDialog')
except ImportError:
    pass

try:
    from .person_dialog import PersonDialog
    __all__.append('PersonDialog')
except ImportError:
    pass
