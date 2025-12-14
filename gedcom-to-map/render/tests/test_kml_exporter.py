import pytest
import os
from render.kml_exporter import KmlExporter
from geo_gedcom.lat_lon import LatLon
from models.line import Line

class DummyReferenced:
    def add(self, *args, **kwargs): pass
    def exists(self, *args, **kwargs): return False
    def gettag(self, *args, **kwargs): return 0

class DummyGOp:
    def __init__(self, resultpath, resultfile):
        self.resultpath = resultpath
        self.ResultFile = resultfile
        self.MaxLineWeight = 5
        self.KMLsort = 0
        self.GEDCOMinput = None
        self.Name = "Test"
        self.Main = "Main"
        self.BornMark = False
        self.DieMark = False
        self.MapTimeLine = False
        self.UseBalloonFlyto = False
        self.AllEntities = False
        self.UseBalloonFlyto = False
        self.people = {}
        self.Referenced = DummyReferenced()
        self.totalpeople = 0
        self.step = lambda *args, **kwargs: None

def test_kml_exporter_init(tmp_path):
    gOp = DummyGOp(str(tmp_path), "test.kml")
    exporter = KmlExporter(gOp)
    assert exporter.file_name == os.path.join(str(tmp_path), "test.kml")
    assert exporter.max_line_weight == 5
    assert exporter.gOp is gOp

def test_kml_exporter_drift_latlon():
    gOp = DummyGOp("/tmp", "test.kml")
    exporter = KmlExporter(gOp)
    latlon = LatLon(10.0, 20.0)
    # driftOn is False, should return original
    assert exporter.driftLatLon(latlon) == (20.0, 10.0)
    exporter.driftOn = True
    lon, lat = exporter.driftLatLon(latlon)
    assert abs(lon - 20.0) < 0.01
    assert abs(lat - 10.0) < 0.01

def test_kml_exporter_done(tmp_path):
    gOp = DummyGOp(str(tmp_path), "test_done.kml")
    exporter = KmlExporter(gOp)
    # Minimal fake kml object with features
    class FakeKml:
        def __init__(self):
            self.features = []
        def save(self, fname): self.saved = fname
    exporter.kml = FakeKml()
    exporter.Done()
    # Should not raise

def test_kml_exporter_export_empty(tmp_path):
    gOp = DummyGOp(str(tmp_path), "test_export.kml")
    exporter = KmlExporter(gOp)
    # Should log errors but not raise
    exporter.export(main=None, lines=[], ntag="", mark="native")
