__all__ = ['Color']

class Color:
    """
Initializes a Color object.

Args:
    r (int): The red component of the color (0-255).
    g (int): The green component of the color (0-255).
    b (int): The blue component of the color (0-255).
    a (int): The alpha component of the color (0-255).

        KML does not use "normal" color order (RGB), instead it is in reversed order of Blue, Green, Red, with alpha/opacity in the front, for: 
        AABBGGRR, where AA is alpha, BB is blue, GG is Green and RR is Red.
        https://developers.google.com/kml/documentation/kmlreference#elements-specific-to-colorstyle

"""
    __slots__ = ('r', 'g', 'b', 'a')

    def __init__(self, r=255, g=0, b=0, a=255):
        if not (0 <= r <= 255 and 0 <= g <= 255 and 0 <= b <= 255):
            raise ValueError("Color values must be in 0..255")
        self.r = r
        self.g = g
        self.b = b
        self.a = a

    def to_hexa(self) -> str:
        return f"{self.a:02x}{self.b:02x}{self.g:02x}{self.r:02x}"
    
    def to_RGBhex(self) -> str:
        return f"{self.r:02x}{self.g:02x}{self.b:02x}"
    
    def __repr__(self) -> str:
        return f"R{self.r:3}G{self.g:3}B{self.b:3}A{self.a:3}"
    
    def __str__(self) -> str:
        return f"R{self.r:3}G{self.g:3}B{self.b:3}A{self.a:3}"
    
    def __eq__(self, other):
        if not isinstance(other, Color):
            return NotImplemented
        return (self.r, self.g, self.b) == (other.r, other.g, other.b)
