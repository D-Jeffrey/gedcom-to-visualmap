"""Models package: Data structures and utilities for rendering genealogical maps.

This package provides core classes for converting GEDCOM genealogical data into
visual elements (lines, colors, traces) for geographic mapping and visualization.

Core classes:
    - Color: RGBA color representation with hex conversion
    - Rainbow: Color gradient generator for visual distinction
    - Line: Geographic line segment with person, locations, and timeline
    - Creator, CreatorTrace, LifetimeCreator: Genealogical visualization generators

Re-exported from geo_gedcom:
    - Person: Individual genealogical record
    - LifeEvent: Dated event in a person's life
    - LatLon: Geographic latitude/longitude coordinate

Usage:
    >>> from models import Color, Rainbow, Line
    >>> color = Color(255, 0, 0)  # Red
    >>> rainbow = Rainbow()
    >>> line = Line(name="John Doe", ...)
"""

from .color import Color
from .creator import Creator, CreatorTrace, LifetimeCreator
from .line import Line
from .rainbow import Rainbow, Tint

# Re-export from geo_gedcom for convenience
from geo_gedcom.person import Person
from geo_gedcom.life_event import LifeEvent
from geo_gedcom.lat_lon import LatLon

__all__ = [
    # Color and visualization
    "Color",
    "Rainbow",
    "Tint",
    # Genealogical visualization creators
    "Creator",
    "CreatorTrace",
    "LifetimeCreator",
    # Geographic representation
    "Line",
    # Re-exported from geo_gedcom
    "Person",
    "LifeEvent",
    "LatLon",
]

__maintainer__ = "D-Jeffrey"