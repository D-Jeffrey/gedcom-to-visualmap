import pytest
import os
from render.kml1.kml_exporter import KmlExporter
from geo_gedcom.lat_lon import LatLon
from models.line import Line


class DummyReferenced:
    def add(self, *args, **kwargs):
        pass

    def exists(self, *args, **kwargs):
        return False

    def gettag(self, *args, **kwargs):
        return 0


# DummyConfig implements IConfig
class DummyConfig:
    def __init__(self, resultpath, resultfile):
        self._config = {
            "resultpath": str(resultpath),
            "ResultFile": str(resultfile),
            "MaxLineWeight": 5,
            "KMLsort": 0,
            "GEDCOMinput": None,
            "Name": "Test",
            "Main": "Main",
            "BornMark": False,
            "DieMark": False,
            "MapTimeLine": False,
            "UseBalloonFlyto": False,
            "AllEntities": False,
        }

    def get(self, key, default=None):
        return self._config.get(key, default)

    def has(self, key):
        return key in self._config

    def get_file_command(self, file_type):
        return None

    @property
    def gedcom_input(self):
        return ""


# DummyState implements IState
class DummyState:
    def __init__(self):
        self.Referenced = DummyReferenced()
        self.people = {}
        self.totalpeople = 0


# DummyProgress implements IProgressTracker
class DummyProgress:
    def step(self, *a, **k):
        return None


def test_kml_exporter_init(tmp_path):
    config = DummyConfig(tmp_path, "test.kml")
    state = DummyState()
    progress = DummyProgress()
    exporter = KmlExporter(config, state, progress)
    assert exporter.file_name == os.path.join(str(tmp_path), "test.kml")
    assert exporter.max_line_weight == 5
    assert exporter.svc_config is config


def test_kml_exporter_drift_latlon():
    config = DummyConfig("/tmp", "test.kml")
    state = DummyState()
    progress = DummyProgress()
    exporter = KmlExporter(config, state, progress)
    latlon = LatLon(10.0, 20.0)
    # driftOn is False, should return original
    assert exporter.driftLatLon(latlon) == (20.0, 10.0)
    exporter.driftOn = True
    lon, lat = exporter.driftLatLon(latlon)
    assert abs(lon - 20.0) < 0.01
    assert abs(lat - 10.0) < 0.01


def test_kml_exporter_done(tmp_path):
    config = DummyConfig(tmp_path, "test_done.kml")
    state = DummyState()
    progress = DummyProgress()
    exporter = KmlExporter(config, state, progress)

    # Minimal fake kml object with features
    class FakeKml:
        def __init__(self):
            self.features = []

        def save(self, fname):
            self.saved = fname

    exporter.kml = FakeKml()
    exporter.Done()
    # Should not raise


def test_kml_exporter_export_empty(tmp_path):
    config = DummyConfig(tmp_path, "test_export.kml")
    state = DummyState()
    progress = DummyProgress()
    exporter = KmlExporter(config, state, progress)
    # Should log errors but not raise
    exporter.export(main=None, lines=[], ntag="", mark="native")
