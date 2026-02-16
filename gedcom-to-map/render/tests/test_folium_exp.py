import pytest
from render.folium.folium_exporter import foliumExporter
from render.folium.mark_clusters import MyMarkClusters
from render.folium.legend import Legend
import folium


# DummyConfig implements IConfig
class DummyConfig:
    def __init__(self, resultpath, resultfile):
        self._config = {
            "resultpath": str(resultpath),
            "ResultFile": str(resultfile),
            "MaxLineWeight": 5,
            "GroupBy": 1,
            "MarksOn": False,
            "BornMark": False,
            "DieMark": False,
            "HeatMap": False,
            "HeatMapTimeStep": 10,
            "MapTimeLine": False,
            "UseAntPath": False,
            "HomeMarker": False,
            "mapMini": False,
            "showLayerControl": True,
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
        self.Referenced = None
        self.people = {}
        self.mainPerson = None


# DummyProgress implements IProgressTracker
class DummyProgress:
    def step(self, *a, **k):
        return None


def test_folium_exporter_init(tmp_path):
    output_file = tmp_path / "test_map.html"
    config = DummyConfig(tmp_path, "test_map.html")
    state = DummyState()
    progress = DummyProgress()
    exporter = foliumExporter(config, state, progress)
    assert exporter is not None
    assert exporter.file_name == str(output_file)


def test_folium_exporter_save(tmp_path):
    output_file = tmp_path / "test_map_save.html"
    config = DummyConfig(tmp_path, "test_map_save.html")
    state = DummyState()
    progress = DummyProgress()
    exporter = foliumExporter(config, state, progress)
    # Should not raise on Done (even if map is empty)
    try:
        exporter.Done()
    except Exception as e:
        pytest.fail(f"foliumExporter.Done raised {e}")


def test_my_mark_clusters_init():
    mymap = folium.Map(location=[0, 0], zoom_start=2)
    clusters = MyMarkClusters(mymap, step=10)
    assert clusters is not None


def test_legend_init():
    legend = Legend()
    assert legend is not None
