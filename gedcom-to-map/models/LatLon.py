"""
latlon.py - Location and LatLon classes for GEDCOM mapping.

Provides LatLon for coordinate validation and Location for geocoded place information.

Author: @colin0brass
"""

__all__ = ['LatLon']

from typing import Optional, Union

class LatLon:
    __slots__ = ['lat', 'lon']
    """ Creater a Position value with a of Lat and Lon  """
    def __init__(self, lat: Union[str, float, None], lon: Union[str, float, None]):
        """
        Initialize LatLon with latitude and longitude.

        Args:
            lat (str|float|None): Latitude value or string.
            lon (str|float|None): Longitude value or string.
        """
        self.lat = self._parse_lat(lat)
        self.lon = self._parse_lon(lon)
    @staticmethod
    def _parse_lat(lat: Union[str, float, None]) -> Optional[float]:
        """
        Parse latitude from string or float, handling N/S prefixes.

        Args:
            lat (str|float|None): Latitude value or string.

        Returns:
            Optional[float]: Parsed latitude or None.
        """
        if lat is None:
            return None
        if isinstance(lat, (float, int)):
            return float(lat)
        lat_str = str(lat).strip()
        if not lat_str:
            return None
        direction = lat_str[0].upper()
        if direction in ('N', 'S'):
            try:
                lat_val = float(lat_str[1:])
                return lat_val if direction == 'N' else -lat_val
            except ValueError:
                return None
        try:
            return float(lat_str)
        except ValueError:
            return None

    @staticmethod
    def _parse_lon(lon: Union[str, float, None]) -> Optional[float]:
        """
        Parse longitude from string or float, handling E/W prefixes.

        Args:
            lon (str|float|None): Longitude value or string.

        Returns:
            Optional[float]: Parsed longitude or None.
        """
        if lon is None:
            return None
        if isinstance(lon, (float, int)):
            return float(lon)
        lon_str = str(lon).strip()
        if not lon_str:
            return None
        direction = lon_str[0].upper()
        if direction in ('E', 'W'):
            try:
                lon_val = float(lon_str[1:])
                return lon_val if direction == 'E' else -lon_val
            except ValueError:
                return None
        try:
            return float(lon_str)
        except ValueError:
            return None
    
    @property
    def latitude(self) -> Optional[float]:
        """
        Returns the latitude value (or None).
        """
        return self.lat

    @property
    def longitude(self) -> Optional[float]:
        """
        Returns the longitude value (or None).
        """
        return self.lon
    
    def hasLocation(self):
        """ Does this Position have a actual value """
        return bool(getattr(self, "lat", None) and getattr(self, "lon", None))
        
    def is_valid(self) -> bool:
        """
        Check if both latitude and longitude are not None.

        Returns:
            bool: True if both latitude and longitude are valid, False otherwise.
        """
        return self.lat is not None and self.lon is not None

    def isNone(self):
        """ Does this Position have No location value """
        return (not self.hasLocation())
        
    def __repr__(self) -> str:
        """
        String representation for debugging.

        Returns:
            str: Representation of LatLon.
        """
        return f"[{self.lat},{self.lon}]"
    def __str__(self) -> str:
        """
        User-friendly string representation.

        Returns:
            str: String representation of LatLon.
        """
        return f"({self.lat},{self.lon})"
    
    @classmethod
    def from_string(cls, s: str) -> "LatLon":
        """
        Create LatLon from a string like 'N51.5,E0.1' or '51.5,0.1'.

        Args:
            s (str): String representation.

        Returns:
            LatLon: Parsed LatLon object.
        """
        parts = s.split(',')
        if len(parts) == 2:
            return cls(parts[0], parts[1])
        return cls(None, None)