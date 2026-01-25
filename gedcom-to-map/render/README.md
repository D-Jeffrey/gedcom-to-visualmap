
# render Module

This module provides export and rendering utilities for visualizing GEDCOM data, including KML generation, Folium-based mapping, and reference handling.
All exporters and renderers now require service objects for configuration, state, and progress tracking (see `services.py`).

## Key Features

- **KML Export:** Generate KML files for use in Google Earth, MyMaps, ArcGIS Earth, and other GIS tools.
- **Folium/HTML Export:** Create interactive HTML maps using Folium, with support for clustering, heatmaps, and timeline visualization.
- **Name Processing:** Utilities for name normalization, comparison, and soundex, all via the `NameProcessor` class.
- **Summary Statistics:** Generate CSV and summary files for places, geocoding, and birth/death heatmaps; outputs are written alongside the input GEDCOM.
- **Reference Handling:** Manage references and links between people, places, and events.


## Main Classes & Functions

- `KmlExporter`, `KmlExporterRefined`, `KML_Life_Lines_Creator`, `KML_Life_Lines`: KML export and visualization.
- `foliumExporter`, `MyMarkClusters`, `Legend`: Folium/HTML map export and marker clustering.
- `NameProcessor`: Name utilities (use static methods: `isValidName`, `compareNames`, `simplifyLastName`, `soundex`).
- `Referenced`: Reference management.
- `save_birth_death_heatmap_matrix`, `write_alt_places_summary`, `write_birth_death_countries_summary`, `write_geocache_summary`, `write_places_summary`: Summary and reporting utilities.

soundex_code = NameProcessor.soundex("Smith")

## Example Usage (with Services)

```python
from render import KmlExporter, foliumExporter, NameProcessor
from services import IConfig, IState, IProgressTracker

# Create or mock your service objects (see tests for examples)
svc_config = ...  # implements IConfig
svc_state = ...   # implements IState
svc_progress = ...  # implements IProgressTracker

# Export KML
kml_exporter = KmlExporter(svc_config, svc_state, svc_progress)
# ... add people, places, lines, etc. ...
kml_exporter.Done()

# Export HTML map
folium_exporter = foliumExporter(svc_config, svc_state, svc_progress)
folium_exporter.export(main_location, lines)

# Name utilities
is_valid = NameProcessor.isValidName("John Doe")
soundex_code = NameProcessor.soundex("Smith")
```

## Directory Structure

```
render/
├── __init__.py
├── kml.py
├── KmlExporter.py
├── foliumExp.py
├── Referenced.py
├── name_processor.py
├── summary.py
└── README.md
```

## Requirements

- [simplekml](https://pypi.org/project/simplekml/)
- [folium](https://pypi.org/project/folium/)
- [xyzservices](https://pypi.org/project/xyzservices/)
- [branca](https://pypi.org/project/branca/)
- [pandas](https://pypi.org/project/pandas/)
- [seaborn](https://pypi.org/project/seaborn/)
- [matplotlib](https://pypi.org/project/matplotlib/)


## Notes

- See the main project README for setup, usage, and the new services-based architecture.
- All new code and tests should use dependency injection for configuration, state, and progress tracking.
- This module is intended to be used as part of the larger `gedcom-to-visualmap` project.

## Authors

- @colin0brass
- @D-jeffrey

## License

See the main repository LICENSE.txt for details.