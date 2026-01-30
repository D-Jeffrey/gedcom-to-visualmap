"""
Lineage tracing and relationship path finding.

This module handles tracing relationships between people in genealogical data.
Extracted from visual_map_actions.py for better separation of concerns.
"""
import logging
from typing import Any, Optional, Dict, List, Tuple

from models.creator import CreatorTrace, Person
from render.referenced import Referenced
from services.interfaces import IConfig, IState, IProgressTracker

_log = logging.getLogger(__name__.lower())


class LineageTracer:
    """Handles tracing and mapping relationships between people.
    
    Responsibilities:
    - Find all people related to a starting person
    - Build relationship paths showing connections
    - Trace specific lineage from main person to target person
    
    Attributes:
        panel: Reference to parent VisualMapPanel for UI updates
    """
    
    def __init__(self, panel: Any) -> None:
        """Initialize lineage tracer.
        
        Args:
            panel: Parent VisualMapPanel instance providing access to services
        """
        self.panel: Any = panel
    
    def doTrace(self, svc_config: IConfig, svc_state: IState, svc_progress: IProgressTracker) -> int:
        """Trace and collect all people connected to main person.
        
        Starting from Main person, recursively finds all related people
        (ancestors, descendants, spouses) and stores their relationship paths
        in state.Referenced. Each person's path is a list of relationship tags
        ('F' for father, 'M' for mother, etc.) showing how they connect to
        the main person.
        
        Args:
            svc_config: Configuration service
            svc_state: Runtime state service (provides people via svc_state.people)
            svc_progress: Progress tracking service
        
        Returns:
            int: Total count of people found in trace, or 0 if error.
        
        Side Effects:
            - Initializes svc_state.Referenced as empty Referenced set
            - Populates svc_state.Referenced with xref_ids and relationship paths
            - Sets svc_state.totalpeople to count of people found
        
        Raises:
            Logs error if:
            - No people data available (svc_state.people is empty)
            - Starting person (svc_config.Main) not found in people dict
        
        Example:
            tracer = LineageTracer(panel)
            count = tracer.doTrace(svc_config, svc_state, svc_progress)
            print(f"Found {count} related people")
            
            # Check if person is related
            if svc_state.Referenced.exists('I0042'):
                path = svc_state.Referenced.gettag('I0042')
                print(f"Relationship path: {path}")
        
        Note:
            Must be called before doTraceTo() or SaveTrace() to populate
            Referenced set.
        """
        
        svc_state.Referenced = Referenced()
        svc_state.totalpeople = 0
        
        people = svc_state.people
        if not people:
            _log.error("Trace:References no people.")
            return 0
        
        main_id = svc_config.get('Main')
        if main_id not in people:
            _log.error("Trace:Could not find your starting person: %s", main_id)
            return 0
        svc_state.Referenced.add(main_id)
        lifeline: CreatorTrace = CreatorTrace(people)

        creator: list = lifeline.create(main_id)

        _log.info("Trace:Total of %i people.", len(creator)) 
        if creator:
            for c in creator:
                svc_state.Referenced.add(c.person.xref_id, tag=c.path)
        
        svc_state.totalpeople = len(creator) if creator else 0
        return svc_state.totalpeople

    def doTraceTo(self, svc_config: IConfig, svc_state: IState, svc_progress: IProgressTracker, ToID: Person) -> List[Tuple[str, str, Optional[int], str]]:
        """Trace lineage path from main person to specified target person.
        
        Builds ancestry chain connecting mainPerson to ToID by following
        the parent relationships stored in state.Referenced. Each step in the path
        identifies whether connection is through father or mother.
        
        Process:
        1. Calls doTrace() if state.Referenced not populated
        2. Starts with main person
        3. For each relationship tag in Referenced path:
           - 'F': Follow father link
           - 'M': Follow mother link
        4. Builds list of (relationship, name, birth_year, xref_id) tuples
        
        Args:
            svc_config: Configuration service
            svc_state: Runtime state service (provides people and mainPerson)
            svc_progress: Progress tracking service
            ToID: Target Person to trace lineage to.
        
        Returns:
            List[Tuple[str, str, Optional[int], str]]: List of ancestry steps, each tuple:
                - relationship: "[Father]", "[Mother]", "NotDirect", or ""
                - name: Person's name
                - birth_year: Birth year (None if unknown)
                - xref_id: Person's ID
        
            Returns list with single "NotDirect" entry if ToID not in Referenced set.
            Returns empty list if mainPerson not set.
        
        Side Effects:
            - Sets svc_state.heritage to resulting lineage list
            - Calls doTrace() if not already called
        
        Raises:
            Logs error if:
            - svc_state.mainPerson not set
            - Parent (father/mother) not found in people dict
            - Invalid relationship tag encountered
        
        Example:
            tracer = LineageTracer(panel)
            target = people['I0042']
            lineage = tracer.doTraceTo(svc_config, target)
            for rel, name, year, xref in lineage:
                print(f"{rel:15} {name:30} b.{year or '?'} ({xref})")
        
            # Output example:
            #                 John Smith                 b.1950 (I0001)
            # [Father]        Robert Smith               b.1920 (I0025)
            # [Father]        William Smith              b.1890 (I0042)
        
        Note:
            Requires prior call to doTrace() to populate Referenced set,
            though will call it automatically if needed.
        """
        if not svc_state.Referenced:
            self.doTrace(svc_config, svc_state, svc_progress)
        
        main_person = svc_state.mainPerson
        if not main_person:
            _log.error("doTraceTo: svc_state.mainPerson not set")
            return []
        
        people: Dict[str, Person] = svc_state.people
        heritage: List[Tuple[str, str, Optional[int], str]] = []
        heritage = [("", main_person.name, main_person.ref_year()[0], main_person.xref_id)]
        if svc_state.Referenced.exists(ToID.xref_id):
            personRelated: Optional[List[str]] = svc_state.Referenced.gettag(ToID.xref_id)
            personTrace: Person = main_person
            if personRelated:    
                for r in personRelated:
                    tag: str = "Unknown"  # Initialize with default value
                    if r == "F":
                        try:
                            personTrace = people[personTrace.father]
                        except KeyError:
                            _log.error("doTraceTo: father %s not in people dict", personTrace.father)
                            break
                        tag = "Father"
                    elif r == "M":
                        try:
                            personTrace = people[personTrace.mother]
                        except KeyError:
                            _log.error("doTraceTo: mother %s not in people dict", personTrace.mother)
                            break
                        tag = "Mother"
                    else:
                        _log.error("doTrace - neither Father or Mother, how did we get here?")
                        tag = "Unknown"
                    heritage.append((f"[{tag}]", personTrace.name, personTrace.ref_year()[0], personTrace.xref_id))
        else:
            heritage.append(("NotDirect", ToID.name, None, ToID.xref_id))
        svc_state.heritage = heritage
        return heritage
