"""services.py

Service interfaces and implementations for dependency injection.

This module provides:
- Protocol-based interfaces for core application services
- Concrete implementations of configuration, state, progress tracking, etc.
- ServiceContainer for dependency injection and service registration
"""

from __future__ import annotations

import logging
import time
import threading
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Protocol, Dict, Any, Optional, Union, TypeVar, Type, TYPE_CHECKING
from dataclasses import dataclass, field

from geo_gedcom.person import Person
from geo_gedcom.lat_lon import LatLon
from geo_gedcom.geolocated_gedcom import GeolocatedGedcom

# Use TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    from render.referenced import Referenced

_log = logging.getLogger(__name__)

# Type variables for generic service container
T = TypeVar("T")

# ============================================================================
# Service Interfaces (Protocols)
# ============================================================================


class IConfig(Protocol):
    """Read-only configuration interface.

    Provides access to application configuration loaded from YAML
    and persisted user settings from INI file.
    """

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by key."""
        ...

    def has(self, key: str) -> bool:
        """Check if a configuration key exists."""
        ...

    def get_file_command(self, file_type: str) -> Optional[str]:
        """Get the file opening command for a specific file type."""
        ...

    @property
    def gedcom_input(self) -> str:
        """Path to the GEDCOM input file."""
        ...

    @property
    def results_file(self) -> str:
        """Path to the results/output file."""
        ...

    @property
    def geo_config_file(self) -> Path:
        """Path to the geo configuration file."""
        ...

    @property
    def use_gps(self) -> bool:
        """Whether to use GPS/geocoding."""
        ...

    @use_gps.setter
    def use_gps(self, value: bool) -> None:
        """Set whether to use GPS/geocoding."""
        ...

    @property
    def result_type(self):
        """Type of output to generate (HTML, KML, KML2, SUM)."""
        ...

    @property
    def result_file(self) -> str:
        """Output file path."""
        ...

    @property
    def file_open_commands(self):
        """File open command lines for different file types."""
        ...

    @property
    def map_style(self) -> str:
        """Map tile style/type for HTML maps."""
        ...

    @property
    def info_box_lines(self) -> int:
        """Number of info box lines to display in UI."""
        ...


class IAppHooks(Protocol):
    """Application hooks interface for progress reporting and callbacks.

    Provides hooks for GEDCOM parsing and geocoding operations to report
    progress and check for user-requested stops.
    """

    def report_step(
        self,
        state: str = None,
        info: str = None,
        target: int = -1,
        reset_counter: bool = False,
        plus_step: int = 1,
        set_counter: int = None,
    ) -> None:
        """Report progress from parsing/geocoding operations.

        Args:
            state: Description of current step
            info: Additional information about progress
            target: Target count for this step
            reset_counter: Whether to reset progress counter
            plus_step: Amount to increment counter
            set_counter: Directly set counter to this value
        """
        ...

    def stop_requested(self) -> bool:
        """Check if a stop has been requested by the user.

        Returns:
            bool: True if stop requested, False otherwise
        """
        ...

    def update_key_value(self, key: str, value) -> None:
        """Update a key-value pair in the application state.

        Args:
            key: State key to update
            value: New value for the key
        """
        ...

    def add_time_reference(self, gedcom_date) -> None:
        """Add a time reference for timeline tracking.

        Args:
            gedcom_date: GEDCOM date object to add
        """
        ...


class IState(Protocol):
    """Mutable runtime state interface.

    Manages application state that changes during execution,
    such as parsed data, lookup services, and runtime flags.
    """

    people: Optional[Dict[str, Person]]
    """Dictionary of parsed Person objects keyed by ID."""

    lookup: Optional[GeolocatedGedcom]
    """Geolocated GEDCOM lookup service."""

    referenced: Any
    """Set of referenced person IDs."""

    main_person: Optional[Person]
    """The main/root person for lineage tracing."""

    parsed: bool
    """Whether GEDCOM has been successfully parsed."""

    stopping: bool
    """Whether a stop has been requested."""

    running: bool
    """Whether an operation is currently running."""

    newload: bool
    """Whether new data has been loaded."""

    def clear(self) -> None:
        """Clear all runtime state."""
        ...


class IProgressTracker(Protocol):
    """Progress tracking interface.

    Manages progress counters, state descriptions, and timing
    for long-running operations.
    """

    counter: int
    """Current progress counter value."""

    target: int
    """Target/total value for progress."""

    state: str
    """Current state description."""

    running: bool
    """Whether an operation is currently running."""

    stopping: bool
    """Whether a stop has been requested."""

    step_info: Optional[str]
    """Additional information about current step."""

    running_since: float
    """Timestamp when current operation started."""

    running_since_step: float
    """Timestamp (as float) when current step with target started."""

    running_last: float
    """Duration in seconds of the last completed operation."""

    def step(self, state: str = "", reset_counter: bool = True, target: int = 0, plus_step: int = 1) -> bool:
        """Advance to a new step in the operation."""
        ...

    def stopstep(self) -> None:
        """Mark the current step as complete."""
        ...

    def reset(self) -> None:
        """Reset all progress tracking."""
        ...

    def stop(self) -> None:
        """Stop the current operation and reset state/progress.

        This method:
        - Stops the running operation
        - Resets running and stopping flags
        - Resets progress counters

        Thread-safe when implemented with proper locking.
        """
        ...

    def keep_going(self) -> bool:
        """Check if operation should continue (not stopped)."""
        ...

    def should_stop(self) -> bool:
        """Check if operation should stop."""
        ...


class IFileManager(Protocol):
    """File management interface.

    Manages input/output file paths and related settings.
    """

    def set_input(self, filepath: str) -> None:
        """Set the GEDCOM input file path."""
        ...

    def set_results_file(self, filepath: str) -> None:
        """Set the results/output file path."""
        ...

    def set_main(self, person_id: str) -> None:
        """Set the main person ID."""
        ...

    def get_cache_file(self) -> Path:
        """Get the GPS cache file path."""
        ...


# ============================================================================
# Concrete Implementations
# ============================================================================


@dataclass
class Config:
    """Concrete implementation of IConfig.

    Loads configuration from YAML and INI files, provides read-only
    access to configuration values.
    """

    _options: Dict[str, Any] = field(default_factory=dict)
    _attributes: Dict[str, Any] = field(default_factory=dict)
    _file_commands: Dict[str, str] = field(default_factory=dict)
    _geo_config_file: Path = field(default_factory=lambda: Path.cwd())
    _app_hooks: Optional[Any] = None  # AppHooks instance

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by key."""
        return self._attributes.get(key, default)

    def has(self, key: str) -> bool:
        """Check if a configuration key exists."""
        return key in self._attributes

    def get_file_command(self, file_type: str) -> Optional[str]:
        """Get the file opening command for a specific file type."""
        return self._file_commands.get(file_type.lower())

    @property
    def gedcom_input(self) -> str:
        """Path to the GEDCOM input file."""
        return self._attributes.get("GEDCOMinput", "")

    @property
    def results_file(self) -> str:
        """Path to the results/output file."""
        return self._attributes.get("resultsfile", "")

    @property
    def geo_config_file(self) -> Path:
        """Path to the geo configuration file."""
        return self._geo_config_file

    @property
    def use_gps(self) -> bool:
        """Whether to use GPS/geocoding."""
        # Reference the geocode_only attribute (from geocoding_options)
        return bool(getattr(self, "geocode_only", self._attributes.get("geocode_only", True)))

    @use_gps.setter
    def use_gps(self, value: bool) -> None:
        """Set whether to use GPS/geocoding."""
        self.geocode_only = bool(value)

    @property
    def result_type(self):
        """Type of output to generate (HTML, KML, KML2, SUM)."""
        return self._attributes.get("ResultType", None)

    @property
    def result_file(self) -> str:
        """Output file path."""
        return self._attributes.get("ResultFile", "")

    @property
    def map_style(self) -> str:
        """Map tile style/type for HTML maps."""
        return self._attributes.get("MapStyle", "CartoDB.Voyager")

    @property
    def info_box_lines(self) -> int:
        """Number of info box lines to display in UI."""
        return int(self._attributes.get("infoBoxLines", 8))

    @property
    def app_hooks(self) -> Optional[Any]:
        """Get the application hooks instance."""
        return self._app_hooks

    @app_hooks.setter
    def app_hooks(self, value: Optional[Any]) -> None:
        """Set the application hooks instance."""
        self._app_hooks = value

    def set(self, key: str, value: Any) -> None:
        """Set a configuration value (internal use only)."""
        self._attributes[key] = value

    def set_file_command(self, file_type: str, command: str) -> None:
        """Set file opening command (internal use only)."""
        self._file_commands[file_type.lower()] = command


@dataclass
class RuntimeState:
    """Concrete implementation of IState.

    Manages mutable runtime state that changes during application execution.
    """

    _people: Optional[Dict[str, Person]] = None
    _lookup: Optional[GeolocatedGedcom] = None
    _referenced: Any = None  # Referenced type to avoid circular import
    _main_person: Optional[Person] = None
    _parsed: bool = False
    _stopping: bool = False
    _running: bool = False
    _newload: bool = False
    _selected_people: int = 0
    _heritage: Optional[Dict[str, Any]] = None
    _lastlines: Optional[Dict[str, Any]] = None
    _main_person_lat_lon: Optional[LatLon] = None
    _gps_file: Optional[Path] = None
    _step_info: str = ""

    def __post_init__(self):
        """Initialize default values that require imports."""
        if self._referenced is None:
            # Lazy import to avoid circular dependency
            from render.referenced import Referenced

            self._referenced = Referenced()

    @property
    def people(self) -> Optional[Dict[str, Person]]:
        return self._people

    @people.setter
    def people(self, value: Optional[Dict[str, Person]]) -> None:
        self._people = value

    @property
    def lookup(self) -> Optional[GeolocatedGedcom]:
        return self._lookup

    @lookup.setter
    def lookup(self, value: Optional[GeolocatedGedcom]) -> None:
        self._lookup = value

    @property
    def referenced(self) -> Referenced:
        return self._referenced

    @referenced.setter
    def referenced(self, value: Referenced) -> None:
        self._referenced = value

    @property
    def main_person(self) -> Optional[Person]:
        return self._main_person

    @main_person.setter
    def main_person(self, value: Optional[Person]) -> None:
        self._main_person = value

    @property
    def parsed(self) -> bool:
        return self._parsed

    @parsed.setter
    def parsed(self, value: bool) -> None:
        self._parsed = value

    @property
    def stopping(self) -> bool:
        return self._stopping

    @stopping.setter
    def stopping(self, value: bool) -> None:
        self._stopping = value

    @property
    def running(self) -> bool:
        return self._running

    @running.setter
    def running(self, value: bool) -> None:
        self._running = value

    @property
    def newload(self) -> bool:
        return self._newload

    @newload.setter
    def newload(self, value: bool) -> None:
        self._newload = value

    @property
    def selected_people(self) -> int:
        return self._selected_people

    @selected_people.setter
    def selected_people(self, value: int) -> None:
        self._selected_people = value

    @property
    def heritage(self) -> Optional[Dict[str, Any]]:
        return self._heritage

    @heritage.setter
    def heritage(self, value: Optional[Dict[str, Any]]) -> None:
        self._heritage = value

    @property
    def lastlines(self) -> Optional[Dict[str, Any]]:
        return self._lastlines

    @lastlines.setter
    def lastlines(self, value: Optional[Dict[str, Any]]) -> None:
        self._lastlines = value

    @property
    def main_person_lat_lon(self) -> Optional[LatLon]:
        return self._main_person_lat_lon

    @main_person_lat_lon.setter
    def main_person_lat_lon(self, value: Optional[LatLon]) -> None:
        self._main_person_lat_lon = value

    @property
    def gps_file(self) -> Optional[Path]:
        return self._gps_file

    @gps_file.setter
    def gps_file(self, value: Optional[Path]) -> None:
        self._gps_file = value

    @property
    def step_info(self) -> str:
        return self._step_info

    @step_info.setter
    def step_info(self, value: str) -> None:
        self._step_info = value

    def clear(self) -> None:
        """Clear all runtime state."""
        from render.referenced import Referenced

        self._people = None
        self._lookup = None
        self._referenced = Referenced()
        self._main_person = None
        self._parsed = False
        self._stopping = False
        self._running = False
        self._newload = False
        self._selected_people = 0
        self._heritage = None
        self._lastlines = None
        self._main_person_lat_lon = None
        self._gps_file = None


@dataclass
class ProgressTracker:
    """Concrete implementation of IProgressTracker.

    Tracks progress, state, and timing for long-running operations.
    """

    _counter: int = 0
    _target: int = 0
    _state: str = ""
    _running_since: Optional[datetime] = None
    _running_since_step: float = 0.0
    _running_last: float = 0.0
    _stop_lock: threading.Lock = field(default_factory=threading.Lock)
    _parent_state: Optional[RuntimeState] = None  # Reference to check stopping flag

    @property
    def counter(self) -> int:
        return self._counter

    @counter.setter
    def counter(self, value: int) -> None:
        self._counter = value

    @property
    def target(self) -> int:
        return self._target

    @property
    def state(self) -> str:
        return self._state

    @state.setter
    def state(self, value: str) -> None:
        self._state = value

    @property
    def running_since(self) -> Optional[datetime]:
        return self._running_since

    @property
    def running_since_step(self) -> float:
        return self._running_since_step

    @running_since_step.setter
    def running_since_step(self, value: float) -> None:
        self._running_since_step = value

    @property
    def running_last(self) -> float:
        return self._running_last

    @running_last.setter
    def running_last(self, value: float) -> None:
        self._running_last = value

    def step(self, state: str = "", reset_counter: bool = True, target: int = 0, plus_step: int = 1) -> bool:
        """Advance to a new step in the operation.

        Args:
            state: Description of the current step
            reset_counter: Whether to reset the counter to 0
            target: Target value for this step
            plus_step: Amount to increment counter (when state is empty and not resetting)

        Returns:
            bool: True if operation should stop, False otherwise
        """
        if state:
            self._state = state
            if reset_counter:
                self._counter = 0
            self._target = target
            if not self._running_since:
                self._running_since = datetime.now()
            if target > 0:
                self._running_since_step = time.time()
            _log.debug("Progress step: %s (target: %d)", state, target)
        else:
            # No state provided - just increment counter
            self._counter += plus_step

        return self.should_stop()

    def stopstep(self) -> None:
        """Mark the current step as complete."""
        self._counter = 0
        self._state = ""
        self._running_since = None

    def reset(self) -> None:
        """Reset all progress tracking."""
        self._counter = 0
        self._target = 0
        self._state = ""
        self._running_since = None

    def stop(self) -> None:
        """Stop the current operation and reset state/progress.

        Thread-safe: Uses a lock to prevent race conditions.
        Coordinates with state service to set running/stopping flags.
        """
        import threading

        if not hasattr(self, "_stop_lock"):
            self._stop_lock = threading.Lock()

        with self._stop_lock:
            if self._parent_state:
                self._parent_state.running = False
                self._parent_state.stopping = False
            import time

            time.sleep(0.1)
            self.reset()
            if self._parent_state:
                self._parent_state.running = False
                self._parent_state.stopping = False

    def keep_going(self) -> bool:
        """Check if operation should continue."""
        if self._parent_state:
            return not self._parent_state.stopping
        return True

    def should_stop(self) -> bool:
        """Check if operation should stop."""
        return not self.keep_going()


@dataclass
class FileManager:
    """Concrete implementation of IFileManager.

    Manages file paths and related settings.
    """

    _config: Config
    _state: RuntimeState

    def set_input(self, filepath: str) -> None:
        """Set the GEDCOM input file path."""
        self._config.set("GEDCOMinput", filepath)
        _log.info("Input file set to: %s", filepath)

    def set_results_file(self, filepath: str) -> None:
        """Set the results/output file path."""
        self._config.set("resultsfile", filepath)
        _log.info("Results file set to: %s", filepath)

    def set_main(self, person_id: str) -> None:
        """Set the main person ID."""
        self._config.set("Main", person_id)
        _log.info("Main person set to: %s", person_id)

    def get_cache_file(self) -> Path:
        """Get the GPS cache file path based on input file."""
        input_path = Path(self._config.gedcom_input)
        cache_file = input_path.parent / (input_path.stem + "_cache.csv")
        return cache_file


# ============================================================================
# Service Container
# ============================================================================


class ServiceContainer:
    """Dependency injection container for managing service instances.

    Provides service registration, resolution, and lifecycle management.
    Supports both singleton and transient service lifetimes.
    """

    def __init__(self):
        """Initialize the service container."""
        self._services: Dict[Type, Any] = {}
        self._factories: Dict[Type, callable] = {}
        self._singletons: Dict[Type, bool] = {}

    def register(self, interface: Type[T], implementation: T, singleton: bool = True) -> None:
        """Register a service implementation.

        Args:
            interface: The interface type (Protocol class)
            implementation: The concrete implementation instance
            singleton: Whether to use the same instance for all resolutions
        """
        self._services[interface] = implementation
        self._singletons[interface] = singleton
        _log.debug(
            "Registered service: %s -> %s (singleton=%s)", interface.__name__, type(implementation).__name__, singleton
        )

    def register_factory(self, interface: Type[T], factory: callable, singleton: bool = False) -> None:
        """Register a factory function for creating service instances.

        Args:
            interface: The interface type
            factory: Callable that returns an instance of the service
            singleton: Whether to cache the first instance created
        """
        self._factories[interface] = factory
        self._singletons[interface] = singleton
        _log.debug("Registered factory for: %s (singleton=%s)", interface.__name__, singleton)

    def resolve(self, interface: Type[T]) -> T:
        """Resolve a service by its interface type.

        Args:
            interface: The interface type to resolve

        Returns:
            The service implementation instance

        Raises:
            KeyError: If the service is not registered
        """
        # Check if we have a pre-registered instance
        if interface in self._services:
            return self._services[interface]

        # Check if we have a factory
        if interface in self._factories:
            factory = self._factories[interface]
            instance = factory()

            # Cache if singleton
            if self._singletons.get(interface, False):
                self._services[interface] = instance

            return instance

        raise KeyError(f"Service not registered: {interface.__name__}")

    def has(self, interface: Type[T]) -> bool:
        """Check if a service is registered.

        Args:
            interface: The interface type to check

        Returns:
            True if the service is registered
        """
        return interface in self._services or interface in self._factories

    def clear(self) -> None:
        """Clear all registered services."""
        self._services.clear()
        self._factories.clear()
        self._singletons.clear()


# ============================================================================
# Global Service Container Instance
# ============================================================================

# Global container instance for application-wide service access
_container: Optional[ServiceContainer] = None


def get_container() -> ServiceContainer:
    """Get the global service container instance.

    Creates the container if it doesn't exist.
    """
    global _container
    if _container is None:
        _container = ServiceContainer()
    return _container


def reset_container() -> None:
    """Reset the global service container (mainly for testing)."""
    global _container
    if _container:
        _container.clear()
    _container = None
