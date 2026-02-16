"""Action handlers: Background processing, file operations, and user actions.

Provides action handlers for user interactions and background operations:
    - VisualMapActions: Coordinates map generation, file operations, and reports
    - BackgroundActions: Background worker thread for long-running operations
    - Geoheatmap: Geospatial heatmap generation
    - FileOpener: Platform-specific file opening utility
    - DoActionsType: Enum for background operation types
    - gedcom_to_map: Map generation orchestration
"""

# Best-effort lazy exports so this package can be imported in non-GUI
# environments (e.g. Ubuntu CI core lane without wxPython).
__all__ = []

try:
    from .visual_map_actions import VisualMapActions, Geoheatmap, gedcom_to_map

    __all__.extend(["VisualMapActions", "Geoheatmap", "gedcom_to_map"])
except ImportError:
    pass

try:
    from .background_actions import BackgroundActions

    __all__.append("BackgroundActions")
except ImportError:
    pass

try:
    from .file_operations import FileOpener

    __all__.append("FileOpener")
except ImportError:
    pass

try:
    from .do_actions_type import DoActionsType

    __all__.append("DoActionsType")
except ImportError:
    pass
