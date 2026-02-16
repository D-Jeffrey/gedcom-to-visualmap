"""Data processors: GEDCOM processing and map generation.

Provides specialized data processors:
    - GedcomLoader: GEDCOM file parsing and geocoding
    - MapGenerator: Map generation (HTML, KML, KML2, SUM formats)
    - ReportGenerator: Statistical reports and summaries
    - LineageTracer: Genealogical relationship tracing
"""

# Best-effort lazy exports so this package can be imported in non-GUI
# environments (e.g. Ubuntu CI core lane without wxPython).
__all__ = []

try:
    from .gedcom_loader import GedcomLoader

    __all__.append("GedcomLoader")
except ImportError:
    pass

try:
    from .map_generator import MapGenerator

    __all__.append("MapGenerator")
except ImportError:
    pass

try:
    from .report_generator import ReportGenerator

    __all__.append("ReportGenerator")
except ImportError:
    pass

try:
    from .lineage_tracer import LineageTracer

    __all__.append("LineageTracer")
except ImportError:
    pass
