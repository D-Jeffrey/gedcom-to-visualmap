import pytest
from models import Creator, Person, LatLon, Line, Color


def test_line_init():
    ll1 = LatLon(51.5, -0.1)
    ll2 = LatLon(52.0, 0.1)
    color = Color(255, 0, 0)
    path = "test"
    branch = 0
    prof = 1
    line = Line([ll1, ll2], fromlocation=ll1, tolocation=ll2, color=color, path=path, branch=branch, prof=prof)
    assert line.fromlocation == ll1
    assert line.tolocation == ll2
    assert line.color == color

def test_line_str_repr():
    ll1 = LatLon(51.5, -0.1)
    ll2 = LatLon(52.0, 0.1)
    color = Color(255, 0, 0)
    path = "test"
    branch = 0
    prof = 1
    line = Line([ll1, ll2], fromlocation=ll1, tolocation=ll2, color=color, path=path, branch=branch, prof=prof)
    s = str(line)
    r = repr(line)
    assert "51.5" in s or "51.5" in r
    assert "52.0" in s or "52.0" in r