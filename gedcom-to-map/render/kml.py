"""
kml.py - KML exporter for geolocated GEDCOM data.

Exports genealogical events and relationships to KML for visualization in Google Earth.

Author: @colin0brass
"""

from typing import Dict, Optional, Tuple, List
import logging
import simplekml

from models.location import LatLon
from models.Person import Person
from gedcom.gedcom import GeolocatedGedcom


logger = logging.getLogger(__name__)

BIRTH_ICON = 'http://maps.google.com/mapfiles/kml/paddle/pink-blank.png'
MARRIAGE_ICON = 'http://maps.google.com/mapfiles/kml/paddle/grn-blank.png'
DEATH_ICON = 'http://maps.google.com/mapfiles/kml/paddle/wht-blank.png'

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

    __slots__ = [
        'kml_file', 'kml', 'kml_folders'
    ]
    line_width = 2
    timespan_default_start_year = 1950
    timespan_default_range_years = 100
    marker_style = {
        'Birth': {
            'icon_href': BIRTH_ICON
        },
        'Marriage': {
            'icon_href': MARRIAGE_ICON,
        },
        'Death': {
            'icon_href': DEATH_ICON,
        }
    }
    line_types = ['Parents']

    def __init__(self, kml_file: str):
        """
        Initialize the KML exporter and create folders/styles for each marker type.

        Args:
            kml_file (str): Path to output KML file.
        """
        self.kml_file = kml_file
        self.kml = simplekml.Kml()
        self.kml_folders = dict()

        for marker_type in self.marker_style.keys():
            self.marker_style[marker_type]['style'] = simplekml.Style()
            self.marker_style[marker_type]['style'].iconstyle.icon.href = self.marker_style[marker_type]['icon_href']
            self.marker_style[marker_type]['style'].name = marker_type
            self.kml_folders[marker_type] = self.kml.newfolder(name=marker_type)
        for line_type in self.line_types:
            self.kml_folders[line_type] = self.kml.newfolder(name=line_type)

    def finalise(self) -> None:
        """
        Save the KML file to disk.
        """
        if not self.kml:
            logger.error('KML not initialised')
        else:
            logger.info(f'Saving KML file: {self.kml_file}')
            self.kml.save(self.kml_file)

    def add_point(self, marker_type: str, name: str, latlon: LatLon, timestamp: str, description: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Add a placemark point to the KML for a given event.

        Args:
            marker_type (str): Type of marker ('Birth', 'Marriage', 'Death').
            name (str): Name for the placemark.
            latlon (LatLon): Latitude/longitude.
            timestamp (str): Timestamp string.
            description (str): Description for the placemark.

        Returns:
            Tuple[Optional[str], Optional[str]]: (placemark_id, point_id)
        """
        placemark_id = None
        point_id = None
        if latlon and latlon.is_valid():
            pnt = self.kml_folders[marker_type].newpoint(
                name=name,
                coords=[(latlon.lon, latlon.lat)],
                description=description
            )
            if timestamp:
                pnt.timestamp.when = timestamp
            if marker_type in self.marker_style.keys():
                pnt.style = self.marker_style[marker_type]['style']
            point_id = pnt.id
            placemark_id = pnt.placemark.id
        return placemark_id, point_id

    def draw_line(self, line_type: str, name: str, begin_lat_lon: LatLon, end_lat_lon: LatLon,
                  begin_date: str, end_date: str,
                  colour: simplekml.Color = simplekml.Color.white) -> Optional[str]:
        """
        Draw a line between two LatLon points in the KML.

        Args:
            line_type (str): Type of line ('Parents').
            name (str): Name for the line.
            begin_lat_lon (LatLon): Start point.
            end_lat_lon (LatLon): End point.
            begin_date (str): Start date.
            end_date (str): End date.
            colour (simplekml.Color): Line color.

        Returns:
            Optional[str]: Line's KML id.
        """
        kml_line = None
        if begin_lat_lon and begin_lat_lon.is_valid() and end_lat_lon and end_lat_lon.is_valid():
            kml_line = self.kml_folders[line_type].newlinestring(
                name=name,
                coords=[(begin_lat_lon.lon, begin_lat_lon.lat), (end_lat_lon.lon, end_lat_lon.lat)]
            )
            kml_line.timespan.begin = begin_date
            kml_line.timespan.end   = end_date
            kml_line.altitudemode   = simplekml.AltitudeMode.clamptoground
            kml_line.extrude        = 1
            kml_line.tessellate     = 1
            kml_line.style.linestyle.color  = colour
            kml_line.style.linestyle.width  = self.line_width
            return kml_line.id
        return None
    
    def lookat(self, latlon: LatLon, begin_year: int, end_year: int, altitude=0, range=1000, heading=0, tilt=0) -> None:
        """
        Set the initial camera view in Google Earth to a given LatLon.

        Args:
            latlon (LatLon): Location to look at.
            begin_year (int): Start year.
            end_year (int): End year.
            altitude (int): Altitude.
            range (int): Range.
            heading (int): Heading.
            tilt (int): Tilt.
        """
        if latlon and latlon.is_valid():
            lookat = simplekml.LookAt(
                latitude=latlon.lat, longitude=latlon.lon,
                altitude=altitude, range=range,
                heading=heading, tilt=tilt
            )
            self.kml.document.lookat = lookat

class KML_Life_Lines_Creator:
    """
    Creates KML life lines and placemarks for people and their relationships.

    Attributes:
        kml_instance (KmlExporter): KML exporter instance.
        gedcom (GeolocatedGedcom): Geolocated GEDCOM data.
        kml_point_to_person_lookup (dict): Maps KML point IDs to person IDs.
        kml_person_to_point_lookup (dict): Maps person IDs to KML point IDs.
        kml_person_to_placemark_lookup (dict): Maps person IDs to placemark IDs.
        use_hyperlinks (bool): Whether to use hyperlinks in descriptions.
        main_person_id (Optional[str]): Main person to focus on.
    """

    __slots__ = [
        'kml_instance', 'gedcom', 'kml_point_to_person_lookup', 'kml_person_to_point_lookup',
        'kml_person_to_placemark_lookup', 'use_hyperlinks', 'main_person_id'
    ]
    place_type_list = ['Birth', 'Marriage', 'Death']

    def __init__(self, gedcom: GeolocatedGedcom, kml_file: str, use_hyperlinks: bool = True, main_person_id: Optional[str] = None):
        """
        Initialize the KML life lines creator.

        Args:
            gedcom (GeolocatedGedcom): Geolocated GEDCOM data.
            kml_file (str): Path to output KML file.
            use_hyperlinks (bool): Use hyperlinks in descriptions.
            main_person_id (Optional[str]): Main person to focus on.
        """
        self.kml_instance = KmlExporterRefined(kml_file)
        self.gedcom = gedcom
        self.kml_point_to_person_lookup = dict()
        self.kml_person_to_point_lookup = dict()
        self.kml_person_to_placemark_lookup = dict()
        self.use_hyperlinks = use_hyperlinks
        self.main_person_id = main_person_id

    def _add_point(self, current: Person, event, event_type: str) -> None:
        """
        Add a placemark for a person's event (birth, marriage, death).

        Args:
            current (Person): The person.
            event: The event object.
            event_type (str): Type of event.
        """
        location = getattr(event, 'location', None)
        latlon = getattr(location, 'latlon', None)
        if event and latlon and latlon.is_valid():
            description =  f'{event_type} {event.date_year()}<br>{event.place}<br>'
            placemark_id, point_id = self.kml_instance.add_point(event_type, current.name, latlon, event.date_year(), description)
            self.kml_point_to_person_lookup[point_id] = current.xref_id
            self.kml_person_to_point_lookup[current.xref_id] = point_id
            self.kml_person_to_placemark_lookup[current.xref_id] = placemark_id

    def add_person(self, current: Person) -> None:
        """
        Add placemarks for all events of a person.

        Args:
            current (Person): The person.
        """
        if current.birth and getattr(current.birth, 'location', None) and getattr(current.birth.location, 'latlon', None) and current.birth.location.latlon.is_valid():
            self._add_point(current, current.birth, "Birth")
        for marriage_event in getattr(current, 'marriages', []):
            if marriage_event and getattr(marriage_event, 'location', None) and getattr(marriage_event.location, 'latlon', None) and marriage_event.location.latlon.is_valid():
                self._add_point(current, marriage_event, "Marriage")
        if getattr(current, 'death', None) and getattr(current.death, 'location', None) and getattr(current.death.location, 'latlon', None) and current.death.location.latlon.is_valid():
            self._add_point(current, current.death, "Death")

    def update_person_description(self, point: simplekml.featgeom.Point, current: Person) -> None:
        """
        Update the KML placemark description with family links.

        Args:
            point (simplekml.featgeom.Point): KML point.
            current (Person): The person.
        """
        description = point.description
        if current.birth and getattr(current.birth, 'location', None) and getattr(current.birth.location, 'latlon', None) and current.birth.location.latlon.is_valid():
            if current.father and (current.father in self.kml_person_to_point_lookup):
                father_id = self.kml_person_to_placemark_lookup.get(current.father)
                if father_id and current.father in self.gedcom.people:
                    if self.use_hyperlinks:
                        description += f'Father: <a href=#{father_id};balloonFlyto>{self.gedcom.people[current.father].name}</a><br>'
                    else:
                        description += f'Father: {self.gedcom.people[current.father].name}<br>'
            if current.mother and (current.mother in self.kml_person_to_point_lookup):
                mother_id = self.kml_person_to_placemark_lookup.get(current.mother)
                if mother_id and current.mother in self.gedcom.people:
                    if self.use_hyperlinks:
                        description += f'Mother: <a href=#{mother_id};balloonFlyto>{self.gedcom.people[current.mother].name}</a><br>'
                    else:
                        description += f'Mother: {self.gedcom.people[current.mother].name}<br>'
            if getattr(current, 'children', None):
                description += 'Children: '
                for child in current.children:
                    if child in self.kml_person_to_placemark_lookup and child in self.gedcom.people:
                        child_id = self.kml_person_to_placemark_lookup[child]
                        description += f'<a href=#{child_id};balloonFlyto>{self.gedcom.people[child].name}</a> '
                    elif child in self.gedcom.people:
                        description += f'{self.gedcom.people[child].name} '
        point.description = description

    def add_people(self) -> None:
        """
        Add all people from the GEDCOM to the KML.
        """
        for person_id, person in self.gedcom.people.items():
            self.add_person(person)

        for g in self.kml_instance.kml.allgeometries:
            person = self.gedcom.people[self.kml_point_to_person_lookup.get(g.id)]
            self.update_person_description(g, person)

    def connect_parents(self) -> None:
        """
        Draw lines connecting each person to their parents.
        """
        line_type = 'Parents'
        for person_id, person in self.gedcom.people.items():
            logger.info(f'person: {person}')
            if person.latlon and person.latlon.is_valid():
                begin_date = person.birth.date_year() if person.birth and person.birth.date else None

                if person.father:
                    father = self.gedcom.people[person.father]
                    line_name = f'Father: {father.name}'
                    if father.latlon and father.latlon.is_valid():
                        end_date = father.birth.date_year() if father.birth and father.birth.date else None
                        self.kml_instance.draw_line(line_type, line_name, person.latlon, father.latlon,
                                                    begin_date, end_date, simplekml.Color.blue)

                if person.mother:
                    mother = self.gedcom.people[person.mother]
                    line_name = f'Mother: {mother.name}'
                    if mother.latlon and mother.latlon.is_valid():
                        end_date = mother.birth.date_year() if mother.birth and mother.birth.date else None
                        self.kml_instance.draw_line(line_type, line_name, person.latlon, mother.latlon,
                                                    begin_date, end_date, simplekml.Color.red)

    def lookat_person(self, person_id: str) -> None:
        """
        Set the camera view to a specific person in the KML.

        Args:
            person_id (str): Person's xref ID.
        """
        person = self.gedcom.people.get(person_id)
        if person and person.latlon and person.latlon.is_valid():
            begin_year = person.birth.date_year() if person.birth and person.birth.date else None
            end_year = person.death.date_year() if person.death and person.death.date else None
            self.kml_instance.lookat(latlon=person.latlon, begin_year=begin_year, end_year=end_year)

    def save_kml(self) -> None:
        """
        Save the KML file to disk.
        """
        self.kml_instance.finalise()

class KML_Life_Lines:
    """
    High-level wrapper for creating and saving KML life lines for a GEDCOM dataset.

    This class uses KML_Life_Lines_Creator to add people, connect parents, set camera view,
    and save the resulting KML file. It is intended to simplify the workflow for exporting
    genealogical relationships to KML for visualization.

    Attributes:
        gedcom (GeolocatedGedcom): Geolocated GEDCOM data.
        kml_file (str): Path to output KML file.
        kml_life_lines_creator (KML_Life_Lines_Creator): Instance of the KML life lines creator.
    """

    __slots__ = ['gedcom', 'kml_file', 'kml_life_lines_creator']

    def __init__(self, gedcom: GeolocatedGedcom, kml_file: str,
                 connect_parents: bool = True, save: bool = True):
        """
        Initialize the KML_Life_Lines wrapper.

        This sets up the KML life lines creator, adds people, optionally connects parents,
        sets the camera view to the main person, and optionally saves the KML file.

        Args:
            gedcom (GeolocatedGedcom): Geolocated GEDCOM data.
            kml_file (str): Path to output KML file.
            connect_parents (bool, optional): Whether to draw parent-child lines. Defaults to True.
            save (bool, optional): Whether to save the KML file immediately. Defaults to True.
        """

        self.kml_life_lines_creator = KML_Life_Lines_Creator(gedcom=gedcom, kml_file=kml_file)
        self.kml_life_lines_creator.add_people()

        if connect_parents:
            self.kml_life_lines_creator.connect_parents()

        if save:
            self.kml_life_lines_creator.save_kml()

    def save(self) -> None:
        """
        Save the KML file to disk.

        This method calls the underlying KML_Life_Lines_Creator's save_kml method.
        """
        self.kml_life_lines_creator.save_kml()