__all__ = ['KmlExporter']

import math

import simplekml as simplekml
from models.Line import Line
from models.Pos import Pos
from gedcomoptions import gvOptions
import logging

logger = logging.getLogger(__name__)

class KmlExporter:
    def __init__(self, gOp: gvOptions):
        self.file_name = gOp.Result
        self.max_line_weight = gOp.MaxLineWeight
        self.kml = None
        self.gOp = gOp

    def Done(self):
        self.gOp.step("Saving KML")
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
            
            kml.newpoint(coords=[
                (main.lon, main.lat)
            ])
        else:
            logger.error ("No GPS locations to generate a map.")

        self.gOp.step("Generating KML")
        for line in lines:
            self.gOp.step()
            if (line.a.lon and line.a.lat):
                kml.newpoint(name=line.name  + ntag, coords=[
                    (line.a.lon, line.a.lat)
                ])
            if (line.b.lon and line.b.lat):
                kml.newpoint(name=line.name  + ntag, coords=[
                    (line.b.lon, line.b.lat)
                ])
            if (line.a.lon and line.a.lat and line.b.lon and line.b.lat):
                kml_line = kml.newlinestring(name=line.name, coords=[
                    (line.a.lon, line.a.lat), (line.b.lon, line.b.lat)
                ])
                kml_line.linestyle.color = line.color.to_hexa()
                kml_line.linestyle.width = max(
                    int(self.max_line_weight/math.exp(0.5*line.prof)),
                    1
                )
            else:
                logger.warning ("skipping {} ({},{}) ({},{})".format(line.name, line.a.lon, line.a.lat, line.b.lon, line.b.lat) )
        self.Done()
   
