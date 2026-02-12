
# render Package

This package provides export and rendering utilities for visualizing GEDCOM genealogical data. It supports multiple output formats including interactive HTML maps, KML files for GIS tools, and statistical summaries.

All exporters and renderers use dependency injection via service objects for configuration, state, and progress tracking (see `services/` package).

## Key Features

- **Interactive HTML Maps:** Generate rich, interactive HTML maps using Folium with support for:
  - Clustered markers
  - Heatmaps (static and timeline-based)
  - Custom map styles via xyzservices
  - Photo popups (with automatic path escaping for cross-platform compatibility)
  - Legend and layer controls

- **KML Export:** Generate KML files for use in Google Earth, MyMaps, ArcGIS Earth, and other GIS tools:
  - Legacy format (kml1): Simple KML export
  - Refined format (kml2): Enhanced KML with life lines and detailed styling

- **Statistical Summaries:** Generate reports in multiple formats:
  - YAML, Markdown, and HTML statistics
  - CSV summaries for places, countries, geocoding cache
  - Birth/death heatmap matrices
  - Enrichment issues reports

- **Name Processing:** Utilities for name normalization, comparison, and soundex (all static methods)
- **Reference Tracking:** Manage references and links between people, places, and events
- **Result Types:** Enum-based output format specification (HTML, KML, KML2, SUM)


## Main Classes & Functions

### Exporters
- `foliumExporter`: Interactive HTML map generation using Folium library
- `KmlExporter`: Legacy KML format exporter (kml1)
- `KmlExporterRefined`, `KML_Life_Lines_Creator`, `KML_Life_Lines`: Refined KML with life lines (kml2)

### Visualization Helpers
- `MyMarkClusters`: Clustered marker management with timeline support
- `Legend`: Map legend generation
- `NameProcessor`: Static methods for name utilities (`isValidName`, `compareNames`, `simplifyLastName`, `soundex`)
- `Referenced`: Reference tracking and deduplication

### Summary & Report Writers
- `write_statistics_summary`: Generate YAML statistics
- `write_statistics_markdown`: Generate Markdown statistics
- `write_statistics_html`: Generate HTML statistics
- `write_places_summary`: Geographic locations summary (CSV)
- `write_geocache_summary`: Geocoding cache export (CSV)
- `write_birth_death_countries_summary`: Country-based statistics (CSV)
- `write_enrichment_issues_summary`: Data quality issues report (CSV)
- `save_birth_death_heatmap_matrix`: Heatmap data export
- `write_alt_places_summary`: Alternative place names (CSV)

### Result Types
- `ResultType`: Enum for output format types (HTML, KML, KML2, SUM)
  - `ResultTypeEnforce()`: Coerce string/value to ResultType
  - `file_extension()`: Get file extension for result type
  - `for_file_extension()`: Get ResultType from file extension

## Example Usage

```python
from render import KmlExporter, foliumExporter, NameProcessor, ResultType
from services.interfaces import IConfig, IState, IProgressTracker

# Create or mock your service objects (see tests for examples)
svc_config = ...  # implements IConfig
svc_state = ...   # implements IState
svc_progress = ...  # implements IProgressTracker

# Export KML
kml_exporter = KmlExporter(svc_config, svc_state, svc_progress)
# ... configure and generate ...
kml_exporter.Done()

# Export interactive HTML map
folium_exporter = foliumExporter(svc_config, svc_state, svc_progress)
folium_exporter.export(main_person, lines, saveresult=True)

# Name utilities (static methods)
is_valid = NameProcessor.isValidName("John Doe")
soundex_code = NameProcessor.soundex("Smith")

# Result type utilities
result_type = ResultType.HTML
extension = result_type.file_extension()  # returns "html"
rt_from_ext = ResultType.for_file_extension("kml")  # returns ResultType.KML
```

## Directory Structure

```
render/
├── __init__.py              # Package exports and documentation
├── README.md                # This file
├── result_type.py           # ResultType enum and utilities
├── referenced.py            # Reference tracking
├── summary.py               # Summary/report generation (CSV)
├── statistics_markdown.py   # Statistics generation (MD/HTML)
├── folium/                  # Folium/HTML map generation
│   ├── __init__.py
│   ├── folium_exporter.py   # Main HTML map exporter
│   ├── legend.py            # Legend generation
│   ├── mark_clusters.py     # Marker clustering
│   ├── name_processor.py    # Name utilities
│   ├── marker_utils.py      # Marker creation helpers
│   ├── polyline_utils.py    # Line drawing helpers
│   ├── heatmap_utils.py     # Heatmap generation
│   └── constants.py         # Folium constants
├── kml1/                    # Legacy KML export
│   ├── __init__.py
│   └── kml_exporter.py      # Simple KML exporter
├── kml2/                    # Refined KML export
│   ├── __init__.py
│   ├── kml_exporter_refined.py
│   ├── kml_life_lines_creator.py
│   └── kml_life_lines.py
└── tests/                   # Unit tests
    └── test_result_type.py
```

## Dependencies

### Required Packages
- [simplekml](https://pypi.org/project/simplekml/) - KML file generation
- [folium](https://pypi.org/project/folium/) - Interactive HTML maps
- [xyzservices](https://pypi.org/project/xyzservices/) - Map tile providers
- [branca](https://pypi.org/project/branca/) - Folium colormap support
- [pandas](https://pypi.org/project/pandas/) - Data manipulation and CSV export
- [seaborn](https://pypi.org/project/seaborn/) - Statistical visualizations
- [matplotlib](https://pypi.org/project/matplotlib/) - Plotting and heatmaps

### Internal Dependencies
- `services/`: Service interfaces (IConfig, IState, IProgressTracker)
- `models/`: Data models (Line, Creator classes)
- `geo_gedcom/`: GEDCOM parsing and Person/Place models

## Architecture Notes

### Service-Based Design
All exporters use dependency injection for configuration, state, and progress tracking:
- **IConfig**: Configuration management (settings, options)
- **IState**: Runtime state (people, main person, referenced items)
- **IProgressTracker**: Progress reporting for UI updates

### Path Handling
The package handles cross-platform file paths correctly:
- Photo paths: Backslashes are converted to forward slashes for HTML/JavaScript compatibility
- Output paths: Use pathlib.Path for platform-independent path handling

### Result Type System
The `ResultType` enum provides type-safe output format specification:
- Maps result types to file extensions
- Supports string coercion and validation
- Used throughout the application for output routing

## Testing

Run tests with pytest from the project root:
```bash
pytest gedcom-to-map/render/tests/
```

See `render/tests/test_result_type.py` for examples of testing with service mocks.

## Usage in Application

This package is intended to be used as part of the larger `gedcom-to-visualmap` project.
The GUI (via `gui/processors/map_generator.py`) and command-line interface both use
these exporters to generate output files based on the selected ResultType.

## Authors

- @colin0brass
- @D-jeffrey

## License

See the main repository LICENSE.txt for details.
