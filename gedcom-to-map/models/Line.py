from models.Color import Color
from models.Pos import Pos
from models.Human import Human, LifeEvent 
from datetime import datetime
from ged4py.date import DateValueVisitor


class Line:
    """Create a Line defination for a person from their birth to the death which includes midpoints and the names of the mmidpoints
    Include the reference to the human, and the name of their parent, and type of line (life, father, mother) along with the year it occured
    prof - how far from orginal, midpoint - (LifeEvent) array,
    human - reference to themeselves, 
    """
    def __init__(self, name: str, a: Pos, b: Pos, color: Color, prof: int, style : str = '', parentofhuman = '', 
                        midpoints:[]=None, human=None, when: int =None, tag:str='', type=''):
        self.name = name
        self.a = a
        self.b = b
        self.color = color
        self.prof = prof
        self.style = style
        self.parentofhuman = parentofhuman
        self.midpoints : LifeEvent =  midpoints
        self.human = human
        self.tag = tag
#        if len(when) > 1:
#            (self.when.a, self.when.b) = (self.valueWhen(when[0]), self.valueWhen(when[1]))

        if when and len(when) > 1:
            self.when= self.valueWhen(when[0])
        else:
            self.when= self.valueWhen(when)
        self.type = type
        

    def __repr__(self):
        return "( {}, {} )".format(self.a, self.b)

    def valueWhen (self, newwhen):
        if type(newwhen) == type(" "):
            newwhen = int(newwhen)
        return newwhen

    def updateWhen(self, newwhen):
        newwhen = self.valueWhen(newwhen)
        if newwhen and not self.when:
           self.when = newwhen
        if self.when and newwhen and newwhen < self.when:
            self.when = newwhen
        
    
    
    


