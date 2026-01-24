import logging
import wx

from ..layout.font_manager import FontManager

_log = logging.getLogger(__name__.lower())

from .html_dialog import HTMLDialog

class HelpDialog(HTMLDialog):
    def __init__(self, parent, title, font_manager: FontManager):
        helppage = """
<h2><a href="PROJECTLINK">VERVER</a></h2>
<p>The "GEDCOM to Visual Map" project is a powerful tool designed to read <a href="https://gedcom.io/">GEDCOM files</a> and translate the locations into GPS addresses. It produces different KML map types that show timelines and movements around the earth. The project includes both command-line and GUI interfaces (tested on Windows) to provide flexibility in usage.</p>
<h3>Key Features:</h3>
<ul><li><b>Interactive Maps:</b> Generates interactive HTML files that display relationships between children and parents, and where people lived over the years.</li>
<li><b>Heatmaps:</b> Includes heatmaps to show busier places, with markers overlayed for detailed views.</li>
<li><b>Geocoding:</b> Converts place names into GPS coordinates, allowing for accurate mapping.</li>
<li><b>Multiple Output Formats:</b> Supports both <a href="https://python-visualization.github.io/folium/latest/">HTML</a> and <a href="https://support.google.com/earth/answer/7365595">KML</a> output formats for versatile map visualization.  KML2 is an alternate and improved version of the orginal way of generating the relationship(Not all Options work with this mode yet)</li>
<li><b>User-Friendly GUI:</b> The GUI version allows users to easily load GEDCOM files, set options, and generate maps with a few clicks.</li>
<li><b>Customizable Options:</b> Offers various options to customize the map, such as grouping by family name, turning on/off markers, and adjusting heatmap settings.</li>
</ul>
<h3>Things to know</h3>
<ul><li><b>Right-click:</b> Right-click on (Activate) a person in the list to view more details.</li>
<li><b>Double-click</b> Double-click on a person in the list to set them as the main person and find all their associcated parents</li>
<li><b>click parent</b> Click on a parent in the person dialog to open that parent's details</li>
<li><b>Trace</b> For the selected person save to a text file all the associcated parents(tab seperated)</li>
<li><b>Geo Table</b> Edit the file and translates so that next time it does better location lookups by putting replacement values in the 'alt' column or by filling in the 'Country', 
then blank the lat, long and boundary have it looked up again. Do not convert it to another format and close Excel so the file can be access.</li>
<li><b>Logging Options</b> Can be updated while the application is loading or resolves addresses.</li>
<li><b>Relatives</b> Can Activate a person and the bring up the Person and if they are in a direct line, it will list the father & mother trace along with the children.</li>                          
<li><b>Photos</b> Photos can be a URL or a local file path.  If a URL it must start with http:// or https://.  If a local file path it can be absolute or relative to the gedcom file.</li>                          
<li><b>Timelines</b> The KML output has a timeline that can be used to show the movement of people over time.  The timeline can be used to filter the display of people on the map.</li>
                          </ul>
For more details and to contribute, visit the <a href="PROJECTLINK">GitHub repository.</a></li>
<p>
</p>
"""
        super().__init__(parent, title=title, icontype=wx.ART_INFORMATION, htmlbody=helppage, width=55, font_manager=font_manager)
        try:
            if font_manager:
                font_manager.apply_current_font_recursive(self)
        except Exception:
            _log.exception("HelpDialog: failed to apply font to dialog")
