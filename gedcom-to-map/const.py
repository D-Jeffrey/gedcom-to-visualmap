"""Constants for gedcom-to-visualmap"""

VERSION = "0.2.6.0"
NAME = "gedcom-to-visualmap"
GEOCODEUSERAGENT = NAME + "/" + VERSION + " GEDCOM-to-map-folium"
GUINAME = 'GEDCOM Visual Map'

GV_COUNTRIES_JSON = 'https://raw.githubusercontent.com/nnjeim/world/master/resources/json/countries.json'
GV_STATES_JSON = 'https://raw.githubusercontent.com/nnjeim/world/master/resources/json/states.json'
KMLMAPSURL = "https://www.google.ca/maps/about/mymaps"
ABOUTLINK = "https://github.com/D-Jeffrey/"

BackgroundProcess = None
panel = None


GVFONT = ('Verdana', 8, 11)             # General Font family and size (suggested range 8 to 11) and Title 'Visual Mapping Options' size
ABOUTFONT = ('Garamond', 13)            # About Font family and size (suggested range 8 to 14)

LOG_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,

    # NOTE the following values are supperceded by the values in "AppData\..\Local\gedcomvisual\gedcom-visualmap.ini"
    # Clear those values if you want to set loggers values here
    'loggers': {
        'gedcomvisual': {
            'level': 'DEBUG' # Works
        },
    }

}


