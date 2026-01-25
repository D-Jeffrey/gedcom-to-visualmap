"""gedcom-to-visualmap: GEDCOM genealogy data visualization and mapping.

Main entry points:
    - gv.py: GUI application
    - gedcom-to-map.py: Command-line interface

Core modules:
    - gedcom_options: Configuration and runtime state
    - const: Application constants
    - models: Data structures for rendering
    - render: Output generation (KML, HTML, Folium)
    - geo_gedcom: GEDCOM parsing and geocoding
    - gui: wxPython GUI components

Architecture:
    - All exporters, renderers, and core logic use a services-based architecture.
    - Pass service objects implementing IConfig, IState, and IProgressTracker (see services.py).
    - The legacy global options object (gOp) is no longer used.

Public API is exposed via submodules; see each subpackage for details.
"""