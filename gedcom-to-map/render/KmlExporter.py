__all__ = ['KmlExporter']

import math

import simplekml as simplekml
from models.Line import Line
from models.Pos import Pos
from gedcomoptions import gvOptions
from render.Referenced import Referenced
import logging
import os.path
import random

logger = logging.getLogger(__name__)

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

    def driftPos(self, l : Pos):
        if not l or not self.driftOn:
            return l
        return ((float(l.lon)+(random.random() * 0.001) - 0.0005), float(l.lat)+(random.random() * 0.001) - 0.0005)
        
    def Done(self):
        self.gOp.step("Saving KML")
        logging.info("Saved as %s", self.file_name)
        self.kml.save(self.file_name)
        self.gOp.stop()
        # self.kml = None
    def export(self, main: Pos, lines: [Line], ntag =""):
        if self.kml:
            kml = self.kml     
        else:
            kml = simplekml.Kml()
            self.kml = kml
        if main:
            kml.newpoint(name=(self.gOp.Name  + ntag),coords=[ (main.lon, main.lat) ])
            self.gOp.totalpeople += 1
        else:
            logger.error ("No GPS locations to generate a map.")

        self.gOp.step("Generating KML")
        sorted_lines = sorted(lines, key=lambda x: x.prof)
        for line in sorted_lines :
            self.gOp.step()
            if (line.a.lon and line.a.lat):
                kml.newpoint(name=line.name  + ntag, coords=[self.driftPos(line.a)])
                self.gOp.Referenced.add(line.human.xref_id, 'kml-a')
                self.gOp.totalpeople += 1
            if (line.b.lon and line.b.lat):
                kml.newpoint(name=line.name  + ntag, coords=[self.driftPos(line.b)])
                self.gOp.Referenced.add(line.human.xref_id, 'kml-b')
                self.gOp.totalpeople += 1
            if (line.a.lon and line.a.lat and line.b.lon and line.b.lat):
                kml_line = kml.newlinestring(name=line.name, coords=[self.driftPos(line.a), self.driftPos(line.b)])
                kml_line.linestyle.color = line.color.to_hexa()
                kml_line.linestyle.width = max(
                    int(self.max_line_weight/math.exp(0.5*line.prof)),
                    1
                )
            else:
                logger.warning ("skipping {} ({},{}) ({},{})".format(line.name, line.a.lon, line.a.lat, line.b.lon, line.b.lat) )
        self.Done()
   
