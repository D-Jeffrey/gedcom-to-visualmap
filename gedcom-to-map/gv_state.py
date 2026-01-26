"""
GVState: Implements IState (runtime state) for gedcom-to-visualmap.
"""
import os
from typing import Union, Dict, Optional
import time
from geo_gedcom.person import Person
from services import IState

class GVState(IState):
    """Runtime state service for gedcom-to-visualmap."""
    def __init__(self):
        self.people: Union[Dict[str, Person], None] = None
        self.mainPerson: Optional[Person] = None
        self.Name: Optional[str] = None
        self.Referenced = None
        self.selectedpeople = 0
        self.lastlines = None
        self.heritage = None
        self.time = time.ctime()
        self.timeframe = {'from': None, 'to': None}
        self.totalpeople = 0
        self.mainPersonLatLon = None
        self.parsed = False

    def resettimeframe(self) -> None:
        self.timeframe = {'from': None, 'to': None}

    def addtimereference(self, timeReference) -> None:
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

    def setMainPerson(self, mainperson: Person) -> None:
        newMain = (self.mainPerson != mainperson and mainperson and self.Name != getattr(mainperson, 'name', None)) or mainperson is None
        self.mainPerson = mainperson
        if mainperson:
            self.Name = mainperson.name
            if hasattr(mainperson, 'bestLatLon'):
                self.mainPersonLatLon = mainperson.bestLatLon()
            else:
                self.mainPersonLatLon = None
        else:
            self.Name = "<not selected>"
            self.mainPersonLatLon = None
        if newMain:
            self.selectedpeople = 0
            self.lastlines = None
            self.heritage = None
            self.Referenced = None

    def setMain(self, Main: str) -> None:
        self.Main = Main
        if self.people and Main in self.people:
            self.setMainPerson(self.people[Main])
        else:
            self.setMainPerson(None)

    def get(self, attribute: str, default=None, ifNone=None):
        if attribute == 'resultpath':
            if getattr(self, 'GEDCOMinput', None):
                ged_dir = os.path.dirname(self.GEDCOMinput)
                return ged_dir if ged_dir else default
            val = getattr(self, attribute, None)
            return val if val else default
        if ifNone is not None:
            val = getattr(self, attribute, default)
            if val == None:
                return ifNone
        return getattr(self, attribute, default)

    def set(self, attribute: str, value) -> None:
        if not hasattr(self, attribute):
            raise ValueError(f'attempting to set an attribute : {attribute} which does not exist')
        if attribute == "Main":
            self.setMain(value)
        else:
            setattr(self, attribute, value)
