__all__ = ['Human', 'LifeEvent']

import logging
import re

from models.Pos import Pos

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
    def __init__(self, xref_id, pos):
        self.xref_id = xref_id
        self.pos :Pos = pos
    def __str__(self):
        return f"Human(id={self.xref_id}, Pos={self.pos})"
 
class Human:
    __slots__ = ['xref_id', 'name', 'father', 'mother', 'pos', 'birth', 'death', 'marriage', 'home', 'map', 'first', 
                 'surname', 'maiden','sex','title', 'photo', 'children', 'partners']
    def __init__(self, xref_id):
        self.xref_id: str = xref_id
        self.name = None
        self.father : Human = None
        self.mother : Human = None
        self.pos : Pos = None           # save the best postion
        self.birth : LifeEvent = None
        self.death : LifeEvent = None
        # TODO need to deal with multiple mariages
        self.marriage = None
        # TODO multiple homes
        self.home : LifeEvent = None
        self.map : Pos = None           # used to save the orginal pos values
        self.first = None               # First Name
        self.surname = None             # Last Name
        self.maiden: None
        self.sex: None
        self.title = None


    def __str__(self) -> str:
        return f"Human(id={self.xref_id}, name={self.name})"
        
    def __repr__(self) -> str:
        return f"[ {self.xref_id} : {self.name} - {self.father} & {self.mother} - {self.pos} ]"

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
        if self.birth and self.birth.pos:
            best = [
                str(self.birth.pos),
                f"{self.birth.where} (Born)" if self.birth.where else "",
            ]
        elif self.death and self.death.pos:
            best = [
                str(self.death.pos),
                f"{self.death.where} (Died)" if self.death.where else "",
            ]
        return best

    def bestPos(self):
        # TODO Best Location should consider if in KML mode and what is selected  
        # If the location is set in the GED, using MAP attribute then that will be the best
        best = Pos(None, None)
        if self.map and self.map.hasLocation():
            best = self.map
        elif self.birth and self.birth.pos and self.birth.pos.hasLocation():
            best = self.birth.pos
        elif self.death and self.death.pos and self.death.pos.hasLocation():
            best = self.death.pos
        return best

class LifeEvent:
    def __init__(self, place :str, atime, position : Pos = None, what = None):  # atime is a Record
        self.where = place
        self.when = atime
        self.pos = position
        self.what = what

    def __repr__(self):
        return f"[ {self.when} : {self.where} is {self.what}]"
    
    def asEventstr(self):
        if self:
            where = f" at {self.getattr('where')}" if self.where else ""
            when = f" about {self.getattr('when')}" if self.when else ""
            return f"{when}{where}"
        else:
            return ""
    
    def whenyear(self, last = False):
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
        if attr == 'pos':
            return self.pos
        elif attr == 'when':
            return self.when.value or ""
        elif attr == 'where':
            return self.where if self.where else ""
        elif attr == 'what':
            return self.what if self.what else ""
        _log.warning("Life Event attr: %s' object has no attribute '%s'", type(self).__name__, attr)    
        return None

    def __str__(self):
        return f"{self.getattr('where')} : {self.getattr('when')} - {self.getattr('pos')} {self.getattr('what')}"
