"""
GVState: Implements IState (runtime state) for gedcom-to-visualmap.

This module provides the concrete implementation of the IState Protocol,
managing mutable runtime state during application execution.
"""
import os
from typing import Union, Dict, Optional, Any, Tuple
import time
from geo_gedcom.person import Person
from services.interfaces import IState


class GVState(IState):
    """Runtime state service for gedcom-to-visualmap.
    
    Manages mutable application state including parsed GEDCOM data,
    geocoding services, main person selection, and lineage tracking.
    
    Attributes:
        people: Dictionary of Person objects keyed by xref ID
        lookup: GeolocatedGedcom instance for geocoding operations
        mainPerson: Currently selected main/root person
        Name: Name of the main person (or "<not selected>")
        Referenced: Set of referenced person IDs
        selectedpeople: Count of people in current selection
        lastlines: Cached line data for rendering
        heritage: Cached heritage/ancestry data
        time: Timestamp of state creation
        timeframe: Date range {'from': year, 'to': year} for timeline
        totalpeople: Total count of people in dataset
        mainPersonLatLon: GPS coordinates of main person's primary location
        parsed: Flag indicating whether GEDCOM has been successfully parsed
        newload: Flag indicating a new GEDCOM file has been loaded
        runavg: Running average list for ETA calculation (used by GUI progress display)
    """
    
    def __init__(self) -> None:
        """Initialize runtime state with default values."""
        self.people: Optional[Dict[str, Person]] = None
        self.lookup: Any = None  # GeolocatedGedcom instance
        self.mainPerson: Optional[Person] = None
        self.Name: Optional[str] = None
        self.Referenced: Any = None
        self.selectedpeople: int = 0
        self.lastlines: Any = None
        self.heritage: Any = None
        self.time: str = time.ctime()
        self.timeframe: Dict[str, Optional[int]] = {'from': None, 'to': None}
        self.totalpeople: int = 0
        self.mainPersonLatLon: Optional[Tuple[float, float]] = None
        self.parsed: bool = False
        self.newload: bool = False
        self.runavg: list = []  # Running average for ETA calculation

    def resettimeframe(self) -> None:
        """Reset the timeframe to empty state (no date range)."""
        self.timeframe = {'from': None, 'to': None}

    def addtimereference(self, timeReference: Any) -> None:
        """Add a time reference to expand the timeframe range.
        
        Updates the timeframe to include the year from the given time reference.
        Expands the range to include earlier 'from' dates and later 'to' dates.
        
        Args:
            timeReference: Object with year_num attribute (typically GedcomDate).
                          Ignored if None or missing year_num.
        
        Example:
            event1 = GedcomDate(year=1950)
            event2 = GedcomDate(year=2000)
            state.addtimereference(event1)  # timeframe: {from: 1950, to: 1950}
            state.addtimereference(event2)  # timeframe: {from: 1950, to: 2000}
        """
        if not timeReference:
            return
        theyear = getattr(timeReference, 'year_num', None)
        if theyear is None:
            return
        if not hasattr(self, 'timeframe') or self.timeframe is None:
            self.timeframe = {'from': None, 'to': None}
        if self.timeframe['from'] is None:
            self.timeframe['from'] = theyear
        else:
            if theyear < self.timeframe['from']:
                self.timeframe['from'] = theyear
        if self.timeframe['to'] is None:
            self.timeframe['to'] = theyear
        else:
            if theyear > self.timeframe['to']:
                self.timeframe['to'] = theyear

    def setMain(self, Main: str) -> None:
        """Set the main person by ID and update related state.
        
        Looks up the person by ID, updates main person reference, and
        resets lineage tracking data if the main person has changed.
        
        Args:
            Main: Person ID (xref string) to set as main person.
                 If ID not found in people dict, sets default "<not selected>".
        
        Side Effects:
            - Sets self.Main to the provided ID
            - Sets self.mainPerson to Person object (or None if not found)
            - Sets self.Name to person's name (or "<not selected>")
            - Sets self.mainPersonLatLon to person's primary coordinates (if available)
            - Resets lineage tracking (selectedpeople, lastlines, heritage, Referenced)
              only if the main person actually changed
        
        Example:
            state.people = {'P1': person1, 'P2': person2}
            state.setMain('P1')  # Sets person1 as main, resets lineage
            state.setMain('P1')  # Same person, no reset
            state.setMain('P2')  # Different person, resets lineage
        """
        self.Main = Main
        
        # Look up the person object
        mainperson = None
        if self.people and Main in self.people:
            mainperson = self.people[Main]
        
        # Check if this is actually a new main person
        newMain = (self.mainPerson != mainperson and mainperson and self.Name != getattr(mainperson, 'name', None)) or mainperson is None
        self.mainPerson = mainperson
        
        # Update related state
        if mainperson:
            self.Name = mainperson.name
            if hasattr(mainperson, 'bestLatLon'):
                self.mainPersonLatLon = mainperson.bestLatLon()
            else:
                self.mainPersonLatLon = None
        else:
            self.Name = "<not selected>"
            self.mainPersonLatLon = None
        
        # Reset lineage tracking if main person changed
        if newMain:
            self.selectedpeople = 0
            self.lastlines = None
            self.heritage = None
            self.Referenced = None
