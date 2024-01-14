__all__ = ['Human', 'LifeEvent']

import logging
import re

from models.Pos import Pos

logger = logging.getLogger(__name__)

class Human:
    def __init__(self, xref_id):
        self.xref_id = xref_id
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

    def __str__(self):
        return f"Human(id={self.xref_id}, name={self.name})"
        
    def __repr__(self):
        return f"[ {self.xref_id} : {self.name} - {self.father} & {self.mother} - {self.pos} ]"
            
            
    def refyear(self):
        bestyear = "?Unknown"
        if self.birth and self.birth.when:
            year = self.birth.whenyear()
            bestyear = self.birth.whenyear() + " (Born)" if year else "?Unknown"
        elif self.death and self.death.when:
            year = self.death.whenyear()
            bestyear = self.death.whenyear() + " (Died)" if year else "?Unknown"
        return bestyear

    def bestlocation(self):
        # TODO Best Location should consider if in KML mode and what is selected
        best = ["Unknown", ""]
        if self.birth and self.birth.pos:
            best = [str(self.birth.pos), self.birth.where + " (Born)" if self.birth.where else ""]
        elif self.death and self.death.pos:
            best = [str(self.death.pos), self.death.where + " (Died)" if self.death.where else ""]
        return best
    
    def bestPos(self):
        # TODO Best Location should consider if in KML mode and what is selected  
        # If the location is set in the GED, using MAP attribute then that will be the best
        best = Pos(None,None)
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

    def whenyear(self, last = False):
        
        if self.when:
            if (type(self.when) == type(' ')):
                return (self.when)
            else:
                if self.when.value.kind.name == "RANGE" or self.when.value.kind.name == "PERIOD":
                    if last:
                        return self.when.value.date1.year_str
                    else:
                        return self.when.value.date2.year_str
                elif self.when.value.kind.name == "PHRASE":
                    # TODO poor error checking here Assumes a year is in this date
                    if re.search(r"[0-9]{4}", self.when.value.phrase):
                        try:
                            return re.search(r"[0-9]{4}", self.when.value.phrase)[0]
                        except:
                            return None
                    else:
                        if hasattr(self.when.value, 'name') :
                            logger.warning ("when year %s as %s", self.when.value.name, self.when.value.phrase)
                        else:
                            logger.warning ("unknown when name %s ", self.when.value)
                        return None
                else:
                    return self.when.value.date.year_str
        return None

    def whenyearnum(self, last = False):
        """ 
        Return 0 if None
        """
        w = self.whenyear(last)
        if not w:
            w = 0
        else:
            # TODO this is a range date hack
            if len(w)>3:
                w = int(w[0:4])
        
        return w

    def getattr(self, attr):
        if attr == 'pos':
            return self.pos
        elif attr == 'when':
            return self.whenyear()
        elif attr == 'where':
            return self.where if self.where else ""
        elif attr == 'what':
            return self.what if self.what else ""
        logger.warning("Life Event attr: %s' object has no attribute '%s'", type(self).__name__, attr)    
        return None

    def __str__(self):
        return f"{self.getattr('where')} : {self.getattr('when')} - {self.getattr('pos')} {self.getattr('what')}"
        
    