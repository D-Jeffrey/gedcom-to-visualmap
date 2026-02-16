"""
Heatmap utility functions for Folium-based genealogical map exporter.
"""

import folium


def normalize_heat_data(heat_data: list) -> None:
    """
    Normalize heat data to range [0,1].
    """
    if not heat_data:
        return
    max_value = max(point[2] for year_data in heat_data for point in year_data)
    for year_data in heat_data:
        for point in year_data:
            point[2] = float(point[2]) / max_value
