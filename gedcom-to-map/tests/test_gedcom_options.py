import pytest
import sys
import types
from pathlib import Path

import gedcom_options

def test_settings_file_pathname(monkeypatch, tmp_path):
    # Simulate different OSes
    monkeypatch.setattr("platform.system", lambda: "Linux")
    path = gedcom_options.settings_file_pathname("testfile.ini")
    assert path.endswith("testfile.ini")
    assert ".config" in path

    monkeypatch.setattr("platform.system", lambda: "Darwin")
    path = gedcom_options.settings_file_pathname("testfile.ini")
    assert "Application Support" in path

    monkeypatch.setattr("platform.system", lambda: "Windows")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    path = gedcom_options.settings_file_pathname("testfile.ini")
    assert path.endswith("testfile.ini")

def test_result_type_enforce():
    assert gedcom_options.ResultType.ResultTypeEnforce("HTML") == gedcom_options.ResultType.HTML
    assert gedcom_options.ResultType.ResultTypeEnforce(gedcom_options.ResultType.KML) == gedcom_options.ResultType.KML
    with pytest.raises(ValueError):
        gedcom_options.ResultType.ResultTypeEnforce("notatype")
    with pytest.raises(TypeError):
        gedcom_options.ResultType.ResultTypeEnforce(123)

def test_result_type_file_extension():
    assert gedcom_options.ResultType.file_extension(gedcom_options.ResultType.HTML) == "html"
    assert gedcom_options.ResultType.file_extension(gedcom_options.ResultType.KML) == "kml"
    assert gedcom_options.ResultType.file_extension(gedcom_options.ResultType.SUM) == "txt"

def test_result_type_for_file_extension():
    assert gedcom_options.ResultType.for_file_extension(".html") == gedcom_options.ResultType.HTML
    assert gedcom_options.ResultType.for_file_extension("kml") == gedcom_options.ResultType.KML
    assert gedcom_options.ResultType.for_file_extension(".txt") == gedcom_options.ResultType.SUM

def test_file_open_command_lines():
    cmd = gedcom_options.FileOpenCommandLines()
    cmd.add_file_type_command("KML", "open $n")
    assert cmd.get_command_for_file_type("KML") == "open $n"
    assert cmd.exists_command_for_file_type("KML")
    assert "KML" in cmd.list_file_types()

@pytest.mark.skip("gvOptions requires real config and GUI hooks; integration test only")
def test_gvoptions_init(monkeypatch, tmp_path):
    # Patch yaml and GUI hooks to avoid file and GUI dependencies
    dummy_yaml = {
        "gedcom_options_types": {"foo": "str"},
        "gedcom_options_defaults": {"foo": "bar"},
        "gui_options_types": {},
        "gui_options_defaults": {},
    }
    monkeypatch.setattr("yaml.safe_load", lambda f: dummy_yaml)
    monkeypatch.setattr("gedcom_options.settings_file_pathname", lambda fname: str(tmp_path / fname))
    # Patch GUI hooks import
    sys.modules["gui.gui_hooks"] = types.SimpleNamespace(GuiHooks=lambda g: None)
    # Patch Path.open to avoid file IO
    monkeypatch.setattr(Path, "open", lambda self, mode="r": types.SimpleNamespace(__enter__=lambda s: s, __exit__=lambda s, exc_type, exc_val, exc_tb: None, read=lambda: ""))
    # Should not raise
    gvo = gedcom_options.gvOptions()
    assert hasattr(gvo, "foo")
    