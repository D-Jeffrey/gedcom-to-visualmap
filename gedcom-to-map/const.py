"""Constants for gedcom-to-visualmap"""

VERSION = "0.2.5.2"
NAME = "gedcom-to-visualmap"
GEOCODEUSERAGENT = NAME + "/" + VERSION + " GEDCOM-to-map-folium"
GUINAME = 'GEDCOM Visual Map'

GV_COUNTRIES_JSON = 'https://raw.githubusercontent.com/nnjeim/world/master/resources/json/countries.json'
GV_STATES_JSON = 'https://raw.githubusercontent.com/nnjeim/world/master/resources/json/states.json'
KMLMAPSURL = "https://www.google.ca/maps/about/mymaps"
ABOUTLINK = "https://github.com/D-Jeffrey/"

GVFONT = ('Verdana', 8)                 # General Font family and size (suggested range 8 to 11)
ABOUTFONT = ('Garamond', 13)            # About Font family and size (suggested range 8 to 14)
LOG_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,

    # NOTE the following values are supperceded by the values in "AppData\Local\gedcomvisual\gedcom-visualmap.ini"
    # Clear those values if you want to set loggers values here
    'loggers': {
        'gedcomvisual': {
            'level': 'DEBUG' # Works
        },
    }

}

BROKEN = {
    
    'formatters': {
        'standard': {
            #'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            # "format": "%(asctime)s : %(levelname)s : %(module)s : %(funcName)s : %(lineno)d : (Process Details : (%(process)d, %(processName)s), Thread Details : (%(thread)d, %(threadName)s))\nLog : %(message)s",
            "format": "%(asctime)s : %(levelname)s : %(name)s : %(module)s : %(funcName)s : %(lineno)d : %(message)s",
            "datefmt": "%d-%m-%Y %I:%M:%S"
        },
    },
    # TODO: figure out how do properly do logging
    'handlers': {
        'stdout': {
            'level': 'WARNING',                        # This one matters
            'formatter': 'standard',
            'class': 'logging.StreamHandler',
            'stream': 'ext://sys.stdout',  # Default is stderr
        },
    }
}