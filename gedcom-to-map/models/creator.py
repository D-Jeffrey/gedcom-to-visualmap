__all__ = ["Creator", "CreatorTrace", "LifetimeCreator", "DELTA", "SPACE"]

import logging
from typing import Dict, Optional

from geo_gedcom.person import Person
from geo_gedcom.life_event import LifeEvent
from .line import Line
from geo_gedcom.life_event import LatLon
from .rainbow import Rainbow
from services.interfaces import IProgressTracker

_log = logging.getLogger(__name__.lower())


SPACE = 2.5  # These values drive how colors are selected
DELTA = 1.5  # These values drive how colors are selected


class Creator:
    """
    Creator
    Class for traversing a family tree of Person objects and producing Line objects
    that represent genealogical connections (using person events that have GPS/latlon
    information). Traversal proceeds recursively along parents (father and mother)
    and records each visited person to protect against infinite loops. The class
    also supports emitting "other" people not reachable from a chosen root by
    extending a provided list in-place.
    Parameters
    ----------
    people : Dict[str, Person]
        Mapping of person xref_id -> Person instance used as the graph to traverse.
    max_missing : int, optional
        Maximum number of consecutive ancestors to traverse that lack the chosen
        geographic event (gpstype). If 0 (default), missing events are not allowed
        to be skipped (i.e. traversal stops when the event is missing). A non-zero
        integer allows skipping up to that many consecutive missing events.
    gpstype : str, optional
        Name of the Person attribute to use as the event containing geographic
        information (e.g. "birth", "home", "residence"). Defaults to "birth".
    Attributes
    ----------
    people : Dict[str, Person]
        Same as the constructor parameter.
    rainbow : Rainbow
        Color generator used to assign a color to each generated Line based on
        traversal parameters.
    max_missing : int
        Same as the constructor parameter.
    alltheseids : Dict
        A temporary registry of visited person xref_ids used to detect and stop
        traversal loops during a single traversal invocation.
    gpstype : str
        Same as the constructor parameter.
    Public Methods
    --------------
    line(latlon, current, branch, prof, miss, path="")
        Create Line(s) for the given current Person and continue traversal to the
        person's parents as appropriate. Performs loop detection (using
        self.alltheseids) and respects the max_missing policy: if the current
        person lacks the requested gpstype event, the method either stops or calls
        link() to continue while incrementing the missing counter. When the person
        has the requested event, it constructs a Line object including optional
        midpoints collected from 'home' events and returns the Line for the
        current person plus any Lines produced by continuing parent traversal.
        Parameters:
          - latlon (LatLon or None): the lat/lon of the origin point used to build
            the Line segment for the current person.
          - current (Person): the person to process.
          - branch (numeric): horizontal branch offset used to compute color.
          - prof (int): generation depth / profile used to compute color and
            traversal depth.
          - miss (int): current count of consecutive missing gpstype events.
          - path (str): string encoding of traversal path (e.g. "FM...") for
            debugging and labels.
        Returns
          - list[Line]: list of Line objects produced by this call (may be empty).
    link(latlon, current, branch=0, prof=0, miss=0, path="")
        Helper that continues traversal to the current person's parents. It calls
        line() for father and mother (if present), adjusting branch/prof/miss/path
        values appropriately and concatenates the results.
        Parameters:
          - latlon (LatLon or None): origin lat/lon for parent lines.
          - current (Person): person whose parents are to be traversed.
          - branch, prof, miss, path: same semantics as in line().
        Returns
          - list[Line]: concatenated list of Lines from parent traversal.
    create(main_id)
        Entry point to create lines for a tree rooted at main_id. Validates that
        main_id exists in the people mapping and raises IndexError if not found.
        The method computes the initial position (using getAttrLatLonif for the
        configured gpstype) and initiates traversal by calling link() and line()
        for the root person. The returned list is the concatenation of the root's
        ancestor lines and the root person's own Line.
        Parameters:
          - main_id (str): xref_id of the root person to start traversal from.
        Returns
          - list[Line]: list of generated Line objects for the traversal.
        Raises
          - IndexError: when main_id is not present in self.people.
    createothers(listof)
        Inspect all Person objects in self.people and append Line objects for any
        persons whose xref_id is not already represented in the provided list.
        The method expects listof to be a list-like collection of objects that
        expose a .person attribute with an .xref_id (the code commonly uses
        previously created Line objects). For each missing person it calls line()
        and extends listof in-place with any produced Lines.
        Parameters:
          - listof (list): a mutable list (typically of Line objects) to which new
            Lines will be appended. This argument is mutated in-place.
        Side effects
          - Modifies listof in-place by extending it with new Line objects.
          - Logs debug information for each "other" person added.
    Behavioral Notes
    ----------------
    - Loop detection: During a single traversal invocation, self.alltheseids
      stores visited xref_ids; when a person is revisited a loop is logged and
      traversal for that branch stops returning an empty list.
    - Missing GPS events: When a person lacks the configured gpstype, the traversal
      will either stop (respecting max_missing) or attempt to skip the person and
      continue toward the parents by invoking link() with an incremented miss
      counter.
    - Color assignment: Colors for Lines are computed from the branch and prof
      parameters and are obtained from the internal Rainbow instance.
    - Side effects: createothers mutates the supplied list parameter; traversal
      methods update self.alltheseids. Logging is used extensively for progress
      and loop diagnostics.
    Dependencies / Expectations
    --------------------------
    This class expects the following helper items to be available in the module:
    - Person objects with attributes such as xref_id, name, father, mother, birth,
      death, home (iterable of events), and event attributes that can expose a
      latlon via getAttrLatLonif().
    - Line and LifeEvent types used to represent output.
    - Functions/objects used in the implementation such as getAttrLatLonif(),
      Rainbow, DELTA, SPACE and a configured logger _log.
    """

    def __init__(
        self,
        people: Dict[str, Person],
        max_missing: int = 0,
        gpstype: str = "birth",
        svc_progress: Optional[IProgressTracker] = None,
    ) -> None:
        """Initialize LineCreator for geographic ancestry visualization.

        Args:
            people: Dictionary mapping person IDs to Person objects.
            max_missing: Maximum consecutive missing GPS events before stopping traversal.
            gpstype: Event type to use for GPS coordinates (default: "birth").
            svc_progress: Optional progress tracker for GUI updates.
        """
        self.people: Dict[str, Person] = people
        self.rainbow: Rainbow = Rainbow()
        self.max_missing: int = max_missing
        self.gpstype: str = gpstype
        self.svc_progress: Optional[IProgressTracker] = svc_progress
        # Instrumentation for pedigree collapse analysis
        self.person_path_count: Dict[str, int] = {}  # Track how many paths reach each person
        self._line_call_count: int = 0  # Track recursive line() calls for progress reporting

    def line(self, latlon: LatLon, current: Person, branch, prof, miss, path="", visited=None) -> list[Line]:
        # Track visited IDs in this specific line to detect sequential loops only
        if visited is None:
            visited = set()

        if current.xref_id in visited:
            _log.warning(
                "Loop detected in ancestry trace: {:2} - {} {} - Path: {}".format(
                    prof, self.people[current.xref_id].name, current.xref_id, path
                )
            )
            return []

        # Add to visited set for this line
        visited = visited | {current.xref_id}

        # Track person appearances for pedigree collapse analysis
        self.person_path_count[current.xref_id] = self.person_path_count.get(current.xref_id, 0) + 1

        # Update progress every 100 recursive calls
        self._line_call_count += 1
        if self.svc_progress and self._line_call_count % 100 == 0:
            self.svc_progress.state = f"Creating ancestry lines: {self._line_call_count:,} paths processed"

        event = current.get_event(self.gpstype) if current else []
        event_latlon = event.getattr("latlon") if event else None
        event_year_num = event.getattr("when_year_num") if event else None

        if not event:
            return (
                []
                if self.max_missing != 0 and miss >= self.max_missing
                else self.link(event_latlon, current, branch, prof, miss + 1, path, visited)
            )
        color = (branch + DELTA / 2) / (SPACE ** (prof % 256))
        _log.debug(
            "{:8} {:8} {:2} {:.10f} {} {:20}".format(
                path, branch, prof, color, self.rainbow.get(color).to_hexa(), current.name
            )
        )
        midpoints = None
        residence_events = current.get_events("residence") if current else []
        if residence_events:
            wyear = None
            midpoints = []
            for h in range(0, len(residence_events)):
                home = residence_events[h]
                home_latlon = home.getattr("latlon") if home else None
                home_year_num = home.getattr("when_year_num") if home else None
                if home_latlon and home.date and home.date.year_num:
                    midpoints.append(LifeEvent(home.place, home_year_num, home_latlon, home.what))
                    wyear = wyear if wyear else home.date.year_num

        birth_event = current.get_event("birth") if current else None
        birth_year_num = birth_event.getattr("when_year_num") if birth_event else None

        death_event = current.get_event("death") if current else None
        death_year_num = death_event.getattr("when_year_num") if death_event else None

        line = Line(
            f"{path:8}\t{current.name}",
            latlon,
            event_latlon,
            self.rainbow.get(color),
            path,
            branch,
            prof,
            person=current,
            whenFrom=birth_year_num,
            whenTo=death_year_num,
            midpoints=midpoints,
        )

        return self.link(event_latlon, current, branch, prof, 0, path, visited) + [line]

    def link(self, latlon: LatLon, current: Person, branch=0, prof=0, miss=0, path="", visited=None) -> list[Line]:
        if visited is None:
            visited = set()
        return (
            self.line(latlon, self.people[current.father], branch * SPACE, prof + 1, miss, f"{path}F", visited)
            if current.father
            else []
        ) + (
            self.line(latlon, self.people[current.mother], branch * SPACE + DELTA, prof + 1, miss, path + "M", visited)
            if current.mother
            else []
        )

    def create(self, main_id: str):
        if main_id not in self.people.keys():
            _log.error("Could not find your starting person: %s", main_id)
            raise IndexError(f"Missing starting person {main_id}")

        # Reset instrumentation for this traversal
        self.person_path_count = {}
        self._line_call_count = 0

        current = self.people[main_id]
        event = current.get_event(self.gpstype) if current else None
        event_latlon = event.getattr("latlon") if event else LatLon(None, None)
        # Only call line() - it handles current person and recursively processes parents via link()
        result = self.line(event_latlon, current, 0, 0, 0, "")

        # Log pedigree collapse statistics
        unique_people = len(self.person_path_count)
        total_lines = len(result)
        multiple_paths = {pid: count for pid, count in self.person_path_count.items() if count > 1}

        _log.info(f"Pedigree collapse analysis: {total_lines:,} lines created for {unique_people:,} unique people")
        if multiple_paths:
            top_collapse = sorted(multiple_paths.items(), key=lambda x: x[1], reverse=True)[:10]
            _log.info(
                f"Top 10 people with most paths: {[(self.people[pid].name, count) for pid, count in top_collapse]}"
            )
            _log.info(
                f"Total people reached via multiple paths: {len(multiple_paths):,} ({100*len(multiple_paths)/unique_people:.1f}%)"
            )

        return result

    def createothers(self, listof):
        """Add Line objects for all people not already in listof.

        WARNING: This method iterates through ALL people in the dataset, which can be
        extremely slow for large datasets (10,000+ people). Consider disabling
        AllEntities option for large files.

        Args:
            listof: List of Line objects to extend with additional people
        """
        total_people = len(self.people)
        processed = 0
        added = 0

        _log.info(f"createothers: Processing {total_people:,} people (current list has {len(listof):,} entries)")

        for person in self.people:
            processed += 1

            # Progress logging every 1000 people
            if processed % 1000 == 0:
                percent = 100 * processed // total_people
                _log.info(
                    f"createothers: Processed {processed:,}/{total_people:,} people "
                    f"({percent}%), added {added:,} so far"
                )

            c = [creates.person.xref_id for creates in listof]
            if person not in c:
                _log.debug("Others: + %s (%s) (%d)", self.people[person].name, person, len(listof))
                event = self.people[person].get_event(self.gpstype) if self.people[person] else None
                event_latlon = event.getattr("latlon") if event else LatLon(None, None)
                line = self.line(event_latlon, self.people[person], len(listof) / 10, 5, 0, path="")
                if line:
                    listof.extend(line)
                    added += len(line)

        _log.info(
            f"createothers: Completed. Processed {processed:,} people, added {added:,} new entries. Total list size: {len(listof):,}"
        )


class CreatorTrace:
    """
    CreatorTrace class
    Tracks and builds ancestry "lines" (Line objects) for Person objects in a family graph.
    Parameters
    ----------
    people : Dict[str, Person]
        Mapping from person xref_id to Person instances used as the data source for traces.
    max_missing : int, optional
        Maximum allowed missing ancestors (unused in current implementation but stored for consumers),
        by default 0
    Attributes
    ----------
    people : Dict[str, Person]
        Same mapping provided at construction.
    rainbow : Rainbow
        An instance of Rainbow constructed for potential coloring/visualization use.
    max_missing : int
        The stored maximum missing count passed at init.
    alltheseids : Dict[str, str]
        Temporary set/dict used during a single trace to detect and prevent loops (keys are xref_ids).
    Methods
    -------
    line(current, branch, prof, path="")
        Build a Line representing `current` and recursively attach Lines for `current`'s parents.
        - Parameters:
            current (Person): the Person to build the Line for.
            branch: branch identifier passed through to Line (used by consumer code).
            prof: recursion depth or "generation" counter (incremented for parents).
            path (str): ancestry path prefix (e.g., "", "F", "M", "FF").
        - Returns: list[Line]
            A list consisting of Lines produced from parents (via link) plus the Line for `current`.
        - Behavior and side-effects:
            * Uses self.alltheseids to detect loops. If current.xref_id already seen, logs an error and
              stops that branch (returns empty list).
            * Logs tracing info and constructs a Line with:
              - label/name combining path and current.name
              - person=current
              - whenFrom/from birth.date.year_num if birth present
              - whenTo/from death.date.year_num if death present
            * Appends parent Lines produced by link(current, ...), so result is parent lines first,
              then the current person's Line.
    link(current, branch=0, prof=0, path="")
        Recursively produce Lines for the father and mother of `current`.
        - Parameters:
            current (Person): the Person whose parents will be traced.
            branch (int): branch id for the immediate call (passed to constructed Lines).
            prof (int): current recursion depth/profession counter (incremented when descending).
            path (str): current ancestry path prefix.
        - Returns: list[Line]
            Concatenation of father branch Lines (if father exists) and mother branch Lines (if mother exists).
        - Notes:
            * For each parent present, calls line(parent_person, branch_value, prof+1, updated_path).
    create(main_id)
        Start a trace from the person identified by main_id.
        - Parameters:
            main_id (str): xref_id key into self.people to start the trace.
        - Returns: list[Line]
            Lines produced by following parents of the starting person (i.e., result of link(current)).
        - Raises:
            IndexError: if main_id is not found in self.people (also logs an error).
    createothers(listof)
        Ensure every Person in self.people is represented in the provided list-like collection by
        appending Lines for those who are not already present in `listof`.
        - Parameters:
            listof (list): a mutable sequence expected to contain Line-like objects (the implementation
            expects elements with a `.person.xref_id` attribute).
        - Behavior and side-effects:
            * Iterates over keys of self.people and builds a list `c` of existing xref_ids from `listof`
              using `creates.person.xref_id`.
            * For any person id not present in `c`, logs a debug message and extends `listof` with the
              result of self.line(...) for that person. This mutates the supplied list in place.
        - Notes and caveats:
            * The function mutates the input list and uses the presence of `.person.xref_id` on its items;
              callers should ensure `listof` elements follow that shape (or accept that a different shape
              will raise an AttributeError).
            * The code currently passes len(listof)/10 as a branch value to line(), which produces a float
              rather than an integer branch identifier; callers should be aware of this behavior.
            * alltheseids is used across line/link calls for loop detection; if createothers is called
              repeatedly without clearing alltheseids between independent traces, loop detection may be
              affected. Caller code should re-instantiate CreatorTrace or clear alltheseids between
              independent trace runs if needed.
    Logging
    -------
    This class uses a module-level logger (_log) to emit info/debug/error messages during tracing,
    including a specific error message when a recursion loop is detected.
    Examples
    --------
    - Construct a CreatorTrace with a people mapping and call create(main_id) to obtain ancestry lines.
    - Pass an existing list of Line-like objects to createothers(list_of_lines) to add missing people.
    """

    def __init__(
        self, people: Dict[str, Person], max_missing: int = 0, svc_progress: Optional[IProgressTracker] = None
    ) -> None:
        """Initialize TraceCreator for genealogical trace visualization.

        Args:
            people: Dictionary mapping person IDs to Person objects.
            max_missing: Maximum consecutive missing events before stopping traversal.
            svc_progress: Optional progress tracker for GUI status updates.
        """
        self.people: Dict[str, Person] = people
        self.rainbow: Rainbow = Rainbow()
        self.max_missing: int = max_missing
        # Cache for birth/death years to avoid repeated event lookups
        self._year_cache: Dict[str, tuple] = {}
        self.svc_progress = svc_progress
        self._line_call_count: int = 0

    def _get_birth_death_years(self, person: Person) -> tuple:
        """Get cached birth and death years for a person.

        Returns:
            tuple: (birth_year_num, death_year_num) or (None, None)
        """
        person_id = person.xref_id
        if person_id not in self._year_cache:
            birth_event = person.get_event("birth")
            birth_year = birth_event.date.year_num if birth_event and birth_event.date else None
            death_event = person.get_event("death")
            death_year = death_event.date.year_num if death_event and death_event.date else None
            self._year_cache[person_id] = (birth_year, death_year)
        return self._year_cache[person_id]

    def line(self, current: Person, branch, prof, path="", visited=None, result=None) -> list[Line]:
        # Track progress for GUI updates
        self._line_call_count += 1
        if self.svc_progress and self._line_call_count % 100 == 0:
            self.svc_progress.state = f"Tracing ancestry lines: {self._line_call_count:,} paths processed"

        # Track visited IDs in this specific line to detect sequential loops only
        if visited is None:
            visited = set()
        if result is None:
            result = []

        if current.xref_id in visited:
            _log.warning(
                "Loop detected in ancestry trace: {:2} - {} {} - Path: {}".format(
                    prof, self.people[current.xref_id].name, current.xref_id, path
                )
            )
            return result

        # Add to visited set for this line
        visited = visited | {current.xref_id}

        _log.debug("{:8} {:8} {:2} {:20}".format(path, branch, prof, current.name))

        # Use cached birth/death years
        birth_year_num, death_year_num = self._get_birth_death_years(current)

        # Process ancestors first (depth-first traversal)
        self.link(current, branch, prof, path, visited, result)

        # Then add current person's line (optimize string formatting)
        line = Line(
            f"{path:8}\t{current.name}",
            None,
            None,
            None,
            path,
            branch,
            prof,
            person=current,
            whenFrom=birth_year_num,
            whenTo=death_year_num,
        )
        result.append(line)
        return result

    def link(self, current: Person, branch=0, prof=0, path="", visited=None, result=None):
        if visited is None:
            visited = set()
        if result is None:
            result = []

        # Process father (optimize path concatenation)
        if current.father and current.father not in visited:
            father_path = path + "F"
            self.line(self.people[current.father], 0, prof + 1, father_path, visited, result)

        # Process mother
        if current.mother and current.mother not in visited:
            mother_path = path + "M"
            self.line(self.people[current.mother], 0, prof + 1, mother_path, visited, result)

        return result

    def create(self, main_id: str):
        self._line_call_count = 0  # Reset counter for each traversal
        if main_id not in self.people.keys():
            _log.error("Could not find your starting person: %s", main_id)
            raise IndexError(f"Missing starting person {main_id}")

        current = self.people[main_id]
        return self.link(current)

    def createothers(self, listof):
        """Add Line objects for all people not already in listof.

        WARNING: This method iterates through ALL people in the dataset, which can be
        extremely slow for large datasets (10,000+ people). Consider disabling
        AllEntities option for large files.

        Args:
            listof: List of Line objects to extend with additional people
        """
        total_people = len(self.people)
        processed = 0
        added = 0

        _log.info(f"createothers: Processing {total_people:,} people (current list has {len(listof):,} entries)")

        for person in self.people:
            processed += 1

            # Progress logging every 1000 people
            if processed % 1000 == 0:
                percent = 100 * processed // total_people
                _log.info(
                    f"createothers: Processed {processed:,}/{total_people:,} people "
                    f"({percent}%), added {added:,} so far"
                )

            c = [creates.person.xref_id for creates in listof]
            if person not in c:
                _log.debug("Others: + %s (%s) (%d)", self.people[person].name, person, len(listof))
                lines = self.line(self.people[person], len(listof) / 10, 5, path="")
                if lines:
                    listof.extend(lines)
                    added += len(lines)

        _log.info(
            f"createothers: Completed. Processed {processed:,} people, added {added:,} new entries. Total list size: {len(listof):,}"
        )


class LifetimeCreator:
    """
    LifetimeCreator
    A class responsible for generating lifetime visualization lines for genealogical data.
    Creates Line objects representing the lifetime journey of individuals and their ancestral
    connections, with color-coding based on branch and profundity levels.
    Attributes:
        people (Dict[str, Person]): Dictionary mapping person IDs to Person objects
        rainbow (Rainbow): Color gradient generator for visual distinction
        max_missing (int): Maximum number of missing parents allowed before stopping recursion
        alltheseids (Dict): Cache of processed person IDs to prevent infinite loops
    Methods:
        selfline(current: Person, branch, prof, miss, path="") -> list[Line]:
            Creates a Line object representing a person's lifetime from birth to death location,
            including intermediate home locations as waypoints.
        line(latlon: LatLon, parent: Person, branch, prof, miss, path="", linestyle="", forperson: Person = None) -> list[Line]:
            Generates a Line from a given location to a parent's birth location, with loop
            detection. Returns empty list if parent already processed or recursion limits reached.
        link(latlon: LatLon, current: Person, branch=0, prof=0, miss=0, path="") -> list[Line]:
            Recursively generates lines for a person and their ancestors (both parents) up to
            maximum recursion depth of 480 generations, splitting branches for each parent.
        create(main_id: str) -> list[Line]:
            Entry point to generate complete ancestral lifetime visualization starting from
            a specified person ID. Raises IndexError if person not found.
        createothers(listof) -> None:
            Extends the provided list with lifetime lines for all people not already included,
            using list length for branch and profundity calculations.
    """

    def __init__(
        self, people: Dict[str, Person], max_missing: int = 0, svc_progress: Optional[IProgressTracker] = None
    ) -> None:
        """Initialize LifeCreator for personal life timeline visualization.

        Args:
            people: Dictionary mapping person IDs to Person objects.
            max_missing: Maximum consecutive missing events before stopping traversal.
            svc_progress: Optional progress tracker for GUI status updates.
        """
        self.people: Dict[str, Person] = people
        self.rainbow: Rainbow = Rainbow()
        self.max_missing: int = max_missing
        self.svc_progress = svc_progress
        self._line_call_count: int = 0

    def selfline(self, current: Person, branch, prof, miss, path: str = "", visited=None) -> list[Line]:
        # Track visited IDs in this specific line
        if visited is None:
            visited = set()

        visited = visited | {current.xref_id}
        color = (branch + DELTA / 2) / (SPACE ** (prof % 256))

        birth_event = current.get_event("birth") if current else None
        birth_year_num = birth_event.getattr("when_year_num") if birth_event else None
        birth_latlon = birth_event.getattr("latlon") if birth_event else None

        death_event = current.get_event("death") if current else None
        death_year_num = death_event.getattr("when_year_num") if death_event else None
        death_latlon = death_event.getattr("latlon") if death_event else None

        if birth_event and death_event:
            _log.debug(
                "{:8} {:8} {:2} {:.10f} {} Self {:20}".format(
                    path, branch, prof, color, self.rainbow.get(color).to_hexa(), current.name
                )
            )
        else:
            _log.debug("{:8} {:8} {:2} {:.10f} {} Self {:20}".format(" ", " ", " ", 0, "-SKIP-", current.name))
        midpoints = []
        wyear = None
        residence_events = current.get_events("residence") if current else []
        if residence_events:
            for h in range(0, len(residence_events)):
                if residence_events[h].location and residence_events[h].getattr("latlon") is not None:
                    midpoints.append(
                        LifeEvent(
                            residence_events[h].place,
                            residence_events[h].date.year_num,
                            residence_events[h].getattr("latlon"),
                            residence_events[h].what,
                        )
                    )
                    wyear = wyear if wyear else residence_events[h].date.year_num

        line = Line(
            f"{path:8}\t{current.name}",
            birth_latlon,
            death_latlon,
            self.rainbow.get(color),
            path,
            branch,
            prof,
            "Life",
            None,
            midpoints,
            current,
            whenFrom=birth_year_num,
            whenTo=death_year_num,
        )

        return [line]

    # Draw a line from the parents birth to the child birth location

    def line(
        self,
        latlon: LatLon,
        parent: Person,
        branch,
        prof,
        miss,
        path="",
        linestyle="",
        forperson: Person = None,
        visited=None,
    ) -> list[Line]:
        # Track visited IDs in this specific line to detect sequential loops only
        if visited is None:
            visited = set()

        if parent.xref_id in visited:
            _log.warning(
                "Loop detected in ancestry trace: {:2} - {} {} - Path: {}".format(
                    prof, parent.name, parent.xref_id, path
                )
            )
            return []

        if getattr(parent, "birth", None):
            color = (branch + DELTA / 2) / (SPACE**prof)
            _log.debug(
                "{:8} {:8} {:2} {:.10f} {} {:20} from {:20}".format(
                    path, branch, prof, color, self.rainbow.get(color).to_hexa(), parent.name, forperson.name
                )
            )

            parent_birth = parent.get_event("birth") if parent else None
            parent_birth_latlon = parent_birth.getattr("latlon") if parent_birth else None
            parent_birth_year = parent_birth.getattr("when_year_num") if parent_birth else None

            parent_death = parent.get_event("death") if parent else None
            parent_death_year = parent_death.getattr("when_year_num") if parent_death else None

            line = Line(
                f"{path:8}\t{parent.name}",
                latlon,
                parent_birth_latlon,
                self.rainbow.get(color),
                path,
                branch,
                prof,
                linestyle,
                forperson,
                person=parent,
                whenFrom=parent_birth_year,
                whenTo=parent_death_year,
            )
            return self.link(parent_birth_latlon, parent, branch, prof, 0, path, visited) + [line]
        else:
            if self.max_missing != 0 and miss >= self.max_missing:
                _log.debug("{:8} {:8} {:2} {:.10f} {} Self {:20}".format(" ", " ", " ", 0, "-STOP-", parent.name))
                return []
            return self.link(latlon, parent, branch, prof, miss + 1, path, visited)

    def link(self, latlon: LatLon, current: Person, branch=0, prof=0, miss=0, path="", visited=None) -> list[Line]:
        # Track progress for GUI updates
        self._line_call_count += 1
        if self.svc_progress and self._line_call_count % 100 == 0:
            self.svc_progress.state = f"Creating lifetime lines: {self._line_call_count:,} paths processed"

        # Maximum recursion depth.  This should never happen
        if visited is None:
            visited = set()

        if prof < 480:
            return (
                (self.selfline(current, branch * SPACE, prof + 1, miss, path, visited))
                + (
                    self.line(
                        latlon,
                        self.people[current.father],
                        branch * SPACE,
                        prof + 1,
                        miss,
                        path + "F",
                        "father",
                        current,
                        visited,
                    )
                    if current.father
                    else []
                )
                + (
                    self.line(
                        latlon,
                        self.people[current.mother],
                        branch * SPACE + DELTA,
                        prof + 1,
                        miss,
                        path + "M",
                        "mother",
                        current,
                        visited,
                    )
                    if current.mother
                    else []
                )
            )
        else:
            _log.warning("{:8} {:8} {:2} {} {} {:20}".format(" ", " ", prof, " ", "-TOO DEEP-", current.name))
            return (self.selfline(current, branch * SPACE, prof + 1, miss, path, visited)) + [] + []

    def create(self, main_id: str):
        self._line_call_count = 0  # Reset counter for each traversal
        if main_id not in self.people.keys():
            _log.error("Could not find your starting person: %s", main_id)
            raise IndexError(f"Missing starting person {main_id}")
        current_person = self.people[main_id]
        birth_event = current_person.get_event("birth") if current_person else None
        birth_latlon = birth_event.getattr("latlon") if birth_event else None

        return self.link(birth_latlon, current_person)

    def createothers(self, listof):
        """Add Line objects for all people not already in listof.

        WARNING: This method iterates through ALL people in the dataset, which can be
        extremely slow for large datasets (10,000+ people). Consider disabling
        AllEntities option for large files.

        Args:
            listof: List of Line objects to extend with additional people
        """
        total_people = len(self.people)
        processed = 0
        added = 0

        _log.info(f"createothers: Processing {total_people:,} people (current list has {len(listof):,} entries)")

        for person in self.people:
            processed += 1

            # Progress logging every 1000 people
            if processed % 1000 == 0:
                percent = 100 * processed // total_people
                _log.info(
                    f"createothers: Processed {processed:,}/{total_people:,} people "
                    f"({percent}%), added {added:,} so far"
                )

            c = [creates.person.xref_id for creates in listof]
            if person not in c:
                _log.debug("Others: + %s(%s) (%d)", self.people[person].name, person, len(listof))
                lines = self.selfline(self.people[person], len(listof) / 10, len(listof) / 10, 5, path="")
                if lines:
                    listof.extend(lines)
                    added += len(lines)

        _log.info(
            f"createothers: Completed. Processed {processed:,} people, added {added:,} new entries. Total list size: {len(listof):,}"
        )
