from creator.Creator import Creator, LifetimeCreator
from gedcom.GedcomParser import GedcomParser
from kml.KmlExporter import KmlExporter
from kml.foliumExp import foliumExporter
from kml.KmlExporter import KmlExporter
from kml.gpslookup import GEDComGPSLookup
from models.Pos import Pos
from gedcomoptions import gvOptions
import webbrowser

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
        
        lifeline = Creator(humans, gOp.MaxMissing) 
        creator = lifeline.create(gOp.Main)
        if gOp.AllEntities:
            lifeline.createothers(creator)
            print (f"Total of {len(creator)} people.")  

        if gOp.Main not in humans:
            print ("Could not find your starting person: {}".format(gOp.Main))
            gOp.step('Error could not fine first person')
            return
        gOp.setMainName(humans[gOp.Main].name)
        if (not kmlInstance):
            kmlInstance = KmlExporter(gOp)
        kmlInstance.export(humans[gOp.Main].pos, creator, nametag)
    kmlInstance.Done()


def Geoheatmap(gOp : gvOptions):
    
    humans = ParseAndGPS(gOp)
    doHTML(gOp, humans)

def doHTML(gOp : gvOptions, humans):
    if (not humans):
        return
    lifeline = LifetimeCreator(humans, gOp.MaxMissing)    
    creator = lifeline.create(gOp.Main)    
    if gOp.Main not in humans:
        print ("Could not find your starting person: {}".format(gOp.Main))
        gOp.step('Error could not fine first person')
        return
    gOp.setMainName(humans[gOp.Main].name)
    if gOp.AllEntities:
        gOp.step('Creating life line for everyone')
        lifeline.createothers(creator)
        print (f"Total of {len(creator)} people.")   
    gOp.totalpeople = len(creator)
    foliumExporter(gOp).export(humans[gOp.Main], creator)
    webbrowser.open(gOp.Result, new = 0, autoraise = True)
        
    


def ParseAndGPS(gOp: gvOptions):

    print ("Starting parsing of GEDCOM :".format(gOp.GEDCOMinput))
    humans = GedcomParser(gOp).create_humans()
    gOp.parsed = True
    gOp.goodmain = False
    if (humans and gOp.UseGPS):
        print ("Starting Address to GPS resolution")
        # TODO This could cause issues
        # Check for change in the datetime of CSV
        if gOp.lookup:
            lookupresults = gOp.lookup
        else:
            lookupresults = GEDComGPSLookup(humans, gOp)
            gOp.lookup = lookupresults
        lookupresults.resolveaddresses(humans)
        gOp.step('Saving Address Cache')
        lookupresults.saveAddressCache()
        print ("Completed resolves")
    
    if humans and not gOp.Main:
        gOp.set('Main', list(humans.keys())[0])
        print ("Using starting person: {} ({})".format(humans[gOp.Main].name, gOp.Main))
    gOp.step('Creating life line')
    return humans