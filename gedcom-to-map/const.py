"""Constants for gedcom-to-visualmap"""

VERSION = "0.2.4.0"
NAME = "gedcom-to-visualmap"
GUINAME = 'GEDCOM Visual Map'

GV_COUNTRIES_JSON = 'https://raw.githubusercontent.com/nnjeim/world/master/resources/json/countries.json'
GV_STATES_JSON = 'https://raw.githubusercontent.com/nnjeim/world/master/resources/json/states.json'
KMLMAPSURL = "https://www.google.ca/maps/about/mymaps"

GVFONT = 'Verdana'
GVFONTSIZE = 9

LOG_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': { 
        'standard': { 
            #'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            # "format": "%(asctime)s : %(levelname)s : %(module)s : %(funcName)s : %(lineno)d : (Process Details : (%(process)d, %(processName)s), Thread Details : (%(thread)d, %(threadName)s))\nLog : %(message)s",
            "format": "%(asctime)s : %(levelname)s : %(name)s : %(module)s : %(funcName)s : %(lineno)d : %(message)s",
            "datefmt":"%d-%m-%Y %I:%M:%S"
        },
    },
    # TODO: figure out how do properly do logging
    'handlers': { 
        'stdout': { 
            'level': 'DEBUG',                        # This one matters
            'formatter': 'standard',
            'class': 'logging.StreamHandler',
            'stream': 'ext://sys.stdout',  # Default is stderr
        },
    },
    'loggers': { 
        'root': {  # root logger
            'handlers': ['stdout'],
            'level': 'DEBUG',
        },
    # These are moving to the INI file
        'gedcomVisualGUI': { 
            'handlers': ['stdout'],
            'level': 'DEBUG',
        },
        'gedcom.gpslookup': { 
            'handlers': ['stdout'],
            'level': 'DEBUG',
        },
        'ged4py.parser': { 
            'handlers': ['stdout'],
            'level': 'INFO',
        },
        '__main__': {  
            'handlers': ['stdout'],
            'level': 'INFO',
            
        },
    } 
}