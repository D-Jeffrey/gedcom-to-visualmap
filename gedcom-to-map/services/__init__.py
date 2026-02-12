"""Services package: Core application services and dependency interfaces.

Provides service implementations for:
    - Configuration management (IConfig → GVConfig)
    - Runtime state tracking (IState → GVState)
    - Progress reporting (IProgressTracker → GVProgress)

All services use a Protocol-based interface (Python structural subtyping) for loose coupling.
Services are injected as dependencies throughout the application.

Key classes:
    - IConfig, GVConfig: Application configuration and settings
    - IState, GVState: Runtime state with people, genealogical data
    - IProgressTracker, GVProgress: Progress and stop-request tracking

Usage:
    >>> from services import GVConfig, GVState, GVProgress
    >>> config = GVConfig()
    >>> state = GVState()
    >>> progress = GVProgress()
"""

from .config_service import GVConfig
from .state_service import GVState
from .progress_service import GVProgress
from .interfaces import IConfig, IState, IProgressTracker

__all__ = [
    # Implementations
    "GVConfig",
    "GVState",
    "GVProgress",
    # Interfaces
    "IConfig",
    "IState",
    "IProgressTracker",
]
