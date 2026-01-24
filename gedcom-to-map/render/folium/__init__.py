"""
folium subpackage: Folium-based mapping and visualization utilities for GEDCOM data.
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
