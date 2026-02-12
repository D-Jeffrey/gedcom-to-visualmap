__all__ = ["Tint", "Rainbow"]
from .color import Color
import logging

_log = logging.getLogger(__name__.lower())


def merge_color(color_a: Color, color_b: Color, coef):
    return Color(
        color_a.r * (1 - coef) + color_b.r * coef,
        color_a.g * (1 - coef) + color_b.g * coef,
        color_a.b * (1 - coef) + color_b.b * coef,
    )


class Tint:
    """Represents a color tint range for gradient interpolation."""

    def __init__(self, x: float, y: float, mincolor: Color, maxcolor: Color) -> None:
        """Initialize a color tint with min and max boundaries.

        Args:
            x: Lower boundary of this tint range.
            y: Upper boundary of this tint range.
            mincolor: Color at the lower boundary.
            maxcolor: Color at the upper boundary.
        """
        self.min: Color = mincolor
        self.max: Color = maxcolor
        self.x: float = x
        self.y: float = y

    def isInside(self, x: float) -> bool:
        return self.x <= x < self.y

    def getColor(self, x: float) -> Color:
        diff = (x - self.x) / (self.y - self.x)
        return merge_color(self.min, self.max, coef=diff)


class Rainbow:
    """Generates colors in rainbow spectrum order for visual distinction."""

    def __init__(self) -> None:
        """Initialize Rainbow with predefined color spectrum and tints."""
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
            int(color_a.b * (1 - coef) + color_b.b * coef),
        )

    def get(self, v: float) -> Color:
        if v >= 1 or v < 0:
            # TODO Need to improve this hack

            # raise
            _log.info("Rainbow coef out of range: %f", v)
            v = v % 1.0
        len_steps = len(self.steps) - 1
        step = int(v * len_steps)
        # Alternate approach
        # pos = v % (1 / len_steps) * len_steps
        pos = (v * len_steps) - step
        _log.debug(f"coef:{v}  step:{step}   pos:{pos}")
        return self.merge_color(self.steps[step], self.steps[step + 1], pos)
