"""
render package initialization.

Provides export and rendering utilities for visualizing GEDCOM data,
including KML generation, Folium-based mapping, and reference handling.
"""

from .kml import KmlExporterRefined, KML_Life_Lines_Creator, KML_Life_Lines
from .KmlExporter import KmlExporter
from .Referenced import Referenced
from .foliumExp import foliumExporter, MyMarkClusters, Legend
from .naming import NameProcessor, isValidName, compareNames, simplifyLastName, soundex
from .summary import (save_birth_death_heatmap_matrix, write_alt_places_summary, 
        write_birth_death_countries_summary,  write_geocache_summary, write_places_summary)

__all__ = [
    "KmlExporter",
    "KmlExporterRefined"
    "KML_Life_Lines_Creator",
    "KML_Life_Lines",
    'Legend',
    'MyMarkClusters', 
    "NameProcessor",
    "Referenced",
    "compareNames",
    "export_folium_map",
    'foliumExporter',
    "isValidName",
    "save_birth_death_heatmap_matrix"
    "simplifyLastName",
    "soundex",
    "write_alt_places_summary",
    "write_birth_death_countries_summary",
    "write_geocache_summary",
    "write_places_summary"
]    

__maintainer__ = "D-Jeffrey"