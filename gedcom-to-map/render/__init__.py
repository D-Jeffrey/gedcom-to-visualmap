"""Render package: Output generation and visualization exporters.

Provides multiple rendering backends for exporting genealogical data as maps,
including KML (legacy and refined), Folium/HTML interactive maps, and summaries.

Exporters:
    - KmlExporter: Legacy KML format exporter (kml1/)
    - KmlExporterRefined, KML_Life_Lines_Creator, KML_Life_Lines: Refined KML with life lines (kml2/)
    - foliumExporter: Interactive HTML maps using Folium library (folium/)
      - Includes cross-platform photo path handling (backslashes → forward slashes)
      - Supports custom map styles via xyzservices
      - Provides clustered markers and timeline heatmaps

Visualization helpers:
    - Legend: Map legend generation
    - MyMarkClusters: Clustered marker management with timeline support
    - NameProcessor: Place name formatting and standardization

Report/Summary generators:
    - write_statistics_summary: Statistical summaries (YAML format)
    - write_statistics_markdown: Statistical summaries (Markdown format)
    - write_statistics_html: Statistical summaries (HTML format)
    - write_places_summary: Geographic locations summary (CSV)
    - write_geocache_summary: Geocoding cache export (CSV)
    - write_birth_death_countries_summary: Country-based statistics (CSV)
    - write_enrichment_issues_summary: Data quality issues report (CSV)
    - save_birth_death_heatmap_matrix: Heatmap data export

Result types:
    - ResultType: Enum for output format specification (HTML, KML, KML2, SUM)
      - Located in render/result_type.py
      - Provides file extension mapping and type coercion

Other:
    - Referenced: Reference tracking and deduplication

Usage:
    >>> from render import foliumExporter, KmlExporter, ResultType
    >>> from services import GVConfig, GVState, GVProgress
    >>>
    >>> # Initialize services
    >>> config = GVConfig()
    >>> state = GVState()
    >>> progress = GVProgress()
    >>>
    >>> # Generate HTML map
    >>> exporter = foliumExporter(config, state, progress)
    >>> exporter.export(main_person, lines, saveresult=True)
    >>>
    >>> # Generate KML
    >>> kml_exporter = KmlExporter(config, state, progress)
    >>> kml_exporter.export(...)
"""

# KML exporters
from .kml1.kml_exporter import KmlExporter
from .kml2.kml_life_lines import KmlExporterRefined, KML_Life_Lines_Creator, KML_Life_Lines

# Folium-based exporters and helpers
from .folium.folium_exporter import foliumExporter
from .folium.mark_clusters import MyMarkClusters
from .folium.legend import Legend
from .folium.name_processor import NameProcessor

# Summary and report writers
from .summary import (
    save_birth_death_heatmap_matrix,
    write_alt_places_summary,
    write_birth_death_countries_summary,
    write_geocache_summary,
    write_places_summary,
    write_enrichment_issues_summary,
    write_statistics_summary,
)
from .statistics_markdown import write_statistics_markdown, write_statistics_html

# Reference handling
from .referenced import Referenced

# Result type enum
from .result_type import ResultType

__all__ = [
    # KML exporters
    "KmlExporter",
    "KmlExporterRefined",
    "KML_Life_Lines_Creator",
    "KML_Life_Lines",
    # Folium exporters and helpers
    "Legend",
    "MyMarkClusters",
    "foliumExporter",
    "NameProcessor",
    # Summary writers
    "save_birth_death_heatmap_matrix",
    "write_alt_places_summary",
    "write_birth_death_countries_summary",
    "write_geocache_summary",
    "write_places_summary",
    "write_enrichment_issues_summary",
    "write_statistics_summary",
    "write_statistics_markdown",
    "write_statistics_html",
    # Other
    "Referenced",
    "ResultType",
]

__maintainer__ = "D-Jeffrey"
