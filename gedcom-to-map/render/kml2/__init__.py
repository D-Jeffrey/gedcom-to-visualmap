"""KML2 package: Refined KML exporter with genealogical life lines.

Provides an improved KML format exporter with ancestor lines showing genealogical
relationships and migration patterns over time.

Classes:
    - KmlExporterRefined: Main refined KML exporter interface
    - KML_Life_Lines_Creator: Generates life line objects from genealogical data
    - KML_Life_Lines: Represents life line objects with style and properties

Usage:
    >>> from render.kml2 import KmlExporterRefined, KML_Life_Lines_Creator
    >>> creator = KML_Life_Lines_Creator(people)
    >>> lines = creator.create('person_id')
    >>> exporter = KmlExporterRefined()
    >>> exporter.export(lines, output_file="family_lifelines.kml")
"""

# Expose kml_life_lines.py symbols
from .kml_life_lines import (
    KmlExporterRefined,
    KML_Life_Lines_Creator,
    KML_Life_Lines,
)

__all__ = [
    "KmlExporterRefined",
    "KML_Life_Lines_Creator",
    "KML_Life_Lines",
]
