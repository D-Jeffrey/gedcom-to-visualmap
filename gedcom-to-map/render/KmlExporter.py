__all__ = ['KmlExporter']

import logging
import math
import os.path
import random

import simplekml as simplekml
from gedcomoptions import gvOptions
from models.Line import Line
from models.Pos import Pos
from render.Referenced import Referenced

_log = logging.getLogger(__name__)

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
            self.kml = kml
            styleA = simplekml.Style()
            # styleA.labelstyle.color = simplekml.Color.blue  # Make the text blue
            styleA.labelstyle.scale = 1  # Make the text twice as big
            styleA.iconstyle.icon.href = f'https://maps.google.com/mapfiles/kml/paddle/{colorA}-{marktype}.png'          #   https://kml4earth.appspot.com/icons.html
            styleB = simplekml.Style()
            # styleB.labelstyle.color = simplekml.Color.pink  # Make the text pink
            styleB.labelstyle.scale = 1  # Make the text twice as big
            styleB.iconstyle.icon.href = f'https://maps.google.com/mapfiles/kml/paddle/{colorB}-{marktype}.png'        #   https://kml4earth.appspot.com/icons.html
            self.styleA = styleA
            self.styleB = styleB
            
        if main:
            kml.newpoint(name=(self.gOp.Name  + ntag),coords=[ (main.lon, main.lat) ])
            self.gOp.totalpeople += 1
        else:
            _log.error ("No GPS locations to generate a map.")

        
        self.gOp.step("Generating KML")
        sorted_lines = sorted(lines, key=lambda x: x.prof)
        for line in sorted_lines :
            self.gOp.step()
            names = line.name.split("\t")
            linage = names[0]
            name = names[len(names)-1]
            if (line.a.lon and line.a.lat):
                pnt = kml.newpoint(name=name + ntag, description=linage, coords=[self.driftPos(line.a)])
                self.gOp.Referenced.add(line.human.xref_id, 'kml-a')
                self.gOp.totalpeople += 1
                if line.when: pnt.TimeStamp.when = line.when
                pnt.style = styleA
                
                # pnt.address = where
            if (line.b.lon and line.b.lat):
                pnt = kml.newpoint(name=name + ntag, description=linage, coords=[self.driftPos(line.b)])
                self.gOp.Referenced.add(line.human.xref_id, 'kml-b')
                self.gOp.totalpeople += 1
                if line.when: pnt.TimeStamp.when = line.when
                pnt.style = styleB
                
                # pnt.address = where
                
            if (line.a.lon and line.a.lat and line.b.lon and line.b.lat):
                kml_line = kml.newlinestring(name=name, description=linage, coords=[self.driftPos(line.a), self.driftPos(line.b)])
                kml_line.linestyle.color = line.color.to_hexa()
                kml_line.linestyle.width = max(
                    int(self.max_line_weight/math.exp(0.5*line.prof)),
                    1
                )
                kml_line.extrude = 1
                kml_line.tessellate = 1
                kml_line.altitudemode = simplekml.AltitudeMode.clamptoground 
            else:
                _log.warning (f"skipping {line.name} ({line.a.lon}, {line.a.lat}) ({line.b.lon}, {line.b.lat})")
        self.Done()
   
