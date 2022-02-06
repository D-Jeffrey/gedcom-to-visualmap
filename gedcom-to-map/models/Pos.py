
class Pos:
    def __init__(self, lat, lon):
           
            if lat and lat[0].isalpha():
                lat = lat[1:] if lat[0] == 'N' else '-{}'.format(lat[1:])
            if lon and lon[0].isalpha():
                lon = lon[1:] if lon[0] == 'E' else '-{}'.format(lon[1:])
            self.lat = lat
            self.lon = lon
            
            
    def __repr__(self):
        return "[{},{}]".format(self.lat, self.lon)
    def __str__(self):
        return "({},{})".format(self.lat, self.lon)

    
