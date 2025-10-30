"""
location.py - Location and LatLon classes for GEDCOM mapping.

Provides LatLon for coordinate validation and Location for geocoded place information.

Author: @colin0brass
"""
__all__ = ['Location']

import logging
from typing import Dict, Optional, Union
from rapidfuzz import process, fuzz
from models.LatLon import LatLon

# Re-use higher-level logger (inherits configuration from main script)
logger = logging.getLogger(__name__)

class Location:
    """
    Stores geocoded location information.

    Attributes:
        used (int): Usage count.
        latlon (LatLon): Latitude/longitude.
        country_code (str): Country code.
        country_name (str): Country name.
        continent (str): Continent name.
        found_country (bool): Whether country was found.
        address (str): Address string.
        alt_addr (str): Alternative address string.
        ... (other optional attributes)
    """
    __slots__ = [
        'used', 'latlon', 'country_code', 'country_name', 'continent', 'found_country', 'address',
        'alt_addr', 'type', 'class_', 'icon', 'place_id', 'boundry', 'size', 'importance'
    ]
    def __init__(
        self,
        used: int = 0,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        country_code: Optional[str] = None,
        country_name: Optional[str] = None,
        continent: Optional[str] = None,
        found_country: Optional[bool] = False,
        address: Optional[str] = None,
        alt_addr: Optional[str] = None,
        type: Optional[str] = None,
        class_: Optional[str] = None,
        icon: Optional[str] = None,
        place_id: Optional[str] = None,
        boundry: Optional[str] = None,
        size: Optional[str] = None,
        importance: Optional[str] = None
    ):
        """
        Initialize a Location object with geocoded information.
        """
        self.used = used
        self.latlon = LatLon(latitude, longitude) if (latitude is not None and longitude is not None) else None
        self.country_code = country_code
        self.country_name = country_name
        self.continent = continent
        self.found_country = found_country
        self.address = address
        self.alt_addr = alt_addr
        self.type = type
        self.class_ = class_
        self.icon = icon
        self.place_id = place_id
        self.boundry = boundry
        self.size = size
        self.importance = importance

    @classmethod
    def from_dict(cls, d: dict) -> "Location":
        """
        Create a Location object from a dictionary.

        Args:
            d (dict): Dictionary of location attributes.

        Returns:
            Location: Location instance.
        """
        # Track unknown attributes
        unknown = []
        obj = cls()
        for key, value in d.items():
            if key.lower() == 'class':
                setattr(obj, 'class_', value)
            elif key.lower() in ('latitude', 'longitude'):
                continue
            elif key.lower() == 'place':
                setattr(obj, 'address', value)
            elif key.lower() == 'alt_place':
                setattr(obj, 'alt_addr', value)
            else:
                # make it ignore extra columns in the CSV file
                if key in obj.__slots__:
                    setattr(obj, key, value)
                else:
                    if value is not None and value != '':
                        unknown.append(key)
        if unknown:
            logger.debug("Ignoring unknown attribute '%s' in Location.from_dict", unknown)
        lat_key = next((k for k in d.keys() if k.lower() in ("latitude", "lat")), None)
        lon_key = next((k for k in d.keys() if k.lower() in ("longitude", "long")), None)
        if lat_key and lon_key:
            obj.latlon = LatLon(d[lat_key], d[lon_key])
        obj.used = 0
        return obj
    
