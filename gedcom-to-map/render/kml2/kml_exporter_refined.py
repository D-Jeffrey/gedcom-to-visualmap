"""
kml_exporter_refined.py - KML exporter for geolocated GEDCOM data.

Exports genealogical events and relationships to KML for visualization in Google Earth.

Author: @colin0brass
"""

from typing import Optional, Tuple
import logging
import simplekml

from geo_gedcom.lat_lon import LatLon

logger = logging.getLogger(__name__)

BIRTH_ICON = "http://maps.google.com/mapfiles/kml/paddle/pink-blank.png"
MARRIAGE_ICON = "http://maps.google.com/mapfiles/kml/paddle/grn-blank.png"
DEATH_ICON = "http://maps.google.com/mapfiles/kml/paddle/wht-blank.png"


class KmlExporterRefined:
    """
    Exports genealogical data to KML format for visualization in Google Earth.

    Attributes:
        kml_file (str): Path to output KML file.
        kml (simplekml.Kml): KML document object.
        kml_folders (Dict[str, simplekml.Folder]): Folders for event types.
        marker_style (Dict[str, dict]): Marker style configuration.
        line_types (List[str]): Types of lines to draw (e.g., parent links).
    """

    __slots__ = ["kml_file", "kml", "kml_folders"]
    line_width = 2
    timespan_default_start_year = 1950
    timespan_default_range_years = 100
    marker_style = {
        "Birth": {"icon_href": BIRTH_ICON},
        "Marriage": {
            "icon_href": MARRIAGE_ICON,
        },
        "Death": {
            "icon_href": DEATH_ICON,
        },
    }
    line_types = ["Parents"]

    def __init__(self, kml_file: str) -> None:
        """
        Initialize the KML exporter and create folders/styles for each marker type.

        Args:
            kml_file (str): Path to output KML file.
        """
        self.kml_file = kml_file
        self.kml = simplekml.Kml()
        self.kml_folders = dict()

        for marker_type in self.marker_style.keys():
            self.marker_style[marker_type]["style"] = simplekml.Style()
            self.marker_style[marker_type]["style"].iconstyle.icon.href = self.marker_style[marker_type]["icon_href"]
            self.marker_style[marker_type]["style"].name = marker_type
            self.kml_folders[marker_type] = self.kml.newfolder(name=marker_type)
        for line_type in self.line_types:
            self.kml_folders[line_type] = self.kml.newfolder(name=line_type)

    def finalise(self) -> None:
        """
        Save the KML file to disk.
        """
        if not self.kml:
            logger.error("KML not initialised")
        else:
            logger.info(f"Saving KML file: {self.kml_file}")
            self.kml.save(self.kml_file)

    def add_point(
        self, marker_type: str, name: str, latlon: LatLon, timestamp: Optional[str], description: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Add a placemark point to the KML for a given event.

        Args:
            marker_type (str): Type of marker ('Birth', 'Marriage', 'Death').
            name (str): Name for the placemark.
            latlon (LatLon): Latitude/longitude.
            timestamp (Optional[str]): Timestamp string (ISO format or year).
            description (str): Description for the placemark.

        Returns:
            Tuple[Optional[str], Optional[str]]: (placemark_id, point_id)
        """
        placemark_id: Optional[str] = None
        point_id: Optional[str] = None
        if latlon and latlon.is_valid():
            pnt = self.kml_folders[marker_type].newpoint(
                name=name, coords=[(latlon.lon, latlon.lat)], description=description
            )
            if timestamp:
                pnt.timestamp.when = timestamp
            if marker_type in self.marker_style.keys():
                pnt.style = self.marker_style[marker_type]["style"]
            point_id = getattr(pnt, "id", None)
            placemark_id = getattr(getattr(pnt, "placemark", None), "id", None)
        return placemark_id, point_id

    def draw_line(
        self,
        line_type: str,
        name: str,
        begin_lat_lon: LatLon,
        end_lat_lon: LatLon,
        begin_date: Optional[str],
        end_date: Optional[str],
        colour: str = simplekml.Color.white,
    ) -> Optional[str]:
        """
        Draw a line between two LatLon points in the KML.

        Args:
            line_type (str): Type of line ('Parents').
            name (str): Name for the line.
            begin_lat_lon (LatLon): Start point.
            end_lat_lon (LatLon): End point.
            begin_date (Optional[str]): Start date (ISO or year).
            end_date (Optional[str]): End date (ISO or year).
            colour (str): Line color (KML color string).

        Returns:
            Optional[str]: Line's KML id.
        """
        kml_line = None
        if begin_lat_lon and begin_lat_lon.is_valid() and end_lat_lon and end_lat_lon.is_valid():
            kml_line = self.kml_folders[line_type].newlinestring(
                name=name, coords=[(begin_lat_lon.lon, begin_lat_lon.lat), (end_lat_lon.lon, end_lat_lon.lat)]
            )
            kml_line.timespan.begin = begin_date
            kml_line.timespan.end = end_date
            kml_line.altitudemode = simplekml.AltitudeMode.clamptoground
            kml_line.extrude = 1
            kml_line.tessellate = 1
            kml_line.style.linestyle.color = colour
            kml_line.style.linestyle.width = self.line_width
            return getattr(kml_line, "id", None)
        return None

    def lookat(
        self,
        latlon: LatLon,
        begin_year: Optional[int],
        end_year: Optional[int],
        altitude: int = 0,
        range: int = 1000,
        heading: int = 0,
        tilt: int = 0,
    ) -> None:
        """
        Set the initial camera view in Google Earth to a given LatLon.

        Args:
            latlon (LatLon): Location to look at.
            begin_year (Optional[int]): Start year.
            end_year (Optional[int]): End year.
            altitude (int): Altitude.
            range (int): Range.
            heading (int): Heading.
            tilt (int): Tilt.
        """
        if latlon and latlon.is_valid():
            lookat = simplekml.LookAt(
                latitude=latlon.lat, longitude=latlon.lon, altitude=altitude, range=range, heading=heading, tilt=tilt
            )
            self.kml.document.lookat = lookat
