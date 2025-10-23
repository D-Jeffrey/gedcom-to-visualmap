__all__ = ['gedcom_to_map', 'Geoheatmap', 'doTrace', 'doTraceTo', 'ParseAndGPS', 'doHTML', 'doKML']

import logging
import os.path
import os
import subprocess
import webbrowser
from pathlib import Path
import argparse     # HACK

from gedcom.GedcomParser import GedcomParser
# from gedcom.gpslookup import GEDComGPSLookup
from gedcomoptions import gvOptions
from models.Creator import Creator, LifetimeCreator, CreatorTrace, Person
from models.LatLon import LatLon
from render.foliumExp import foliumExporter
from render.KmlExporter import KmlExporter
from render.Referenced import Referenced
from render.kml import KML_Life_Lines
from render.summary import write_places_summary, write_people_summary, write_birth_death_countries_summary, write_geocache_summary, write_alt_places_summary
from gedcom.gedcom import GeolocatedGedcom

# Constants
GLOBAL_GEO_CACHE_FILENAME = 'geo_cache.csv'
FILE_ALT_PLACE_FILENAME_SUFFIX = '_alt.csv'
FILE_GEOCACHE_FILENAME_SUFFIX = '_cache.csv'
GEO_CONFIG_FILENAME = 'geo_config.yaml'

# Thread for controlling the background processes Created in gedcomVisualGUI.py
# BackgroundProcess

_log = logging.getLogger(__name__)

def gedcom_to_map(gOp : gvOptions):
    
    people = ParseAndGPS(gOp)
    doKML(gOp, people)

def doKML(gOp : gvOptions, people: list[Person]):
    if (not people):
        return
    kmlInstance = None

    placeTypes = []
#    if gOp.MarksOn:
    if gOp.BornMark:
        placeTypes.append(['birth', '(b)', 'birth'])
    if gOp.DieMark:
        placeTypes.append(['death', '(d)', 'death'])
#    if gOp.HomeMarker:
#        placeTypes.append(['home[h]', '(e)', 'event'])

    

    for (key, nametag, placeType) in placeTypes:

        # lifeline = LifetimeCreator(people, gOp.MaxMissing)    
        lifeline = Creator(people, gOp.MaxMissing, gpstype=key) 
        creator = lifeline.create(gOp.Main)
        if gOp.AllEntities:
            lifeline.createothers(creator)
            _log.info  ("Total of %i people.", len(creator))  

        if gOp.Main not in people:
            _log.error  ("Could not find your starting person: %s", gOp.Main)
            gOp.stopstep('Error could not find first person')
            return
        gOp.setMainPerson(people [gOp.Main])
        if (not kmlInstance):
            kmlInstance = KmlExporter(gOp)

        kmlInstance.export(people[gOp.Main].latlon, creator, nametag, placeType)
    if kmlInstance:
        kmlInstance.Done()
        cmdfile = os.path.join(gOp.resultpath, gOp.Result)
        gOp.BackgroundProcess.SayInfoMessage(f"KML output to : {cmdfile}") 
        if gOp.KMLcmdline:
            gOp.panel.runCMDfile(gOp.KMLcmdline, cmdfile)
        else:
            _log.error("Use Options -> Options Setup to define a command line to run")
    else:
        _log.error("No KML output created")
        gOp.BackgroundProcess.SayInfoMessage(f"No KML output created - No data selected to map") 

def doKML2(gOp : gvOptions, people: list[Person]):
    if (not gOp.lookup):
        _log.error("doKML2: GeolocatedGedcom is not processed")
        return
    cmdfile = os.path.join(gOp.resultpath, gOp.Result)

    kml_life_lines = KML_Life_Lines(gedcom=gOp.lookup, kml_file=str(cmdfile),
                                        connect_parents=True, save=True)
    if kml_life_lines and kml_life_lines.kml:
        gOp.BackgroundProcess.SayInfoMessage(f"KML(2) output to : {cmdfile}") 
        if gOp.KMLcmdline:
            gOp.panel.runCMDfile(gOp.KMLcmdline, cmdfile)
        else:
            _log.error("Use Options -> Options Setup to define a command line to run")
    else:
        _log.error("No KML output created")
        gOp.BackgroundProcess.SayInfoMessage(f"No KML(2) output created") 

def doSUM(gOp : gvOptions):
# HACK this in
    args = argparse.Namespace()

    base_file_name = Path(gOp.GEDCOMinput).stem
    output_folder = Path(gOp.resultpath).parent
    my_gedcom = gOp.lookup
    if True or args.write_places_summary or args.write_all:
        places_summary_file = output_folder / f"{base_file_name}_places.csv"
        places_summary_file = places_summary_file.resolve()
        _log.info(f"Writing places summary to {places_summary_file}")
        write_places_summary(args, my_gedcom.address_book, str(places_summary_file))
        gOp.BackgroundProcess.SayInfoMessage(f"Places Summary: {places_summary_file}") 
        gOp.panel.runCMDfile("", str(places_summary_file))
    if True or args.write_people_summary or args.write_all:
        people_summary_file = output_folder / f"{base_file_name}_people.csv"
        people_summary_file = people_summary_file.resolve()
        _log.info(f"Writing people summary to {people_summary_file}")
        write_people_summary(args, my_gedcom.people, str(people_summary_file))
        gOp.BackgroundProcess.SayInfoMessage(f"Places Summary: {places_summary_file}") 
        gOp.panel.runCMDfile("", str(places_summary_file))

    if True or args.write_countries_summary or args.write_all:
        countries_summary_file = output_folder / f"{base_file_name}_countries.csv"
        countries_summary_file = countries_summary_file.resolve()
        _log.info(f"Writing countries summary to {countries_summary_file}")
        write_birth_death_countries_summary(args, my_gedcom.people, str(countries_summary_file), base_file_name)
        gOp.BackgroundProcess.SayInfoMessage(f"Countries summary: {countries_summary_file}") 
        gOp.panel.runCMDfile("", str(countries_summary_file))

    if True or args.write_geocache_per_input_file or args.write_all:
        per_file_cache = output_folder / f"{base_file_name}{FILE_GEOCACHE_FILENAME_SUFFIX}"
        per_file_cache = per_file_cache.resolve()
        _log.info(f"Writing geo cache to {per_file_cache}")
        write_geocache_summary(my_gedcom.address_book, str(per_file_cache))
        gOp.BackgroundProcess.SayInfoMessage(f"geo cache: {per_file_cache}") 
        gOp.panel.runCMDfile("", str(per_file_cache))

    if True or not args.skip_file_alt_places and (args.write_alt_place_summary or args.write_all):
        alt_places_summary_file = output_folder / f"{base_file_name}_alt_places.csv"
        alt_places_summary_file = alt_places_summary_file.resolve()
        _log.info(f"Writing alternative places summary to {alt_places_summary_file}")
        write_alt_places_summary(args, my_gedcom.address_book, str(alt_places_summary_file))
        gOp.BackgroundProcess.SayInfoMessage(f"Alternative places summary: {alt_places_summary_file}") 
        gOp.panel.runCMDfile("", str(alt_places_summary_file))


def Geoheatmap(gOp : gvOptions):
    
    people = ParseAndGPS(gOp)
    doHTML(gOp, people, True)

def doHTML(gOp : gvOptions, people, fullresult ):
    
    if (not people):
        return
    _log.debug  ("Creating Lifeline (fullresult:%s)", fullresult)
    lifeline = LifetimeCreator(people, gOp.MaxMissing)    
    _log.debug  ("Creating People ")
    creator = lifeline.create(gOp.Main)    
    if gOp.Main not in people:
        _log.error ("Could not find your starting person: %s", gOp.Main)
        gOp.stopstep('Error could not find first person')
        return
    gOp.setMainPerson(people[gOp.Main])
    if gOp.AllEntities:
        gOp.step('Creating life line for everyone')
        lifeline.createothers(creator)
        _log.info ("Total of %i people & events.", len(creator))   
    gOp.totalpeople = len(creator)

    foliumExporter(gOp).export(people[gOp.Main], creator, fullresult)
    if (fullresult):
        webbrowser.open(os.path.join(gOp.resultpath, gOp.Result), new = 0, autoraise = True)
        
    

def ParseAndGPS(gOp: gvOptions, stage: int = 0 ):
    """
    ParseAndGPS: Parse the GEDCOM file and optionally resolve addresses to GPS coordinates.
        - Resolve paths and filenames.
        - Parse and correct GEDCOM file.
        - Geocode places and cache results.
        - Optionally use alternative place/address files.
        - Save updated cache.
    """
    global BackgroundProcess
    # Link and establish the BackgroundProcess connection to the other thread
    BackgroundProcess = gOp.BackgroundProcess
    people = None
    _log.info ("Starting parsing of GEDCOM : %s (stage: %d)", gOp.GEDCOMinput, stage)
    if (stage == 0 or stage == 1):
        if gOp.people:
            del gOp.people
            gOp.people = None
        gOp.newload = True
        if hasattr(gOp, "UpdateBackgroundEvent") and hasattr(gOp.UpdateBackgroundEvent, "updategrid"):
            gOp.UpdateBackgroundEvent.updategrid = True
        # people = GedcomParser(gOp).create_people()
        # gOp.people = people
    # gOp.parsed = True
    # gOp.goodmain = False
    #if (stage == 2):
    #    people = gOp.people
    #if (people and gOp.UseGPS and (stage == 0 or stage == 2)):
    if (stage == 1):
            gOp.parsed = True
            _log.info ("Starting Address to GPS resolution")
        # TODO This could cause issues
        # Check for change in the datetime of CSV
#        if gOp.lookup:
#            lookupresults = gOp.lookup
#        else:
            # lookupresults = GEDComGPSLookup(people, gOp)
            input_path = Path(gOp.GEDCOMinput)
            if not input_path.is_absolute():
                input_path = (Path.cwd() / input_path).resolve()
            base_file_name = input_path.stem
            cache_filename = (r"geodat-address-cache.csv", r"geodat-address-cache-1.csv", r"geodat-address-cache-2.csv")
            
            cachefile = input_path.parent / cache_filename[0]
            alt_place_file_path = input_path.parent / f"{base_file_name}{FILE_ALT_PLACE_FILENAME_SUFFIX}"
            file_geo_cache_path = input_path.parent / f"{base_file_name}{FILE_GEOCACHE_FILENAME_SUFFIX}"
            geo_config_path = Path(__file__).parent.resolve() / GEO_CONFIG_FILENAME
            gOp.lookup = GeolocatedGedcom(
                gedcom_file=input_path.resolve(), 
                location_cache_file=cachefile,
                default_country=gOp.defaultCountry,      #TODO make this an option
                always_geocode=not gOp.CacheOnly,
                use_alt_places = not gOp.skip_file_alt_places,
                alt_place_file_path=alt_place_file_path if not gOp.skip_file_alt_places else None,
#                geo_config_path=geo_config_path if geo_config_path.exists() else None,
#                file_geo_cache_path=file_geo_cache_path if not gOp.skip_file_geocache else None,
#                include_canonical= gOp.include_canonical,         # TODO make this an option
                background=gOp.BackgroundProcess
            )
            _log.info ("Completed Geocode")
#            gOp.lookup = lookupresults
#        lookupresults.resolve_addresses(people)
            gOp.step('Saving Address Cache')
#        lookupresults.saveAddressCache()
            gOp.lookup.save_location_cache()
            gOp.people = gOp.lookup.people
            _log.info ("Completed resolves")
            people = gOp.people
    
    if people and (not gOp.Main or not gOp.Main in list(people.keys())):
            gOp.set('Main', list(people.keys())[0])
            _log.info ("Using starting person: %s (%s)", people[gOp.Main].name, gOp.Main)
    
    return people

def doTrace(gOp : gvOptions):
    
    gOp.Referenced = Referenced()
    gOp.totalpeople = 0
    
    if not gOp.people:
        _log.error ("Trace:References no people.")
        return
    people = gOp.people
    if gOp.Main not in people:
        _log.error  ("Trace:Could not find your starting person: %s", gOp.Main)
        return
    gOp.Referenced.add(gOp.Main)
    lifeline = CreatorTrace(people)
    #for h in people.keys():
    creator = lifeline.create(gOp.Main)

    _log.info  ("Trace:Total of %i people.", len(creator)) 
    if  creator:
        for c in creator:
            gOp.Referenced.add(c.person.xref_id,tag=c.path)

# Trace from the main person to this ID
def doTraceTo(gOp : gvOptions, ToID : Person):
    if not gOp.Referenced:
        doTrace(gOp)
    people = gOp.people
    heritage = []
    heritage = [("", gOp.mainPerson.name, gOp.mainPerson.refyear()[0], gOp.mainPerson.xref_id)]
    if gOp.Referenced.exists(ToID.xref_id):
        personRelated = gOp.Referenced.gettag(ToID.xref_id)
        personTrace = gOp.mainPerson
        if personRelated:    
            for r in personRelated:
                if r == "F":
                    personTrace = people[personTrace.father]
                    tag = "Father"
                elif r == "M":
                    personTrace = people[personTrace.mother]
                    tag = "Mother"
                else:
                    _log.error("doTrace - neither Father or Mother, how did we get here?")
                    tag = "?????"
                heritage.append((f"[{tag}]",personTrace.name, personTrace.refyear()[0], personTrace.xref_id))
    else:
        heritage.append([("NotDirect", ToID.name)])
    gOp.heritage = heritage
    return heritage
    
