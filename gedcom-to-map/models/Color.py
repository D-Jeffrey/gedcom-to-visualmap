class Color:
    def __init__(self, r=255, g=0, b=0, a=255):
        self.r = r
        self.g = g
        self.b = b
        self.a = a

    def to_hexa(self) -> str:
        return "{:02x}{:02x}{:02x}".format(self.r, self.g, self.b)

    def __repr__(self):
        return "({:3}, {:3}, {:3}, {:3})".format(self.r, self.g, self.b, self.a)