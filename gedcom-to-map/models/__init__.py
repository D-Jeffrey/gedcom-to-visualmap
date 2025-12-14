"""
models package initialization.

Contains data structures and utilities for rendering visual maps
from GEDCOM data, including color schemes, positional logic,
and person representation.
"""

from .color import Color
from .creator import Creator
from .line import Line
from .rainbow import Rainbow

# If you want to expose these from geo_gedcom, import them here:
from geo_gedcom.person import Person
from geo_gedcom.life_event import LifeEvent
from geo_gedcom.lat_lon import LatLon

__all__ = [
    "Color",
    "Creator",
    "Line",
    "Rainbow",
    "Person",
    "LifeEvent",
    "LatLon",
]

__maintainer__ = "D-Jeffrey"