__all__ = ['KmlExporter']

import logging
import math
import os.path
import random
import re

import simplekml as simplekml
from gedcomoptions import gvOptions
from models.Line import Line
from models.Pos import Pos
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
            

    def driftPos(self, l : Pos):
        if not l or not self.driftOn:
            return l
        return ((float(l.lon)+(random.random() * 0.001) - 0.0005), float(l.lat)+(random.random() * 0.001) - 0.0005)
        
    def Done(self):
        self.gOp.step("Finalizing KML")
        # Fix up the links in the placemark
        for placemark in self.kml.features:
            if placemark.description:
                pattern = r'href=#(.*?);'
                for match in re.finditer(pattern, placemark.description):
                    tag = match.group(1)
                    if self.gOp.Referenced.exists(tag):
                        replacewith = 1 + int(self.gOp.Referenced.gettag(tag))
                        original = f"href=#{tag};"
                        replacement = f"href=#{replacewith};"
                        placemark.description = placemark.description.replace(original, replacement)
            if placemark.balloonstyle and placemark.balloonstyle.text:
                pattern = r'href=#(.*?);'
                for match in re.finditer(pattern, placemark.balloonstyle.text):
                    tag = match.group(1)
                    if self.gOp.Referenced.exists(tag):
                        replacewith = 1 + int(self.gOp.Referenced.gettag(tag))
                        original = f"href=#{tag};"
                        replacement = f"href=#{replacewith};"
                        placemark.balloonstyle.text = placemark.balloonstyle.text.replace(original, replacement)

        
        self.gOp.step("Saving KML")
        logging.info("Saved as %s", self.file_name)
        self.kml.save(self.file_name)
        # self.gOp.stop()
        # self.kml = None
    def export(self, main: Pos, lines: list[Line], ntag ="", mark="native"):
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
            
            
            kmldoc = kml.newdocument(name='About Geomap KML', description=descript)

            self.kml = kml
            
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
            kml.newpoint(name=(self.gOp.Name  + ntag),coords=[ (main.lon, main.lat) ])
            self.gOp.totalpeople += 1
        else:
            _log.error (f"No GPS locations to generate a map for main for {ntag}.")

        
        self.gOp.step("Generating KML")
        sorted_lines = sorted(lines, key=lambda x: x.prof)
        for line in sorted_lines :
            self.gOp.step()
            (desend, name) = line.name.split("\t")
            linage = ""
            timeA = line.whenFrom if hasattr(line, 'whenFrom') and line.whenFrom else None
            timeB = line.whenTo if hasattr(line, 'whenTo') and line.whenTo else None
            
            if line.human.father:
                if self.gOp.UseBalloonFlyto:
                    linage += '<br>Father: <a href=#{};balloonFlyto>{}</a></br>'.format(line.human.father[1:-1],self.gOp.humans[line.human.father].name)    
                else:
                    linage += '<br>Father: {}</br>'.format(self.gOp.humans[line.human.father].name)
            if line.human.mother:
                if self.gOp.UseBalloonFlyto:
                    linage += '<br>Mother: <a href=#{};balloonFlyto>{}</a></br>'.format(line.human.mother[1:-1],self.gOp.humans[line.human.mother].name)
                else:
                    linage += '<br>Mother: {}</br>'.format(self.gOp.humans[line.human.mother].name)
            family = []
            thisparent = line.human.xref_id

            for c in self.gOp.humans:
                if self.gOp.humans[c].father == thisparent or self.gOp.humans[c].mother == thisparent:
                    family.append(c)
            if family:
                if self.gOp.UseBalloonFlyto:
                    # Format each child as a clickable link
                    family_links = [
                        f'<a href=#{child[1:-1]};balloonFlyto>{self.gOp.humans[child].name}</a>'
                        for child in family
                    ]
                    familyLinage = '<br>Children: {}</br>'.format(", ".join(family_links))
                else:
                    family_names = [self.gOp.humans[child].name for child in family]
                    familyLinage = '<br>Children: {}</br>'.format(", ".join(family_names))

            

            
            if line.a.hasLocation() and mark in ['birth']:
                event = "<br>Born: {}</br>".format(timeA if timeA else "Unknown", timeB if timeB else "Unknown")
                pnt = kml.newpoint(name=name + ntag, coords=[self.driftPos(line.a)], description="<![CDATA[ " + event + linage + familyLinage + " ]]>")
                self.gOp.Referenced.add(line.human.xref_id, 'kml-a',tag=pnt.id)
                self.gOp.Referenced.add(line.human.xref_id[1:-1], tag=pnt.id)
                if self.gOp.MapTimeLine and hasattr(line, 'whenFrom') and line.whenFrom: 
                    pnt.timestamp.when = line.whenFrom
            
                pnt.style = simplekml.Style()
                pnt.style.labelstyle.scale = styleA.labelstyle.scale
                pnt.style.iconstyle.icon.href = styleA.iconstyle.icon.href

                # pnt.style.balloonstyle = simplekml.BalloonStyle()
                # pnt.style.balloonstyle.text = linage

                
            if line.b.hasLocation() and mark in ['death']:
                event = "<br>Death: {}</br>".format(timeB if timeB else "Unknown") 
                pnt = kml.newpoint(name=name + ntag, coords=[self.driftPos(line.b)], description="<![CDATA[ " + event + linage  + familyLinage + " ]]>")

                self.gOp.Referenced.add(line.human.xref_id, 'kml-b')
                self.gOp.Referenced.add(line.human.xref_id[1:-1], tag=pnt.id)
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
                kml_line = kml.newlinestring(name=name, description="<![CDATA[ " + event + linage + familyLinage + " ]]>", coords=[self.driftPos(line.a), self.driftPos(line.b)])
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
                for mid in line.midpoints:
                    if mid.pos and mid.pos.hasLocation():
                        whatevent = mid.what if mid.what else "Event"
                        event = "<br>{}: {}</br>".format(whatevent, mid.when if mid.when else "Unknown") 
                        pnt = kml.newpoint(name=f"{name} ({whatevent})", coords=[self.driftPos(mid.pos)], description="<![CDATA[ " + event + " ]]>")
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
        self.Done()

