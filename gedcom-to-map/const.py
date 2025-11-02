import sys
import platform
import wx

# Constants for gedcom-to-visualmap

VERSION = "0.2.7.0.3"
NAME = "gedcom-to-visualmap"
GEOCODEUSERAGENT = NAME + "/" + VERSION + " GEDCOM-to-visualmap"
GUINAME = 'GEDCOM Visual Map'

GV_COUNTRIES_JSON = 'https://raw.githubusercontent.com/nnjeim/world/master/resources/json/countries.json'
GV_STATES_JSON = 'https://raw.githubusercontent.com/nnjeim/world/master/resources/json/states.json'
KMLMAPSURL = "https://www.google.ca/maps/about/mymaps"
ABOUTLINK = "https://github.com/D-Jeffrey/"

GLOBAL_GEO_CACHE_FILENAME = 'geo_cache.csv'
FILE_ALT_PLACE_FILENAME_SUFFIX = '_alt.csv'
FILE_GEOCACHE_FILENAME_SUFFIX = '_cache.csv'
GEO_CONFIG_FILENAME = 'geo_config.yaml'
OFFICECMDLINE = "soffice"               # command to start LibreOffice

# Default GVFONT dict (family left as None until wx is available)
GVFONT = {
    "Windows": {
        "family": "Tahoma",         #  alternates "Segoe UI", "Calibri", "Corbel", "Tahoma", "Arial"
        "sizePt": 10,
        "sizeTitle": 16
    },
    "Darwin": {
        "family": "San Francisco",  # alternates "Helvetica Neue", "Helvetica", "Arial"
        "sizePt": 9,
        "sizeTitle": 12
    },
    "Linux": { 
        "family": "DejaVu Sans",    # alternates "Noto Sans", "Liberation Sans", "Arial"
        "sizePt": 9,
        "sizeTitle": 12
    }  
}

ABOUTFONT = {            # About Font family and size (suggested range 8 to 14)
    "Windows": {
        "family": "Garamond",
        "sizePt": 13
    },
    "Darwin": {
        "family": "Garamond",
        "sizePt": 13
    },
    "Linux": { 
        "family": "Garamond",
        "sizePt": 13
    }  
}

LOG_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,

    "formatters": {
        "standard": {"format": "%(asctime)s %(name)s %(levelname)s: %(message)s"},
    },

    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'ERROR',
            'formatter': 'standard',
            'stream': 'ext://sys.stdout',
        },
        'file': {
            'class': 'logging.FileHandler',
            'level': 'DEBUG',
            'formatter': 'standard',
            'filename': f'{NAME}.log',
            'mode': 'w',
            'encoding': 'utf-8',
        },
    },

    'root': {
        'handlers': ['file', 'console'],
        'level': 'DEBUG',
    },

    # NOTE the following values are supperceded by the values in "AppData\..\Local\gedcomvisual\gedcom-visualmap.ini"
    # Clear those values if you want to set loggers values here
    'loggers': {
        'gedcomvisual': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG' # Works
        },
    }

}


