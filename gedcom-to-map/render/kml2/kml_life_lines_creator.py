"""
kml_life_lines_creator.py - KML exporter for geolocated GEDCOM data.

Exports genealogical events and relationships to KML for visualization in Google Earth.

Author: @colin0brass
"""

from typing import Dict, Optional
import logging
import simplekml
from geo_gedcom.person import Person
from geo_gedcom.geolocated_gedcom import GeolocatedGedcom
from .kml_exporter_refined import KmlExporterRefined

logger = logging.getLogger(__name__)

from .kml_exporter_refined import BIRTH_ICON, MARRIAGE_ICON, DEATH_ICON


class KML_Life_Lines_Creator:
    """
    Creates KML life lines and placemarks for people and their relationships.

    Attributes:
        kml_instance (KmlExporterRefined): KML exporter instance.
        gedcom (GeolocatedGedcom): Geolocated GEDCOM data.
        kml_point_to_person_lookup (Dict[Optional[str], str]): Maps KML point IDs to person IDs.
        kml_person_to_point_lookup (Dict[str, Optional[str]]): Maps person IDs to KML point IDs.
        kml_person_to_placemark_lookup (Dict[str, Optional[str]]): Maps person IDs to placemark IDs.
        use_hyperlinks (bool): Whether to use hyperlinks in descriptions.
        main_person_id (Optional[str]): Main person to focus on.
    """

    __slots__ = [
        'kml_instance', 'gedcom', 'kml_point_to_person_lookup', 'kml_person_to_point_lookup',
        'kml_person_to_placemark_lookup', 'use_hyperlinks', 'main_person_id'
    ]
    place_type_list = ['Birth', 'Marriage', 'Death']

    def __init__(
        self,
        gedcom: GeolocatedGedcom,
        kml_file: str,
        use_hyperlinks: bool = True,
        main_person_id: Optional[str] = None
    ) -> None:
        """
        Initialize the KML life lines creator.

        Args:
            gedcom (GeolocatedGedcom): Geolocated GEDCOM data.
            kml_file (str): Path to output KML file.
            use_hyperlinks (bool): Use hyperlinks in descriptions.
            main_person_id (Optional[str]): Main person to focus on.
        """
        self.kml_instance: KmlExporterRefined = KmlExporterRefined(kml_file)
        self.gedcom: GeolocatedGedcom = gedcom
        self.kml_point_to_person_lookup: Dict[Optional[str], str] = dict()
        self.kml_person_to_point_lookup: Dict[str, Optional[str]] = dict()
        self.kml_person_to_placemark_lookup: Dict[str, Optional[str]] = dict()
        self.use_hyperlinks: bool = use_hyperlinks
        self.main_person_id: Optional[str] = main_person_id

    def _add_point(self, current: Person, event: object, event_type: str) -> None:
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
            description =  f'{event_type} {event.date.year_str}<br>{event.place}<br>'
            placemark_id, point_id = self.kml_instance.add_point(event_type, current.name, latlon, event.date.year_num if event.date.year_num is not None else 0, description)
            self.kml_point_to_person_lookup[point_id] = current.xref_id
            self.kml_person_to_point_lookup[current.xref_id] = point_id
            self.kml_person_to_placemark_lookup[current.xref_id] = placemark_id

    def add_person(self, current: Person) -> None:
        """
        Add placemarks for all events of a person.

        Args:
            current (Person): The person.
        """
        birth_event = current.get_event('birth') if current else None
        current_birth_latlon = birth_event.getattr('latlon') if birth_event else None
        if birth_event and current_birth_latlon and current_birth_latlon.is_valid():
            self._add_point(current, birth_event, "Birth")

        marriages = current.get_events('marriage') if current else []
        for marriage in marriages:
            marriage_event = marriage.event
            marriage_latlon = marriage_event.getattr('latlon') if marriage_event else None
            if marriage_event and marriage_latlon and marriage_latlon.is_valid():
                self._add_point(current, marriage_event, "Marriage")

        death_event = current.get_event('death') if current else None
        current_death_latlon = death_event.getattr('latlon') if death_event else None
        if death_event and current_death_latlon and current_death_latlon.is_valid():
            self._add_point(current, death_event, "Death")

    def update_person_description(self, point: simplekml.featgeom.Point, current: Person) -> None:
        """
        Update the KML placemark description with family links.

        Args:
            point (simplekml.featgeom.Point): KML point.
            current (Person): The person.
        """
        description = point.description
        birth_event = current.get_event('birth') if current else None
        if birth_event and getattr(birth_event, 'location', None) and getattr(birth_event.location, 'latlon', None) and birth_event.location.latlon.is_valid():
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
        for _, person in self.gedcom.people.items():
            self.add_person(person)

        for g in self.kml_instance.kml.allgeometries:
            person = self.gedcom.people[self.kml_point_to_person_lookup.get(g.id)]
            self.update_person_description(g, person)

    def connect_parents(self) -> None:
        """
        Draw lines connecting each person to their parents.
        """
        line_type = 'Parents'
        for _, person in self.gedcom.people.items():
            logger.info(f'person: {person}')
            if person.latlon and person.latlon.is_valid():
                birth_event = person.get_event('birth') if person else None
                begin_date = birth_event.date.year_num if birth_event and birth_event.date else None

                if person.father:
                    father = self.gedcom.people[person.father]
                    line_name = f'Father: {father.name}'
                    if father.latlon and father.latlon.is_valid():
                        father_birth_event = father.get_event('birth') if father else None
                        end_date = father_birth_event.date.year_num if father_birth_event and father_birth_event.date else None
                        self.kml_instance.draw_line(line_type, line_name, person.latlon, father.latlon,
                                                    begin_date, end_date, simplekml.Color.blue)

                if person.mother:
                    mother = self.gedcom.people[person.mother]
                    line_name = f'Mother: {mother.name}'
                    if mother.latlon and mother.latlon.is_valid():
                        mother_birth_event = mother.get_event('birth') if mother else None
                        end_date = mother_birth_event.date.year_num if mother_birth_event and mother_birth_event.date else None
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
            birth_event = person.get_event('birth') if person else None
            death_event = person.get_event('death') if person else None
            begin_year = birth_event.date.year_num if birth_event and birth_event.date else None
            end_year = death_event.date.year_num if death_event and death_event.date else None
            self.kml_instance.lookat(latlon=person.latlon, begin_year=begin_year, end_year=end_year)

    def save_kml(self) -> None:
        """
        Save the KML file to disk.
        """
        self.kml_instance.finalise()
