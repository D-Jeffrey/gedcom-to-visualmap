# --- ResultType Enum and helpers (migrated from gedcom_options.py) ---
import re
import logging
from enum import Enum

_log = logging.getLogger(__name__)

class ResultType(Enum):
    HTML = 'HTML'
    KML = 'KML'
    KML2 = 'KML2'
    SUM = 'SUM'

    @staticmethod
    def ResultTypeEnforce(value) -> "ResultType":
        """Coerce a value to a ResultType.
        Accepts an existing ResultType or a string (case-insensitive). Raises ValueError if not valid."""
        if isinstance(value, ResultType):
            return value
        if isinstance(value, str):
            # handle ResultType like "ResultType.HTML"
            m = re.match(r'^\s*ResultType\.([A-Za-z_][A-Za-z0-9_]*)\s*$', value)
            if m:
                value = m.group(1)
            try:
                return ResultType[value.upper()]
            except Exception:
                raise ValueError(f"Invalid ResultType string: {value}")
        raise TypeError(f"Cannot convert {type(value)} to ResultType")

    def __str__(self) -> str:
        """Return the value as a string."""
        return self.value

    def long_name(self) -> str:
        """Return the long form name (e.g., 'ResultType.HTML')."""
        try:
            name_attr = getattr(self, "name")
            if callable(name_attr):
                name_str = name_attr()
            else:
                name_str = name_attr
        except Exception:
            name_str = str(self.value)
        return f"ResultType.{name_str}"

    def index(self) -> int:
        """Return the index of this ResultType in the enum list."""
        rt = ResultType.ResultTypeEnforce(self)
        return list(ResultType).index(rt)

    @staticmethod
    def file_extension(result_type: "ResultType") -> str:
        """Return the standard file extension for a given ResultType."""
        rt = ResultType.ResultTypeEnforce(result_type)
        if rt == ResultType.HTML:
            return "html"
        elif rt == ResultType.KML or rt == ResultType.KML2:
            return "kml"
        elif rt == ResultType.SUM:
            return "txt"  # Changed from "md" to match old behavior
        else:
            return "html"

    @staticmethod
    def for_file_extension(file_extension: str) -> "ResultType":
        """Return the appropriate ResultType for a given file extension."""
        ext = file_extension.lower().lstrip('.')
        if ext == "html":
            return ResultType.HTML
        elif ext == "kml":
            return ResultType.KML
        elif ext in ("txt", "md"):  # Support both txt and md
            return ResultType.SUM
        else:
            _log.warning("Unsupported file extension for ResultType: %s; reverting to HTML", file_extension)
            return ResultType.HTML

    @staticmethod
    def list_values():
        """Return a list of all ResultType values as strings."""
        return [rt.value for rt in ResultType]
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
INI_SECTIONS = ['Core', 'HTML', 'Summary', 'Logging', INI_SECTION_GEDCOM_MAIN, 'KML']
INI_OPTION_SECTIONS = ['Core', 'HTML', 'Summary', 'KML']

# Migration version constants
MIGRATION_VERSION_UNSET = '0'
MIGRATION_VERSION_CURRENT = '1'

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
