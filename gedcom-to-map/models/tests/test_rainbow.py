import pytest
from models import Rainbow, Color


def test_rainbow_init():
    rb = Rainbow()
    assert isinstance(rb, Rainbow)


def test_rainbow_get_returns_color():
    rb = Rainbow()
    color = rb.get(0.5)
    assert isinstance(color, Color)


def test_rainbow_get_range():
    rb = Rainbow()
    # Test that get returns a Color for values in [0, 1]
    for v in [0.0, 0.25, 0.5, 0.75, 1.0]:
        color = rb.get(v)
        assert isinstance(color, Color)


def test_rainbow_merge_color():
    rb = Rainbow()
    c1 = Color(255, 0, 0)
    c2 = Color(0, 0, 255)
    merged = rb.merge_color(c1, c2, 0.5)
    assert isinstance(merged, Color)
    # Should be a blend (not equal to either endpoint)
    assert merged != c1 and merged != c2
