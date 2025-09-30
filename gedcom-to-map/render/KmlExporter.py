__all__ = ['KmlExporter']

import logging
import math
import os.path
import random
import re

import simplekml as simplekml
from gedcomoptions import gvOptions
from models.Line import Line
from models.LatLon import LatLon
from render.Referenced import Referenced

_log = logging.getLogger(__name__.lower())

                

class KmlExporter:
    def __init__(self, gOp: gvOptions):
        self.file_name = os.path.join(gOp.resultpath, gOp.Result)
        self.max_line_weight = gOp.MaxLineWeight
        self.kml = None
        self.gOp = gOp
        self.gOp.Referenced = Referenced()
        random.seed()
        self.driftOn = True
        self.gOp.totalpeople = 0
        self.styleA = None
        self.styleB = None
        self.styles = []
            

    def driftLatLon(self, l : LatLon):
        if not l or not self.driftOn:
            return l
        return ((float(l.lon)+(random.random() * 0.001) - 0.0005), float(l.lat)+(random.random() * 0.001) - 0.0005)
        
    def Done(self):
        alist = []
        glist = []
        self.gOp.step("Finalizing KML")
        # Fix up the links in the placemark
        for placemark in self.kml.features:
            if hasattr(placemark, 'description') and placemark.description:
                pattern = r'href=(#.*?);'
                for match in re.finditer(pattern, placemark.description):
                    tag = match.group(1)
                    if self.gOp.Referenced.exists(tag):
                        replacewith = 1 + int(self.gOp.Referenced.gettag(tag))
                        original = f"href={tag};"
                        replacement = f"href=#{replacewith};"
                        placemark.description = placemark.description.replace(original, replacement)
                        # glist.append(original+"->"+replacement)
                    else:
                        # remove the link
                        replaceit = r'(<a '+ f"href={tag};" + r'[^<]+>)([^>]+)(</a>)'
                        for ripout in re.findall(replaceit, placemark.description):
                            if ripout:
                                # alist.append(ripout[0])
                                placemark.description = placemark.description.replace(ripout[0]+ripout[1]+ripout[2], ripout[1])


        
        self.gOp.step("Saving KML")
        logging.info("Saved as %s", self.file_name)
        self.kml.save(self.file_name)
        # self.gOp.stop()
        # self.kml = None
    def export(self, main: LatLon, lines: list[Line], ntag ="", mark="native"):
        foldermode = self.gOp.KMLsort == 1
        # marker types are : 
        #           diamond, square, circle, blank, stars
        # colors are : 
        #           grn, ltblu, pink, blu, purple, red, wht, ylw
        if mark == 'death':
            marktype = "stars"
        elif mark == "born":
            marktype = "circle"
        else:
            marktype = "blank"
        colorA = "ylw"
        colorB = "ltblu"
        if self.kml:
            kml = self.kml
            
            styleA = self.styleA
            styleB = self.styleB     
        else:
            kml = simplekml.Kml()
            inputfile = os.path.basename(self.gOp.GEDCOMinput) if self.gOp.GEDCOMinput else "Unknown"
            descript = f"Family tree generated for using {inputfile}<br>{self.gOp.Name} ({self.gOp.Main}) as starting person"
            descript += f"<br>Marker types are {'Birth' if self.gOp.BornMark else ''} {'Death' if self.gOp.DieMark else ''}"
            kmloptions = []
            if self.gOp.MapTimeLine:
                kmloptions.append("Timeline enabled.")
            if self.gOp.UseBalloonFlyto:
                kmloptions.append("Balloon Flyto enabled.")
            if self.gOp.AllEntities:
                kmloptions.append("All people are included.")
            if kmloptions:
                descript += "<br>" + " ".join(kmloptions)
    #         myschema = kml.newschema(name='Life')
    #         myschema.newsimplefield(name='name', type='int', displayname='<![CDATA[Name]]')
    #         myschema.newsimplefield(name='birth', type='int', displayname='<![CDATA[Birth]]')
    #         myschema.newsimplefield(name='death', type='int', displayname='<![CDATA[Death]]')
    #         myschema.newsimplefield(name='birthplace', type='int', displayname='<![CDATA[Born :]]')
    #         myschema.newsimplefield(name='deathplace', type='int', displayname='<![CDATA[Died :]]')
    #         myschema.newsimplefield(name='father', type='string', displayname='<![CDATA[Father :]]')
    #         myschema.newsimplefield(name='mother', type='string', displayname='<![CDATA[Mother :]]')
    #         myschema.newsimplefield(name='children', type='string', displayname='<![CDATA[Children :]]')
    #         "string"
    #         self.styles = simplekml.BalloonStyle()
    #         self.styles.text = """
    # <![CDATA[
    #     <h2> $[Life/name/displayName]$[Life/name] Born</h2>`n<br />
    #     </br>Born $[Life/birth] - $[Life/death]</br>
    #     </br>$[Life/birthplace/displayName]$[Life/birthplace]</br>
    #     <br />
    #     Parents: 
    #     <br>$[Life/father/displayName]$[Life/father]</br>
    #     <br>$[Life/mother/displayName]$[Life/mother]</br>
    #     <br />
    #     <br>$[Life/children/displayName]$[Life/children]</br>
    # ]]>"""
            
            
            kmldoc = kml.newdocument(name='About Geomap KML', description=descript)

            self.kml = kml
            if foldermode:
                self.folderBirth = kml.newfolder(name="Births")
                # self.folderMarriage = kml.newfolder(name="Marriages")
                self.folderDeath = kml.newfolder(name="Deaths")
                # self.folderParents = kml.newfolder(name="Parents")
                self.folderLife = kml.newfolder(name="Lifelines")
                
            
            styleA = simplekml.Style()
            # styleA.labelstyle.color = simplekml.Color.blue  # Make the text blue
            # styleA.labelstyle.scale = 1  # Make the text twice as big
            styleA.iconstyle.icon.href = f'https://maps.google.com/mapfiles/kml/paddle/{colorA}-{marktype}.png'
                      #   https://kml4earth.appspot.com/icons.html
            styleB = simplekml.Style()
            # styleB.labelstyle.color = simplekml.Color.pink  # Make the text pink
            styleB.labelstyle.scale = 1  # Make the text twice as big
            # styleB.iconstyle.icon.href = f'https://maps.google.com/mapfiles/kml/paddle/{colorB}-{marktype}.png'        #   https://kml4earth.appspot.com/icons.html
            self.styleA = styleA
            self.styleB = styleB
            
        if main and main.lon and main.lat:
            _log.error (f"No GPS locations to generate a map for main person for {ntag}.")
        if not lines or len(lines)==0:
            _log.error (f"No GPS locations to generate any person for {ntag}.")

        
        self.gOp.step("Generating KML")
        sorted_lines = sorted(lines, key=lambda x: x.prof)
        for line in sorted_lines :
            self.gOp.step()
            (desend, name) = line.name.split("\t")
            linage = ""
            timeA = line.whenFrom if hasattr(line, 'whenFrom') and line.whenFrom else None
            timeB = line.whenTo if hasattr(line, 'whenTo') and line.whenTo else None
            
            if line.person.father:
                if self.gOp.UseBalloonFlyto:
                    linage += '<br>Father: <a href=#{};balloonFlyto>{}</a></br>'.format(line.person.father[1:-1],self.gOp.people[line.person.father].name)    
                else:
                    linage += '<br>Father: {}</br>'.format(self.gOp.people[line.person.father].name)
            if line.person.mother:
                if self.gOp.UseBalloonFlyto:
                    linage += '<br>Mother: <a href=#{};balloonFlyto>{}</a></br>'.format(line.person.mother[1:-1],self.gOp.people[line.person.mother].name)
                else:
                    linage += '<br>Mother: {}</br>'.format(self.gOp.people[line.person.mother].name)
            family = []
            familyLinage = ""
            thisparent = line.person.xref_id

            for c in self.gOp.people:
                if self.gOp.people[c].father == thisparent or self.gOp.people[c].mother == thisparent:
                    family.append(c)
            if family:
                if self.gOp.UseBalloonFlyto:
                    # Format each child as a clickable link
                    family_links = [
                        f'<a href=#{child[1:-1]};balloonFlyto>{self.gOp.people[child].name}</a>'
                        for child in family
                    ]
                    familyLinage = '<br>Children: {}</br>'.format(", ".join(family_links))
                else:
                    family_names = [self.gOp.people[child].name for child in family]
                    familyLinage = '<br>Children: {}</br>'.format(", ".join(family_names))

            

            if timeA and timeB:
                event = f"{timeA} - {timeB}"
            elif timeB:
                event = f"Death: {timeB}"
            elif timeA:
                event = f"Born: {timeA}"
            else:
                event = "Unknown dates"
            event = f"<br>{event}</br>"
                
            if line.a.hasLocation() and mark in ['birth']:
                connectWhere = self.folderBirth if foldermode else kml
                pnt = connectWhere.newpoint(name=name + ntag, coords=[self.driftLatLon(line.a)], description="<![CDATA[ " + event + linage + familyLinage + " ]]>")
                self.gOp.Referenced.add(line.person.xref_id, 'kml-a',tag=pnt.id)
                self.gOp.Referenced.add("#"+line.person.xref_id[1:-1], tag=pnt.id)
                if self.gOp.MapTimeLine and hasattr(line, 'whenFrom') and line.whenFrom: 
                    pnt.timestamp.when = line.whenFrom
            
                pnt.style = simplekml.Style()
                pnt.style.labelstyle.scale = styleA.labelstyle.scale
                pnt.style.iconstyle.icon.href = styleA.iconstyle.icon.href

                # pnt.style.balloonstyle = simplekml.BalloonStyle()
                # pnt.style.balloonstyle.text = linage

                
            if line.b.hasLocation() and mark in ['death']:
                connectWhere = self.folderDeath if foldermode else kml
                pnt = connectWhere.newpoint(name=name + ntag, coords=[self.driftLatLon(line.b)], description="<![CDATA[ " + event + linage  + familyLinage + " ]]>")

                self.gOp.Referenced.add(line.person.xref_id, 'kml-b')
                self.gOp.Referenced.add("#"+line.person.xref_id[1:-1], tag=pnt.id)
                self.gOp.totalpeople += 1
                if self.gOp.MapTimeLine and hasattr(line, 'whenTo') and line.whenTo: 
                    pnt.timestamp.when = line.whenTo
                # 
                pnt.style = simplekml.Style()
                pnt.style.labelstyle.scale = styleB.labelstyle.scale
                pnt.style.iconstyle.icon.href = styleB.iconstyle.icon.href

                
                # pnt.style.balloonstyle = simplekml.BalloonStyle()
                # pnt.style.balloonstyle.text = linage 
                
            if line.a.hasLocation() and line.b.hasLocation():
                # Put the life span description in the line
                event  = "<br>Lifespan: {} to {}, related as {}</br>".format(timeA if timeA else "Unknown", timeB if timeB else "Unknown", desend) 
                connectWhere = self.folderLife if foldermode else kml
                kml_line = connectWhere.newlinestring(name=name, description="<![CDATA[ " + event + linage + familyLinage + " ]]>", coords=[self.driftLatLon(line.a), self.driftLatLon(line.b)])
                kml_line.linestyle.color = line.color.to_hexa()
                # - exponential decay function for the line width - Protect the exp from overflow for very long linages because the line is in pixels
                kml_line.linestyle.width = max( int(self.max_line_weight/math.exp(0.5*min(line.prof,100))), .1 )
                kml_line.extrude = 1                                                # This makes the line drop to the ground
                kml_line.tessellate = 1                                             # This makes the line follow the terrain
                kml_line.altitudemode = simplekml.AltitudeMode.clamptoground        # Alternate is relativetoground
                # kml_line.altitude = random.randrange(1,5)                           # This helps to seperate lines in 3d space
                # Used for timerange spanning/filtering in Google Earth Pro or ArcGIS
                if self.gOp.MapTimeLine: 
                    if timeA and timeB: 
                        kml_line.timespan.begin = timeA                                 
                        kml_line.timespan.end = timeB
                    elif timeA:
                        # If we only know when the birth or death then us a point in time
                        kml_line.timestamp.when = timeA                       
                    elif timeB:
                        kml_line.timestamp.when = timeB
                _log.info    (f"    line    {line.name} ({line.a.lon}, {line.a.lat}) ({line.b.lon}, {line.b.lat})")    
            else:
                _log.warning (f"skipping {line.name} ({line.a.lon}, {line.a.lat}) ({line.b.lon}, {line.b.lat})")
            self.gOp.totalpeople += 1
            # NOT WORKING YET
            if line.midpoints:
                connectWhere = self.folderLife if foldermode else kml
                for mid in line.midpoints:
                    if mid.pos and mid.pos.hasLocation():
                        whatevent = mid.what if mid.what else "Event"
                        event = "<br>{}: {}</br>".format(whatevent, mid.when if mid.when else "Unknown") 
                        pnt = connectWhere.newpoint(name=f"{name} ({whatevent})", coords=[self.driftLatLon(mid.pos)], description="<![CDATA[ " + event + " ]]>")
                        pnt.style = simplekml.Style()
                        pnt.style.labelstyle.scale = 0.7 * styleA.labelstyle.scale
                        # pnt.style.iconstyle.icon.href = f'https://maps.google.com/mapfiles/kml/paddle/wht-blank.png'
                        if mid.when and not (isinstance(mid.when, str)):
                            if hasattr(mid.when.value, 'date'):
                                pnt.timestamp.when = mid.when.value.date.isoformat()
                            elif hasattr(mid.when.value, 'date1'):
                                pnt.timestamp.when = mid.when.value.date1.isoformat()
                        
                        
                        _log.info    (f"    midpt   {line.name} ({mid.pos.lon}, {mid.pos.lat})")    
                    else:
                        _log.warning (f"skipping {line.name} ({mid.pos.lon}, {mid.pos.lat})")


