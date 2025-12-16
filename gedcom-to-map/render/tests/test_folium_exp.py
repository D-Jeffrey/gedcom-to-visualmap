import pytest
from render.folium.folium_exporter import foliumExporter
from render.folium.mark_clusters import MyMarkClusters
from render.folium.legend import Legend
import folium

class DummyGOp:
    def __init__(self, resultpath, resultfile):
        self.resultpath = resultpath
        self.ResultFile = resultfile
        self.MaxLineWeight = 5
        self.GroupBy = 1
        self.MarksOn = False
        self.BornMark = False
        self.DieMark = False
        self.HeatMap = False
        self.HeatMapTimeStep = 10
        self.MapTimeLine = False
        self.UseAntPath = False
        self.HomeMarker = False
        self.mapMini = False
        self.showLayerControl = True
        self.Referenced = None
        self.people = {}
        self.mainPerson = None
        def step(*args, **kwargs): return False
        self.step = step

def test_folium_exporter_init(tmp_path):
    output_file = tmp_path / "test_map.html"
    gOp = DummyGOp(str(tmp_path), "test_map.html")
    exporter = foliumExporter(gOp)
    assert exporter is not None
    assert exporter.file_name == str(output_file)

def test_folium_exporter_save(tmp_path):
    output_file = tmp_path / "test_map_save.html"
    gOp = DummyGOp(str(tmp_path), "test_map_save.html")
    exporter = foliumExporter(gOp)
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
    