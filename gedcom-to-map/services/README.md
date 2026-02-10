# services package

This package contains the core service classes and interfaces for the gedcom-to-visualmap application. It provides modular, testable implementations using Protocol-based dependency injection for configuration, runtime state, progress tracking, and file I/O operations.

## Architecture

The services layer uses Python Protocols (PEP 544) for structural subtyping, enabling:
- **Loose coupling**: Components depend on interfaces, not concrete implementations
- **Testability**: Easy to mock services in unit tests
- **Flexibility**: Swap implementations without changing client code
- **Type safety**: Full type checking support with mypy/pyright

All service implementations use **simple attribute access** (not properties) for consistency and simplicity.

## Module Overview

### Core Services

- **`config_service.py`** — Implements `GVConfig` (IConfig)
  - Configuration management from YAML and INI files
  - Input/output file handling
  - Marker options and timeframe tracking
  - File open command management
  - Geocoding mode configuration:
    - `geocode_only`: Always geocode, ignore cache
    - `cache_only`: Only use cache, no network requests (read-only mode)
    - Normal mode: Both flags False (default - uses cache and geocodes new addresses)
  - Comprehensive docstrings and type hints

- **`state_service.py`** — Implements `GVState` (IState)
  - Runtime state management (parsed data, lookup services)
  - Main person selection and lineage tracking
  - Simple attribute-based interface

- **`progress_service.py`** — Implements `GVProgress` (IProgressTracker)
  - Thread-safe progress tracking for long operations
  - Counter and target tracking with step management
  - Stop request handling
  - Timing information (start time, duration, ETA support)
  - Snake_case naming convention throughout

### Supporting Modules

- **`config_io.py`** — Low-level configuration I/O utilities
  - Platform-specific settings file paths
  - Type coercion (bool, int, str, list, dict, LatLon, ResultType)
  - INI section loading/saving with migration support
  - Comprehensive docstrings and type hints

- **`file_commands.py`** — File open command management
  - Case-insensitive file type lookup
  - Command storage and retrieval
  - Used by GVConfig for opening output files

- **`interfaces.py`** — Protocol definitions
  - `IConfig`: Configuration access interface
  - `IState`: Runtime state interface  
  - `IProgressTracker`: Progress tracking interface
  - All protocols use simple attribute annotations

## Usage

### Basic Usage

Import and instantiate the services as needed:

```python
from services.config_service import GVConfig
from services.state_service import GVState
from services.progress_service import GVProgress

# Initialize services
config = GVConfig()  # Loads from gedcom_options.yaml
state = GVState()
progress = GVProgress()

# Use configuration
input_file = config.GEDCOMinput
result_type = config.ResultType

# Track runtime state
state.people = parsed_people
state.main_person = selected_person

# Monitor progress
progress.state = "Processing records"
progress.counter = 0
progress.target = 1000
for item in items:
    if progress.should_stop():
        break
    process(item)
    progress.counter += 1
```

### Protocol-Based Dependency Injection

Pass service instances via protocols for loose coupling:

```python
from services.interfaces import IConfig, IState, IProgressTracker

def process_gedcom(
    config: IConfig,
    state: IState, 
    progress: IProgressTracker
) -> None:
    """Process GEDCOM file using injected services."""
    progress.state = "Loading GEDCOM"
    # ... implementation uses service interfaces
```

### Testing with Mocks

Protocols make testing straightforward:

```python
def test_process_gedcom():
    # Create simple mock objects
    mock_config = Mock(spec=IConfig)
    mock_config.GEDCOMinput = "test.ged"
    
    mock_state = Mock(spec=IState)
    mock_progress = Mock(spec=IProgressTracker)
    
    # Test with mocks
    process_gedcom(mock_config, mock_state, mock_progress)
```

## Testing

Comprehensive test suite with 131 tests across 5 test modules:

### Test Coverage

- **`test_config_io.py`** (39 tests)
  - Platform-specific paths (4 tests)
  - Type coercion (15 tests)
  - Section management (3 tests)
  - Option setting (6 tests)
  - Marker options (5 tests)
  - Loading/saving/migration (6 tests)

- **`test_config_service.py`** (41 tests)
  - Initialization and YAML loading (3 tests)
  - Marker options (3 tests)
  - Get/set operations (9 tests including has() method)
  - Input/output handling (7 tests)
  - Timeframe tracking (5 tests)
  - File commands (3 tests)
  - Settings persistence (3 tests)
  - Helper functions (8 tests)

- **`test_file_commands.py`** (13 tests)
  - Initialization and storage
  - Case-insensitive lookups
  - Command existence checks
  - File type listing

- **`test_progress_service.py`** (26 tests)
  - Initialization (2 tests)
  - Counter/state/target management (3 tests)
  - Step operations (9 tests including stepCounter legacy method)
  - Stop control (6 tests)
  - Stop and reset (3 tests)
  - Workflow integration (2 tests)
  - Legacy method compatibility (1 test)

- **`test_state_service.py`** (12 tests)
  - Initialization and attribute access
  - Timeframe tracking (5 tests including edge cases)
  - Main person selection (6 tests)

### Running Tests

Run all service tests:
```bash
pytest gedcom-to-map/services/tests/
```

Run specific test module:
```bash
pytest gedcom-to-map/services/tests/test_config_service.py -v
```

Run with coverage:
```bash
pytest gedcom-to-map/services/tests/ --cov=services --cov-report=html
```

## Design Principles

### 1. Simple Attributes Over Properties

All services use direct attribute access instead of `@property` decorators:

```python
# ✅ Simple attributes
progress.counter = 10
progress.state = "Processing"

# ❌ Not using properties
# progress.counter() or @property decorators
```

**Benefits:**
- Less boilerplate code (~70 lines saved in GVProgress alone)
- Cleaner Protocol definitions
- Consistent with Python's duck typing philosophy
- Easier to understand and maintain

### 2. Protocol-Based Interfaces

Protocols define contracts without inheritance:

```python
class IProgressTracker(Protocol):
    counter: int
    state: str
    target: int
    # ... attributes and methods
```

**Benefits:**
- No need to inherit from base classes
- Structural subtyping (duck typing with type checking)
- Better for dependency injection
- Works with any object that matches the structure

### 3. Snake_Case Naming

All methods and attributes follow Python's snake_case convention:

```python
# ✅ Correct
progress.should_stop()
progress.running_since_step
progress.step_info

# ❌ Legacy (removed)
# progress.ShouldStop()
# progress.runningSinceStep
# progress.stepinfo
```

### 4. Thread Safety

Progress tracking includes thread-safe operations:

```python
class GVProgress:
    def __init__(self):
        self._stop_lock = threading.Lock()
    
    def stop(self):
        with self._stop_lock:
            # Thread-safe state modification
```

### 5. Comprehensive Documentation

All modules include:
- Module-level docstrings explaining purpose
- Function docstrings with Args/Returns/Note sections
- Type hints for all parameters and return values
- Inline comments for complex logic

## Extending

### Adding a New Service

1. **Define the Protocol** in `interfaces.py`:
```python
class INewService(Protocol):
    """New service interface description."""
    
    attribute_name: str
    """Attribute description."""
    
    def method_name(self, param: str) -> bool:
        """Method description.
        
        Args:
            param: Parameter description.
            
        Returns:
            bool: Return value description.
        """
        ...
```

2. **Implement the Service** in `new_service.py`:
```python
"""new_service.py

Service description and purpose.
"""
from services.interfaces import INewService

class GVNewService(INewService):
    """Implementation of INewService.
    
    Detailed description of implementation.
    """
    
    def __init__(self):
        """Initialize service with default values."""
        self.attribute_name: str = "default"
    
    def method_name(self, param: str) -> bool:
        """Implementation with full docstring."""
        # Implementation
        return True
```

3. **Add Tests** in `tests/test_new_service.py`:
```python
"""test_new_service.py

Unit tests for new_service.py.
"""
import pytest
from services.new_service import GVNewService

class TestGVNewServiceInit:
    """Tests for GVNewService initialization."""
    
    def test_init_creates_default_values(self):
        """Test service initializes with correct defaults."""
        service = GVNewService()
        assert service.attribute_name == "default"
```

4. **Update README** with new service information.

### Best Practices

- **Use Protocols**: Define interfaces for all services
- **Keep it simple**: Prefer attributes over properties
- **Document thoroughly**: Add comprehensive docstrings
- **Test extensively**: Aim for high coverage
- **Follow conventions**: snake_case, type hints, etc.
- **Thread-safe when needed**: Use locks for concurrent access
- **Log appropriately**: Use module-level loggers

## Migration Notes

Recent refactoring improvements:

- **Removed legacy naming**: All camelCase methods converted to snake_case
- **Simplified Protocols**: Converted from properties to simple attributes
- **Added documentation**: Comprehensive docstrings throughout
- **Enhanced testing**: Expanded from 68 to 127 tests
- **Removed duplication**: Consolidated functionality across services
- **Fixed bugs**: GVState.lookup initialization, progress property access

All 127 tests passing with full type hint coverage.
