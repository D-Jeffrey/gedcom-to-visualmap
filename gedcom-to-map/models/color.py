__all__ = ["Color"]


class Color:
    """
    Initializes a Color object.

    Args:
        r (int): The red component of the color (0-255).
        g (int): The green component of the color (0-255).
        b (int): The blue component of the color (0-255).
        a (int): The alpha component of the color (0-255).

            KML does not use "normal" color order (RGB), instead it is in reversed order of
            Blue, Green, Red, with alpha/opacity in the front, for: AABBGGRR, where AA is alpha,
            BB is blue, GG is Green and RR is Red.
            https://developers.google.com/kml/documentation/kmlreference#elements-specific-to-colorstyle

    """

    __slots__ = ("r", "g", "b", "a")

    def __init__(self, r: int = 255, g: int = 0, b: int = 0, a: int = 255) -> None:
        """Initialize Color with RGBA values.

        Args:
            r: Red channel (0-255).
            g: Green channel (0-255).
            b: Blue channel (0-255).
            a: Alpha channel (0-255).

        Raises:
            ValueError: If any RGB value is not in range 0-255.
        """
        if not (0 <= r <= 255 and 0 <= g <= 255 and 0 <= b <= 255):
            raise ValueError("Color values must be in 0..255")
        self.r: int = r
        self.g: int = g
        self.b: int = b
        self.a: int = a

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
