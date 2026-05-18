"""
Constants and templates for Folium-based genealogical map exporter.
"""

lgd_txt = '<span style="color: {col};">{txt}</span>'

MidPointMarker = {
    "born": ("baby", "orange", False),
    "death": ("cross", "gray", False),
    "home": ("home", "lightred", False),
    "Marriage": ("ring", "orange", True),
    "IMMI": ("ship", "darkgreen", True),
    "CHR": ("church", "darkgreen", True),
    "BAPM": ("church", "darkgreen", True),
    "Deed": ("landmark", "darkgreen", True),
    "Arrival": ("ship", "darkgreen", True),
    "OCCU": ("briefcase", "blue", True),
    "ADDR": ("home", "lightred", True),
    "CENS": ("home", "lightred", True),
    "EDUC": ("graduation-cap", "blue", True),
    "Other": ("shoe-prints", "lightgray", True),
}

icon_create_function = """\
function(cluster) {
    return L.divIcon({
    html: '<b>' + cluster.getChildCount() + '</b>',
    className: 'marker-cluster marker-cluster-large',
    iconSize: new L.Point(20, 20)
    });
}"""
