import math

import simplekml as simplekml
from models.Line import Line
from models.Pos import Pos



class KmlExporter:
    def __init__(self, file_name, max_line_weight=1):
        self.file_name = file_name
        self.kml = None
        self.max_line_weight = max_line_weight

    def Done(self):
        self.kml.save(self.file_name)
        self.kml = None
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
            print ("No GPS locations to generate a map.")

        for line in lines:
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
            print("skipping {} ({},{}) ({},{})".format(line.name, line.a.lon, line.a.lat, line.b.lon, line.b.lat) )
        #self.Done()
   
