from typing import Dict

from models.Color import Color
from models.Human import Human, LifeEvent
from models.Line import Line
from models.Pos import Pos
from models.Rainbow import Rainbow


space = 2.5
delta = 1.5

def getattrif(obj, attname, attvaluename):
    if obj:
        if hasattr(obj, attname):
            a = getattr(obj, attname)
            if hasattr(a, attvaluename):
                return getattr(a, attvaluename)
    return None
    

class Creator:
    def __init__(self, humans: Dict[str, Human], max_missing=0):
        self.humans = humans
        self.rainbow = Rainbow()
        self.max_missing = max_missing

    def line(self, pos: Pos, current: Human, branch, prof, miss, path="") -> [Line]:
        if current.pos:
            color = (branch + delta / 2) / (space ** prof)
            print("{:8} {:8} {:2} {:.10f} {} {:20}".format(path, branch, prof, color, self.rainbow.get(color).to_hexa(), current.name))
            line = Line("{:8} {}".format(path, current.name), pos, current.pos, self.rainbow.get(color), prof, human=current)
            return self.link(current.pos, current, branch, prof, 0, path) + [line]
        else:
            if self.max_missing != 0 and miss >= self.max_missing:
                return []
            return self.link(pos, current, branch, prof, miss+1, path)

    def link(self, pos: Pos, current: Human, branch=0, prof=0, miss=0, path="") -> [Line]:
        return (self.line(pos, self.humans[current.father], branch*space, prof+1, miss, path + "0") if current.father else []) \
               + (self.line(pos, self.humans[current.mother], branch*space+delta, prof+1, miss, path + "1") if current.mother else [])

    def create(self, main_id: str):
        if main_id not in self.humans.keys():
            print ("Could not find your starting person: {}".format(main_id))
            raise
        current = self.humans[main_id]
        return self.link(current.pos, current)

    def createothers(self,listof):
       for human in self.humans:
           c = [creates.human.xref_id for creates in listof]
           if not human in c:
               # print (f"Others: + {self.humans[human].name}({human}) ({len(listof)})")
               listof.extend(self.line(self.humans[human].pos, self.humans[human], len(listof)/10, 5, 0, path=""))

class LifetimeCreator:
    def __init__(self, humans: Dict[str, Human], max_missing=0):
        self.humans = humans
        self.rainbow = Rainbow()
        self.max_missing = max_missing

    def selfline(self, current: Human, branch, prof, miss, path="") -> [Line]:
        # We can not draw a line from Birth to death without both ends  --- or can we???
        color = (branch + delta / 2) / (space ** prof)
        if current.birth and current.death:
            if current.birth.pos and current.death.pos:
                print("{:8} {:8} {:2} {:.10f} {} Self {:20}".format(path, branch, prof, color, self.rainbow.get(color).to_hexa(), current.name))
            else:
                print("{:8} {:8} {:2} {:.10f} {} Self {:20}".format(" ", " ", " ", 0, "-SKIP-", current.name))
        midpoints = []
        if (current.home):
            wyear = None
            for h in (range(0,len(current.home))):
                if (current.home[h].pos and current.home[h].pos.lat != None):
                    midpoints.append(LifeEvent(current.home[h].where, current.home[h].whenyear(), current.home[h].pos, current.home[h].what))
                    wyear = wyear if wyear else current.home[h].whenyear()
        else:
            wyear = None
        bp = current.birth.pos if current.birth else None
        bd = current.death.pos if current.death else None
        line = Line("{:8} {}".format(path, current.name), bp, bd, self.rainbow.get(color), prof, 'Life', 
                    current.name, midpoints, current, wyear)
        if current.birth: 
            line.updateWhen(current.birth.whenyear())
        line.updateWhen(wyear)
        if current.death: 
            line.updateWhen(current.death.whenyear())
        return [line]
        
    # Draw a line from the parents birth to the child birth location
                            
    def line(self, pos: Pos, parent: Human, branch, prof, miss, path="", linestyle="", forhuman="") -> [Line]:
        if hasattr(parent, 'birth') and parent.birth:
            color = (branch + delta / 2) / (space ** prof)
            print("{:8} {:8} {:2} {:.10f} {} {:20} from {:20}".format(path, branch, prof, color, self.rainbow.get(color).to_hexa(), parent.name, forhuman))
            line = Line("{:8} {}".format(path, parent.name), pos, parent.birth.pos, self.rainbow.get(color), prof, linestyle,  
                            forhuman,  human=parent, when= (parent.birth.whenyear(), getattrif(parent, 'death','whenyear()')))
            return self.link(parent.birth.pos, parent, branch, prof, 0, path) + [line]
        else:
            if self.max_missing != 0 and miss >= self.max_missing:
                print("{:8} {:8} {:2} {:.10f} {} Self {:20}".format(" ", " ", " ", 0, "-STOP-", parent.name))
                return []
            return self.link(pos, parent, branch, prof, miss+1, path)
        print("{:8} {:8} {:2} {:.10f} {} Self {:20}".format(" ", " ", " ", 0, "-KICK-", parent.name))

        
    def link(self, pos: Pos, current: Human, branch=0, prof=0, miss=0, path="") -> [Line]:
        return (self.selfline(current, branch*space, prof+1, miss, path)) \
               + (self.line(pos, self.humans[current.father], branch*space, prof+1, miss, path + "0",'father', current.name) if current.father else []) \
               + (self.line(pos, self.humans[current.mother], branch*space+delta, prof+1, miss, path + "1", 'mother', current.name) if current.mother else [])

    def create(self, main_id: str):
        if main_id not in self.humans.keys():
            print ("Could not find your starting person: {}".format(main_id))
            raise
        current = self.humans[main_id]

        return self.link(current.birth.pos if hasattr(current, 'birth') and current.birth != None else Pos(None, None), current) 
    
    def createothers(self,listof):
       for human in self.humans:
           c = [creates.human.xref_id for creates in listof]
           if not human in c:
               # print (f"Others: + {self.humans[human].name}({human}) ({len(listof)})")
               listof.extend(self.selfline(self.humans[human], len(listof)/10, len(listof)/10, 5, path=""))
               