import pytest
from models import Color

def test_color_init():
    c = Color(10, 20, 30)
    assert c.r == 10
    assert c.g == 20
    assert c.b == 30

def test_color_str_repr():
    c = Color(100, 150, 200)
    s = str(c)
    r = repr(c)
    assert "100" in s or "100" in r
    assert "150" in s or "150" in r
    assert "200" in s or "200" in r

def test_color_equality():
    c1 = Color(1, 2, 3)
    c2 = Color(1, 2, 3)
    c3 = Color(3, 2, 1)
    assert c1 == c2
    assert c1 != c3

def test_color_invalid_values():
    with pytest.raises(Exception):
        Color(-1, 0, 0)
    with pytest.raises(Exception):
        Color(0, 256, 0)