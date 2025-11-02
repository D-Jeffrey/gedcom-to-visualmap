__all__ = ['GedcomParser', 'DateFormatter']

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Dict

from ged4py import GedcomReader
from ged4py.date import DateValueVisitor
from ged4py.model import NameRec, Record
from gedcomoptions import gvOptions
from models.Person import Person, LifeEvent
from models.LatLon import LatLon

_log = logging.getLogger(__name__.lower())

homelocationtags = ('OCCU', 'CENS', 'EDUC')
otherlocationtags = ('CHR', 'BAPM', 'BASM', 'BAPL', 'IMMI', 'NATU', 'ORDN','ORDI', 'RETI', 
                     'EVEN',  'CEME', 'CREM', 'FACT' )

bitstags = {"OCCU" : ("Occupation", True), "RELI" : ("Religion", True), "EDUC" : ("Education", True), 
            
            "TITL" : ("Title", True), "BAPM" : ("Baptism", False), "BASM" : ("Baptism", False), "BAPL" : ("Baptism", False),
            "NATU" : ("Naturalization", ("PLACE", "DATE")),  'BURI' : ('Burial', False), 'CREM' : ('Cremation', False) }
eventtags = {"EVEN" : "Event"}

addrtags = ('ADR1', 'ADR2', 'ADR3', 'CITY', 'STAE', 'POST', 'CTRY')

maxage = 122        # https://en.wikipedia.org/wiki/List_of_the_verified_oldest_people
maxmotherage = 66   # https://www.oldest.org/people/mothers/
maxfatherage = 93   # https://www.guinnessworldrecords.com/world-records/oldest-father-
minmother = 11
minfather = 12


thisgvOps = None

def getgdate (gstr):
    r = datetime.fromisocalendar(1000,1,1)
    d = m = y = None
    if gstr:
        k = gstr.value.kind.name
        if (k in ['SIMPLE', 'ABOUT','FROM']):
            y = gstr.value.date.year
            m = gstr.value.date.month_num
            d = gstr.value.date.day
        elif (k in ['AFTER','BEFORE']):
            y = gstr.value.date.year
            m = gstr.value.date.month_num
            d = gstr.value.date.day
        elif (k == 'RANGE') or(k ==  'PERIOD'):
            y = gstr.value.date1.year
            m = gstr.value.date1.month_num
            d = gstr.value.date1.day

        elif k == 'PHRASE':
            #TODO need to fix up
            y = y 
        else:
            _log.warning ("Date type; %s", gstr.value.kind.name)
        y = (y, 1000) [y == None]
        m = (m, 1) [m == None]
        d = (d, 1) [d == None]

        r = r.replace(y, m, d)
    return r

def getplace(gedcomtag : Record, placetag ="PLAC"):
    
    if gedcomtag:
        myplace = gedcomtag.sub_tag(placetag)
        return myplace.value if myplace else None

    return None

def CheckAge(people: Dict[str, Person], thisXrefID ):
    ""
    problems :list[str] = []
    if people[thisXrefID]:
        thisperson = people[thisXrefID]
        born = None
        died = None
        if thisperson.birth:
            born = thisperson.birth.whenyearnum()
        if thisperson.death:
            died = thisperson.death.whenyearnum()
        if born and died:
            if died < born:
                problems.append("Died before Born")
            if died - born > maxage:
                problems.append(f"Too old {died - born} > {maxage}")
        if thisperson.children:
            for childId in thisperson.children:
                if people[childId]:
                    child = people[childId]
                    if child.birth and child.birth.whenyearnum():
                        if born:
                            parentatage = child.birth.whenyearnum() - born
                            if thisperson.sex == "F":
                                if parentatage > maxmotherage:
                                    problems.append(f"Mother too old {parentatage} > {maxmotherage} for {child.name} [{child.xref_id}]")
                                if parentatage < minmother:
                                    problems.append(f"Mother too young {parentatage} < {minmother} for {child.name} [{child.xref_id}]")
                             
                                if died and died < parentatage:
                                    problems.append(f"Mother after death for {child.name} [{child.xref_id}]")
                            elif thisperson.sex == "M":
                                if parentatage > maxfatherage:
                                    problems.append(f"Father too old {parentatage} > {maxfatherage} for {child.name} [{child.xref_id}]")
                                if parentatage < minfather:
                                    problems.append(f"Father too young {parentatage} < {minfather} for {child.name} [{child.xref_id}]")

                                # Birth after father dies within a year
                                if died and died+1 < parentatage:    
                                    problems.append(f"Father after death for {child.name} [{child.xref_id}]")
                            else:
                                if parentatage > max(maxfatherage,maxmotherage):
                                    problems.append(f"Parent too old {parentatage} > {max(maxfatherage,maxmotherage)} for {child.name} [{child.xref_id}]")
                                if parentatage < min(minmother, minfather):
                                    problems.append(f"Parent too young {parentatage} < {min(maxfatherage,maxmotherage)} for {child.name} [{child.xref_id}]")

    return problems

class GetPosFromTag: 
    """ build an LifeEvent, but also return the other attributes """
    def __init__(self, gedcomtag : Record, tag : str, placetag ="PLAC"):
        self.when = None
        self.place = None
        self.latlon = LatLon(None, None)
        self.event = None
        if tag:
            subtag = gedcomtag.sub_tag(tag)
        else:
            subtag = gedcomtag
        if subtag:
            self.place = getplace(subtag)
            self.when = subtag.sub_tag("DATE")
            # Looking for:
            #   2 PLAC Our Lady of Calvary Cemetery, 134 Forest Street, Yarmouth, Yarmouth County, Nova Scotia, Canada
            #   3 MAP
            #   4 LATI 43.831944
            #   4 LONG -66.102222
            # --or--
            #   4 _LATI 43.831944
            #   4 _LONG -66.102222
            plactag = subtag.sub_tag(placetag)
            if plactag:
                maploc = plactag.sub_tag("MAP")
                if maploc:
                    lat = maploc.sub_tag("LATI")
                    lon = maploc.sub_tag("LONG")
                    if lat and lon:
                        self.latlon = LatLon(lat.value,lon.value)
                    else: 
                        lat = maploc.sub_tag("_LATI")
                        lon = maploc.sub_tag("_LONG")
                        if lat and lon:
                            self.latlon = LatLon(lat.value,lon.value)
                else:
                    if hasattr(plactag, 'value') : 
                        # Conderation for : 
                        # 2 PLAC Our Lady of Calvary Cemetery, 134 Forest Street, Yarmouth, Yarmouth County, Nova Scotia, Canada, , , 43.831944,-66.102222

                        # Regular expression pattern to match GPS coordinates at the end of the string
                        pattern = r"(.*?)(?:,\s*(-?\d+\.\d+),\s*(-?\d+\.\d+))?$"
                        match = re.match(pattern, plactag.value)

                        # Match the string using the pattern
                        if match:
                            # Extract the main location and optional GPS coordinates
                            self.place = match.group(1).strip()
                            lat = match.group(2)
                            lon = match.group(3)
                            if lat and lon:
                                self.latlon = LatLon(float(lat),float(lon))
            self.event = LifeEvent(self.place, self.when, self.latlon, tag)
            

class DateFormatter(DateValueVisitor):
    """Visitor class that produces string representation of dates.
    """
    def visitSimple(self, date):
        return f"{date.date}"
    def visitPeriod(self, date):
        return f"from {date.date1} to {date.date2}"
    def visitFrom(self, date):
        return f"from {date.date}"
    def visitTo(self, date):
        return f"to {date.date}"
    def visitRange(self, date):
        return f"between {date.date1} and {date.date2}"
    def visitBefore(self, date):
        return f"before {date.date}"
    def visitAfter(self, date):
        return f"after {date.date}"
    def visitAbout(self, date):
        return f"about {date.date}"
    def visitCalculated(self, date):
        return f"calculated {date.date}"
    def visitEstimated(self, date):
        return f"estimated {date.date}"
    def visitInterpreted(self, date):
        return f"interpreted {date.date} ({date.phrase})"
    def visitPhrase(self, date):
        return f"({date.phrase})"
