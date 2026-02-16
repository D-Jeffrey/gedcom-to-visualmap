# Constants for gedcom-to-visualmap

import yaml
from pathlib import Path

VERSION = "0.2.8.0"
NAME = "gedcom-to-visualmap"
GEOCODEUSERAGENT = NAME + "/" + VERSION + " GEDCOM-to-visualmap"
GUINAME = "GEDCOM Visual Map"

# Application root directory (parent of gedcom-to-map/)
APP_ROOT = Path(__file__).parent.parent

GV_COUNTRIES_JSON = "https://raw.githubusercontent.com/nnjeim/world/master/resources/json/countries.json"
GV_STATES_JSON = "https://raw.githubusercontent.com/nnjeim/world/master/resources/json/states.json"
KMLMAPSURL = "https://www.google.ca/maps/about/mymaps"
ABOUTLINK = "https://github.com/D-Jeffrey/"

GLOBAL_GEO_CACHE_FILENAME = "geo_cache.csv"
FILE_ALT_PLACE_FILENAME_SUFFIX = "_alt.csv"
FILE_GEOCACHE_FILENAME_SUFFIX = "_cache.csv"
GEO_CONFIG_FILENAME = "geo_config.yaml"
OFFICECMDLINE = "soffice"  # command to start LibreOffice

# INI file section constants
INI_SECTION_GEDCOM_MAIN = "Gedcom.Main"
INI_SECTION_GEO_CONFIG = "GeoConfig"
INI_SECTION_GEOCODING = "GeoCoding"

# Note: ini_sections and ini_option_sections have been moved to services/config_io.py

# Migration version constants
MIGRATION_VERSION_UNSET = "0"
MIGRATION_VERSION_CURRENT = "2"

LOG_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {"format": "%(asctime)s %(name)s %(levelname)s: %(message)s"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "ERROR",
            "formatter": "standard",
            "stream": "ext://sys.stdout",
        },
        "file": {
            "class": "logging.FileHandler",
            "level": "DEBUG",
            "formatter": "standard",
            "filename": str(APP_ROOT / f"{NAME}.log"),
            "mode": "w",
            "encoding": "utf-8",
        },
    },
    "root": {
        "handlers": ["file", "console"],
        "level": "DEBUG",
    },
    # NOTE the following values are supperceded by the values in "AppData\..\Local\gedcomvisual\gedcom-visualmap.ini"
    # Clear those values if you want to set loggers values here
    "loggers": {
        "gedcomvisual": {"handlers": ["file", "console"], "level": "DEBUG"},  # Works
    },
}
