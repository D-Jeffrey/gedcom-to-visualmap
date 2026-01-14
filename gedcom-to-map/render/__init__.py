"""
render package initialization.

Provides export and rendering utilities for visualizing GEDCOM data,
including KML generation, Folium-based mapping, and reference handling.
"""

from .kml1.kml_exporter import KmlExporter
from .kml2.kml_life_lines import KmlExporterRefined, KML_Life_Lines_Creator, KML_Life_Lines
from .referenced import Referenced
from .folium.folium_exporter import foliumExporter
from .folium.mark_clusters import MyMarkClusters
from .folium.legend import Legend
from .folium.name_processor import NameProcessor
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