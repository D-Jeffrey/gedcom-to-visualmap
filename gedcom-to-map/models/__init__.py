"""
models package initialization.

Contains data structures and utilities for rendering visual maps
from GEDCOM data, including color schemes, positional logic,
and person representation.
"""

from .Color import Color
from .Creator import Creator
from .Person import Person, LifeEvent, DateFromField
from .Line import Line
from .LatLon import LatLon
from .Rainbow import Rainbow

__all__ = [
    "Color",
    "Creator",
    "DateFromField",
    "Person",
    'LifeEvent',
    "Line",
    "LatLon",
    "Rainbow"
]

__maintainer__ = "D-Jeffrey"