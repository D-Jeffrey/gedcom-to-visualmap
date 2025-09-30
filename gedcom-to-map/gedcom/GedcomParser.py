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
        self.pos = LatLon(None, None)
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
                        self.pos = LatLon(lat.value,lon.value)
                    else: 
                        lat = maploc.sub_tag("_LATI")
                        lon = maploc.sub_tag("_LONG")
                        if lat and lon:
                            self.pos = LatLon(lat.value,lon.value)
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
                                self.pos = LatLon(float(lat),float(lon))
            self.event = LifeEvent(self.place, self.when, self.pos, tag)
            

class GedcomParser:
    def __init__(self, gOp :gvOptions):
        self.file_path = gOp.GEDCOMinput
        self.gOp = gOp
        gOp.totalGEDpeople = None
        gOp.totalGEDfamily = None
        gOp.timeframe = [None,None]
        global thisgvOps
        thisgvOps= gOp
        if self.file_path == '':
            self.gOp.stopstep("no file to Parse")
        else:
            fpath = Path(self.file_path)
            if fpath.is_file():
                self.gOp.step("GEDCOM Parsing")
            else:
                self.gOp.stopstep("file does not exist")
                _log.warning ("File %s does not exist to read.", self.file_path)

            
        self.gOp.parsed = False


    @staticmethod
    def __create_person(record: Record) -> Person:
        global thisgvOps
        thisgvOps.step()
        person = Person(record.xref_id)
        person.name = ''
        name: NameRec = record.sub_tag("NAME")
        _log.debug (f"Create Person : {name}")
        if name:
            person.first = record.name.first
            person.surname =record.name.surname
            person.maiden = record.name.maiden
            person.name = "{}".format(record.name.format())
            # person.name = "{} {}".format(name.value[0], name.value[1])
        if person.name == '':
            person.first = "Unknown"
            person.surname = "Unknown"
            person.maiden = "Unknown"
        
        title = record.sub_tag("TITL")
        person.title = title.value if title else ""

        # Grab a link to the photo
        obj = record.sub_tag("OBJE")
        person.photo = None
        if (obj):
            if obj.sub_tag("FILE"):
                # Depending on how the GEDCOM was created the FORM maybe at 2 or 3 it may be in a sub tag and it may or may not have the right extension
                if obj.sub_tag("_PRIM") and obj.sub_tag("_PRIM") == 'N':
                    # skip non primary photos
                    pass
                else:
                    ext = obj.sub_tag("FILE").value.lower().split('.')[-1]
                    if ext in ('jpg','bmp','jpeg','png','gif'):
                        person.photo = obj.sub_tag("FILE").value
                    else:
                        form = obj.sub_tag("FORM")
                        if form and obj.sub_tag("FORM").value.lower() in ('jpg','bmp','jpeg','png','gif'):
                            person.photo = obj.sub_tag("FILE").value
                        else:
                            form = obj.sub_tag("FILE").sub_tag("FORM")
                            if form and form.value.lower() in ('jpg','bmp','jpeg','png','gif'):
                                person.photo = obj.sub_tag("FILE").value 
        person.sex = record.sex
        # BIRTH TAG
        birthtag = GetPosFromTag(record, "BIRT")
        person.birth = birthtag.event
        # Build a time range 
        if thisgvOps.timeframe[0]:
            if person.birth and person.birth.whenyearnum() and person.birth.whenyearnum() < thisgvOps.timeframe[0]:
                thisgvOps.timeframe[0] = person.birth.whenyearnum()
        else:
            thisgvOps.timeframe[0] = person.birth.whenyearnum()
        person.pos = birthtag.pos
        
        # Use the Burial Tag as a backup for the Death attributes
        # TODO need to code this as backup
        burialtag = GetPosFromTag(record, "BURI")

        # DEATH TAG
        deathtag = record.sub_tag("DEAT")
        if deathtag:
            deathtagAge = deathtag.sub_tag_value("AGE")
            deathtagCause = deathtag.sub_tag_value("CAUS")
            if deathtagAge:
                person.age = deathtagAge
                if deathtagCause: person.age = f"{deathtagAge} of {deathtagCause}"
        deathtagPos = GetPosFromTag(record, "DEAT")
        person.death = deathtagPos.event 
        if thisgvOps.timeframe[1]:
            if person.death and person.death.whenyearnum() and person.death.whenyearnum() > thisgvOps.timeframe[0]:
                thisgvOps.timeframe[1] = person.death.whenyearnum()
        else:
            thisgvOps.timeframe[1] = person.death.whenyearnum()
        
        
        # Last Possible is death (or birth)
        if person.death and LatLon.hasLocation(person.death.pos):
            person.pos = person.death.pos
        
        homes = {}
        allhomes=record.sub_tags("RESI")
        if allhomes:
            for hom in (allhomes):
                alladdr = ''
                homadr = hom.sub_tag("ADDR")
                if homadr:
                    for adr in (addrtags):
                        addrval = homadr.sub_tag(adr)
                        alladdr = alladdr + " " + addrval.value if addrval else alladdr
                    # If we don't have an address it is of no use
                    alladdr = alladdr.strip()
                    if alladdr != '':
                        homedate = getgdate(hom.sub_tag("DATE"))
                        if homedate in homes:
                            _log.debug ("**Double RESI location for : %s on %s @ %s", person.name, homedate , alladdr)
                        homes[homedate] = LifeEvent(alladdr, hom.sub_tag("DATE"))
        for tags in (homelocationtags):
            allhomes=record.sub_tags(tags)
            if allhomes:
                for hom in (allhomes):
                    # If we don't have an address it is of no use
                    plac = getplace(hom)
                    if plac: 
                        homedate = getgdate(hom.sub_tag("DATE"))
                        homes[homedate] = LifeEvent(plac, hom.sub_tag("DATE"), what='home')
        for tags in (otherlocationtags):
            allhomes=record.sub_tags(tags)
            if allhomes:
                for hom in (allhomes):
                    # If we don't have an address it is of no use
                    plac = getplace(hom)
                    if plac:
                        otherwhat = tags
                        otherstype = hom.sub_tag("TYPE")
                        if otherstype:
                            otherwhat = otherstype.value
                        homedate = getgdate(hom.sub_tag("DATE"))
                        homes[homedate] = LifeEvent(plac, hom.sub_tag("DATE"), what=otherwhat)
                    
                    
        # Sort them by year          
        if (homes):
            for i in sorted (homes.keys()) :
                if person.home:
                    person.home.append(homes[i])
                else:
                    person.home = [homes[i]]

        # bits = ""
        # for tags in (bitstags):
        #     bitstag=record.sub_tags(tags)
        #     if bitstag:
        #         for hom in (allhomes):
        #             plac = getplace(hom)
        #             if plac:
        #                 otherwhat = tags
        #                 otherstype = hom.sub_tag("TYPE")
        #                 if otherstype:
        #                     otherwhat = otherstype.value
        #                 homedate = getgdate(hom.sub_tag("DATE"))
        #                 homes[homedate] = LifeEvent(plac, hom.sub_tag("DATE"), what=otherwhat)
                    



        return person

    @staticmethod
    def __create_people(records0) -> Dict[str, Person]:
        global thisgvOps
        people : Dict[str, Person] = dict()
        thisgvOps.step("Reading GED", target=(thisgvOps.totalGEDpeople+thisgvOps.totalGEDfamily))
        for record in records0("INDI"):
            if thisgvOps.ShouldStop():
                break
            people[record.xref_id] = GedcomParser.__create_person(record)
        familyloop = 0
        for record in records0("FAM"):
            if thisgvOps.ShouldStop():
                break
            familyloop += 1
            if familyloop % 15 == 0:
                thisgvOps.step(info=f"Family loop {familyloop}", plusStep=15)  
            husband = record.sub_tag("HUSB")
            wife = record.sub_tag("WIFE")
            for marry in record.sub_tags("MARR"):
                marryevent = GetPosFromTag(marry, None).event
                if husband and wife:
                    if people[husband.xref_id].marriage:
                        people[husband.xref_id].marriage.append((wife.xref_id, marryevent))
                    else:
                        people[husband.xref_id].marriage = [(wife.xref_id, marryevent)]
                    if people[wife.xref_id].marriage :
                        people[wife.xref_id].marriage.append((husband.xref_id, marryevent))
                    else:
                        people[wife.xref_id].marriage = [(husband.xref_id, marryevent)]
            if husband:
                if people[husband.xref_id].name == "Unknown":
                    people[husband.xref_id].name = "Unknown [Father]"
            if wife:
                if people[wife.xref_id].name == "Unknown":
                    people[wife.xref_id].name = "Unknown [Mother]"
            
            for chil in record.sub_tags("CHIL"):
                if chil:
                    if chil.xref_id not in people.keys():
                        continue
                    if husband:
                        people[chil.xref_id].father = husband.xref_id
                        people[husband.xref_id].children.append(chil.xref_id)
                    if wife:
                        people[chil.xref_id].mother = wife.xref_id
                        people[wife.xref_id].children.append(chil.xref_id)
                else:
                    _log.warning("Family has missing INDI record for one of the CHIL: %s",  record.xref_id)
                
        return people

    def create_people(self) -> Dict[str, Person]:
        global thisgvOps
        if self.file_path == '':
            return None
        fpath = Path(self.file_path)
        if not fpath.is_file():
            return None
        # TODO Date formating is handled elsewhere so the following in not in effect
        # format_visitor = DateFormatter()


        with GedcomReader(self.file_path) as parser:
            thisgvOps.step("Loading GED")
            try:
                thisgvOps.totalGEDpeople = sum(1 for value in parser.xref0.values() if value[1] == 'INDI')
            except Exception as e:
                _log.error("Error reading file %s", self.file_path)
                _log.error("Error %s", e)
                if self.gOp.BackgroundProcess:
                    mye = e.args[0].replace("'", "").replace("\"", "").replace("`", "").replace("<", "[").replace(">", "]")
                    self.gOp.BackgroundProcess.SayErrorMessage(f"Error {mye}", True)
                return None
            
            thisgvOps.totalGEDfamily = sum(1 for value in parser.xref0.values() if value[1] == 'FAM')
            return self.__create_people(parser.records0)
        






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
