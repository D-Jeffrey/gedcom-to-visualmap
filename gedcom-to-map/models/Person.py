"""
Person.py - Person and LifeEvent classes for GEDCOM mapping.

Person represents a person in the GEDCOM file.
LifeEvent represents a life event (birth, death, marriage, etc.) for a person.

authors: @lmallez, @D-jeffrey, @colin0brass
"""
__all__ = ['Person', 'LifeEvent', 'DateFromField']

import logging
import re
from typing import Dict, Union, Optional, List

from models.LatLon import LatLon
from ged4py.model import Record, NameRec

_log = logging.getLogger(__name__.lower())

def DateFromField(field):
    if field:
        if not isinstance(field, str):
            field = str(field)
        # BC or B.C
        if field.lower().find("bc") > 0 or field.lower().find("b.c") > 0:
                return -int(field[:field.lower().find("b")])
        if len(field) > 3 and field[3].isdigit():
            try:
                return int(field[:4])
            except:
                pass
        try:
            return int(field)
        except:
            digits = ''
            for char in field:
                if char.isdigit() or char == '-':
                    digits += char
            return int(digits) if digits else None
    return None

class Partner:
    def __init__(self, xref_id, latlon : LatLon = None):
        self.xref_id = xref_id
        self.latlon :LatLon = latlon
    def __str__(self):
        return f"Person(id={self.xref_id}, LatLon={self.latlon})"
    def __repr__(self) -> str:
        return f'[ {self.parent.xref_id} : {self.parent.name} -> {self.xref_id} {self.mother} - {self.latlon} ]'
 
class Person:
    """
    Represents a person in the GEDCOM file.

    Attributes:
        xref_id (str): GEDCOM cross-reference ID.
        name (str): Full name.
        father (Optional[str]): Father's xref ID.
        mother (Optional[str]): Mother's xref ID.
        children (List[str]): List of children xref IDs.
        latlon (Optional[LatLon]): Latitude/longitude.
        birth (Optional[LifeEvent]): Birth event.
        death (Optional[LifeEvent]): Death event.
        marriages (List[LifeEvent]): Marriage events.
        firstname (str): First name.
        surname (str): Surname.
        maidenname (str): Maiden name.
        sex (str): Sex.
        age (Union[int, str]): Age or age with cause of death.
        location: Best known location.
    """
    __slots__ = ['xref_id', 'name', 'father', 'mother', 'latlon', 'birth', 'death', 'marriages', 'home', 'firstname', 
                 'surname', 'maidenname','sex','title', 'photo', 'children', 'partners', 'age', 'location']
    def __init__(self, xref_id : str):
        """
        Initialize a Person.

        Args:
            xref_id (str): GEDCOM cross-reference ID.
        """
        self.xref_id = xref_id
        self.name : Optional[str] = None
        self.father : Person = None
        self.mother : Person = None
        self.latlon : LatLon = None           # save the best postion
        self.birth : LifeEvent = None
        self.death : LifeEvent = None
        # TODO need to deal with multiple mariages
        self.marriages : List[LifeEvent] = []
        # TODO multiple homes
        self.home : List[LifeEvent] = []
        self.firstname : Optional[str] = None               # firstname Name
        self.surname : Optional[str] = None             # Last Name
        self.maidenname : Optional[str] = None
        self.sex : Optional[str] = None
        self.title : Optional[str] = None
        self.children : List[str] = []    # xref_id of children NOT YET USED
        self.partners : List[str] = []    # xref_id of partners NOT YET USED
        self.age = None           # This can be age number or a including the cause of death
        self.photo = None         # URL or file path to photo
        self.location = None

    def __str__(self) -> str:
        return f"Person(id={self.xref_id}, name={self.name})"
        
    def __repr__(self) -> str:
        return f"[ {self.xref_id} : {self.name} - {self.father} & {self.mother} - {self.latlon} ]"

    # return "year (Born)" or "year (Died)" or "? (Unknown)" along with year as a string or None
    # Example "2010 (Born)", "2010" or "1150 (Died)", "1150" or "? (Unknown)"
    def refyear(self):
        bestyear = "? (Unknown)"
        year = None
        if self.birth and self.birth.date:
            year = self.birth.whenyear()
            bestyear = f"{self.birth.whenyear()} (Born)" if year else bestyear
        elif self.death and self.death.date:
            year = self.death.whenyear()
            bestyear = f"{self.death.whenyear()} (Died)" if year else bestyear
        return (bestyear, year)

    def ref_year(self) -> str:
        """
        Returns a reference year string for the person.

        Returns:
            str: Reference year string.
        """
        if self.birth and self.birth.date:
            return f'Born {self.birth.date_year()}'
        if self.death and self.death.date:
            return f'Died {self.death.date_year()}'
        return 'Unknown'
    
    def bestlocation(self):
        # TODO Best Location should consider if in KML mode and what is selected
        best = ["Unknown", ""]
        if self.birth and self.birth.location:
            best = [
                str(self.birth.location.latlon),
                f"{self.birth.place} (Born)" if self.birth.place else "",
            ]
        elif self.death and self.death.location:
            best = [
                str(self.death.location.latlon),
                f"{self.death.place} (Died)" if self.death.place else "",
            ]
        return best

    def bestLatLon(self):
        # TODO Best Location should consider if in KML mode and what is selected  
        # If the location is set in the GED, using MAP attribute then that will be the best
        best = LatLon(None, None)
#        if self.map and self.map.latlon.hasLocation():
#            best = self.map.latlon
        if self.birth and self.birth.latlon and self.birth.latlon.hasLocation():
            best = self.birth.latlon
        elif self.death and self.death.latlon and self.death.latlon.hasLocation():
            best = self.death.latlon
        return best
    
class LifeEvent:
    """
    Represents a life event (birth, death, marriage, etc.) for a person.

    Attributes:
        place (str): The place where the event occurred.
        date: The date of the event (can be string or ged4py date object).
        what: The type of event (e.g., 'BIRT', 'DEAT').
        record (Record): The GEDCOM record associated with the event.
        location (Location): Geocoded location object.
        latlon (LatLon): Latitude/longitude of the event, if available.
    """
    __slots__ = [
        'place',
        'date',
        'what',
        'record',
        'location',
        'latlon'
    ]
    def __init__(self, place: str, atime, position: Optional[LatLon] = None, what=None, record: Optional[Record] = None):
        """
        Args:
            place (str): Place of the event.
            atime: Date of the event.
            latlon (Optional[LatLon]): Latitude/longitude.
            what: Type of event.
            record (Optional[Record]): GEDCOM record.
        """
        self.place: Optional[str] = place
        self.date = atime
        self.latlon : Optional[LatLon] = position
        self.what: Optional[str] = what
        self.record = record
        

    def __repr__(self) -> str:
        if self.what:
            return f"[ {self.date} : {self.place} is {self.what}]"
        return f'[ {self.date} : {self.place} ]'
    
    def asEventstr(self):
        if self:
            place = f" at {self.getattr('place')}" if self.place else ""
            date = f" on {self.getattr('date')}" if self.date else ""
            return f"{date}{place}"
        return ""
    
    def whenyear(self, last = False) -> Optional[str]:
        if self.date:
            if isinstance(self.date, str):
                return (self.date)
            else:
                if self.date.value.kind.name == "RANGE" or self.date.value.kind.name == "PERIOD":
                    if last:
                        return self.date.value.date1.year_str
                    else:
                        return self.date.value.date2.year_str
                elif self.date.value.kind.name == "PHRASE":
                    # use match.group(0) to extract the year safely
                    m = re.search(r"-?\d{3,4}", self.date.value.phrase)
                    if m:
                        return m.group(0)
                    return None
                else:
                    return self.date.value.date.year_str
        return None

    def whenyearnum(self, last = False):
        """
        Return 0 if None
        """
        return DateFromField(self.whenyear(last))

    def getattr(self, attr):
        if attr == 'latlon':
            return self.latlon
        elif attr == 'when' or attr == 'date':
            return getattr(self.date, 'value', "")
        elif attr == 'where' or attr == 'place':
            return self.place if self.place else ""
        elif attr == 'what':
            return self.what if self.what else ""
        _log.warning("LifeEvent attr: %s' object has no attribute '%s'", type(self).__name__, attr)    
        return None

    def __str__(self) -> str:
        return f"{self.getattr('place')} : {self.getattr('date')} - {self.getattr('latlon')} {self.getattr('what')}"
    def date_year(self, last: bool = False) -> Optional[str]:
        """
        Returns the year string for the event date.

        Args:
            last (bool): If True, returns the last year in a range.

        Returns:
            Optional[str]: Year string or None.
        """
        if self.date:
            if isinstance(self.date, str):
                return self.date
            else:
                kind = getattr(self.date.value, 'kind', None)
                if kind and kind.name in ('RANGE', 'PERIOD'):
                    if last:
                        return self.date.value.date1.year_str
                    else:
                        return self.date.value.date2.year_str
                elif kind and kind.name == 'PHRASE':
                    # Safely extract a 3- or 4-digit year (allow optional leading minus)
                    phrase = getattr(getattr(self.date, 'value', None), 'phrase', None)
                    if not phrase:
                        _log.warning('LifeEvent: date_year: no phrase available on date.value')
                        return None
                    m = re.search(r'-?\d{3,4}', phrase)
                    if m:
                        return m.group(0)
                    _log.warning('LifeEvent: date_year: unable to parse date phrase: %s', phrase)
                    return None
                else:
                    return getattr(self.date.value.date, 'year_str', None)
        return None

    def __getattr__(self, name):
        if name == 'pos':
            return (None, None)
        return None

