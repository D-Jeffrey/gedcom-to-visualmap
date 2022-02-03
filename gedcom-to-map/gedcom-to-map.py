import argparse
import os

from creator.Creator import Creator, LifetimeCreator
from gedcom.GedcomParser import GedcomParser
from kml.KmlExporter import KmlExporter
from kml.foliumExp import foliumExporter, setGeoExpOptions
from kml.KmlExporter import KmlExporter
from kml.gpslookup import GEDComGPSLookup
from models.Pos import Pos

def gedcom_to_map(input_file, output_file, main_entity, max_missing=0, max_line_weight=1, usegps=True, cacheonly=False, placetype={'native'}):
    kmlInstance = None
    print ("Starting parsing of GEDCOM :".format(input_file))

    humans = GedcomParser(input_file).create_humans()
    if (usegps):
        print ("Starting Address to GPS resolution")
        lookupresults = GEDComGPSLookup(humans, cacheonly)
        lookupresults.resolveaddresses(humans)
        lookupresults.saveAddressCache()
        print ("Completed resolves")

    # Save in case we overwrite
    for h in humans.keys():
        humans[h].map = humans[h].pos

    for p in placetype:
        
        if (p == 'native'):
            for h in humans.keys():
                humans[h].pos = humans[h].map
            print ("KML native")
            nametag = ''
        if (p == 'born'):
            for h in humans.keys():
                humans[h].pos = Pos(None,None)
                if humans[h].birth:
                    if humans[h].birth.pos:
                        humans[h].pos = humans[h].birth.pos
            print ("KML born")
            nametag = ' (b)'
        if (p == 'death'):
            for h in humans.keys():
                humans[h].pos = Pos(None,None)
                if humans[h].death:
                    if humans[h].death.pos:
                        humans[h].pos = humans[h].death.pos
            print ("KML death")
            nametag = ' (d)'
        creator = Creator(humans, max_missing).create(main_entity)    
        if main_entity not in humans:
            print ("Could not find your starting person: {}".format(main_entity))
            raise
        if (not kmlInstance):
            kmlInstance = KmlExporter(output_file, max_line_weight)
        kmlInstance.export(humans[main_entity].pos, creator, nametag)
    kmlInstance.Done()


def Geoheatmap(input_file, output_file, main_entity, max_missing=0, max_line_weight=1,  usegps=True, cacheonly=False, gOptions = None):
    kmlInstance = None
    print ("Starting parsing of GEDCOM :".format(input_file))
    humans = GedcomParser(input_file).create_humans()
    if (usegps):
        print ("Starting Address to GPS resolution")
        lookupresults = GEDComGPSLookup(humans, cacheonly)
        lookupresults.resolveaddresses(humans)
        lookupresults.saveAddressCache()
        print ("Completed resolves")

    """     
    for h in humans.keys():
        humans[h].pos = Pos(None,None)
        if humans[h].birth:
           if humans[h].birth.pos:
              humans[h].pos = humans[h].birth.pos
    """


    creator = LifetimeCreator(humans, max_missing).create(main_entity)    
    if main_entity not in humans:
        print ("Could not find your starting person: {}".format(main_entity))
        raise
    foliumExporter(output_file, max_line_weight, gOptions=gOptions).export(humans[main_entity], creator)
    


class ArgParse(argparse.ArgumentParser):
    def __init__(self):
        super().__init__(description="convert gedcom to kml file and lookup GPS addresses")
        self.add_argument('input_file', type=str)
        self.add_argument('output_file', type=str)
        self.add_argument('main_entity', type=str)
        self.add_argument('-format', type=str, default='HTML', choices=('HTML', 'KML'), help="type of output result for map format")
        self.add_argument('-max_missing', type=int, default=0, help="maximum generation missing (0 = no limit)")
        self.add_argument('-max_line_weight', type=int, default=20, help="line maximum weight")
        
        self.geocodegroup = self.add_argument_group('Geocoding')
        self.geocodegroup.add_argument('-gpscache', action='store_true', dest='cacheonly', help="use the GPS cache only")
        self.geocodegroup.add_argument('-nogps', action='store_false', dest='usegps', help="lookup places using geocode to determine GPS")
        
        self.htmlgroup = self.add_argument_group('Folium Map as HTML (format HTML)')
        self.htmlgroup.add_argument('-nomarker',  action='store_true', dest='marksoff', help="Turn off the markers")
        self.htmlgroup.add_argument('-nobornmarker',  action='store_true', dest='bornmarksoff', help="Turn off the markers for born")
        self.htmlgroup.add_argument('-noheatmap', action='store_true', dest='heatmapoff', help="Turn off the heat map")
        self.htmlgroup.add_argument('-maptiletype', type=int, default=3,  choices=range(1, 8), help="Map tile styles")
        self.htmlgroup.add_argument('-nomarkstar', action='store_true', dest='markstaroff', help="Turn off the markers starting person")
        self.htmlgroup.add_argument('-groupby', type=int, default=0,  choices=range(0,3), help="1 - Family Name, 2 - Person")
        self.htmlgroup.add_argument('-antpath', action='store_true', dest='antpath', help="Turn on AntPath")
        self.htmlgroup.add_argument('-heattime', action='store_true', dest='heattime', help="Turn on heatmap timeline")
        self.htmlgroup.add_argument('-heatstep', type=int, default=5, help="years per heatmap group step")
        self.htmlgroup.add_argument('-homemarker', action='store_true', dest='markhomes', help="Turn on marking homes")
        
        
        self.kmlgroup = self.add_argument_group('KML processing')
        self.kmlgroup.add_argument('-born', action='store_true', dest='usebornplace', help="use place born for mapping")
        
        self.args = self.parse_args()
        pathname, extension = os.path.splitext(self.args.output_file)
        if extension == "":
            if self.args.format=='KML':  self.args.output_file = self.args.output_file + ".kml"
            if self.args.format=='HTML': self.args.output_file = self.args.output_file + ".html"


if __name__ == '__main__':
    arg_parse = ArgParse()

    # "c:\Users\darre\Downloads\mytree-py.ged" fol.html   "@I500003@"  --nobornmarker --gpscache  --maptiletype 1
    # "input.ged"  "output_fol.html"   "@I0000@"  --nobornmarker  --maptiletype 1
    myGeoOptions = setGeoExpOptions(BornMark = not arg_parse.args.bornmarksoff, MarksOn = not arg_parse.args.marksoff, 
                                     HeatMap = not arg_parse.args.heatmapoff,
                                     MapStyle = arg_parse.args.maptiletype, 
                                     MarkStarOn = not arg_parse.args.markstaroff, 
                                     GroupBy = arg_parse.args.groupby,
                                     AntPath = arg_parse.args.antpath, 
                                     HeatMapTimeLine = arg_parse.args.heattime,
                                     HeatMapTimeStep = arg_parse.args.heatstep,
                                     HomeMarker = arg_parse.args.markhomes)
    
    if (arg_parse.args.format =='HTML'):
        Geoheatmap(
            arg_parse.args.input_file,
            arg_parse.args.output_file,
            arg_parse.args.main_entity,
            max_missing=arg_parse.args.max_missing,
            max_line_weight=arg_parse.args.max_line_weight,
            usegps=arg_parse.args.usegps,
            cacheonly=arg_parse.args.cacheonly, 
            gOptions = myGeoOptions,
            )
    elif arg_parse.args.format =='KML': 
        
        places = {'native'}
        if (arg_parse.args.usebornplace):
            places = ('born')
            places.add('death')
        gedcom_to_map(
            arg_parse.args.input_file,
            arg_parse.args.output_file,
            arg_parse.args.main_entity,
            max_missing=arg_parse.args.max_missing,
            max_line_weight=arg_parse.args.max_line_weight,
            placetype=places,
            usegps=arg_parse.args.usegps,
            cacheonly=arg_parse.args.cacheonly
            )
        