__all__ = ['gedcom_to_map', 'Geoheatmap', 'doTrace', 'doTraceTo', 'ParseAndGPS', 'doHTML', 'doKML']

import logging
import os.path
import os
import subprocess
import webbrowser

from gedcom.GedcomParser import GedcomParser
from gedcom.gpslookup import GEDComGPSLookup
from gedcomoptions import gvOptions
from models.Creator import Creator, LifetimeCreator, CreatorTrace, Human
from models.Pos import Pos
from render.foliumExp import foliumExporter
from render.KmlExporter import KmlExporter
from render.Referenced import Referenced

# Thread for controlling the background processes Created in gedcomVisualGUI.py
# BackgroundProcess

_log = logging.getLogger(__name__)

def gedcom_to_map(gOp : gvOptions):
    
    humans = ParseAndGPS(gOp)
    doKML(gOp, humans)

def doKML(gOp : gvOptions, humans: list[Human]):
    if (not humans):
        return
    kmlInstance = None
    # Save in case we overwrite
#    for h in humans.keys():
#        humans[h].map = humans[h].pos

    placeTypes = []
#    if gOp.MarksOn:
    if gOp.BornMark:
        placeTypes.append(['birth', '(b)', 'birth'])
    if gOp.DieMark:
        placeTypes.append(['death', '(d)', 'death'])
#    if gOp.HomeMarker:
#        placeTypes.append(['home[h]', '(e)', 'event'])

    

    for (key, nametag, placeType) in placeTypes:

        # lifeline = LifetimeCreator(humans, gOp.MaxMissing)    
        lifeline = Creator(humans, gOp.MaxMissing, gpstype=key) 
        creator = lifeline.create(gOp.Main)
        if gOp.AllEntities:
            lifeline.createothers(creator)
            _log.info  ("Total of %i people.", len(creator))  

        if gOp.Main not in humans:
            _log.error  ("Could not find your starting person: %s", gOp.Main)
            gOp.stopstep('Error could not find first person')
            return
        gOp.setMainHuman(humans [gOp.Main])
        if (not kmlInstance):
            kmlInstance = KmlExporter(gOp)

        kmlInstance.export(humans[gOp.Main].pos, creator, nametag, placeType)
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
    
    humans = ParseAndGPS(gOp)
    doHTML(gOp, humans, True)

def doHTML(gOp : gvOptions, humans, fullresult ):
    
    if (not humans):
        return
    _log.debug  ("Creating Lifeline (fullresult:%s)", fullresult)
    lifeline = LifetimeCreator(humans, gOp.MaxMissing)    
    _log.debug  ("Creating Humans ")
    creator = lifeline.create(gOp.Main)    
    if gOp.Main not in humans:
        _log.error ("Could not find your starting person: %s", gOp.Main)
        gOp.stopstep('Error could not find first person')
        return
    gOp.setMainHuman(humans[gOp.Main])
    if gOp.AllEntities:
        gOp.step('Creating life line for everyone')
        lifeline.createothers(creator)
        _log.info ("Total of %i people & events.", len(creator))   
    gOp.totalpeople = len(creator)

    foliumExporter(gOp).export(humans[gOp.Main], creator, fullresult)
    if (fullresult):
        webbrowser.open(os.path.join(gOp.resultpath, gOp.Result), new = 0, autoraise = True)
        
    

def ParseAndGPS(gOp: gvOptions, stage: int = 0 ):
    _log.info ("Starting parsing of GEDCOM : %s (stage: %d)", gOp.GEDCOMinput, stage)
    if (stage == 0 or stage == 1):
        if gOp.humans:
            del gOp.humans
            gOp.humans = None
        if hasattr(gOp, "UpdateBackgroundEvent") and hasattr(gOp.UpdateBackgroundEvent, "updategrid"):
            gOp.UpdateBackgroundEvent.updategrid = True
        humans = GedcomParser(gOp).create_humans()
        gOp.humans = humans
    gOp.parsed = True
    gOp.goodmain = False
    if (stage == 2):
        humans = gOp.humans
    if (humans and gOp.UseGPS and (stage == 0 or stage == 2)):
        _log.info ("Starting Address to GPS resolution")
        # TODO This could cause issues
        # Check for change in the datetime of CSV
        if gOp.lookup:
            lookupresults = gOp.lookup
        else:
            lookupresults = GEDComGPSLookup(humans, gOp)
            _log.info ("Completed Geocode")
            gOp.lookup = lookupresults
        lookupresults.resolve_addresses(humans)
        gOp.step('Saving Address Cache')
        lookupresults.saveAddressCache()
        _log.info ("Completed resolves")
    
    if humans and (not gOp.Main or not gOp.Main in list(humans.keys())):
            gOp.set('Main', list(humans.keys())[0])
            _log.info ("Using starting person: %s (%s)", humans[gOp.Main].name, gOp.Main)
    
    return humans

def doTrace(gOp : gvOptions):
    
    gOp.Referenced = Referenced()
    gOp.totalpeople = 0
    
    if not gOp.humans:
        _log.error ("Trace:References no humans.")
        return
    humans = gOp.humans
    if gOp.Main not in humans:
        _log.error  ("Trace:Could not find your starting person: %s", gOp.Main)
        return
    gOp.Referenced.add(gOp.Main)
    lifeline = CreatorTrace(humans)
    #for h in humans.keys():
    creator = lifeline.create(gOp.Main)

    _log.info  ("Trace:Total of %i people.", len(creator)) 
    if  creator:
        for c in creator:
            gOp.Referenced.add(c.human.xref_id,tag=c.path)

# Trace from the main person to this ID
def doTraceTo(gOp : gvOptions, ToID : Human):
    if not gOp.Referenced:
        doTrace(gOp)
    humans = gOp.humans
    heritage = []
    heritage = [("", gOp.mainHuman.name, gOp.mainHuman.refyear()[0], gOp.mainHuman.xref_id)]
    if gOp.Referenced.exists(ToID.xref_id):
        personRelated = gOp.Referenced.gettag(ToID.xref_id)
        humanTrace = gOp.mainHuman
        if personRelated:    
            for r in personRelated:
                if r == "F":
                    humanTrace = humans[humanTrace.father]
                    tag = "Father"
                elif r == "M":
                    humanTrace = humans[humanTrace.mother]
                    tag = "Mother"
                else:
                    _log.error("doTrace - neither Father or Mother, how did we get here?")
                    tag = "?????"
                heritage.append((f"[{tag}]",humanTrace.name, humanTrace.refyear()[0], humanTrace.xref_id))
    else:
        heritage.append([("NotDirect", ToID.name)])
    gOp.heritage = heritage
    return heritage
    
