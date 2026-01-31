"""Models package: Data structures and utilities for rendering genealogical maps.

This package provides core classes for converting GEDCOM genealogical data into
visual elements (lines, colors, traces) for geographic mapping and visualization.

Core classes:
    - Color: RGBA color representation with hex conversion
    - Rainbow: Color gradient generator for visual distinction
    - Line: Geographic line segment with person, locations, and timeline
    - Creator, CreatorTrace, LifetimeCreator: Genealogical visualization generators
      with per-line loop detection supporting pedigree collapse

Loop Detection:
    All creator classes use per-line loop detection (via visited set parameter) instead
    of global tracking. This allows the same person to appear in different branches of
    the tree (pedigree collapse), while still preventing infinite loops in individual
    ancestral lines.

Re-exported from geo_gedcom:
    - Person: Individual genealogical record
    - LifeEvent: Dated event in a person's life
    - LatLon: Geographic latitude/longitude coordinate

Usage:
    >>> from models import Creator, Line, Rainbow
    >>> rainbow = Rainbow()
    >>> creator = Creator(people_dict, max_missing=2, gpstype='birth')
    >>> lines = creator.create(main_person_id)
    >>> for line in lines:
    ...     print(f"{line.name}: {line.color.to_hexa()}")
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