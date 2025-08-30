__all__ = ['Line']

#TODO need to improved this subclass
from ged4py.date import DateValueVisitor
from models.Color import Color
from models.Human import Human, LifeEvent, DateFromField
from models.Pos import Pos


class Line:
    """Create a Line defination for a person from their birth to the death which includes midpoints and the names of the mmidpoints
    Include the reference to the human, and the name of their parent, and type of line (life, father, mother) along with the year it occured
    prof - how far from orginal, midpoint - (LifeEvent) array,
    human - reference to themeselves, 
    """
    def __init__(self, name: str, a: Pos, b: Pos, color: Color, path: str, branch: float, prof: int, style : str = '', parentofhuman : Human = None, 
                        midpoints:list[LifeEvent]=None, human=None, whenFrom = None, whenTo = None, tag:str='', linetype=''):
        self.name = name
        # TODO we need to use id to avoid problems with duplicate names
        # BUG
        
        self.a = a
        self.b = b
        self.color = color

        self.path = path
        self.branch = branch
        self.prof = prof
        self.style = style
        self.parentofhuman = parentofhuman
        self.midpoints : LifeEvent =  midpoints
        self.human = human
        self.tag = tag
#        if len(when) > 1:
#            (self.when.a, self.when.b) = (self.valueWhen(when[0]), self.valueWhen(when[1]))

        if whenFrom: # and len(whenFrom) > 1:
            #self.whenFrom= self.valueWhen(whenFrom[0])
        #else:
            self.whenFrom= self.valueWhen(whenFrom)
        
        if whenTo: # and len(whenTo) > 1:
            #self.whenTo= self.valueWhen(whenTo[0])
        #else:
            self.whenTo= self.valueWhen(whenTo)
        self.linetype = linetype
        

    def __repr__(self):
        return f"( {self.a}, {self.b} )"

    def valueWhen(self, newwhen):
        return DateFromField(newwhen)

    def updateWhen(self, newwhen):
        newwhen = self.valueWhen(newwhen)
        if newwhen and not self.whenFrom:
            self.whenFrom = newwhen
        if self.whenFrom and newwhen and newwhen < self.whenFrom:
            self.whenFrom = newwhen
    def updateWhenTo(self, newwhen):
        newwhen = self.valueWhen(newwhen)
        if newwhen and not self.whenTo:
            self.whenTo = newwhen
        if self.whenTo and newwhen and newwhen > self.whenTo:
            self.whenTo = newwhen

    def __getattr__(self, attr):
        if attr == 'parentofhuman' and self.parentofhuman is None:
            return ''
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{attr}'")