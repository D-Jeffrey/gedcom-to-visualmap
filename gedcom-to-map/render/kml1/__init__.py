"""KML1 package: Legacy KML exporter for geolocated GEDCOM data.

Provides the original KML format exporter for geographic visualization of
genealogic relationships and person locations.

Classes:
    - KmlExporter: Exports genealogical data as KML (Keyhole Markup Language) files

Usage:
    >>> from render.kml1 import KmlExporter
    >>> exporter = KmlExporter()
    >>> exporter.export(geolocated_gedcom, output_file="family.kml")
"""

from .kml_exporter import KmlExporter

__all__ = ["KmlExporter"]
