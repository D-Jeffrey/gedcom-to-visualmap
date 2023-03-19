__all__ = ['Human', 'LifeEvent']

import re
from models.Pos import Pos

class Human:
    def __init__(self, xref_id):
        self.xref_id = xref_id
        self.name = None
        self.father : Human = None
        self.mother : Human = None
        self.pos = None
        self.birth : LifeEvent = None
        self.death : LifeEvent = None
        # TODO need to deal with multiple mariages
        self.marriage = None
        # multiple homes
        self.home : LifeEvent = None
        self.map = None   # used to save the orginal pos values
        self.first = None
        self.surname = None
        self.maiden: None
        self.sex: None
        
    def __repr__(self):
        return "[ {} : {} - {} {} - {} ]".format(
            self.xref_id,
            self.name,
            self.father,
            self.mother,
            self.pos
            
        )
    def refyear(self):
        bestyear = "Unknown"
        if self.birth and self.birth.when:
            bestyear = "Born " + self.birth.whenyear()
        elif self.death and self.death.when:
            bestyear = "Died " + self.death.whenyear()
        return bestyear

class LifeEvent:
    def __init__(self, place :str, atime, position : Pos = None, what = None):  # atime is a Record
        self.where = place
        self.when = atime
        self.pos = position
        self.what = what
        

    def __repr__(self):
        return "[ {} : {} ]".format(
            self.when,
            self.where
        )

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
                    # TODO poor error checking here
                    return re.search(r"[0-9]{4}", self.when.value.phrase)[0]
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

    def __getattr__(self, name):
        if name == 'pos':
            return (None, None)
        return None