"""Migration flow visualization using Sankey diagrams.

Analyzes genealogical data to extract and visualize population migration patterns
between geographic locations across time periods.

Classes:
    - MigrationFlowExporter: Main exporter class
    - MigrationFlowAnalyzer: Analyzes migration patterns
    - SankeyBuilder: Constructs Plotly Sankey diagrams

Usage:
    >>> from render.migration import MigrationFlowExporter
    >>> exporter = MigrationFlowExporter(config, state, progress)
    >>> exporter.export(geolocated_gedcom)
"""

from .sankey_exporter import (
    MigrationFlowExporter,
    MigrationFlowAnalyzer,
    SankeyBuilder,
    LocationNode,
    MigrationFlow,
    MigrationEventType,
    MigrationStats,
)

__all__ = [
    "MigrationFlowExporter",
    "MigrationFlowAnalyzer",
    "SankeyBuilder",
    "LocationNode",
    "MigrationFlow",
    "MigrationEventType",
    "MigrationStats",
]