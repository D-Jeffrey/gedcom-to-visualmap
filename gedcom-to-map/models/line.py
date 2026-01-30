__all__ = ['Line']

#TODO need to improved this subclass
from ged4py.date import DateValueVisitor
from .color import Color
from geo_gedcom.person import Person
from geo_gedcom.life_event import LifeEvent
from geo_gedcom.lat_lon import LatLon


class Line:
    """Represents a geographic line connecting two locations for a person's life timeline.
    
    Attributes:
        name: Display name for the line (typically person name and event).
        fromlocation: Starting LatLon coordinate for the line.
        tolocation: Ending LatLon coordinate for the line.
        color: Color object for rendering the line.
        path: String encoding of traversal path (e.g., "FM...") for debugging.
        branch: Horizontal branch offset for visual distinction.
        prof: Generation depth/profile for color and traversal depth.
        midpoints: Intermediate life events as waypoints along the line.
        person: Reference to the Person object this line represents.
        whenFrom: Start year for the line segment.
        whenTo: End year for the line segment.
        tag: Optional tag for grouping or identification.
        linetype: Type of line ('life', 'father', 'mother', etc.).
    """
    
    def __init__(
        self,
        name: str,
        fromlocation: LatLon | None,
        tolocation: LatLon | None,
        color: Color | None,
        path: str,
        branch: float,
        prof: int,
        style: str = '',
        parentofperson: Person | None = None,
        midpoints: list[LifeEvent] | None = None,
        person: Person | None = None,
        whenFrom: int | None = None,
        whenTo: int | None = None,
        tag: str = '',
        linetype: str = '',
    ) -> None:
        """Initialize a Line representing a geographic segment of a person's life.
        
        Args:
            name: Display name for this line segment.
            fromlocation: Starting geographic location (can be None).
            tolocation: Ending geographic location (can be None).
            color: Color for rendering (can be None).
            path: Traversal path encoding (e.g., "FM..." for Father-Mother).
            branch: Branch offset for visual positioning.
            prof: Profundity/generation depth.
            style: Optional line style specification.
            parentofperson: Reference to parent Person (if applicable).
            midpoints: List of intermediate LifeEvent waypoints.
            person: Reference to the Person object this represents.
            whenFrom: Start year for the timeline.
            whenTo: End year for the timeline.
            tag: Optional identification tag.
            linetype: Type of line (life, father, mother, etc.).
        """
        self.name: str = name
        self.whenFrom: int | None = whenFrom
        self.whenTo: int | None = whenTo
        self.fromlocation: LatLon | None = fromlocation
        self.tolocation: LatLon | None = tolocation
        self.color: Color | None = color
        self.path: str = path
        self.branch: float = branch
        self.prof: int = prof
        self.style: str = style
        self.parentofperson: Person | None = parentofperson
        self.midpoints: list[LifeEvent] | None = midpoints
        self.person: Person | None = person
        self.tag: str = tag
        self.linetype: str = linetype
        

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
