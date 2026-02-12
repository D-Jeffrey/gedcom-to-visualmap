"""gedcom-to-visualmap: GEDCOM genealogy data visualization and mapping.

A comprehensive tool for reading GEDCOM genealogical data files, resolving place names
to GPS coordinates via geocoding, and generating interactive maps visualizing ancestral
relationships and migration patterns.

Main entry points:
    - gv.py: GUI application (wxPython interface)
    - gedcom-to-map.py: Command-line interface

Core modules:
    - services: Dependency-injected services (IConfig, IState, IProgressTracker)
    - const: Application constants and configuration
    - models: Genealogical data models and visualization primitives (Creator classes with
      per-line loop detection for pedigree collapse support)
    - render: Output generation (KML, HTML/Folium with cross-platform photo paths, reports)
      - ResultType enum for output format specification
      - Photo path handling: Backslashes converted to forward slashes for JavaScript
    - geo_gedcom: GEDCOM parsing, geocoding, and enrichment
    - gui: wxPython GUI components (panels, dialogs, actions, processors)
      - Enhanced progress messaging for HTML generation
      - Simplified logging configuration with 12 core loggers

Recent Improvements:
    - Photo paths: Cross-platform compatibility (Windows backslashes → forward slashes)
    - Progress messages: Early feedback during HTML generation
    - Loop detection: Per-line tracking supporting pedigree collapse
    - Logging: Simplified to 12 loggers with WARNING default and Clear Log File option
    - Configuration: "Set All Levels" control for batch logging level changes
    - ResultType: Moved to render/result_type.py module for better organization

Architecture:
    - Services-based design: All business logic receives service instances implementing
      IConfig (settings), IState (runtime state), IProgressTracker (progress/cancellation).
    - Protocol-based interfaces: Services use structural subtyping (Python Protocol) for
      loose coupling and flexible testing.
    - Dependency injection: Services are passed through constructors; no global state.
    - No legacy globals: The old gedcom_options global object (gOp) has been completely
      removed in favor of the modern service architecture.

Subpackages:
    - services: Configuration, state, and progress service implementations
    - models: Color, Line, Creator, Rainbow for map visualization
    - render: Exporters for KML, HTML, and report generation
    - geo_gedcom: GEDCOM parsing, geocoding, enrichment
    - gui: GUI components organized into panels, dialogs, actions, widgets, processors

Usage examples:
    # Programmatic API
    >>> from services import GVConfig, GVState, GVProgress
    >>> from geo_gedcom import GedcomParser, GeolocatedGedcom
    >>> from render import foliumExporter, ResultType
    >>> from gui.core import GuiHooks
    >>>
    >>> config = GVConfig('gedcom_options.yaml')
    >>> state = GVState()
    >>> progress = GVProgress()
    >>>
    >>> parser = GedcomParser()
    >>> people = parser.parse('family.ged')
    >>> geogedcom = GeolocatedGedcom(people, app_hooks=GuiHooks(progress, state))
    >>>
    >>> # Generate HTML map
    >>> exporter = foliumExporter(config, state, progress)
    >>> exporter.export(state.mainPerson, lines, saveresult=True)
    >>>
    >>> # Check result type
    >>> result_type = ResultType.HTML
    >>> print(result_type.file_extension())  # 'html'

    # GUI application
    >>> from gui.core import GedcomVisualGUI
    >>> app = GedcomVisualGUI(parent=None, svc_config=config, svc_state=state,
    ...                       svc_progress=progress, title="GEDCOM to Visual Map")
    >>> app.start()

Documentation:
    See README.md for overview and setup instructions.
    See docs/ for detailed guides and examples.
    See each subpackage for module-specific documentation.
"""
