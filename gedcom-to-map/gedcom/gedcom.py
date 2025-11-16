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
from gedcom_options import gvOptions

logger = logging.getLogger(__name__)

homelocationtags = ('OCCU', 'CENS', 'EDUC')
otherlocationtags = ('CHR', 'BAPM', 'BASM', 'BAPL', 'IMMI', 'NATU', 'ORDN','ORDI', 'RETI', 
                     'EVEN',  'CEME', 'CREM', 'FACT' )
addrtags = ('ADR1', 'ADR2', 'ADR3', 'CITY', 'STAE', 'POST', 'CTRY')

# Common pieces we want to remove when extracting the surname
_TITLES = {
    "mr", "mrs", "ms", "miss", "dr", "prof", "rev", "sir", "lady", "lord",
    "capt", "major", "lt", "hon", "dame"
}
_SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "v", "phd", "md", "esq"}

# Prefix sequences (lowercased tokens) to include as part of the surname if they appear immediately before the final token(s).
# Order matters: multi-token prefixes should appear before their single-token components.
_PREFIX_SEQUENCES: List[List[str]] = [
    ["de", "la"], ["de", "le"], ["del"], ["de", "los"], ["van", "der"], ["van", "de"],
    ["st", "john"], ["st", "claire"], ["saint"], ["von"], ["van"],
    ["de"], ["da"], ["di"], ["dos"], ["du"], ["do"], ["dei"], ["del"],
    ["le"], ["mac"], ["mc"], ["ap"], ["fitz"], ["ibn"], ["bin"], ["binti"], ["ben"]
]

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
        'gedcom_file',
        'gOp'
    ]

    LINE_RE = re.compile(
        r'^(\d+)\s+(?:@[^@]+@\s+)?([A-Z0-9_]+)(.*)$'
    )  # allow optional @xref@ before the tag

    def __init__(self, gedcom_file: Path = None, gOp: Optional[gvOptions] = None):
        """
        Initialize GedcomParser.

        Args:
            gedcom_file (Path): Path to GEDCOM file.
        """
        self.gedcom_file = self.check_fix_gedcom(gedcom_file)
        self.gOp = gOp

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
        global BackgroundProcess

        person = Person(record.xref_id)
        person.name = ''
        name: NameRec = record.sub_tag('NAME')
        if name:
            person.firstname = record.name.first
            person.surname = record.name.surname
            person.maidenname = record.name.maiden
            person.name = f'{record.name.format()}'
            # Try and approxcimate the last name 
            if person.surname == '':
                person.surname = extract_surname(person.name)
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
        # update timeframe ranges
        bg = self.gOp.BackgroundProcess if self.gOp else None
        if bg:
            bg.gOp.addtimereference(person.birth)
            bg.gOp.addtimereference(person.death)
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
                        homes[homedate] = LifeEvent(alladdr, hom.sub_tag("DATE"), what='home', record=hom)
                        if bg:
                            bg.gOp.addtimereference(homes[homedate])
        for tags in (homelocationtags):
            allhomes=record.sub_tags(tags)
            if allhomes:
                for hom in (allhomes):
                    # If we don't have an address it is of no use
                    plac = self.__get_event_location(hom)
                    if plac: 
                        homedate = getgdate(hom.sub_tag("DATE"))
                        homes[homedate] = LifeEvent(plac, hom.sub_tag("DATE"), what='home', record=hom)
                        if self.gOp:
                            self.gOp.addtimereference(homes[homedate])
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
                        homes[homedate] = LifeEvent(plac, hom.sub_tag("DATE"), what=otherwhat, record=hom)
                        if bg:
                            bg.gOp.addtimereference(homes[homedate])
                    
                    
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
        if self.gOp:
            self.gOp.step(info=f"Loaded People", target=self.gOp.totalGEDpeople)
        for record in records0('INDI'):
            people[record.xref_id] = self.__create_person(record)
            if self.gOp:
                self.gOp.step(info=f"Loaded {people[record.xref_id].name}")
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
            logger.exception("Issues in parse_people")
            logger.error(f"Error parsing GEDCOM file '{self.gedcom_file}': {e}")
        return people


    def _fast_count(self):
        def _count_gedcom_records( path, encoding):
                """Return (people, families) counts for a GEDCOM file with given encoding."""
                people = families = 0
                with open(path, encoding=encoding) as f:
                    for line in f:
                        if line.startswith("0 @") and " INDI" in line:
                            people += 1
                        elif line.startswith("0 @") and " FAM" in line:
                            families += 1
                return people, families

        encodings = ["utf-8", "latin-1"]  # try in order
        for enc in encodings:
            try:
                people, families = _count_gedcom_records(str(self.gedcom_file), enc)
                self.gOp.totalGEDpeople = people
                self.gOp.totalGEDfamily = families
                logger.info(f"Fast count people {people} & families {families}")
                return
            except UnicodeDecodeError:
                # try next encoding
                continue
            except Exception as e:
                logger.error(
                    f"Error fast counting people and families from GEDCOM file '{self.gedcom_file}' with encoding {enc}: {e}"
                )
                return
        # If we get here, all encodings failed
        logger.error(f"Could not decode GEDCOM file '{self.gedcom_file}' with any known encoding")

    def get_full_address_book(self) -> FuzzyAddressBook:
        """
        Returns address book of all places found in the GEDCOM file.

        Returns:
            FuzzyAddressBook: Address book of places.
        """
        iteration = 0
        address_book = FuzzyAddressBook()

        # Calculate total for people and families in the GEDCOM for progress tracking
        if self.gOp:
            self.gOp.step("Counting people", target=0)
            self.gOp.totalGEDpeople = 0
            self.gOp.totalGEDfamily = 0
            # Super fast counter rather than parsing the whole file (using instead of using gedpy)
            self._fast_count()
        try:

            with GedcomReader(str(self.gedcom_file)) as g:
                if self.gOp:
                    self.gOp.step("Loading addresses from GED", target=self.gOp.totalGEDpeople+self.gOp.totalGEDfamily)
                # Individuals: collect PLAC under any event (BIRT/DEAT/BAPM/MARR/etc.)
                for indi in g.records0("INDI"):
                    for ev in indi.sub_records:
                        plac = ev.sub_tag_value("PLAC")
                        if plac:
                            place = plac.strip()
                            address_book.fuzzy_add_address(place, None)
                    if self.gOp:
                        iteration += 1
                        if iteration % 250 == 0:
                            self.gOp.stepCounter(iteration)
                            if self.gOp.ShouldStop():
                                break

                # Families: marriages/divorce places, etc.
                for fam in g.records0("FAM"):
                    for ev in fam.sub_records:
                        plac = ev.sub_tag_value("PLAC")
                        if plac:
                            place = plac.strip()
                            address_book.fuzzy_add_address(place, None)
                    if self.gOp:
                        iteration += 1
                        if iteration % 100 == 0:
                            self.gOp.stepCounter(iteration)
                            if self.gOp.ShouldStop():
                                break

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
        'gOp'
    ]
    def __init__(self, gedcom_file: Path, gOp: Optional[gvOptions] = None):
        """
        Initialize Gedcom.

        Args:
            gedcom_file (Path): Path to GEDCOM file.
        """
        self.gedcom_parser = GedcomParser(
            gedcom_file=gedcom_file,
            gOp=gOp
        )
        self.people: Dict[str, Person] = {}
        self.address_book: FuzzyAddressBook = FuzzyAddressBook()
        self.gOp = gOp
        if gOp:
            gOp.resettimeframe()
            gOp.totalGEDpeople = 0
            gOp.totalGEDfamily = 0
        else:
            logger.warning("Gedcom initialized without gvOptions; some features may be limited.")

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
        'alt_place_file_path',
        'gOp'
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
            gOp: Optional[gvOptions] = None
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
        super().__init__(gedcom_file, gOp=gOp)
        self.geocoder = Geocode(
            cache_file=location_cache_file,
            default_country=default_country,
            always_geocode=always_geocode,
            alt_place_file_path=alt_place_file_path if use_alt_places else None,
            gOp=gOp
        )
        self.gOp = gOp
        # self.address_book: FuzzyAddressBook = FuzzyAddressBook()
        bg = self.gOp.BackgroundProcess if self.gOp else None
        if bg:
            self.gOp.step("Reading GED")
        self._geolocate_all()
        if self.gOp.ShouldStop():
            return
        self._parse_people()
        if self.gOp.ShouldStop():
            return
        self.gOp.parsed = True


        

    def save_location_cache(self) -> None:
        """
        Save the location cache to the specified file.
        """
        self.geocoder.save_geo_cache()

    def _geolocate_all(self) -> None:
        """
        Geolocate all places in the GEDCOM file.
        """
        self.gOp.step("Loading Addressbook")
        self.address_book = self.gedcom_parser.get_full_address_book()
        self.gOp.step("Loading Cached")
        cached_places, non_cached_places = self.geocoder.separate_cached_locations(self.address_book)
        num_cached_places = cached_places.len()
        logger.info(f"Found {num_cached_places} cached places, {non_cached_places.len()} non-cached places.")
        logger.info(f"Geolocating {num_cached_places} cached places...")
        self.gOp.step(f"Matching cached places...", target=num_cached_places) if self.gOp else None
        for idx, (place, data) in enumerate(cached_places.addresses().items(), 1):
            use_place = data.alt_addr if data.alt_addr else place
            location = self.geocoder.lookup_location(use_place)
            self.address_book.fuzzy_add_address(place, location)
            if self.gOp.ShouldStop():
                return
            if idx % 250 == 0:
                self.gOp.step(info=f"Geolocated {idx}")

        num_non_cached_places = non_cached_places.len()
        self.gOp.step(f"Geolocating uncached places...", target=num_non_cached_places) if self.gOp else None
        logger.info(f"Geolocating {num_non_cached_places} non-cached places...")
        
        for place in non_cached_places.addresses().keys():
            logger.debug(f"- {place}...")
        for idx, (place, data) in enumerate(non_cached_places.addresses().items(), 1):
            use_place = data.alt_addr if data.alt_addr else place
            location = self.geocoder.lookup_location(use_place)
            self.address_book.fuzzy_add_address(place, location)
            if idx % self.geolocate_all_logger_interval == 0 or idx == num_non_cached_places:
                logger.info(f"Geolocated {idx} of {num_non_cached_places} non-cached places...")
            self.gOp.step(info=f"Geolocated {idx} of {num_non_cached_places}")
            if self.gOp.ShouldStop():
                break
            # Save the cache every 100 locations
            if idx % 100 == 0:
                self.save_location_cache()
        self.save_location_cache() # Final save

        logger.info(f"Geolocation of all {self.address_book.len()} places completed.")

    def _parse_people(self) -> None:
        """
        Parse and geolocate all people in the GEDCOM file.
        """
        super()._parse_people()
        # People loaded
        self.gOp.step("Locating People", target=(self.gOp.totalGEDpeople))
        self._geolocate_people()

    def _geolocate_people(self) -> None:
        """
        Geolocate birth, marriages, and death events for all people.
        """
        for person in self.people.values():
            found_location = False
            self.gOp.step(info =f"Reviewing {getattr(person, 'name', '-Unknwon-')}")
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
            if person.home:
                for home_event in person.home:
                    event = self._geolocate_event(home_event)
                    home_event.location = event.location
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
                    logger.debug(f"Place found {location.address if location else '-unknown-'} for event in record {record}")
                if map_tag:
                    lat = map_tag.sub_tag('LATI')
                    lon = map_tag.sub_tag('LONG')
                    if lat and lon:
                        latlon = LatLon(lat.value, lon.value)
                        if latlon.is_valid():
                            event.location = Location(position=latlon, address=place_tag.value)

            else:
                logger.info(f"No place tag found for event in record {record}")
        else:
            logger.warning("No record found for event")
        return event
    
# Normalize token (strip punctuation except internal apostrophe or hyphen)
def _normalize_token(tok: str) -> str:
    tok = tok.strip()
    # Remove leading/trailing punctuation but keep internal apostrophes and hyphens
    tok = re.sub(r"^[^\w']+|[^\w']+$", "", tok, flags=re.UNICODE)
    return tok

def extract_surname(full_name: str) -> str:
    """
    Extracts the surname from a full personal name for genealogical usage.

    Returns the surname as it appears in the input (preserves caps, apostrophes, hyphens).
    If nothing recognizable, returns the last non-empty token.
    """
    if not full_name or not full_name.strip():
        return ""

    # Normalize whitespace and remove commas typically used to separate surname-first formats
    name = re.sub(r"\s+", " ", full_name.strip())
    # Remove trailing commas/spurious punctuation
    name = name.strip(",;")

    # Handle common "Surname, Given" formats: move last comma-separated piece to end if needed
    if "," in name:
        # Example: "Doe, John" or "Doe, John William"
        parts = [p.strip() for p in name.split(",") if p.strip()]
        if len(parts) >= 2:
            # Assume first part is surname
            return parts[0]

    tokens_raw = name.split(" ")

    # Remove leading titles
    while tokens_raw and _normalize_token(tokens_raw[0]).lower() in _TITLES:
        tokens_raw.pop(0)

    # Remove trailing suffixes like Jr., III, PhD
    while tokens_raw and _normalize_token(tokens_raw[-1]).lower().rstrip(".") in _SUFFIXES:
        tokens_raw.pop(-1)

    if not tokens_raw:
        return ""

    # Prepare tokens with original form and normalized lowercase forms
    tokens = tokens_raw[:]  # keep originals for final return
    lctoks = [_normalize_token(t).lower() for t in tokens]

    # Start looking for a multi-token prefix immediately before the last token.
    # Check sequences from longest to shortest.
    surname_tokens = [tokens[-1]]  # default: last token
    found_prefix_len = 0

    # Try to match multi-token prefixes (we try up to 2 tokens before the last by list definition)
    for seq in _PREFIX_SEQUENCES:
        seq_len = len(seq)
        if seq_len >= len(lctoks):
            continue
        # Check if the sequence matches the tokens immediately before the final token or includes final token for one-token prefix
        # We want the sequence to appear directly before the final core token(s)
        start_idx = len(lctoks) - 1 - seq_len
        if start_idx >= 0:
            window = lctoks[start_idx:start_idx + seq_len]
            if window == seq:
                # include these prefix tokens plus the final token(s)
                surname_tokens = tokens[start_idx:]  # from prefix through end
                found_prefix_len = seq_len
                break

    # Special handling for names where prefix is capitalized (e.g., "De Graf") but normalized matched
    # Also handle cases like "Mac Something" and "McSomething" — we include "Mac" or "Mc" if present before last token
    if found_prefix_len == 0 and len(lctoks) >= 2:
        # If second-last looks like a prefix token (single-token prefix list)
        single_prefixes = {seq[0] for seq in _PREFIX_SEQUENCES if len(seq) == 1}
        if lctoks[-2] in single_prefixes:
            surname_tokens = tokens[-2:]

    # If only one token remains after stripping titles/suffixes, that's the surname
    if len(tokens) == 1:
        return tokens[0]

    # Join surname tokens preserving original spacing/punctuation
    surname = " ".join(surname_tokens).strip()
    return surname