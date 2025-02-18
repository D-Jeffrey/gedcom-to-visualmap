import logging
import os.path
import webbrowser

from gedcom.GedcomParser import GedcomParser
from gedcom.gpslookup import GEDComGPSLookup
from gedcomoptions import gvOptions
from models.Creator import Creator, LifetimeCreator
from models.Pos import Pos
from render.foliumExp import foliumExporter
from render.KmlExporter import KmlExporter

_log = logging.getLogger(__name__)

def gedcom_to_map(gOp : gvOptions):
    
    humans = ParseAndGPS(gOp)
    doKML(gOp, humans)

def doKML(gOp : gvOptions, humans):
    if (not humans):
        return
    kmlInstance = None
    # Save in case we overwrite
    for h in humans.keys():
        humans[h].map = humans[h].pos

    for p in gOp.PlaceType:
        
        if (p == 'native'):
            for h in humans.keys():
                humans[h].pos = humans[h].map
            _log.info ("KML native")
            nametag = ''
        if (p == 'born'):
            for h in humans.keys():
                humans[h].pos = Pos(None,None)
                if humans[h].birth:
                    if humans[h].birth.pos:
                        humans[h].pos = humans[h].birth.pos
            _log.info  ("KML born")
            nametag = ' (b)'
        if (p == 'death'):
            for h in humans.keys():
                humans[h].pos = Pos(None,None)
                if humans[h].death:
                    if humans[h].death.pos:
                        humans[h].pos = humans[h].death.pos
            _log.info  ("KML death")
            nametag = ' (d)'
        
        lifeline = Creator(humans, gOp.MaxMissing) 
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

        kmlInstance.export(humans[gOp.Main].pos, creator, nametag)
    kmlInstance.Done()
    # TODO restore keys (this is a patch that needs to be changed)
    for h in humans.keys():
        humans[h].pos = humans[h].map



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