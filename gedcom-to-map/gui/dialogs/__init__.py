"""Dialog windows: Configuration, help, search, and data display dialogs.

Provides modal dialogs for user interaction:
    - AboutDialog: About/credits information
    - ConfigDialog: Application configuration settings
    - FindDialog: Search/find functionality
    - HelpDialog: Help documentation
    - HTMLDialog: Generic HTML content display
    - PersonDialog: Individual genealogical data display
    - SimpleMessageDialog: Themed message dialog (replaces wx.MessageBox for dark mode)

All dialogs are lazy-loaded with error handling to support import without wxPython.
"""

try:
    from .about_dialog import AboutDialog

    __all__ = ["AboutDialog"]
except ImportError:
    __all__ = []

try:
    from .config_dialog import ConfigDialog

    __all__.append("ConfigDialog")
except ImportError:
    pass

try:
    from .find_dialog import FindDialog

    __all__.append("FindDialog")
except ImportError:
    pass

try:
    from .help_dialog import HelpDialog

    __all__.append("HelpDialog")
except ImportError:
    pass

try:
    from .html_dialog import HTMLDialog

    __all__.append("HTMLDialog")
except ImportError:
    pass

try:
    from .person_dialog import PersonDialog

    __all__.append("PersonDialog")
except ImportError:
    pass

try:
    from .simple_message_dialog import SimpleMessageDialog

    __all__.append("SimpleMessageDialog")
except ImportError:
    pass
