# Constants for gedcom-to-visualmap

VERSION = "0.2.8.0"
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

# INI file section constants
INI_SECTION_GEDCOM_MAIN = 'Gedcom.Main'
INI_SECTION_GEO_CONFIG = 'GeoConfig'
INI_SECTION_GEOCODING = 'GeoCoding'
INI_SECTIONS = ['Core', 'HTML', 'Summary', 'Logging', INI_SECTION_GEDCOM_MAIN, 'KML', INI_SECTION_GEO_CONFIG, INI_SECTION_GEOCODING]
INI_OPTION_SECTIONS = [s for s in INI_SECTIONS if s not in ['Logging', INI_SECTION_GEDCOM_MAIN, INI_SECTION_GEO_CONFIG]]

# Migration version constants
MIGRATION_VERSION_UNSET = '0'
MIGRATION_VERSION_CURRENT = '2'

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
