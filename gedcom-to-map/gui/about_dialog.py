import logging
import wx

from .font_manager import FontManager
from const import VERSION, GUINAME, ABOUTLINK, NAME

_log = logging.getLogger(__name__.lower())

from .html_dialog import HTMLDialog

class AboutDialog(HTMLDialog):
    def __init__(self, parent, title, font_manager: FontManager):
        abouttype = """
<h1><a href="PROJECTLINK">VERVER</a></h1>
<b>Orginal project:</b> Originally forked from <a href="https://github.com/lmallez/gedcom-to-map/">gedcom-to-map.</a><p />
<h2>Contributors:</h2> 
<ul><li><b>Darren Jeffrey</b> (<a href="https://github.com/D-Jeffrey/">D-Jeffrey</a>)</li>
<li><b>Colin Osborne</b> (<a href="https://github.com/colin0brass/">colin0brass</a>)</li>
<li><b>Laurent Mallez</b> (<a href="https://github.com/lmallez/">lmallez</a>)</li>
</ul>
<h3>Major Packages:</h3>
<ul>
<li><b>ged4py</b> (<a href="https://ged4py.readthedocs.io/en/latest/">ged4py</a>) - For parsing GEDCOM files</li>
<li><b>wxPython</b> (<a href="https://wxpython.org/">wxPython</a>) - For building the graphical user interface (GUI)</li>
<li><b>folium</b> (<a href="https://python-visualization.github.io/folium/">folium</a>) - For creating interactive maps with Leaflet.js</li>
<li><b>simplekml</b> (<a href="https://simplekml.readthedocs.io/en/latest/">simplekml</a>) - For generating KML files for Google Earth</li>
<li><b>geopy</b> (<a href="https://geopy.readthedocs.io/en/stable/">geopy</a>) - For geocoding and reverse geocoding</li>
</ul>
<p />
<b>License:</b> <a href="https://github.com/D-Jeffrey/gedcom-to-visualmap/blob/main/LICENSE">MIT License.</a>

<p />
For more details and to contribute, visit the <a href="PROJECTLINK">GitHub repository.</a></li>
"""
        super().__init__(parent, title=title, icontype=wx.ART_INFORMATION, htmlbody=abouttype, width=55, font_manager=font_manager)
        try:
            if font_manager:
                font_manager.apply_current_font_recursive(self)
        except Exception:
            _log.exception("AboutDialog: failed to apply font to dialog")
