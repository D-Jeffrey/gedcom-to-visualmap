"""
render package initialization.

Provides export and rendering utilities for visualizing GEDCOM data,
including KML generation, Folium-based mapping, and reference handling.
"""

from .KmlExporter import KmlExporter
from .Referenced import Referenced
from .foliumExp import foliumExporter, MyMarkClusters, Legend
from .naming import NameProcessor, isValidName, compareNames, simplifyLastName, soundex

__all__ = [
    "KmlExporter",
    "Referenced",
    "export_folium_map",
    'MyMarkClusters', 
    'foliumExporter',
    'Legend',
    "NameProcessor",
    "isValidName",
    "compareNames",
    "simplifyLastName",
    "soundex"
]

__author__ = "D-Jeffrey"