__all__ = ['Pos']

class Pos:
    """ Creater a Position value with a of Lat and Llon  """
    def __init__(self, lat, lon):
           
        if lat and lat[0].isalpha():
            lat = lat[1:] if lat[0] == 'N' else f'-{lat[1:]}'
        if lon and lon[0].isalpha():
            lon = lon[1:] if lon[0] == 'E' else f'-{lon[1:]}'
        self.lat = lat
        self.lon = lon
    

    def hasLocation(self):
        """ Does this Position have a actual value """
        if hasattr(self, "lat"):
            if self.lat != None and self.lon:
                return True
        return False
        
    
    def isNone(self):
        """ Does this Position have No location value """
        return (not self.hasLocation())
        
    def __repr__(self):
        return f"[{self.lat},{self.lon}]"
    def __str__(self):
        return f"({self.lat},{self.lon})"
