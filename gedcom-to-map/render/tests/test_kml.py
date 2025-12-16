import pytest
from render.kml2.kml_exporter_refined import KmlExporterRefined
from render.kml2.kml_life_lines_creator import KML_Life_Lines_Creator
from render.kml2.kml_life_lines import KML_Life_Lines
from geo_gedcom.geolocated_gedcom import GeolocatedGedcom

def test_kml_exporter_refined_init(tmp_path):
    kml_file = tmp_path / "test.kml"
    exporter = KmlExporterRefined(str(kml_file))
    assert exporter.kml_file == str(kml_file)
    assert hasattr(exporter, "kml")

def test_kml_life_lines_creator_init(tmp_path):
    kml_file = tmp_path / "test_life_lines.kml"
    gedcom_file = tmp_path / "dummy.ged"
    location_cache_file = tmp_path / "dummy_cache.csv"
    # Create empty files if the constructor expects them to exist
    gedcom_file.write_text("")
    location_cache_file.write_text("")
    gedcom = GeolocatedGedcom(str(gedcom_file), str(location_cache_file))
    creator = KML_Life_Lines_Creator(gedcom, str(kml_file))
    assert creator.kml_instance.kml_file == str(kml_file)
    assert hasattr(creator.kml_instance, "kml")

def test_kml_life_lines_init(tmp_path):
    kml_file = tmp_path / "test_life_lines2.kml"
    gedcom_file = tmp_path / "dummy.ged"
    location_cache_file = tmp_path / "dummy_cache.csv"
    # Create empty files if the constructor expects them to exist
    gedcom_file.write_text("")
    location_cache_file.write_text("")
    gedcom = GeolocatedGedcom(str(gedcom_file), str(location_cache_file))
    life_lines = KML_Life_Lines(gedcom, str(kml_file))
    assert life_lines.kml_life_lines_creator.kml_instance.kml_file == str(kml_file)
    assert hasattr(life_lines.kml_life_lines_creator.kml_instance, "kml")

def test_kml_exporter_refined_save(tmp_path):
    kml_file = tmp_path / "test_save.kml"
    exporter = KmlExporterRefined(str(kml_file))
    # Should not raise on save (even if empty)
    try:
        exporter.kml.save(str(kml_file))
    except Exception as e:
        pytest.fail(f"KmlExporterRefined.kml.save raised {e}")
        