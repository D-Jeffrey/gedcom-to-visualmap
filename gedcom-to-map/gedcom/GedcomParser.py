from typing import Dict
from datetime import datetime

from ged4py import GedcomReader
from ged4py.model import Record, NameRec
from ged4py.date import DateValueVisitor

from models.Human import Human, LifeEvent
from models.Pos import Pos

homelocationtags = ('OCCU', 'CENS', 'EDUC')
otherlocationtags = ('CHR', 'BAPM', 'BASM', 'BAPL', 'MARR', 'IMMI', 'NATU', 'ORDN','ORDI''RETI', 
                     'EVEN',  'CEME', 'CREM' )

addrtags = ('ADR1', 'ADR2', 'ADR3', 'CITY', 'STAE', 'POST', 'CTRY')

def getgdate (str):
    r = datetime.fromisocalendar(1000,1,1)
    d = m = y = None
    if str:
        k = str.value.kind.name
        if (k == 'SIMPLE') or (k == 'ABOUT') or (k == 'FROM'):
            y = str.value.date.year
            m = str.value.date.month_num
            d = str.value.date.day
        elif (k == 'RANGE') or(k ==  'PERIOD'):
            y = str.value.date1.year
            m = str.value.date1.month_num
            d = str.value.date1.day

        elif (k == 'PHRASE'):
           y = y 
            #TODO need to fix up
        else:
            print ("Date type; {}".format(str.value.kind.name))
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


class GedcomParser:
    def __init__(self, file_name):
        self.file_path = file_name

    @staticmethod
    def __create_human(record: Record) -> Human:
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
            human.name = "Unknown"
        
        # Grab a link to the photo
        obj = record.sub_tag("OBJE")
        human.photo = None
        if (obj):
            isjpg = obj.sub_tag("FORM") and obj.sub_tag("FORM").value == 'jpg'
            if (isjpg):
                human.photo = obj.sub_tag("FILE").value
        human.sex = record.sex
        birt = record.sub_tag("BIRT")
        if birt:
            human.birth = LifeEvent(getplace(birt), birt.sub_tag("DATE"))
            plac = getplace(birt)
            plactag = birt.sub_tag("PLAC")
            if plactag:
                map = plactag.sub_tag("MAP")
                if map:
                    lat = map.sub_tag("LATI")
                    lon = map.sub_tag("LONG")
                    if lat and lon:
                        human.pos = Pos(lat.value,lon.value)
                        human.birth.pos = Pos(lat.value,lon.value)
        # Use the Burial Tag as a backup for the Death attributes
        buri = record.sub_tag("BURI")
        buri = LifeEvent(getplace(buri), buri.sub_tag("DATE")) if buri else LifeEvent(None, None)
        death = record.sub_tag("DEAT")
        if death:
            plac = getplace(death)
            pdate = death.sub_tag("DATE")
            human.death = LifeEvent(plac if plac else buri.where, pdate if pdate else buri.when)
            plactag = death.sub_tag("PLAC")
            if plactag:
                map = plactag.sub_tag("MAP")
                if map:
                    lat = map.sub_tag("LATI")
                    lon = map.sub_tag("LONG")
                    if lat and lon:
                        human.pos = Pos(lat.value,lon.value)
                        human.death.pos = Pos(lat.value,lon.value)
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
                        hdate = getgdate(hom.sub_tag("DATE"))
                        #if hdate in homes:
                        #    print (f"**Double RESI location for : {human.name} on {hdate} @ {alladdr}")
                        homes[hdate] = LifeEvent(alladdr, hom.sub_tag("DATE"))
        for tags in (homelocationtags):
            allhomes=record.sub_tags(tags)
            if allhomes:
                for hom in (allhomes):
                    # If we don't have an address it is of no use
                    plac = getplace(hom)
                    if plac: 
                        hdate = getgdate(hom.sub_tag("DATE"))
                        homes[hdate] = LifeEvent(plac, hom.sub_tag("DATE"), what='home')
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
                        hdate = getgdate(hom.sub_tag("DATE"))
                        homes[hdate] = LifeEvent(plac, hom.sub_tag("DATE"), what=otherwhat)
                    
                    
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
        humans = dict()
        for record in records0("INDI"):
            humans[record.xref_id] = GedcomParser.__create_human(record)
        for record in records0("FAM"):
            husband = record.sub_tag("HUSB")
            wife = record.sub_tag("WIFE")
            for chil in record.sub_tags("CHIL"):
                if chil.xref_id not in humans.keys():
                    continue
                if husband:
                    humans[chil.xref_id].father = husband.xref_id
                if wife:
                    humans[chil.xref_id].mother = wife.xref_id

        return humans

    def create_humans(self) -> Dict[str, Human]:
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
