import time
import csv
import os.path
import tempfile
import json
import urllib.request
# import pyap
import re
import hashlib

from models.Human import Human, LifeEvent
from models.Pos import Pos

from geopy.geocoders import Nominatim
from pprint import pprint
from gedcomoptions import gvOptions

fixuplist   = {r'\bof\s': '',
               r'\spart of\s' : ' ', 
               r'po box [0-9]+\s' : ' ', 
               '(town)' : '', 
               '(town/ville)' : '',
               'Upper Canada, British Colonial America': 'Ontario, Canada',
               'Lower Canada, British Colonial America': 'Quebec, Canada',
               'British Colonial America': 'Canada'} 
wordfixlist = {'of': '',
               r'co\.' : 'county', 
               r'twp\.': 'township'}

geoapp = None
cache_filename = (r"geodat-address-cache.csv", r"geodat-address-cache-1.csv", r"geodat-address-cache-2.csv")

csvheader = ['name','alt','country','type','class','icon', 'place_id','lat','long', 'boundry', 'size', 'importance', 'used']
debug = False

defaultcountry = "CA"

   
def readCachedURL(cfile, url):
    nfile = os.path.join(tempfile.gettempdir() , cfile)
    if not os.path.exists(nfile):
        webUrl  = urllib.request.urlopen(url)
        data = webUrl.read()
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
    def __init__(self, humans,  gvOptions: gvOptions):    
        self.addresses = None
        self.addresslist = None
        self.usecacheonly = not gvOptions.UseGPS
        self.gOptions = gvOptions 
        self.orgMD5 = None
        self.humans = humans
      
        # This pulls from the same directory as GEDCOM file
        if gvOptions.resultpath:
            cachefile = os.path.join(gvOptions.resultpath, cache_filename[0])
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
                        print ('Error reading GPS cache file {}, line {}: {}'.format(cache_filename[0], readfrom.line_num, e))
             
        if (self.addresslist):
            self.addresses = dict()
            
            self.addressalt = dict()
            
            self.orgMD5 = hashlib.md5()    
            for a in range(0,len(self.addresslist)):
                if self.addresslist[a]['name'] !='': 
                    
                    # self.addresslist[a]['name'] = bytearray(self.addresslist[a]['name'],encoding='utf-8').decode('unicode_escape').strip("'") 
                    # self.addresslist[a]['alt'] = bytearray(self.addresslist[a]['alt'],encoding='utf-8').decode('unicode_escape').strip("'") 
                    self.addresslist[a]['boundry'] = None if self.addresslist[a]['boundry'] == '' else eval(self.addresslist[a]['boundry'])
                    self.addresslist[a]['size'] = 0 if self.addresslist[a]['size'] == '' else float(self.addresslist[a]['size'])
                    self.addresslist[a]['lat'] = None if self.addresslist[a]['lat'] == '' else self.addresslist[a]['lat']
                    self.addresslist[a]['long'] = None if self.addresslist[a]['long'] == '' else self.addresslist[a]['long']
                    # Clear the 'used' column so we can count reference
                    self.addresslist[a]['used'] = 0
                    self.addresses[self.addresslist[a]['name'].lower()]= self.addresslist[a]
                    self.addressalt[self.addresslist[a]['alt'].lower()]= self.addresslist[a]['name']
                    self.orgMD5.update((self.addresslist[a]['name'] +  
                         self.addresslist[a]['alt'] +  
                         str(self.addresslist[a]['lat']) +  
                         str(self.addresslist[a]['long'])).encode(errors='ignore'))
            print ("Loaded {} cached records".format(len(self.addresses)))    
            self.gOptions.step("Loaded {} cached records".format(len(self.addresses)))
        else:
            print ("No GPS cached addresses to use")
            self.gOptions.step("No GPS cached addresses")
        
        
        
        # Cache up and don't reload if it we have it already

        if not (hasattr(self, 'countrieslist') and self.countrieslist):
            
            self.gOptions.step("Loading Countries/states")
            data = readCachedURL ('gv.countries.json', 'https://raw.githubusercontent.com/nnjeim/world/master/resources/json/countries.json')
        
            self.countrieslist = json.loads(data)
            self.countrynames=dict()
            self.countryname3=dict()
            self.countries=dict()
            for c in range(0,len(self.countrieslist)): 
                self.countrynames[self.countrieslist[c]['iso2']] = self.countrieslist[c]['name'].lower()
                self.countryname3[self.countrieslist[c]['iso3']] = self.countrieslist[c]['name'].lower()
                self.countries[self.countrieslist[c]['name'].lower()] = self.countrieslist[c]
            
        
            data = readCachedURL ('gv.states.json', 'https://raw.githubusercontent.com/nnjeim/world/master/resources/json/states.json')
            self.stateslist = json.loads(data)
            self.states=dict()
            for c in range(0,len(self.stateslist)): 
                self.states[(self.stateslist[c]['name']).lower()] = self.stateslist[c]
            self.wordxlat = WordXlator(wordfixlist)
            self.xlat = Xlator(fixuplist)

    def saveAddressCache(self):
        if self.usecacheonly or self.gOptions.ShouldStop():
            return
        # Nothing to save ?? and has not changed
        newMD5 = hashlib.md5()
        if self.addresslist:
            for a in range(0,len(self.addresslist)):
              if self.addresslist[a]['name'] !='': 
                newMD5.update((self.addresslist[a]['name'] +  
                         self.addresslist[a]['alt'] +  
                         str(self.addresslist[a]['lat']) +  
                         str(self.addresslist[a]['long'])).encode(errors='ignore'))
            if newMD5.hexdigest() == self.orgMD5.hexdigest():
                print("*Warning* Blank GPS Cache has not changed")
                return
        else:
            print("**Warning No Addresses in addresslist")
        used = 0
        usedNone = 0
        totaladdr = 0
        if self.addresses:
            resultpath = self.gOptions.resultpath
            self.gOptions.step("Saving GPS Cache")
            
            if (os.path.exists(os.path.join(resultpath,cache_filename[0]))):
                  if (os.path.exists(os.path.join(resultpath,cache_filename[1]))):
                    if (os.path.exists(os.path.join(resultpath,cache_filename[2]))):
                       try:
                          os.remove(os.path.join(resultpath,cache_filename[2]))
                       except:
                           print("**Error removing {}".format(os.path.join(resultpath,cache_filename[2])))
                    try:
                       os.rename(os.path.join(resultpath,cache_filename[1]), os.path.join(resultpath,cache_filename[2]))
                    except:
                           print("**Error renaming {}".format(os.path.join(resultpath,cache_filename[1])))
                  try:
                     os.rename(os.path.join(resultpath,cache_filename[0]), os.path.join(resultpath,cache_filename[1]))
                  except:
                     print("**Error renaming {}".format(os.path.join(resultpath,cache_filename[0])))
            self.gOptions.set('gpsfile', os.path.join(resultpath,cache_filename[0]))     
            with open(os.path.join(resultpath,cache_filename[0]), "w", newline='', encoding='utf-8') as csvfile:
                
                csvwriter = csv.writer(csvfile, dialect='excel' )
                csvwriter.writerow(csvheader)
                
                for xaddr in self.addresses.keys():
                    # TODO Short term fix
                    if self.addresses[xaddr]['boundry']:
                            for i in (range(0,len(self.addresses[xaddr]['boundry']))):
                               self.addresses[xaddr]['boundry'][i] = float(self.addresses[xaddr]['boundry'][i])
                    if self.addresses[xaddr]['size'] is None or self.addresses[xaddr]['size'] == '':
                        boundrybox = self.addresses[xaddr]['boundry']
                        if boundrybox:
                            self.addresses[xaddr]['size'] = abs(boundrybox[1]-boundrybox[0]) * abs(boundrybox[3]-boundrybox[2])*1000000
                        else:
                            self.addresses[xaddr]['size'] = None
                    # TODO deal with Unicode names

                    r = [self.addresses[xaddr]['name'], 
                         self.addresses[xaddr]['alt'], 
                         self.addresses[xaddr]['country'],
                         self.addresses[xaddr]['type'],
                         self.addresses[xaddr]['class'],
                         self.addresses[xaddr]['icon'],
                         self.addresses[xaddr]['place_id'],
                         self.addresses[xaddr]['lat'], 
                         self.addresses[xaddr]['long'],
                         self.addresses[xaddr]['boundry'],
                         self.addresses[xaddr]['size'],
                         self.addresses[xaddr]['importance'],
                         self.addresses[xaddr]['used']
                         ]
                    
                    csvwriter.writerow(r)
                for xaddr in self.addresses.keys():
                
                    if (self.addresses[xaddr]['used'] > 0): 
                        used += 1
                        totaladdr += self.addresses[xaddr]['used']
                        if (self.addresses[xaddr]['lat'] is None): usedNone += 1

        print("Unique addresses: {} and {} have missing GPS for a Total of {}".format(used, usedNone, totaladdr))   
        self.gOptions.step(f"Saved {totaladdr} addresses")  

        
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
            lastwords = re.findall("[\s,]((\w+){"+ str(i) + "}\s?\w+)$",theaddress.strip())
        
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
        #        print(" !Large location for: {} ({})".format(self.addresses[name]['name'], self.addresses[name]['size']))
        self.addresses[name]['used'] += 1
        # This large areas maps the trace look wrong, because they are most likely a state or provience.  Flag them to the user.
        return Pos(self.addresses[name]['lat'], self.addresses[name]['long'])
    
    def lookupaddresses(self, myaddress, addressdepth=0):
       self.gOptions.step(info=myaddress)  
       addressindex = None
       theaddress = None
       trycountry = ""

       
       if myaddress:
          if (debug): print ("### {} {}".format( addressdepth, myaddress))
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
                        print ("##* Updated POS\t{}\t{} {},{}".format(a['name'], self.addressalt[myaddress.lower()].lower(), ps.lat, ps.lon))
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
                    print ("## Updated POS\t{} {},{}".format(self.addresses[addressindex]['name'], ps.lat, ps.lon))
                 
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
              print ("#BBefore ??? {}\n\t{}\n\t{}".format(theaddress.lower() in self.addresses.keys(), self.addresses[addressindex]['name'], self.addresses[addressindex]['alt']))          
          if (self.usecacheonly):
              return (Pos(None,None))
          if (len(theaddress)>0):
              print(":Lookup: {} +within+ {}::".format(theaddress, trycountry), end=" ")
              try:
                  location = self.Geoapp.geocode(theaddress, country_codes=trycountry)
              except:
                  print("Error: Geocode {}".format(theaddress))
                  time.sleep(1)  # extra sleep time
                  location = None
          else:
              print(":Lookup: {} ::".format(myaddress), end=" ")
              try:
                  location = self.Geoapp.geocode(myaddress)
              except:
                  print("Error: Geocode {}".format(myaddress))
                  time.sleep(1)     # extra sleep time
                  location = None
          if location:
              location = location.raw
              print(location['display_name'])
              boundrybox = getattr(location, 'boundingbox')
              bsize = abs(float(boundrybox[1])-float(boundrybox[0])) * abs(float(boundrybox[3])-float(boundrybox[2]))*1000000
              locrec = {'name': myaddress, 'alt' : getattr(location, 'display_name'), 'country' : trycountry, 'type': getattr(location, 'type'), 'class': getattr(location,'class'), 'icon': getattr(location,'icon'),
                                'place_id': getattr(location,'place_id'), 'lat': getattr(location, 'lat'),
                                'long': getattr(location, 'lon'), 'boundry' : boundrybox, 'importance': getattr(location, 'importance'), 'size': bsize, 'used' : 0}
              
          else:
              print("----none----")
              locrec = {'name': myaddress, 'alt' : theaddress, 'country' : trycountry, 'type': None, 'class':None, 'icon':None,'place_id': None,'lat': None, 'long': None, 'boundry' : None, 'importance': None, 'size': None, 'used' : 0}
          time.sleep(1)         # Go slow so since Nominatim limits the speed for a free service
          
          if not self.addresses:
             self.addresses=dict()
             self.addressalt=dict()
          if locrec['name'].lower() in self.addresses.keys():
                print ("#UU={} Changed\n\t{}\n\t{}".format(self.addresses[locrec['name'].lower()]['used'], myaddress, theaddress))

          self.addresses[locrec['name'].lower()]= locrec
          self.addressalt[locrec['alt'].lower()]= locrec['name'].lower()
          
          if location:
             return self.returnandcount(locrec['name'])
       return Pos(None,None)
     
   
    def resolveaddresses(self, humans):

        self.Geoapp = Nominatim(user_agent="GEDCOM-to-map-folium")  
        self.gOptions.step("Lookup addresses")
        for human in humans:
            if self.gOptions.ShouldStop():
                break
            if (humans[human].birth and humans[human].birth):
                humans[human].birth.pos = self.lookupaddresses(humans[human].birth.where)
                # print ("{:30} @ B {:60} = {}".format(humans[human].name, humans[human].birth.where if humans[human].birth.where else '??', humans[human].birth.pos ))
            if (humans[human].home):
               for homs in (range(0,len(humans[human].home))):
                   h = humans[human].home[homs]
                   if (humans[human].home[homs].where):
                      humans[human].home[homs].pos = self.lookupaddresses(humans[human].home[homs].where)
            if (humans[human].death and humans[human].death.where):
                humans[human].death.pos = self.lookupaddresses(humans[human].death.where)
                # print ("{:30} @ D {:60} = {}".format(humans[human].name, humans[human].death.where, humans[human].death.pos ))
            
   
