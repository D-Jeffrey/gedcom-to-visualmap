__all__ = ['gedcom_to_map', 'Geoheatmap', 'doTrace', 'doTraceTo', 'ParseAndGPS', 'doHTML', 'doKML']

import logging
import os.path
import os
import subprocess
import webbrowser

from gedcom.GedcomParser import GedcomParser
from gedcom.gpslookup import GEDComGPSLookup
from gedcomoptions import gvOptions
from models.Creator import Creator, LifetimeCreator, CreatorTrace, Person
from models.LatLon import LatLon
from render.foliumExp import foliumExporter
from render.KmlExporter import KmlExporter
from render.Referenced import Referenced

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
        if gOp.KMLcmdline:
            if gOp.KMLcmdline.startswith('http'):
                webbrowser.open(gOp.KMLcmdline, new = 0, autoraise = True)
            else:
                # TODO
                cmdline = gOp.KMLcmdline.replace("$n", os.path.join(gOp.resultpath, gOp.Result))
                _log.info(f"KML Running command line : '{cmdline}'") 
                gOp.BackgroundProcess.SayInfoMessage(f"KML output to : {os.path.join(gOp.resultpath, gOp.Result)}") 
                try:
                    if os.name == 'posix':
                        subprocess.Popen(["/bin/sh" , cmdline])
                    elif os.name == 'nt':
                        cmd = os.environ.get("SystemRoot") + "\\system32\\cmd.exe"
                        subprocess.Popen([cmd, "/c", cmdline])
                    else:
                        _log.error(f"Unknwon OS to run command-line: '{cmdline}'")
                        
                except FileNotFoundError:
                    _log.error(f"command errored: '{cmdline}'") 
                except Exception as e:
                    _log.error(f"command errored as: {e} : '{cmdline}'") 
    else:
        _log.error("No KML output created")
        gOp.BackgroundProcess.SayInfoMessage(f"No KML output created - No data selected to map") 

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
    _log.info ("Starting parsing of GEDCOM : %s (stage: %d)", gOp.GEDCOMinput, stage)
    if (stage == 0 or stage == 1):
        if gOp.people:
            del gOp.people
            gOp.people = None
        if hasattr(gOp, "UpdateBackgroundEvent") and hasattr(gOp.UpdateBackgroundEvent, "updategrid"):
            gOp.UpdateBackgroundEvent.updategrid = True
        people = GedcomParser(gOp).create_people()
        gOp.people = people
    gOp.parsed = True
    gOp.goodmain = False
    if (stage == 2):
        people = gOp.people
    if (people and gOp.UseGPS and (stage == 0 or stage == 2)):
        _log.info ("Starting Address to GPS resolution")
        # TODO This could cause issues
        # Check for change in the datetime of CSV
        if gOp.lookup:
            lookupresults = gOp.lookup
        else:
            lookupresults = GEDComGPSLookup(people, gOp)
            _log.info ("Completed Geocode")
            gOp.lookup = lookupresults
        lookupresults.resolve_addresses(people)
        gOp.step('Saving Address Cache')
        lookupresults.saveAddressCache()
        _log.info ("Completed resolves")
    
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
    
