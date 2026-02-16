"""
Polyline utility functions for Folium-based genealogical map exporter.
"""

import math
import folium


def add_polyline(line, fg, fm_line, marker_options, popup_content, max_line_weight, use_ant_path, gOp):
    """
    Add a polyline to the feature group if there are enough points.
    """
    if len(fm_line) > 1:
        line_color = marker_options["line_color"]
        line_width = (
            max(int(max_line_weight / math.exp(0.5 * min(getattr(line, "prof", 1), 1000))), 2)
            if getattr(line, "prof", None)
            else 1
        )
        if use_ant_path:
            polyline = folium.plugins.AntPath(
                fm_line,
                weight=line_width,
                opacity=0.7,
                tooltip=line.name,
                popup=popup_content,
                color=line_color,
                lineJoin="arcs",
            )
        else:
            polyline = folium.features.PolyLine(
                fm_line,
                color=line_color,
                weight=line_width,
                opacity=1,
                tooltip=line.name,
                popup=popup_content,
                dash_array=marker_options["dash_array"],
                lineJoin="arcs",
            )
        fg.add_child(polyline)
