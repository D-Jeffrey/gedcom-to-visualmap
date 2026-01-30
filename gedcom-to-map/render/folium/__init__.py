"""Folium subpackage: Interactive HTML map generation using Folium library.

Provides utilities for generating interactive HTML maps with genealogical overlays:
    - Legend: Map legend generation
    - MyMarkClusters: Clustered marker management
    - foliumExporter: Main HTML map exporter
    - NameProcessor: Place name formatting and standardization

Usage:
    >>> from render.folium import foliumExporter
    >>> map_obj = foliumExporter.export(geolocated_gedcom, title="Family Map")
    >>> map_obj.save('output.html')
"""
from .legend import Legend
from .mark_clusters import MyMarkClusters
from .folium_exporter import foliumExporter
from .name_processor import NameProcessor

__all__ = [
    "Legend",
    "MyMarkClusters",
    "foliumExporter",
    "NameProcessor",
]
