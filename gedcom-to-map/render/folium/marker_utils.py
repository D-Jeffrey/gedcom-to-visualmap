"""
Marker utility functions for Folium-based genealogical map exporter.
"""
import random
import folium
from .constants import MidPointMarker

def Drift(l: float) -> float:
    """
    Apply a small random drift to a coordinate value to avoid marker overlap.
    """
    d = ((random.random() * 0.001) - 0.0005)
    return float(l) + d if l is not None else None

def add_point_marker(fg: folium.FeatureGroup, point: list, options: dict, 
                     tooltip: str, popup: str, icon_name: str, color: str, gOp=None) -> None:
    """
    Add a marker to the feature group or collect for clustering if gOp is provided and MarksOn is False.
    """
    if gOp is not None and not getattr(gOp, 'MarksOn', True):
        # Collect for clustering
        if hasattr(gOp, 'locations') and hasattr(gOp, 'popups'):
            gOp.locations.append(point)
            gOp.popups.append(popup)
        return
    marker = folium.Marker(
        point,
        tooltip=tooltip,
        popup=popup,
        opacity=0.5,
        icon=folium.Icon(color=color, icon=icon_name, prefix='fa', extraClasses='fas')
    )
    fg.add_child(marker)
