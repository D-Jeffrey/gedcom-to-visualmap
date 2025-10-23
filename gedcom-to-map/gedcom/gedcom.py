"""
gedcom.py - GEDCOM data model and parser.

Defines classes for representing people, life events, and parsing GEDCOM files.
Supports geolocation integration and KML export.

Author: @colin0brass
"""

import os
import csv
import re
import copy
from datetime import datetime
import tempfile
import logging
from pathlib import Path
from typing import Dict, List, Optional

from ged4py.parser import GedcomReader
from ged4py.model import Record, NameRec

from .geocode import Geocode
from models.location import Location
from models.LatLon import LatLon
from models.Person import Person, LifeEvent
from .addressbook import FuzzyAddressBook
from gedcomoptions import gvOptions

logger = logging.getLogger(__name__)

homelocationtags = ('OCCU', 'CENS', 'EDUC')
otherlocationtags = ('CHR', 'BAPM', 'BASM', 'BAPL', 'IMMI', 'NATU', 'ORDN','ORDI', 'RETI', 
                     'EVEN',  'CEME', 'CREM', 'FACT' )
addrtags = ('ADR1', 'ADR2', 'ADR3', 'CITY', 'STAE', 'POST', 'CTRY')

def getgdate (gstr):
    r = datetime.fromisocalendar(1000,1,1)
    d = m = y = None
    if gstr:
        k = gstr.value.kind.name
        if (k in ['SIMPLE', 'ABOUT','FROM']):
            y = gstr.value.date.year
            m = gstr.value.date.month_num
            d = gstr.value.date.day
        elif (k in ['AFTER','BEFORE']):
            y = gstr.value.date.year
            m = gstr.value.date.month_num
            d = gstr.value.date.day
        elif (k == 'RANGE') or(k ==  'PERIOD'):
            y = gstr.value.date1.year
            m = gstr.value.date1.month_num
            d = gstr.value.date1.day

        elif k == 'PHRASE':
            #TODO need to fix up
            y = y 
        else:
            logger.warning ("Date type; %s", gstr.value.kind.name)
        y = (y, 1000) [y == None]
        m = (m, 1) [m == None]
        d = (d, 1) [d == None]

        r = r.replace(y, m, d)
    return r
class GedcomParser:
    """
    Parses GEDCOM files and extracts people and places.

    Attributes:
        gedcom_file (Optional[str]): Path to GEDCOM file.
    """
    __slots__ = [
        'gedcom_file'
    ]

    LINE_RE = re.compile(
        r'^(\d+)\s+(?:@[^@]+@\s+)?([A-Z0-9_]+)(.*)$'
    )  # allow optional @xref@ before the tag

    def __init__(self, gedcom_file: Path = None):
        """
        Initialize GedcomParser.

        Args:
            gedcom_file (Path): Path to GEDCOM file.
        """
        self.gedcom_file = self.check_fix_gedcom(gedcom_file)

    def close(self):
        """Placeholder for compatibility."""
        pass

    def check_fix_gedcom(self, input_path: Path) -> Path:
        """Fixes common issues in GEDCOM records."""
        temp_fd, temp_path = tempfile.mkstemp(suffix='.ged')
        os.close(temp_fd)
        changed = self.fix_gedcom_conc_cont_levels(input_path, temp_path)
        if changed:
            logger.warning(f"Checked and made corrections to GEDCOM file '{input_path}' saved as {temp_path}")
        return temp_path if changed else input_path

    def fix_gedcom_conc_cont_levels(self, input_path: Path, temp_path: Path) -> bool:
        """
        Fixes GEDCOM continuity and structure levels.
        These types of GEDCOM issues have been seen from Family Tree Maker exports.
        If not fixed, they can cause failure to parse the GEDCOM file correctly.
        """

        cont_level = None
        changed = False

        try:
            with open(input_path, 'r', encoding='utf-8', newline='', errors="replace") as infile, \
                open(temp_path, 'w', encoding='utf-8', newline='') as outfile:
                for raw in infile:
                    line = raw.rstrip('\r\n')
                    m = self.LINE_RE.match(line)
                    if not m:
                        outfile.write(raw)
                        continue

                    level_s, tag, rest = m.groups()
                    level = int(level_s)

                    if tag in ('CONC', 'CONT'):
                        fixed_level = cont_level if cont_level is not None else level
                        outfile.write(f"{fixed_level} {tag}{rest}\n")
                        if fixed_level != level:
                            changed = True
                    else:
                        cont_level = level + 1
                        outfile.write(raw)
        except IOError as e:
            logger.error(f"Failed to fix GEDCOM file {input_path}: {e}")
        return changed

    @staticmethod
    def get_place(record: Record, placetag: str = 'PLAC') -> Optional[str]:
        """
        Extracts the place value from a record.

        Args:
            record (Record): GEDCOM record.
            placetag (str): Tag to extract.

        Returns:
            Optional[str]: Place value or None.
        """
        place_value = None
        if record:
            place = record.sub_tag(placetag)
            if place:
                place_value = place.value
        return place_value
    
    def __get_event_location(self, record: Record) -> Optional[LifeEvent]:
        """
        Creates a LifeEvent from a record.

        Args:
            record (Record): GEDCOM record.

        Returns:
            Optional[LifeEvent]: LifeEvent object or None.
        """
        event = None
        if record:
            place = GedcomParser.get_place(record)
            event = LifeEvent(place, record.sub_tag('DATE'), record=record)
        return event

    def __create_person(self, record: Record) -> Person:
        """
        Creates a Person object from a record.

        Args:
            record (Record): GEDCOM record.

        Returns:
            Person: Person object.
        """
        person = Person(record.xref_id)
        person.name = ''
        name: NameRec = record.sub_tag('NAME')
        if name:
            person.firstname = record.name.first
            person.surname = record.name.surname
            person.maidenname = record.name.maiden
            person.name = f'{record.name.format()}'
        if person.name == '':
            person.firstname = 'Unknown'
            person.surname = 'Unknown'
            person.maidenname = 'Unknown'
            person.name = 'Unknown'
        person.sex = record.sex
        person.birth = self.__get_event_location(record.sub_tag('BIRT'))
        person.death = self.__get_event_location(record.sub_tag('DEAT'))
        title = record.sub_tag("TITL")
        person.title = title.value if title else ""

        # Grab a link to the photo
        obj = record.sub_tag("OBJE")
        person.photo = None
        if (obj):
            if obj.sub_tag("FILE"):
                # Depending on how the GEDCOM was created the FORM maybe at 2 or 3 it may be in a sub tag and it may or may not have the right extension
                if obj.sub_tag("_PRIM") and obj.sub_tag("_PRIM") == 'N':
                    # skip non primary photos
                    pass
                else:
                    ext = obj.sub_tag("FILE").value.lower().split('.')[-1]
                    if ext in ('jpg','bmp','jpeg','png','gif'):
                        person.photo = obj.sub_tag("FILE").value
                    else:
                        form = obj.sub_tag("FORM")
                        if form and obj.sub_tag("FORM").value.lower() in ('jpg','bmp','jpeg','png','gif'):
                            person.photo = obj.sub_tag("FILE").value
                        else:
                            form = obj.sub_tag("FILE").sub_tag("FORM")
                            if form and form.value.lower() in ('jpg','bmp','jpeg','png','gif'):
                                person.photo = obj.sub_tag("FILE").value 
        #TODO update timeframe ranges
        homes = {}
        allhomes=record.sub_tags("RESI")
        if allhomes:
            for hom in (allhomes):
                alladdr = ''
                homadr = hom.sub_tag("ADDR")
                if homadr:
                    for adr in (addrtags):
                        addrval = self.__get_event_location(homadr.sub_tag(adr))
                        alladdr = alladdr + " " + addrval.record.value if addrval and addrval.record.value else alladdr
                    # If we don't have an address it is of no use
                    alladdr = alladdr.strip()
                    if alladdr != '':
                        homedate = getgdate(hom.sub_tag("DATE"))
                        if homedate in homes:
                            logger.debug ("**Double RESI location for : %s on %s @ %s", person.name, homedate , alladdr)
                        homes[homedate] = LifeEvent(alladdr, hom.sub_tag("DATE"), what='home')
        for tags in (homelocationtags):
            allhomes=record.sub_tags(tags)
            if allhomes:
                for hom in (allhomes):
                    # If we don't have an address it is of no use
                    plac = self.__get_event_location(hom)
                    if plac: 
                        homedate = getgdate(hom.sub_tag("DATE"))
                        homes[homedate] = LifeEvent(plac, hom.sub_tag("DATE"), what='home')
        for tag in (otherlocationtags):
            allhomes=record.sub_tags(tag)
            if allhomes:
                for hom in (allhomes):
                    # If we don't have an address it is of no use
                    plac = self.__get_event_location(hom)
                    if plac:
                        otherwhat = tag
                        otherstype = hom.sub_tag("TYPE")
                        if otherstype:
                            otherwhat = otherstype.value
                        homedate = getgdate(hom.sub_tag("DATE"))
                        homes[homedate] = LifeEvent(plac, hom.sub_tag("DATE"), what=otherwhat)
                    
                    
        # Sort them by year          
        if (homes):
            for i in sorted (homes.keys()) :
                if person.home:
                    person.home.append(homes[i])
                else:
                    person.home = [homes[i]]

        
        return person
    
    def __create_people(self, records0) -> Dict[str, Person]:
        """
        Creates a dictionary of Person objects from records.

        Args:
            records0: GEDCOM records.

        Returns:
            Dict[str, Person]: Dictionary of Person objects.
        """
        people = {}
        for record in records0('INDI'):
            people[record.xref_id] = self.__create_person(record)
        return people

    def __add_marriages(self, people: Dict[str, Person], records) -> Dict[str, Person]:
        """
        Adds marriages and parent/child relationships to people.

        Args:
            people (Dict[str, Person]): Dictionary of Person objects.
            records: GEDCOM records.

        Returns:
            Dict[str, Person]: Updated dictionary of Person objects.
        """
        for record in records('FAM'):
            husband_record = record.sub_tag('HUSB')
            wife_record = record.sub_tag('WIFE')
            husband = people.get(husband_record.xref_id) if husband_record else None
            wife = people.get(wife_record.xref_id) if wife_record else None
            for marriages in record.sub_tags('MARR'):
                marriage_event = self.__get_event_location(marriages)
                if husband:
                    # add missing xref_id to marriage event record for later use
                    # BUG this causes the xref_id to be overwritten sometime between husband and wife processing
                    marriage_event.record.xref_id = wife_record.xref_id if wife_record else None
                    husband.marriages.append(marriage_event)
                if wife:
                    marriage_event.record.xref_id = husband_record.xref_id if husband_record else None
                    wife.marriages.append(marriage_event)
            for child in record.sub_tags('CHIL'):
                if child.xref_id in people:
                    if people[child.xref_id]:
                        if husband:
                            people[child.xref_id].father = husband.xref_id
                            husband.children.append(child.xref_id)
                        if wife:
                            people[child.xref_id].mother = wife.xref_id
                            wife.children.append(child.xref_id)
        return people

    def parse_people(self) -> Dict[str, Person]:
        """
        Parses people from the GEDCOM file.

        Returns:
            Dict[str, Person]: Dictionary of Person objects.
        """
        people = {}
        try:
            with GedcomReader(str(self.gedcom_file)) as parser:
                records = parser.records0
                people = self.__create_people(records)
                people = self.__add_marriages(people, records)
        except Exception as e:
            logger.error(f"Error parsing GEDCOM file '{self.gedcom_file}': {e}")
        return people

    def get_full_address_book(self) -> FuzzyAddressBook:
        """
        Returns address book of all places found in the GEDCOM file.

        Returns:
            FuzzyAddressBook: Address book of places.
        """
        address_book = FuzzyAddressBook()
        try:
            with GedcomReader(str(self.gedcom_file)) as g:
                # Individuals: collect PLAC under any event (BIRT/DEAT/BAPM/MARR/etc.)
                for indi in g.records0("INDI"):
                    for ev in indi.sub_records:
                        plac = ev.sub_tag_value("PLAC")
                        if plac:
                            place = plac.strip()
                            address_book.fuzzy_add_address(place, None)

                # Families: marriages/divorce places, etc.
                for fam in g.records0("FAM"):
                    for ev in fam.sub_records:
                        plac = ev.sub_tag_value("PLAC")
                        if plac:
                            place = plac.strip()
                            address_book.fuzzy_add_address(place, None)
        except Exception as e:
            logger.error(f"Error extracting places from GEDCOM file '{self.gedcom_file}': {e}")
        return address_book

class Gedcom:
    """
    Main GEDCOM handler for people and places.

    Attributes:
        gedcom_parser (GedcomParser): GEDCOM parser instance.
        people (Dict[str, Person]): Dictionary of Person objects.
        address_book (FuzzyAddressBook): Address book of places.
    """
    __slots__ = [
        'gedcom_parser',
        'people',
        'address_book',
    ]
    def __init__(self, gedcom_file: Path):
        """
        Initialize Gedcom.

        Args:
            gedcom_file (Path): Path to GEDCOM file.
        """
        self.gedcom_parser = GedcomParser(
            gedcom_file=gedcom_file
        )
        self.people: Dict[str, Person] = {}
        self.address_book: FuzzyAddressBook = FuzzyAddressBook()

    def close(self):
        """Close the GEDCOM parser."""
        self.gedcom_parser.close()

    def _parse_people(self) -> Dict[str, Person]:
        """
        Parse people from the GEDCOM file.

        Returns:
            Dict[str, Person]: Dictionary of Person objects.
        """
        self.people = self.gedcom_parser.parse_people()
        return self.people

    def get_full_address_book(self) -> FuzzyAddressBook:
        """
        Get all places from the GEDCOM file.

        Returns:
            FuzzyAddressBook: Address book of places.
        """
        self.address_book = self.gedcom_parser.get_full_address_book()
        return self.address_book

class GeolocatedGedcom(Gedcom):
    """
    GEDCOM handler with geolocation support.

    Attributes:
        geocoder (Geocode): Geocode instance.
        address_book (FuzzyAddressBook): Address book of places.
    """
    __slots__ = [
        'geocoder',
        'address_book',
        'alt_place_file_path'
    ]
    geolocate_all_logger_interval = 20
    
    def __init__(
            self,
            gedcom_file: Path,
            location_cache_file: Path,
            default_country: Optional[str] = None,
            always_geocode: Optional[bool] = False,
            use_alt_places: Optional[bool] = False,
            alt_place_file_path: Optional[Path] = None,
            background: Optional[gvOptions] = None
    ):
        """
        Initialize GeolocatedGedcom.

        Args:
            gedcom_file (str): Path to GEDCOM file.
            location_cache_file (str): Location cache file.
            default_country (Optional[str]): Default country for geocoding.
            always_geocode (Optional[bool]): Whether to always geocode.
            use_alt_places (Optional[bool]): Whether to use alternative place names.
        """
        super().__init__(gedcom_file)
        global BackgroundProcess
        BackgroundProcess = background
        self.geocoder = Geocode(
            cache_file=location_cache_file,
            default_country=default_country,
            always_geocode=always_geocode,
            alt_place_file_path=alt_place_file_path if use_alt_places else None
        )
        # self.address_book: FuzzyAddressBook = FuzzyAddressBook()
        self.geocoder.setupBackgroundProcess(background)
        BackgroundProcess.gOp.step("Reading GED", target=(BackgroundProcess.gOp.totalGEDpeople+BackgroundProcess.gOp.totalGEDfamily))
        self._geolocate_all()
        self._parse_people()

    def save_location_cache(self) -> None:
        """
        Save the location cache to the specified file.
        """
        self.geocoder.save_geo_cache()

    def _geolocate_all(self) -> None:
        """
        Geolocate all places in the GEDCOM file.
        """
        global BackgroundProcess
        BackgroundProcess.gOp.step("Loading Addressbook") if BackgroundProcess.gOp else None
        self.address_book = self.gedcom_parser.get_full_address_book()
        BackgroundProcess.gOp.step("Loading Cacehd") if BackgroundProcess.gOp else None
        cached_places, non_cached_places = self.geocoder.separate_cached_locations(self.address_book)
        logger.info(f"Found {cached_places.len()} cached places, {non_cached_places.len()} non-cached places.")
        BackgroundProcess.gOp.step(f"Found {cached_places.len()}") if BackgroundProcess.gOp else None
        logger.info(f"Geolocating {cached_places.len()} cached places...")
        for place, data in cached_places.addresses().items():
            use_place = data.alt_addr if data.alt_addr else place
            location = self.geocoder.lookup_location(use_place)
            self.address_book.fuzzy_add_address(place, location)
        num_non_cached_places = non_cached_places.len()
        BackgroundProcess.gOp.step(f"Geolocating non-cached places...", target=num_non_cached_places) if BackgroundProcess.gOp else None
        logger.info(f"Geolocating {num_non_cached_places} non-cached places...")
        
        for place in non_cached_places.addresses().keys():
            logger.info(f"- {place}...")
        for idx, (place, data) in enumerate(non_cached_places.addresses().items(), 1):
            use_place = data.alt_addr if data.alt_addr else place
            location = self.geocoder.lookup_location(use_place)
            self.address_book.fuzzy_add_address(place, location)
            if idx % self.geolocate_all_logger_interval == 0 or idx == num_non_cached_places:
                logger.info(f"Geolocated {idx} of {num_non_cached_places} non-cached places...")
        logger.info(f"Geolocation of all {self.address_book.len()} places completed.")

    def _parse_people(self) -> None:
        """
        Parse and geolocate all people in the GEDCOM file.
        """
        super()._parse_people()
        self._geolocate_people()

    def _geolocate_people(self) -> None:
        """
        Geolocate birth, marriages, and death events for all people.
        """
        for person in self.people.values():
            found_location = False
            if person.birth:
                event = self._geolocate_event(person.birth)
                person.birth.location = event.location
                if not found_location and event.location and event.location.latlon and event.location.latlon.is_valid():
                    person.latlon = event.location.latlon
                    found_location = True
            for marriage_event in person.marriages:
                event = self._geolocate_event(marriage_event)
                marriage_event.location = event.location
                if not found_location and event.location and event.location.latlon and event.location.latlon.is_valid():
                    person.latlon = event.location.latlon
                    found_location = True
            if person.death:
                event = self._geolocate_event(person.death)
                person.death.location = event.location
                if not found_location and event.location and event.location.latlon and event.location.latlon.is_valid():
                    person.latlon = event.location.latlon
                    found_location = True

    def _geolocate_event(self, event: LifeEvent) -> LifeEvent:
        """
        Geolocate a single event. If no location is found, event.location remains None.

        Args:
            event (LifeEvent): The event to geolocate.

        Returns:
            LifeEvent: The event with updated location and latlon if found.
        """
        record = getattr(event, 'record', None)
        
        if record:
            place_tag = record.sub_tag('PLAC')
            if place_tag:
                map_tag = place_tag.sub_tag('MAP')
                if place_tag.value:
                    location = self.geocoder.lookup_location(place_tag.value)
                    event.location = location
                    logger.debug(f"Place found {location.address} for event in record {record}")
                if map_tag:
                    lat = map_tag.sub_tag('LATI')
                    lon = map_tag.sub_tag('LONG')
                    if lat and lon:
                        latlon = LatLon(lat.value, lon.value)
                        event.latlon = latlon if latlon.is_valid() else None
                    else:
                        event.latlon = None
            else:
                logger.info(f"No place tag found for event in record {record}")
        else:
            logger.warning("No record found for event")
        return event