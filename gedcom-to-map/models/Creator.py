__all__ = ['Creator', 'LifetimeCreator', 'DELTA', 'SPACE']

import logging
from typing import Dict

from models.Person import Person, LifeEvent
from models.Line import Line
from models.LatLon import LatLon
from models.Rainbow import Rainbow

_log = logging.getLogger(__name__.lower())


SPACE = 2.5     # These values drive how colors are selected
DELTA = 1.5     # These values drive how colors are selected

#TODO fix up this function and write it better
def getAttrLatLonif(obj, attname, attvaluename = 'latlon') -> LatLon:
    if obj:
        if hasattr(obj, attname):
            a = getattr(obj, attname)
            if hasattr(a, 'location'):
                if hasattr(a.location, attvaluename):
                    return getattr(a.location, attvaluename)
    return LatLon(None, None)
    
class Creator:
    def __init__(self, people: Dict[str, Person], max_missing: int =0, gpstype="birth"):
        self.people = people
        self.rainbow = Rainbow()
        self.max_missing = max_missing
        self.alltheseids= {}
        self.gpstype = gpstype

    def line(self, latlon: LatLon, current: Person, branch, prof, miss, path="") -> list[Line]:
        if current.xref_id in self.alltheseids:
            _log.error("Looping Problem: {:2} -LOOP STOP - {} {} -Looping= {:20}".format(  prof, self.people[current.xref_id].name, current.xref_id, path))
            return []
        self.alltheseids[current.xref_id] = current.xref_id
        if not getattr(current, self.gpstype):
            return (
                []
                if self.max_missing != 0 and miss >= self.max_missing
                else self.link(getAttrLatLonif(current, self.gpstype), current, branch, prof, miss + 1, path)
            )
        color = (branch + DELTA / 2) / (SPACE ** (prof % 256))
        _log.info("{:8} {:8} {:2} {:.10f} {} {:20}".format(path, branch, prof, color, self.rainbow.get(color).to_hexa(), current.name))
        line = Line(f"{path:8}\t{current.name}", latlon, getAttrLatLonif(current, self.gpstype), self.rainbow.get(color), path, branch,prof, person=current,
                    whenFrom=current.birth.whenyear() if getattr(current, 'birth',None) else None, whenTo=current.death.whenyear() if getattr(current, 'death', None) else None )
        return self.link(getAttrLatLonif(current, self.gpstype), current, branch, prof, 0, path) + [line]

    def link(self, latlon: LatLon, current: Person, branch=0, prof=0, miss=0, path="") -> list[Line]:
        return (self.line(latlon, self.people[current.father], branch*SPACE, prof+1, miss, f"{path}F") if current.father else []) \
               + (self.line(latlon, self.people[current.mother], branch*SPACE+DELTA, prof+1, miss, path + "M") if current.mother else [])

    def create(self, main_id: str):
        if main_id not in self.people.keys():
            _log.error("Could not find your starting person: %s", main_id)
            raise IndexError(f"Missing starting person {main_id}")

        current = self.people[main_id]
        createpos = getAttrLatLonif(current, self.gpstype, 'latlon')
        return self.link(createpos, current) + \
            self.line(createpos, current, 0, 0, 0, "")

    def createothers(self,listof):
        for person in self.people:
            c = [creates.person.xref_id for creates in listof]
            if person not in c:
                _log.debug("Others: + %s (%s) (%d)", self.people[person].name, person, len(listof))
                listof.extend(self.line(getAttrLatLonif(self.people[person], self.gpstype), self.people[person], len(listof)/10, 5, 0, path=""))

class CreatorTrace:
    def __init__(self, people: Dict[str, Person], max_missing=0):
        self.people = people
        self.rainbow = Rainbow()
        self.max_missing = max_missing
        self.alltheseids= {}

    def line(self, current: Person, branch, prof, path="") -> list[Line]:
        if current.xref_id in self.alltheseids:
            _log.error("Looping Trace Problem: {:2} -LOOP STOP - {} {} -Tracing= {:20}".format(  prof, self.people[current.xref_id].name, current.xref_id, path))
            return []
        self.alltheseids[current.xref_id] = current.xref_id
        
        _log.info("{:8} {:8} {:2} {:20}".format(path, branch, prof, current.name))
        line = Line(f"{path:8}\t{current.name}", None, None, None, path, branch,prof, person=current, 
                    whenFrom=current.birth.whenyear() if getattr(current, 'birth', None) else None , whenTo=current.death.whenyear() if getattr(current, 'death', None)  else None)
        return self.link(current, branch, prof, path) + [line]

    def link(self, current: Person, branch=0, prof=0,  path="") -> list[Line]:
        return (self.line(self.people[current.father],  0, prof+1,  f"{path}F") if current.father else []) \
               + (self.line(self.people[current.mother], 0, prof+1,  path + "M") if current.mother else [])

    def create(self, main_id: str):
        if main_id not in self.people.keys():
            _log.error("Could not find your starting person: %s", main_id)
            raise IndexError(f"Missing starting person {main_id}")

        current = self.people[main_id]
        return self.link(current)
    
    def createothers(self,listof):
        for person in self.people:
            c = [creates.person.xref_id for creates in listof]
            if person not in c:
                _log.debug("Others: + %s (%s) (%d)", self.people[person].name, person, len(listof))
                listof.extend(self.line(self.people[person], len(listof)/10, 5, path=""))


class LifetimeCreator:
    def __init__(self, people: Dict[str, Person], max_missing=0):
        self.people = people
        self.rainbow = Rainbow()
        self.max_missing = max_missing
        self.alltheseids= {}

    def selfline(self, current: Person, branch, prof, miss, path="") -> list[Line]:
        # We can not draw a line from Birth to death without both ends  --- or can we???
        self.alltheseids[current.xref_id] = current.xref_id
        color = (branch + DELTA / 2) / (SPACE ** (prof % 256))
        if current.birth and current.death:
            if current.birth and current.death.latlon:
                _log.info("{:8} {:8} {:2} {:.10f} {} Self {:20}".format(path, branch, prof, color, self.rainbow.get(color).to_hexa(), current.name))
            else:
                _log.info("{:8} {:8} {:2} {:.10f} {} Self {:20}".format(" ", " ", " ", 0, "-SKIP-", current.name))
        midpoints = []
        wyear = None
        if current.home:
            for h in (range(0,len(current.home))):
                if current.home[h].latlon and current.home[h].latlon.hasLocation():
                    midpoints.append(LifeEvent(current.home[h].place, current.home[h].whenyear(), current.home[h].latlon, current.home[h].what))
                    wyear = wyear if wyear else current.home[h].whenyear()
        bp = getAttrLatLonif(current, 'birth')
        bd = getAttrLatLonif(current, 'death')
        line = Line(f"{path:8}\t{current.name}", bp, bd, self.rainbow.get(color), path, branch, prof, 'Life', 
                    None, midpoints, current, whenFrom=current.birth.whenyear() if getattr(current, 'birth', None)  else None , whenTo=current.death.whenyear() if getattr(current, 'death', None) else None)
        return [line]
        
    # Draw a line from the parents birth to the child birth location
                            
    def line(self, latlon: LatLon, parent: Person, branch, prof, miss, path="", linestyle="", forperson: Person = None ) -> list[Line]:
        # Check to make sure we are not looping and have been here before
        if parent.xref_id in self.alltheseids:
            _log.error("Looping Problem: {:2} -LOOP STOP- {} {} -Looping= {:20}".format(  prof, parent.name, parent.xref_id, path))
            return []
        if getattr(parent, 'birth', None):
            color = (branch + DELTA / 2) / (SPACE ** prof)
            _log.info("{:8} {:8} {:2} {:.10f} {} {:20} from {:20}".format(path, branch, prof, color, self.rainbow.get(color).to_hexa(), parent.name, forperson.name))
            line = Line(f"{path:8}\t{parent.name}", latlon, getAttrLatLonif(parent, 'birth'), self.rainbow.get(color), path, branch, prof, linestyle,  
                            forperson,  person=parent, whenFrom=parent.birth.whenyear() if getattr(parent, 'birth', None) else None , whenTo=parent.death.whenyear() if getattr(parent, 'death', None) else None)
            return self.link(parent.birth.latlon, parent, branch, prof, 0, path) + [line]
        else:
            if self.max_missing != 0 and miss >= self.max_missing:
                _log.info("{:8} {:8} {:2} {:.10f} {} Self {:20}".format(" ", " ", " ", 0, "-STOP-", parent.name))
                return []
            return self.link(latlon, parent, branch, prof, miss+1, path)
        _log.info("{:8} {:8} {:2} {:.10f} {} Self {:20}".format(" ", " ", " ", 0, "-KICK-", parent.name))

        
    def link(self, latlon: LatLon, current: Person, branch=0, prof=0, miss=0, path="") -> list[Line]:
        # Maximun recursion depth.  This should never happen
        if prof < 480: 
            return (self.selfline(current, branch*SPACE, prof+1, miss, path)) \
               + (self.line(latlon, self.people[current.father], branch*SPACE, prof+1, miss, path + "F",'father', current) if current.father else []) \
               + (self.line(latlon, self.people[current.mother], branch*SPACE+DELTA, prof+1, miss, path + "M", 'mother', current) if current.mother else [])
        else:
            _log.warning("{:8} {:8} {:2} {} {} {:20}".format(" ", " ", prof, " ", "-TOO DEEP-", current.name))
            return (self.selfline(current, branch*SPACE, prof+1, miss, path)) + [] + []

    def create(self, main_id: str):
        if main_id not in self.people.keys():
            _log.error ("Could not find your starting person: %s", main_id)
            raise IndexError(f"Missing starting person {main_id}")
        current = self.people[main_id]

        return self.link(getAttrLatLonif(current, 'birth'), current) 
    
    def createothers(self,listof):
        for person in self.people:
            c = [creates.person.xref_id for creates in listof]
            if person not in c:
                _log.debug ("Others: + %s(%s) (%d)", self.people[person].name, person, len(listof))
                listof.extend(self.selfline(self.people[person], len(listof)/10, len(listof)/10, 5, path=""))
               