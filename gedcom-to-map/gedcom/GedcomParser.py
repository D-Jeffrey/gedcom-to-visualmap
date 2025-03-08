__all__ = ['GedcomParser', 'DateFormatter']

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict

from ged4py import GedcomReader
from ged4py.date import DateValueVisitor
from ged4py.model import NameRec, Record
from gedcomoptions import gvOptions
from models.Human import Human, LifeEvent
from models.Pos import Pos

_log = logging.getLogger(__name__)

homelocationtags = ('OCCU', 'CENS', 'EDUC')
otherlocationtags = ('CHR', 'BAPM', 'BASM', 'BAPL', 'IMMI', 'NATU', 'ORDN','ORDI', 'RETI', 
                     'EVEN',  'CEME', 'CREM' )

addrtags = ('ADR1', 'ADR2', 'ADR3', 'CITY', 'STAE', 'POST', 'CTRY')

thisgvOps = None

def getgdate (gstr):
    r = datetime.fromisocalendar(1000,1,1)
    d = m = y = None
    if gstr:
        k = gstr.value.kind.name
        if (k == 'SIMPLE') or (k == 'ABOUT') or (k == 'FROM'):
            y = gstr.value.date.year
            m = gstr.value.date.month_num
            d = gstr.value.date.day
        elif (k == 'RANGE') or(k ==  'PERIOD'):
            y = gstr.value.date1.year
            m = gstr.value.date1.month_num
            d = gstr.value.date1.day

        elif (k == 'PHRASE'):
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

class GetPosFromTag: 
    """ build an LifeEvent, but also return the other attributes """
    def __init__(self, gedcomtag : Record, tag : str, placetag ="PLAC"):
        self.when = None
        self.place = None
        self.pos = Pos(None, None)
        self.event = None
        if tag:
            subtag = gedcomtag.sub_tag(tag)
        else:
            subtag = gedcomtag
        if subtag:
            self.place = getplace(subtag)
            self.when = subtag.sub_tag("DATE")
            plactag = subtag.sub_tag(placetag)
            if plactag:
                maploc = plactag.sub_tag("MAP")
                if maploc:
                    lat = maploc.sub_tag("LATI")
                    lon = maploc.sub_tag("LONG")
                    if lat and lon:
                        self.pos = Pos(lat.value,lon.value)
            self.event = LifeEvent(self.place, self.when, self.pos, tag)
            

class GedcomParser:
    def __init__(self, gOp :gvOptions):
        self.file_path = gOp.GEDCOMinput
        self.gOp = gOp
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
    def __create_human(record: Record) -> Human:
        global thisgvOps
        thisgvOps.step()
        human = Human(record.xref_id)
        human.name = ''
        name: NameRec = record.sub_tag("NAME")
        if name:
            human.first = record.name.first
            human.surname =record.name.surname
            human.maiden = record.name.maiden
            human.name = "{}".format(record.name.format())
            # human.name = "{} {}".format(name.value[0], name.value[1])
        if human.name == '':
            human.first = "Unknown"
            human.surname = "Unknown"
            human.maiden = "Unknown"
            8
        
        # Grab a link to the photo
        obj = record.sub_tag("OBJE")
        human.photo = None
        if (obj):
            isjpg = obj.sub_tag("FORM") and obj.sub_tag("FORM").value == 'jpg'
            if (isjpg):
                human.photo = obj.sub_tag("FILE").value
        human.sex = record.sex
        # BIRTH TAG
        birthtag = GetPosFromTag(record, "BIRT")
        human.birth = birthtag.event
        human.pos = birthtag.pos
        
        # Use the Burial Tag as a backup for the Death attributes
        # TODO need to code this as backup
        burialtag = GetPosFromTag(record, "BURI")

        # DEATH TAG
        deathtag = GetPosFromTag(record, "DEAT")
        human.death = deathtag.event 
        
        # Last Possible is death (or birth)
        if human.death and Pos.hasLocation(human.death.pos):
            human.pos = human.death.pos
        
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
                            _log.debug ("**Double RESI location for : %s on %s @ %s", human.name, homedate , alladdr)
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
                if human.home:
                    human.home.append(homes[i])
                else:
                    human.home = [homes[i]]

        return human

    @staticmethod
    def __create_humans(records0) -> Dict[str, Human]:
        global thisgvOps
        humans = dict()
        for record in records0("INDI"):
            if thisgvOps.ShouldStop():
                break
            humans[record.xref_id] = GedcomParser.__create_human(record)
        familyloop = 0
        for record in records0("FAM"):
            if thisgvOps.ShouldStop():
                break
            familyloop += 1
            if familyloop % 15 == 0:
                thisgvOps.step(info=f"Family loop {familyloop}")  
            husband = record.sub_tag("HUSB")
            wife = record.sub_tag("WIFE")
            for marry in record.sub_tags("MARR"):
                marryevent = GetPosFromTag(marry, None).event
                if husband and wife:
                    if humans[husband.xref_id].marriage:
                        humans[husband.xref_id].marriage.append((wife.xref_id, marryevent))
                    else:
                        humans[husband.xref_id].marriage = [(wife.xref_id, marryevent)]
                    if humans[wife.xref_id].marriage :
                        humans[wife.xref_id].marriage.append((husband.xref_id, marryevent))
                    else:
                        humans[wife.xref_id].marriage = [(husband.xref_id, marryevent)]
            if husband:
                if humans[husband.xref_id].name == "Unknown":
                    humans[husband.xref_id].name = "Unknown [Father]"
            if wife:
                if humans[wife.xref_id].name == "Unknown":
                    humans[wife.xref_id].name = "Unknown [Mother]"
            
            for chil in record.sub_tags("CHIL"):
                if chil.xref_id not in humans.keys():
                    continue
                if husband:
                    humans[chil.xref_id].father = husband.xref_id
                    
                if wife:
                    humans[chil.xref_id].mother = wife.xref_id
                    

                    
            
            

        return humans

    def create_humans(self) -> Dict[str, Human]:
        if self.file_path == '':
            return None
        fpath = Path(self.file_path)
        if not fpath.is_file():
            return None
        with GedcomReader(self.file_path) as parser:
            return self.__create_humans(parser.records0)
        






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
