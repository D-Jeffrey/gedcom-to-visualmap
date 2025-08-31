__all__ = ['Pos']

from typing import Optional, Union

class Pos:
    """ Creater a Position value with a of Lat and Lon  """
    def __init__(self, lat: Union[str, float, None], lon: Union[str, float, None]):
        if lat and lat[0].isalpha():
            lat = lat[1:] if lat[0] == 'N' else f'-{lat[1:]}'
        if lon and lon[0].isalpha():
            lon = lon[1:] if lon[0] == 'E' else f'-{lon[1:]}'
        self.lat = lat
        self.lon = lon
    
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
        return bool(hasattr(self, "lat") and self.lat != None and self.lon != None)
        
    
    def isNone(self):
        """ Does this Position have No location value """
        return (not self.hasLocation())
        
    def __repr__(self) -> str:
        return f"[{self.lat},{self.lon}]"
    def __str__(self) -> str:
        return f"({self.lat},{self.lon})"
