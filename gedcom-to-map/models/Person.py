__all__ = ['Person', 'LifeEvent']

import logging
import re
from typing import Dict, Union, Optional, List

from models.LatLon import LatLon

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
        return f'[ {self.parent.xref_id} : {self.parent.name} -> {self.xref_id} {self.mother} - {self.lat_lon} ]'
 
class Person:
    __slots__ = ['xref_id', 'name', 'father', 'mother', 'latlon', 'birth', 'death', 'marriage', 'home', 'first', 
                 'surname', 'maiden','sex','title', 'photo', 'children', 'partners', 'age']
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
        self.marriage : List[LifeEvent] = []
        # TODO multiple homes
        self.home : List[LifeEvent] = []
        self.first : Optional[str] = None               # First Name
        self.surname : Optional[str] = None             # Last Name
        self.maiden : Optional[str] = None
        self.sex : Optional[str] = None
        self.title : Optional[str] = None
        self.children : list[str] = []    # xref_id of children NOT YET USED
        self.partners : list[str] = []    # xref_id of partners NOT YET USED
        self.age = None           # This can be age number or a including the cause of death
        self.photo = None         # URL or file path to photo


    def __str__(self) -> str:
        return f"Person(id={self.xref_id}, name={self.name})"
        
    def __repr__(self) -> str:
        return f"[ {self.xref_id} : {self.name} - {self.father} & {self.mother} - {self.latlon} ]"

    # return "year (Born)" or "year (Died)" or "? (Unknown)" along with year as a string or None
    # Example "2010 (Born)", "2010" or "1150 (Died)", "1150" or "? (Unknown)"
    def refyear(self):
        bestyear = "? (Unknown)"
        year = None
        if self.birth and self.birth.when:
            year = self.birth.whenyear()
            bestyear = f"{self.birth.whenyear()} (Born)" if year else bestyear
        elif self.death and self.death.when:
            year = self.death.whenyear()
            bestyear = f"{self.death.whenyear()} (Died)" if year else bestyear
        return (bestyear, year)

    def bestlocation(self):
        # TODO Best Location should consider if in KML mode and what is selected
        best = ["Unknown", ""]
        if self.birth and self.birth.latlon:
            best = [
                str(self.birth.latlon),
                f"{self.birth.where} (Born)" if self.birth.where else "",
            ]
        elif self.death and self.death.latlon:
            best = [
                str(self.death.latlon),
                f"{self.death.where} (Died)" if self.death.where else "",
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
    def __init__(self, place :str, atime, position : LatLon = None, what = None):  # atime is a Record
        self.where: Optional[str] = place
        self.when = atime
        self.latlon : Optional[LatLon] = position
        self.what: Optional[str] = what

    def __repr__(self) -> str:
        return f"[ {self.when} : {self.where} is {self.what}]"
    
    def asEventstr(self):
        if self:
            where = f" at {self.getattr('where')}" if self.where else ""
            when = f" about {self.getattr('when')}" if self.when else ""
            return f"{when}{where}"
        else:
            return ""
    
    def whenyear(self, last = False) -> Optional[str]:
        if self.when:
            if (isinstance(self.when, str)):
                return (self.when)
            else:
                if self.when.value.kind.name == "RANGE" or self.when.value.kind.name == "PERIOD":
                    if last:
                        return self.when.value.date1.year_str
                    else:
                        return self.when.value.date2.year_str
                elif self.when.value.kind.name == "PHRASE":
                    # TODO poor error checking here Assumes a year is in this date
                    if re.search(r"-?\d{3,4}", self.when.value.phrase):
                        try:
                            return re.search(r"-?\d{3,4}", self.when.value.phrase)[0]
                        except Exception:
                            return None
                    # (xxx BC) or xxx B.C.
                    elif re.search(r"\(?\d{1,4} [Bb]\.?[Cc]\.?\)?", self.when.value.phrase):
                        matched = re.search(r"\(?(\d{1,4}) [Bb]\.?[Cc]\.?\)?", self.when.value.phrase)
                        return -int(matched.group(1))
                        
                    else:
                        if hasattr(self.when.value, 'name') :
                            _log.warning ("'when' year %s as %s", self.when.value.name, self.when.value.phrase)
                        else:
                            _log.warning ("unknown 'when' name %s ", self.when.value)
                        return None
                else:
                    return self.when.value.date.year_str
        return None

    def whenyearnum(self, last = False):
        """
        Return 0 if None
        """
        return DateFromField(self.whenyear(last))

    def getattr(self, attr):
        if attr == 'latlon':
            return self.latlon
        elif attr == 'when':
            return self.when.value or ""
        elif attr == 'where':
            return self.where if self.where else ""
        elif attr == 'what':
            return self.what if self.what else ""
        _log.warning("Life Event attr: %s' object has no attribute '%s'", type(self).__name__, attr)    
        return None

    def __str__(self) -> str:
        return f"{self.getattr('where')} : {self.getattr('when')} - {self.getattr('latlon')} {self.getattr('what')}"

