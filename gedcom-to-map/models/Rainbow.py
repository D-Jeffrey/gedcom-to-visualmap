__all__ = ['Tint', 'Rainbow']
from models.Color import Color


def merge_color(color_a: Color, color_b: Color, coef):
    return Color(
        color_a.r * (1 - coef) + color_b.r * coef,
        color_a.g * (1 - coef) + color_b.g * coef,
        color_a.b * (1 - coef) + color_b.b * coef
    )


class Tint:
    def __init__(self, x, y, mincolor: Color, maxcolor: Color):
        self.min = mincolor
        self.max = maxcolor
        self.x = x
        self.y = y

    def isInside(self, x):
        return self.x <= x < self.y

    def getColor(self, x):
        diff = (x - self.x) / (self.y - self.x)
        return merge_color(self.min, self.max, coef=diff)


class Rainbow:
    def __init__(self):
        self.steps = [
            Color(255, 0, 127),
            Color(255, 0, 0),
            Color(255, 127, 0),
            Color(255, 255, 0),
            Color(127, 255, 0),
            Color(0, 255, 0),
            Color(0, 255, 127),
            Color(0, 255, 255),
            Color(0, 127, 255),
            Color(0, 0, 255),
        ]
        if len(self.steps) == 0:
            raise AssertionError("Rainbow did not initialize")

    @staticmethod
    def merge_color(color_a: Color, color_b: Color, coef: float):
        return Color(
            int(color_a.r * (1 - coef) + color_b.r * coef),
            int(color_a.g * (1 - coef) + color_b.g * coef),
            int(color_a.b * (1 - coef) + color_b.b * coef)
        )

    def get(self, v: float) -> Color:
        if v >= 1 or v < 0:
            #TODO Need to improve this hack

            # raise
            v = 0.9999
        len_steps = len(self.steps ) - 1
        step = int(v * len_steps)
        latlon = v % (1 / len_steps) * len_steps
        return self.merge_color(self.steps[step], self.steps[step + 1], latlon)
