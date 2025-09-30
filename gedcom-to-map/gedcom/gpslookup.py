__all__ = ['Xlator', 'WordXlator', 'GEDComGPSLookup']

import logging
_log = logging.getLogger(__name__)

import csv
import hashlib
import json
import os.path
from pathlib import Path
import re
import tempfile
import time
import requests
import platform
from typing import Optional, Tuple, Dict, List
from datetime import datetime

from const import GV_COUNTRIES_JSON, GV_STATES_JSON, GEOCODEUSERAGENT
from gedcomoptions import gvOptions
import certifi
import ssl
import geopy.geocoders
from geopy.geocoders import Nominatim
from models.Person import Person, LifeEvent
from models.LatLon import LatLon




# TODO This needs to be moved into it's out JSON driven configuration
fixuplist   = {r'\spart of\s' : ' ', 
               r'\bof\s': '',
               r'po box [0-9]+\s' : ' ', 
               r'\([\w\s\.]+\)' : '',
               '(town)' : '', 
               '(town/ville)' : '',
               '(west/ouest)' : '',
               'Upper Canada, British Colonial America': 'Ontario, Canada',
               'Lower Canada, British Colonial America': 'Quebec, Canada',
               'British Colonial America': 'Canada'} 
wordfixlist = {'of': '',
               r'co\.' : 'county', 
               r'twp\.': 'township',
               r'tp\.': 'township', 
               r'tp': 'township'}

geoapp = None
cache_filename = (r"geodat-address-cache.csv", r"geodat-address-cache-1.csv", r"geodat-address-cache-2.csv")
csvheader = ['name','alt','country','type','class','icon', 'place_id','lat','long', 'boundry', 'size', 'importance', 'used']
defaultcountry = "CA"
geoappContext = ssl.create_default_context(cafile=certifi.where())
geopy.geocoders.options.default_ssl_context = geoappContext

# The cache files should not change, but they might in the future.  There should be an option to clear the cache files.   #TODO
def readCachedURL(cfile, url):
    nfile = os.path.join(tempfile.gettempdir() , cfile)
    if not os.path.exists(nfile):
        _log.debug("Attempting to request %s as %s", url, nfile)
        webUrl  = requests.get(url)
        data = webUrl.content
        _log.debug("request read, saving to %s", nfile)
        with open(nfile, 'wb') as file:
            file.write(data)
        
    return open(nfile, 'rb').read()

def getattr(line, attr):
    if attr in line.keys():
        return line[attr]
    else:
        return None


class Xlator(dict):
    """ All-in-one multiple-string-substitution class """
    def _make_regex(self):
        """ Build re object based on the keys of the current dictionary """
        return re.compile("|".join(map(re.escape, self.keys(  ))))

    def __call__(self, match):
        """ Handler invoked for each regex match """
        return self[match.group(0)]

    def xlat(self, text):
        """ Translate text, returns the modified text. """
        return self._make_regex(  ).sub(self, text)


class WordXlator(Xlator):
    """ An Xlator version to substitute only entire words """
    def _make_regex(self):
        return re.compile(
          r'\b'+r'\b|\b'.join(map(re.escape, self.keys(  )))+r'\b')
    
class GEDComGPSLookup:
    def __init__(self, people,  gvO: gvOptions):

        self.addresses = None
        self.addresslist = None
        self.usecacheonly = gvO.get('CacheOnly')
        self.gOptions = gvO 
        self.orgMD5 = None
        self.people = people
        self.countrieslist = None
        self.Geoapp = None
        
        global BackgroundProcess
        BackgroundProcess = gvO.BackgroundProcess

        # Build the user agent string using OS and architecture details used for making our agent string
        self.geocodeUserAgent = f"{GEOCODEUSERAGENT} ({platform.system()} {platform.release()}; {platform.machine()})"
        self.stats = ""
        self.used = 0
        self.usedNone = 0
        self.totaladdr = 0
      
        # This pulls from the same directory as GEDCOM file
        if self.gOptions.resultpath:
            cachefile = os.path.join(self.gOptions.resultpath, cache_filename[0])
            self.gOptions.set('gpsfile', cachefile )     
            if os.path.exists(cachefile):
          
                with open(cachefile,  newline='', encoding='utf-8') as csvfile:
                    readfrom = csv.DictReader(csvfile, dialect='excel')
                    try: 
                    
                        for line in readfrom:
                            if self.addresslist:
                                self.addresslist.extend([line])
                            else:
                                self.addresslist = [line]
                        
                    except csv.Error as e:
                        _log.error  ('Error reading GPS cache file %s, line %d: %s', cache_filename[0], readfrom.line_num, e)
             
        if (self.addresslist):
            self.gOptions.step('Loading Geocode Cache')
            self.addresses = dict()
            
            self.addressalt = dict()
            
            for a in range(0,len(self.addresslist)):
                if self.addresslist[a]['name'] !='': 
                    
                    # due to values being Ascii or unicode or utl-8, the file and data needs to be treated carefully
                    self.addresslist[a]['boundry'] = None if self.addresslist[a]['boundry'] == '' else eval(self.addresslist[a]['boundry'])
                    if hasattr(self.addresslist[a], 'size'):
                        self.addresslist[a]['size'] = 0 if self.addresslist[a]['size'] == '' else float(self.addresslist[a]['size'])
                    else:
                        self.addresslist[a]['size'] = 0 
                    self.addresslist[a]['lat'] = None if self.addresslist[a]['lat'] == '' else self.addresslist[a]['lat']
                    self.addresslist[a]['long'] = None if self.addresslist[a]['long'] == '' else self.addresslist[a]['long']
                    # Clear the 'used' column so we can count reference
                    self.addresslist[a]['used'] = 0
                    self.addresses[self.addresslist[a]['name'].lower()]= self.addresslist[a]
                    self.addressalt[self.addresslist[a]['alt'].lower()]= self.addresslist[a]['name']
            _log.info ("Loaded %d cached records", len(self.addresses))
            #
            # Make the checksum for checking later to see if the table has changed
            #
            self.orgMD5 = hashlib.md5()
            for a in self.addresses.keys():
                if self.addresses[a]['name'] !='': 
                    self.orgMD5.update((self.addresses[a]['name'] +  self.addresses[a]['alt'] +  
                             str(self.addresses[a]['lat']) +  str(self.addresses[a]['long'])).encode(errors='ignore'))
            self.gOptions.step("Loaded {} cached records".format(len(self.addresses)))
            self.addresslist = None
        else:
            _log.info ("No GPS cached addresses to use")
            self.gOptions.step("No GPS cached addresses")
        
        
        
        # Cache up and don't reload if it we have it already

        if not self.countrieslist:
            
            self.gOptions.step("Loading Countries/states")
            data = readCachedURL ('gv.countries.json', GV_COUNTRIES_JSON)
        
            self.countrieslist = json.loads(data)
            self.countrynames=dict()
            self.countryname3=dict()
            self.countries=dict()
            for c in range(0,len(self.countrieslist)): 
                self.countrynames[self.countrieslist[c]['iso2']] = self.countrieslist[c]['name'].lower()
                self.countryname3[self.countrieslist[c]['iso3']] = self.countrieslist[c]['name'].lower()
                self.countries[self.countrieslist[c]['name'].lower()] = self.countrieslist[c]
            
        
            data = readCachedURL ('gv.states.json', GV_STATES_JSON)
            self.stateslist = json.loads(data)
            self.states=dict()
            for c in range(0,len(self.stateslist)): 
                self.states[(self.stateslist[c]['name']).lower()] = self.stateslist[c]
            self.wordxlat = WordXlator(wordfixlist)
            self.xlat = Xlator(fixuplist)
        self.updatestats()
    
        
    def updatestats(self):
        self.used = 0
        self.usedNone = 0
        self.totaladdr = 0
        if hasattr(self, 'addresses') and self.addresses:
            for xaddr in self.addresses.keys():
                
                if (self.addresses[xaddr]['used'] > 0): 
                    self.used += 1
                    self.totaladdr += self.addresses[xaddr]['used']
                    if (self.addresses[xaddr]['lat'] is None): self.usedNone += 1
        hit = 1-(self.usedNone / self.used) if self.used > 0 else 0
        self.stats = f"Unique addresses: {self.used} with unresolvable: {self.usedNone}\nAddress hit rate {hit:.1%}\n"
        

    def saveAddressCache(self):
        if self.usecacheonly or self.gOptions.ShouldStop():
            return
        # Nothing to save ?? and has not changed
        newMD5 = hashlib.md5()
        if self.addresses:
            for a in self.addresses.keys():
                if self.addresses[a]['name'] !='': 
                    newMD5.update((self.addresses[a]['name'] +  self.addresses[a]['alt'] +  
                             str(self.addresses[a]['lat']) +  str(self.addresses[a]['long'])).encode(errors='ignore'))
            if self.orgMD5 and newMD5.hexdigest() == self.orgMD5.hexdigest():
                _log.debug("GPS Cache has not changed")
                return
        else:
            _log.warning("No Addresses in addresslist")
        n = ['','','']
        if self.addresses:
            resultpath = self.gOptions.resultpath
            self.gOptions.step("Saving GPS Cache", resetCounter=False)
            # Rotate cache files for backup
            cache_files = [os.path.join(resultpath, fname) for fname in cache_filename]
            # Remove oldest backup if it exists
            if os.path.exists(cache_files[2]):
                try:
                    os.remove(cache_files[2])
                except Exception as e:
                    _log.error(f"Error removing {cache_files[2]}: {e}")
            # Shift backups
            for i in [1, 0]:
                if os.path.exists(cache_files[i]):
                    try:
                        os.rename(cache_files[i], cache_files[i+1])
                    except Exception as e:
                        _log.error(f"Error renaming {cache_files[i]} to {cache_files[i+1]}: {e}")
            self.gOptions.set('gpsfile', cache_files[0])

            # Prepare the cache file path
            cache_file_path = os.path.join(resultpath, cache_filename[0])
            with open(cache_file_path, "w", newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=csvheader, dialect='excel')
                writer.writeheader()

                for addr_key, addr in self.addresses.items():
                    # Ensure boundary values are floats
                    if addr['boundry']:
                        addr['boundry'] = [float(b) for b in addr['boundry']]

                    # Calculate size if missing
                    if addr['size'] is None or addr['size'] == '':
                        boundry = addr['boundry']
                        if boundry and len(boundry) == 4:
                            addr['size'] = abs(boundry[1] - boundry[0]) * abs(boundry[3] - boundry[2]) * 1_000_000
                        else:
                            addr['size'] = None

                    # Prepare row for writing
                    row = {
                        'name': addr['name'],
                        'alt': addr['alt'],
                        'country': addr['country'],
                        'type': addr['type'],
                        'class': addr['class'],
                        'icon': addr['icon'],
                        'place_id': addr['place_id'],
                        'lat': addr['lat'],
                        'long': addr['long'],
                        'boundry': addr['boundry'],
                        'size': addr['size'],
                        'importance': addr['importance'],
                        'used': addr['used']
                    }
                    writer.writerow(row)
            _log.debug("GPS Cache saved")    
                
        self.updatestats()
        _log.info("Unique addresses: %d with %d have missing GPS for a Total of %d",self.used, self.usedNone, self.totaladdr)   
        
        self.gOptions.step(f"Cache Table is {self.totaladdr} addresses", resetCounter=False)  

        
    def improveaddress(self,theaddress, thecountry= None):

        # Check for the going in country code and add it if it is missing
        if thecountry:
            if not re.findall(self.countrynames[thecountry.upper()] + "$", theaddress.strip().lower()) :
                theaddress = theaddress + ", " + self.countrynames[thecountry.upper()]
            return (theaddress, thecountry.upper())    
        
        # Check for the country name, if that is found, then geocoding should land on the right country
        # Check for the state name, if that is found, then add country to the geocoding to get the right country
        # Loop thru twice for countries with two words
        for i in (0,1):
            lastwords = re.findall(r"[\s,]((\w+){"+ str(i) + r"}\s?\w+)$",theaddress.strip())
        
            # the last word should be the country
            if not lastwords:
                return (theaddress, None)
            lastword = lastwords[0][0].strip()

            theaddress = theaddress.replace("'","\'")
            
            if lastword.upper() in self.countrynames.keys():
                trycountrycode = self.countries[self.countrynames[lastword.upper()]]['iso2']
                return (theaddress, trycountrycode)
            if lastword.upper() in self.countryname3.keys():
                trycountrycode = self.countries[self.countryname3[lastword.upper()]]['iso2']
                return (theaddress, trycountrycode)

            # it has a valid country already stop improving
            if lastword.lower() in self.countries.keys():
                trycountrycode = self.countries[lastword.lower()]['iso2']
                return (theaddress, trycountrycode)

            # the checked for countries and it was not found, check for prov/state
            if lastword.lower() in self.states.keys():
            
                trycountrycode = self.states[lastword.lower()]['country_code']
                return (theaddress + ", " + self.countrynames[trycountrycode], trycountrycode)
        return (theaddress, None)    

  #
  # Other things to build:
  # Take the county name out of the name.  That could be by looking for County or Co. and if there is words before that drop them
  # Take the township out of the name.  It could be just drop the 'Twp.' or township from the name.
  # look for township reference which is a single 1 or 2 digit number at the start followed by a coma, ... most likely a township reference
  
    def refineaddress(self,theaddress):
        
        return theaddress
  #  
  #
  #
           

    def returnandcount(self, name):
        name = name.lower()
        # if self.addresses[name]['size'] and self.addresses[name]['used'] == 0 and self.addresses[name]['size'] > 100000:
        #        _log.debug(" !Large location for: {} ({})".format(self.addresses[name]['name'], self.addresses[name]['size']))
        self.addresses[name]['used'] += 1
        # This large areas maps the trace look wrong, because they are most likely a state or provience.  Flag them to the user.
        return LatLon(self.addresses[name]['lat'], self.addresses[name]['long'])
    
    def lookupaddresses(self, myaddress, addressdepth=0):
        self.gOptions.step(info=myaddress, resetCounter=False)  
        self.usecacheonly = self.gOptions.get('CacheOnly')          # Refresh as it could have changed since _init_
        addressindex = None
        theaddress = None
        trycountry = ""

       
        if myaddress:
            _log.debug("### %d %s", addressdepth, myaddress)
            if self.addresses:
                # straight up, is it a valid existing cached address?
                if myaddress.lower() in self.addresses.keys():
                    addressindex = myaddress.lower()
                # okay then , check the alternate cached addresses?
                elif myaddress.lower() in self.addressalt.keys():
                    # TODO Set the Lat/Long of this source record
                    a = self.addresses[self.addressalt[myaddress.lower()].lower()]
                    ps = (self.lookupaddresses(a['name'], addressdepth+1))
                    if (ps.lat and ps.lon):
                        # Do we need to look this up?
                        if (not self.addresses[self.addressalt[myaddress.lower()].lower()]['lat']):
                            _log.debug ("##* Updated POS\t%s\t%s %f,%f", a['name'], self.addressalt[myaddress.lower()].lower(), ps.lat, ps.lon)
                    (self.addresses[self.addressalt[myaddress.lower()].lower()]['lat'] , self.addresses[self.addressalt[myaddress.lower()].lower()]['long']) = (ps.lat, ps.lon)
                    (self.addresses[a['name'].lower()]['lat'], self.addresses[a['name'].lower()]['lon']) = (ps.lat, ps.lon)
                    
                 
                    return ps
                    #   addressindex = self.addressalt[myaddress.lower()].lower()
                    #   if (self.addresses[addressindex]['name'] != self.addresses[addressindex]['alt']):
                        
                if (addressindex):         
                # We have a Cache match, but is there any Lat/Long there?
                    if self.addresses[addressindex]['lat'] and self.addresses[addressindex]['lat']:
                        return self.returnandcount(addressindex)
                      
                 
                        # Try using an alternate name from the cache
                    if self.addresses[addressindex]['name'].lower() == self.addresses[addressindex]['alt'].lower():
                        return self.returnandcount(addressindex)
            trycountry = None
            if (self.usecacheonly):
                theaddress = myaddress
            else:
                if addressindex:
                    (theaddress, trycountry) = self.improveaddress(myaddress, self.addresses[addressindex]['country'])
                else:
                    (theaddress, trycountry) = self.improveaddress(myaddress)
              
          
            if self.addresses and theaddress.lower() in self.addresses.keys():
                addressindex = theaddress.lower()
                if self.addresses[addressindex]['lat'] and self.addresses[addressindex]['lat']:
                    return self.returnandcount(addressindex)
                else: 
                    if theaddress in self.addressalt.keys():
                        if self.addresses[addressindex]['name'].lower() == self.addresses[addressindex]['alt'].lower():
                            return self.returnandcount(addressindex)
                        # We have tried alternate  (This is a bit of a hack with the 4 but it works)
                if self.addresses[addressindex]['name'].lower() != self.addresses[addressindex]['alt'].lower() and addressdepth < 4 :
                    # TODO Set the Lat/Long of this source record
                    a = self.addresses[addressindex]['alt'].lower()
                    ps = (self.lookupaddresses(a, addressdepth+1))
                    if (ps.lat and ps.lon):
                        (self.addresses[addressindex]['lat'] , self.addresses[addressindex]['long']) = (ps.lat, ps.lon)
                        _log.debug ("## Updated POS\t%s %f,%f", self.addresses[addressindex]['name'], ps.lat, ps.lon)
                    else: 
                        _log.debug ("## Cannot resolve address\t%s", self.addresses[addressindex]['name'])
                    return ps

                  
                # Been here looked this up
                if self.addresses[addressindex]['used'] > 0:
                    return self.returnandcount(addressindex)
                if self.addresses[addressindex]['name'].lower() != self.addresses[addressindex]['alt'].lower()  and addressdepth > 0:
                    return self.returnandcount(addressindex)


            # Been here and looked this up before
            if self.addresses and myaddress.lower() in self.addresses.keys():
                if self.addresses[myaddress.lower()]['name'].lower() == myaddress.lower() and self.addresses[myaddress.lower()]['alt'].lower() == theaddress.lower():
                    return self.returnandcount(myaddress)
                else:
                    # The user gave a new address???
                    theaddress = self.addresses[myaddress.lower()]['alt'].lower()
            if self.addresses and theaddress.lower() in self.addresses.keys():
                _log.debug ("#BBefore ??? %s\n\t%s\n\t%s", theaddress.lower() in self.addresses.keys(), self.addresses[addressindex]['name'], self.addresses[addressindex]['alt'])
            if (self.usecacheonly):
                return (LatLon(None,None))
            usedGeocode = False
            if (len(theaddress)>0):
                _log.debug(":Lookup: %s +within+ %s::", theaddress, trycountry)
                try:
                    usedGeocode = True
                    location = self.Geoapp.geocode(theaddress, country_codes=trycountry, timeout=5)
                except:
                    _log.error("Error: Geocode %s", theaddress)
                    time.sleep(1)  # extra sleep time
                    location = None
            else:
                _log.info(":Lookup: %s ::", myaddress)
                try:
                    usedGeocode = True
                    location = self.Geoapp.geocode(myaddress)
                except:
                    _log.error("Error: Geocode %s", myaddress)
                    time.sleep(1)     # extra sleep time
                    location = None
            if location:
                location = location.raw
                _log.info(location['display_name'])
                boundrybox = getattr(location, 'boundingbox')
                bsize = abs(float(boundrybox[1])-float(boundrybox[0])) * abs(float(boundrybox[3])-float(boundrybox[2]))*1000000
                locrec = {'name': myaddress, 'alt' : getattr(location, 'display_name'), 'country' : trycountry, 'type': getattr(location, 'type'), 'class': getattr(location,'class'), 'icon': getattr(location,'icon'),
                                'place_id': getattr(location,'place_id'), 'lat': getattr(location, 'lat'),
                                'long': getattr(location, 'lon'), 'boundry' : boundrybox, 'importance': getattr(location, 'importance'), 'size': bsize, 'used' : 0}
              
            else:
                _log.info("----none---- for %s", myaddress)
                locrec = {'name': myaddress, 'alt' : theaddress, 'country' : trycountry, 'type': None, 'class':None, 'icon':None,'place_id': None,'lat': None, 'long': None, 'boundry' : None, 'importance': None, 'size': None, 'used' : 0}

            if usedGeocode:
                # https://operations.osmfoundation.org/policies/nominatim/
                #       "No heavy uses (an absolute maximum of 1 request per second)."
                time.sleep(1)         # Go slow so since Nominatim limits the speed for a free service
                        
          
            if not self.addresses:
                self.addresses=dict()
                self.addressalt=dict()
            if locrec['name'].lower() in self.addresses.keys():
                _log.debug ("#UU=%s Changed\n\t%s\n\t%s", self.addresses[locrec['name'].lower()]['used'], myaddress, theaddress)

            self.addresses[locrec['name'].lower()]= locrec
            self.addressalt[locrec['alt'].lower()]= locrec['name'].lower()
          
            if location:
                return self.returnandcount(locrec['name'])
        return LatLon(None,None)
     
   
    def resolve_addresses(self, people):
        donesome = 0
        nowis =  datetime.now()
        # Update the Grid in 60 seconds if we are still doing this loop
        startis = nowis.timestamp() + 15
        if hasattr(self, 'addresses') and self.addresses:
            donesome = len(self.addresses)
        self.Geoapp = Nominatim(user_agent=self.geocodeUserAgent)  
        self.gOptions.step("Lookup addresses")
        target = 0
        for person in people:
            ho = people[person]
            if ho:
                target += (1 if (ho.birth and ho.birth.where) else 0) + (1 if ho.death and ho.death.where else 0)
                if ho.home:
                    target += len(ho.home)
        self.gOptions.step("Lookup addresses", target=target)
        gpsstep = 0
        for person in people:
            if self.gOptions.ShouldStop():
                self.saveAddressCache()
                break

            person_obj = people[person]
        
            # Resolve birth address
            if person_obj.birth and person_obj.birth.where:
                person_obj.birth.pos = self.lookupaddresses(person_obj.birth.where)
                _log.debug(f"{person_obj.name:30} @ B {person_obj.birth.where:60} = {person_obj.birth.pos}")
        
            # Resolve home address
            if person_obj.home:
                for home in person_obj.home:
                    if home.where:
                        home.pos = self.lookupaddresses(home.where)
        
            # Resolve death address
            if person_obj.death and person_obj.death.where:
                person_obj.death.pos = self.lookupaddresses(person_obj.death.where)
                _log.debug(f"{person_obj.name:30} @ D {person_obj.death.where:60} = {person_obj.death.pos}")
            if self.addresses:
                if len(self.addresses) - donesome > 512 or datetime.now().timestamp() - nowis.timestamp() > 300:  # Every 5 minutes or 512 addresses save Addresses
                    _log.info(f"************** Saving cache {donesome} {len(self.addresses)}")
                    self.saveAddressCache()
                    donesome = len(self.addresses)
                    nowis =  datetime.now()
            if startis < datetime.now().timestamp():
                BackgroundProcess.updategrid = True
                BackgroundProcess.updateinfo= f"Updating with {len(people)} people while resolving some addresses ({len(self.addresses)})" 
                startis = datetime.now().timestamp() + 60  # update again in a minutes

            # Hack Step info because when we redraw the grid they overlap
            if self.gOptions.state == "":
                self.gOptions.step("Lookup addresses", target=target)
                self.gOptions.stepCounter(gpsstep)
            gpsstep += 1

        self.updatestats()
        self.gOptions.step("Resolved addresses", target=0)



        
            
   
