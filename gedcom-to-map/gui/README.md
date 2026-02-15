# GUI Package

wxPython-based graphical user interface for gedcom-to-visualmap.

## Overview

This package provides the complete GUI application for visualizing GEDCOM genealogy files on maps. The interface allows users to load GEDCOM files, configure visualization options, generate various outputs (KML, HTML reports, folium maps), and explore family relationships.

## Package Structure

The GUI package is organized into logical subpackages by responsibility:

### `core/` - Main Application
Core application components that manage the application lifecycle:
- **`GedcomVisualGUI`** - Application facade and entry point
- **`VisualMapFrame`** - Main window frame with menu bar and status bar
- **`GuiHooks`** - GUI callback hooks for external integration

### `panels/` - UI Panels
Reusable panel components that compose the main interface:
- **`VisualMapPanel`** - Primary panel with all visualization controls
- **`FamilyPanel`** - Family relationships display panel
- **`PeopleListCtrlPanel`** - Panel wrapper for the people list control

### `processors/` - Data Processing
Backend processors that handle GEDCOM data and generate outputs:
- **`GedcomLoader`** - GEDCOM file parsing and geocoding
- **`MapGenerator`** - KML and Folium map generation
- **`ReportGenerator`** - HTML report and statistics generation
- **`LineageTracer`** - Ancestor/descendant lineage computation

### `actions/` - Action Handlers
Controllers that coordinate user actions and background operations:
- **`VisualMapActions`** - Main action coordinator for UI operations
- **`BackgroundActions`** - Background worker thread for long-running tasks
- **`FileOpener`** - Cross-platform file opening utilities
- **`DoActionsType`** - Action type enumeration and flags
- **CLI wrappers**: `Geoheatmap`, `gedcom_to_map` - Standalone command-line entry points

### `dialogs/` - Dialog Windows
Modal and non-modal dialog windows:
- **`AboutDialog`** - Application about/version information
- **`ConfigDialog`** - Application configuration settings including:
  - Geocoding mode (radio buttons): Normal, Geocode only (ignore cache), or Cache only (no geocode)
  - Days between retrying failed geocode lookups
  - Default country for geocoding
  - File open commands for KML, CSV, and trace files
  - Logging levels for all system loggers
- **`FindDialog`** - Person search dialog
- **`HelpDialog`** - Help and documentation viewer
- **`HTMLDialog`** - Generic HTML content display dialog
- **`PersonDialog`** - Detailed person information and relationships

### `widgets/` - Custom Controls
Reusable custom wxPython controls:
- **`PeopleListCtrl`** - Searchable, sortable list of people with context menu
- **`GedRecordDialog`** - GEDCOM record inspector/viewer

### `layout/` - Layout Helpers
UI layout construction and event handling utilities:
- **`LayoutOptions`** - Layout construction for VisualMapPanel
- **`LayoutHelpers`** - Common layout patterns and utilities
- **`VisualMapEventHandler`** - Event handler delegate for VisualMapPanel
- **`VisualGedcomIds`** - Central wxPython widget ID management
- **`FontManager`** - Font configuration and sizing
- **`ColourManager`** - GUI colour management (wx.Colour handling)

## Usage

### Starting the Application

```python
import wx
from gui.core import GedcomVisualGUI
from services.config_service import GVConfig

app = wx.App()
gOp = GVConfig()
gui = GedcomVisualGUI(gOp)
gui.start()
app.MainLoop()
```

### Importing Components

Import from subpackages for specific functionality:

```python
# Import processors for standalone data processing
from gui.processors import GedcomLoader, MapGenerator, ReportGenerator

# Import actions for programmatic control
from gui.actions import VisualMapActions, BackgroundActions

# Import dialogs for custom UI
from gui.dialogs import PersonDialog, FindDialog
```

Or import from the main package for convenience:

```python
# Main package re-exports all public classes
from gui import GedcomVisualGUI, VisualMapPanel, GedcomLoader
```

### Using CLI Wrappers

The `actions` package provides standalone command-line wrappers:

```python
from gui.actions import gedcom_to_map, Geoheatmap

# Generate visualization from GEDCOM file
gedcom_to_map('family.ged', output_dir='output/')

# Create geographic heatmap
Geoheatmap('family.ged', 'heatmap.html')
```

## Architecture

### Separation of Concerns

The package follows a clear separation of concerns:

1. **UI Layer** (`core/`, `panels/`, `dialogs/`, `widgets/`) - Presentation and user interaction
2. **Action Layer** (`actions/`) - Coordination and control flow
3. **Processing Layer** (`processors/`) - Business logic and data transformation
4. **Utilities** (`layout/`) - Shared helpers and configuration

### Background Processing

Long-running operations (GEDCOM parsing, geocoding, map generation) run in a background thread via `BackgroundActions` to keep the UI responsive. The worker communicates progress and results back to the UI through wxPython events.

**Robustness Features**:
- **Automatic Error Recovery**: Worker thread always returns to ready state even when exceptions occur
- **State Synchronization**: `readyToDo` flag reset happens first before any cleanup that could fail
- **Isolated Cleanup**: All cleanup operations wrapped in separate try-except blocks
- **Rejection Handling**: New work requests rejected when worker is busy with clear user messaging
- **Comprehensive Logging**: Detailed timing and progress logs for all operations, with verbose internal state tracking at DEBUG level

**Memory Tracking**:
- **Baseline Snapshots**: Memory monitoring uses baseline comparison to show only NEW allocations since app start
- **Configurable Tracking**: Enable `tracemalloc` via Configuration Options → Performance for detailed memory analysis
- **Accurate Reporting**: Eliminates misleading cumulative statistics from Python's built-in memory tracking

**Large Dataset Warnings**:
- **Two-Tier Alerts**: Critical errors for >10K people (with option to cancel), standard warnings for 200-10K people
- **Pedigree Collapse**: For royal genealogy files tracing to biblical figures, the system tracks and logs unique people vs total Line objects. Extreme pedigree collapse (same ancestor via thousands of paths) is by design but can create hundreds of thousands of Line objects

### Event Handling

Event handling is delegated to `VisualMapEventHandler` rather than having handlers inline in the panel. This improves testability and keeps the panel focused on layout and state management.

### File Opening Infrastructure

The `FileOpener` utility provides cross-platform file opening with configurable commands:
- **System Defaults**: KML and HTML files use system default handlers (`$n` placeholder)
- **Custom Commands**: CSV and trace files support custom editor commands
- **Platform-Specific**: Automatically selects correct command format for Windows, macOS, or Linux
- **Configuration**: All file commands configurable via Configuration Options dialog

**Default Behaviors**:
- KML files → System default (Google Earth on most systems)
- HTML files → Default web browser
- CSV files → Configurable (Excel, Numbers, LibreOffice, etc.)
- Trace files → Configurable text editor

## Dependencies

- **wxPython** - GUI framework (required for all UI components)
- **gv_config** - Application configuration (GVConfig)
- **geo_gedcom** - GEDCOM parsing and geographic data structures
- **models** - Data models for visualization
- **render** - Output generators (KML, Folium, HTML reports)

Note: The `processors` and `actions` packages can be imported without wxPython for headless/CLI usage.

## Testing

The GUI package includes integration tests in the project's `tests/` directory:

```bash
# Run GUI file operation tests
pytest tests/test_gui_file_operations.py

# Run all tests
pytest
```

Tests use mocking to avoid requiring a display server or wxPython GUI instance.

## Development

### Adding New Features

1. **New dialog?** → Add to `dialogs/`
2. **New panel?** → Add to `panels/`
3. **New data processor?** → Add to `processors/`
4. **New action handler?** → Add to `actions/`
5. **New widget?** → Add to `widgets/`

### Code Style

- Use type hints for function parameters and return values
- Use descriptive variable names
- Keep functions focused and testable
- Delegate complex logic to specialized classes
- Add docstrings for public classes and methods

### Import Guidelines

**Within the gui package:**
```python
# Cross-package imports use relative paths with parent reference
from ..processors.gedcom_loader import GedcomLoader  # From actions/ to processors/
from ..dialogs.person_dialog import PersonDialog     # From panels/ to dialogs/
```

**From outside the gui package:**
```python
# Use absolute imports
from gui.core import GedcomVisualGUI
from gui.processors import MapGenerator
```

## Common Issues

### ImportError: partially initialized module (circular import)
Move the import into the function/method that needs it (lazy import). Remove mutual top-level imports.

### AssertionError when binding event
Ensure the event type/binder is not `None` before calling `Bind(...)`.

### ModuleNotFoundError for imports
Use package-relative imports (`from .module import X`) within the package, and run from project root or ensure PYTHONPATH includes the package root.

## History

The GUI package was reorganized from a flat structure (28 files in one directory) to a hierarchical structure (6 logical subpackages) in January 2026. The `VisualMapActions` class was refactored from a 965-line "God class" into 5 specialized modules totaling 1,281 lines with clear responsibilities.

See `docs/gui-reorganization.md` for detailed migration information.
