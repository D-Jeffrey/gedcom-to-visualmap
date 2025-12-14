__all__ = ['Line']

#TODO need to improved this subclass
from ged4py.date import DateValueVisitor
from .color import Color
from geo_gedcom.person import Person
from geo_gedcom.life_event import LifeEvent
from geo_gedcom.lat_lon import LatLon


class Line:
    """Create a Line defination for a person from their birth to the death which includes midpoints and the names of the mmidpoints
    Include the reference to the person, and the name of their parent, and type of line (life, father, mother) along with the year it occured
    prof - how far from orginal, midpoint - (LifeEvent) array,
    person - reference to themeselves, 
    """
    def __init__(self, name: str, fromlocation: LatLon, tolocation: LatLon, color: Color, path: str, branch: float, prof: int, style : str = '', parentofperson : Person = None, 
                        midpoints:list[LifeEvent]=None, person=None, whenFrom = None, whenTo = None, tag:str='', linetype=''):
        self.name = name
        # TODO we need to use id to avoid problems with duplicate names
        # BUG
        self.whenFrom = None 
        self.whenTo = None
        self.fromlocation = fromlocation
        self.tolocation = tolocation
        self.color = color

        self.path = path
        self.branch = branch
        self.prof = prof
        self.style = style
        self.parentofperson = parentofperson
        self.midpoints : LifeEvent =  midpoints
        self.person = person
        self.tag = tag

        self.whenFrom = whenFrom if whenFrom else None
        self.whenTo= whenTo if whenTo else None
        self.linetype = linetype
        

    def __repr__(self):
        return f"( {self.fromlocation}, {self.tolocation} )"

    def updateWhen(self, newwhen):
        newwhen = newwhen
        if newwhen and not self.whenFrom:
            self.whenFrom = newwhen
        if self.whenFrom and newwhen and newwhen < self.whenFrom:
            self.whenFrom = newwhen

    def updateWhenTo(self, newwhen):
        newwhen = newwhen
        if newwhen and not self.whenTo:
            self.whenTo = newwhen
        if self.whenTo and newwhen and newwhen > self.whenTo:
            self.whenTo = newwhen

    def __getattr__(self, attr):
        if attr == 'parentofperson' and self.parentofperson is None:
            return ''
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{attr}'")
