# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
#
#
#  getcom-to-map : command-line version of interface
#    See https://github.com/D-Jeffrey/gedcom-to-visualmap
#
#
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
import argparse
import logging
import logging
import logging.config

from gedcomoptions import gvOptions
from gedcomvisual import gedcom_to_map, Geoheatmap
from const import NAME, VERSION, LOG_CONFIG, KMLMAPSURL

logger = logging.getLogger(__name__)

class ArgParse(argparse.ArgumentParser):
    def __init__(self):
        super().__init__(description="convert gedcom to kml file and lookup GPS addresses - V" + VERSION )
        self.add_argument('input_file', type=str, help="GEDCOM file, usually ends at .ged")
        self.add_argument('output_file', type=str, help="results file, extension will be added if none is given")
        self.add_argument('-main', type=str, default=None,  help="if this is missing it will use the first person in the GEDCOM file")
        self.add_argument('-format', type=str, default='HTML', choices=('HTML', 'KML'), help="type of output result for map format")
        self.add_argument('-max_missing', type=int, default=0, help="maximum generation missing (0 = no limit)")
        self.add_argument('-max_line_weight', type=int, default=20, help="Line maximum weight")
        self.add_argument('-everyone', action='store_true',  help="Plot everyone in your tree")
        self.add_argument('-log', type=str, default='WARNING', choices=('ERROR', 'WARNING', 'INFO', 'DEBUG'), help="logging level")
        self.add_argument('-logfile', type=str, default=None, help="log file name")

        self.geocodegroup = self.add_argument_group('Geocoding')
        self.geocodegroup.add_argument('-gpscache', action='store_true', dest='cacheonly', help="Use the GPS cache only")
        self.geocodegroup.add_argument('-nogps', action='store_false', dest='usegps', help="Do not lookup places using geocode to determine GPS, use built in GPS values")
        
        self.htmlgroup = self.add_argument_group('Folium Map as HTML (format HTML)')
        self.htmlgroup.add_argument('-nomarker',  action='store_true', dest='marksoff', help="Turn off the markers")
        self.htmlgroup.add_argument('-nobornmarker',  action='store_true', dest='bornmarksoff', help="Turn off the markers for born")
        self.htmlgroup.add_argument('-noheatmap', action='store_true', dest='heatmapoff', help="Turn off the heat map")
        self.htmlgroup.add_argument('-maptiletype', type=int, default=3,  choices=range(1, 8), help="Map tile styles")
        self.htmlgroup.add_argument('-nomarkstar', action='store_true', dest='markstaroff', help="Turn off the markers starting person")
        self.htmlgroup.add_argument('-groupby', type=int, default=2,  choices=range(0,3), help="1 - Family Name, 2 - Person")
        self.htmlgroup.add_argument('-antpath', action='store_true', dest='antpath', help="Turn on AntPath")
        self.htmlgroup.add_argument('-heattime', action='store_true', dest='heattime', help="Turn on heatmap timeline")
        self.htmlgroup.add_argument('-heatstep', type=int, default=5, help="years per heatmap group step")
        self.htmlgroup.add_argument('-homemarker', action='store_true', dest='markhomes', help="Turn on marking homes")
        
        
        self.kmlgroup = self.add_argument_group('KML processing')
        self.kmlgroup.add_argument('-born', action='store_true', help="use place born for mapping")
        self.kmlgroup.add_argument('-death', action='store_true',  help="use place born for mapping")
        
        try:
            self.args = self.parse_args()
        except Exception as e:
            print(repr(e))



if __name__ == '__main__':
    arg_parse = ArgParse()
    
    
    logging.config.dictConfig(LOG_CONFIG)

    logger.setLevel(logging.DEBUG)
    logger.info("Starting up %s %s", NAME, VERSION)
    
    logging.basicConfig(level=logging.INFO)
    
    myGeoOptions = gvOptions    (BornMark = not arg_parse.args.bornmarksoff, MarksOn = not arg_parse.args.marksoff, 
                                     HeatMap = not arg_parse.args.heatmapoff,
                                     MapStyle = arg_parse.args.maptiletype, 
                                     MarkStarOn = not arg_parse.args.markstaroff, 
                                     GroupBy = arg_parse.args.groupby,
                                     AntPath = arg_parse.args.antpath, 
                                     HeatMapTimeLine = arg_parse.args.heattime,
                                     HeatMapTimeStep = arg_parse.args.heatstep,
                                     HomeMarker = arg_parse.args.markhomes)
    places = {'native':'native'}
    if arg_parse.args.born or arg_parse.args.death:
        places = {}
        if arg_parse.args.born:
            places['born'] = 'born'
        if arg_parse.args.death:
            places['death'] = 'death'
       
    myGeoOptions.setstatic( arg_parse.args.input_file, arg_parse.args.output_file,
            arg_parse.args.format =='HTML', arg_parse.args.main, 
            arg_parse.args.max_missing, arg_parse.args.max_line_weight, 
            arg_parse.args.usegps, arg_parse.args.cacheonly,  arg_parse.args.everyone) 

    if (myGeoOptions.ResultHTML):
        Geoheatmap(myGeoOptions)
    elif arg_parse.args.format =='KML': 
        gedcom_to_map(myGeoOptions)
    logger.info('Finished')
    exit(0)
        