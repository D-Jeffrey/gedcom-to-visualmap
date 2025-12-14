"""
render package initialization.

Provides export and rendering utilities for visualizing GEDCOM data,
including KML generation, Folium-based mapping, and reference handling.
"""

from .kml import KmlExporterRefined, KML_Life_Lines_Creator, KML_Life_Lines
from .kml_exporter import KmlExporter
from .referenced import Referenced
from .name_processor import NameProcessor
from .foliumExp import foliumExporter, MyMarkClusters, Legend
from .summary import (
    save_birth_death_heatmap_matrix,
    write_alt_places_summary,
    write_birth_death_countries_summary,
    write_geocache_summary,
    write_places_summary,
)

__all__ = [
    "KmlExporter",
    "KmlExporterRefined",
    "KML_Life_Lines_Creator",
    "KML_Life_Lines",
    "Legend",
    "MyMarkClusters",
    "Referenced",
    "foliumExporter",
    "NameProcessor",
    "save_birth_death_heatmap_matrix",
    "write_alt_places_summary",
    "write_birth_death_countries_summary",
    "write_geocache_summary",
    "write_places_summary",
]

__maintainer__ = "D-Jeffrey"