"""Tests for GVConfig configuration service."""
import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch
from services.config_service import GVConfig
from render.result_type import ResultType


class TestGVConfigInit:
    """Test GVConfig initialization."""
    
    def test_gvconfig_init_loads_yaml(self):
        """Test that GVConfig loads YAML options on initialization."""
        config = GVConfig()
        assert hasattr(config, 'options')
        assert isinstance(config.options, dict)
        assert 'marker_options' in config.options
    
    def test_gvconfig_init_creates_attributes(self):
        """Test that GVConfig creates expected attributes."""
        config = GVConfig()
        assert hasattr(config, 'gvConfig')
        assert hasattr(config, 'settingsfile')
        assert hasattr(config, '_geo_config_file')
        assert hasattr(config, '_file_open_commands')
    
    def test_gvconfig_invalid_path_raises_error(self):
        """Test that invalid gedcom_options path raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            GVConfig(gedcom_options_path="/nonexistent/path/gedcom_options.yaml")


class TestGVConfigMarkerOptions:
    """Test marker option configuration."""
    
    def test_set_marker_defaults(self):
        """Test setting marker defaults from YAML configuration."""
        config = GVConfig()
        config.set_marker_defaults()
        marker_options = config.options.get('marker_options', {})
        for key in marker_options:
            assert hasattr(config, key)
    
    def test_set_marker_options_valid(self):
        """Test setting marker options with valid values."""
        config = GVConfig()
        test_options = {'marker_size': 10, 'marker_color': 'blue'}
        # Get valid marker options from YAML
        valid_keys = list(config.options.get('marker_options', {}).keys())
        if valid_keys:
            test_options = {valid_keys[0]: 'test_value'}
            config.set_marker_options(test_options)
            assert getattr(config, valid_keys[0]) == 'test_value'
    
    def test_set_marker_options_unknown_warns(self, caplog):
        """Test that unknown marker options generate warnings."""
        config = GVConfig()
        config.set_marker_options({'unknown_marker_option': 'value'})
        assert 'Unknown marker option' in caplog.text


class TestGVConfigGetSet:
    """Test get and set methods."""
    
    def test_set_and_get_attribute(self):
        """Test setting and getting a basic attribute."""
        config = GVConfig()
        config.set('Name', 'TestName')
        assert config.get('Name') == 'TestName'
    
    def test_get_with_default(self):
        """Test get returns default for missing attribute."""
        config = GVConfig()
        assert config.get('NonExistentAttr', default='default_value') == 'default_value'
    
    def test_get_with_ifNone(self):
        """Test get returns ifNone when attribute is None."""
        config = GVConfig()
        config.SomeAttr = None
        assert config.get('SomeAttr', default='default', ifNone='if_none') == 'if_none'
    
    def test_has_existing_attribute(self):
        """Test has() returns True for existing attributes."""
        config = GVConfig()
        config.TestAttr = 'value'
        assert config.has('TestAttr') is True
    
    def test_has_nonexistent_attribute(self):
        """Test has() returns False for non-existent attributes."""
        config = GVConfig()
        assert config.has('NonExistentAttr') is False
    
    def test_get_resultpath_from_gedcom(self):
        """Test that resultpath is derived from GEDCOMinput."""
        config = GVConfig()
        config.GEDCOMinput = '/path/to/file.ged'
        result = config.get('resultpath')
        assert result == '/path/to'
    
    def test_get_resulttype_enum_handling(self):
        """Test that ResultType is properly coerced to enum."""
        config = GVConfig()
        config.ResultType = 'HTML'
        result = config.get('ResultType')
        assert result == ResultType.HTML
    
    def test_set_nonexistent_attribute_raises_error(self):
        """Test that setting non-existent attribute raises ValueError."""
        config = GVConfig()
        with pytest.raises(ValueError, match='attempting to set an attribute'):
            config.set('NonExistentAttribute', 'value')
    
    def test_set_name_allowed_even_if_not_exists(self):
        """Test that Name attribute can be set even if it doesn't exist."""
        config = GVConfig()
        config.set('Name', 'TestName')  # Should not raise error
        assert config.Name == 'TestName'


class TestGVConfigInputOutput:
    """Test input and output file configuration."""
    
    def test_setInput_basic(self):
        """Test basic input file setting."""
        config = GVConfig()
        config.setInput('/path/to/file.ged', generalRequest=False)
        assert config.GEDCOMinput == '/path/to/file.ged'
        assert config.parsed == False
    
    def test_setInput_adds_extension_if_missing(self):
        """Test that .ged extension is added if missing."""
        config = GVConfig()
        config.setInput('/path/to/file', generalRequest=False)
        assert config.GEDCOMinput == '/path/to/file.ged'
    
    def test_setInput_sets_resultpath(self):
        """Test that resultpath is set from input file directory."""
        config = GVConfig()
        config.setInput('/path/to/file.ged', generalRequest=False)
        assert config.resultpath == '/path/to'
    
    def test_setInput_none_clears_resultpath(self):
        """Test that None input clears resultpath."""
        config = GVConfig()
        config.setInput(None, generalRequest=False)
        assert config.GEDCOMinput is None
        assert config.resultpath is None
    
    def test_setResultsFile_with_html(self):
        """Test setting results file with HTML output type."""
        config = GVConfig()
        config.setResultsFile('output', ResultType.HTML)
        assert config.ResultFile == 'output.html'
        assert config.ResultType == ResultType.HTML
    
    def test_setResultsFile_with_kml(self):
        """Test setting results file with KML output type."""
        config = GVConfig()
        config.setResultsFile('output', ResultType.KML)
        assert config.ResultFile == 'output.kml'
        assert config.ResultType == ResultType.KML
    
    def test_setstatic(self):
        """Test setting multiple static configuration options."""
        config = GVConfig()
        config.setstatic(
            GEDCOMinput='/path/to/file.ged',
            ResultFile='output',
            ResultType=ResultType.HTML,
            Main='I001',
            MaxMissing=5,
            MaxLineWeight=25,
            UseGPS=False,
            CacheOnly=True,
            AllEntities=True
        )
        assert config.GEDCOMinput == '/path/to/file.ged'
        assert config.Main == 'I001'
        assert config.MaxMissing == 5
        assert config.MaxLineWeight == 25
        assert config.UseGPS == False
        assert config.CacheOnly == True
        assert config.AllEntities == True


class TestGVConfigTimeframe:
    """Test timeframe tracking methods."""
    
    def test_resettimeframe(self):
        """Test resetting timeframe to empty state."""
        config = GVConfig()
        config.timeframe = {'from': 1900, 'to': 2000}
        config.resettimeframe()
        assert config.timeframe == {'from': None, 'to': None}
    
    def test_addtimereference_first(self):
        """Test adding first time reference initializes timeframe."""
        config = GVConfig()
        config.resettimeframe()
        time_ref = Mock(year_num=1950)
        config.addtimereference(time_ref)
        assert config.timeframe['from'] == 1950
        assert config.timeframe['to'] == 1950
    
    def test_addtimereference_extends_range(self):
        """Test adding time references extends the range."""
        config = GVConfig()
        config.resettimeframe()
        config.addtimereference(Mock(year_num=1950))
        config.addtimereference(Mock(year_num=1930))
        config.addtimereference(Mock(year_num=1970))
        assert config.timeframe['from'] == 1930
        assert config.timeframe['to'] == 1970
    
    def test_addtimereference_none_ignored(self):
        """Test that None time reference is ignored."""
        config = GVConfig()
        config.resettimeframe()
        config.addtimereference(None)
        assert config.timeframe == {'from': None, 'to': None}
    
    def test_addtimereference_no_year_ignored(self):
        """Test that time reference without year_num is ignored."""
        config = GVConfig()
        config.resettimeframe()
        config.addtimereference(Mock(spec=[]))
        assert config.timeframe == {'from': None, 'to': None}


class TestGVConfigFileCommands:
    """Test file command configuration."""
    
    def test_file_open_commands_property(self):
        """Test that file_open_commands property returns FileOpenCommandLines."""
        config = GVConfig()
        assert hasattr(config.file_open_commands, 'get_command_for_file_type')
    
    def test_get_file_command_valid_type(self):
        """Test getting file command for valid file type."""
        config = GVConfig()
        # Platform-specific commands should be initialized
        result = config.get_file_command('html')
        # Result may be None or a string depending on platform config
        assert result is None or isinstance(result, str)
    
    def test_get_file_command_invalid_type(self):
        """Test getting file command for invalid file type returns None."""
        config = GVConfig()
        result = config.get_file_command('nonexistent_type')
        assert result is None


class TestGVConfigSaveLoad:
    """Test save and load settings to/from INI file."""
    
    def test_savesettings_creates_ini(self):
        """Test that savesettings creates INI file."""
        config = GVConfig()
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
            temp_ini = f.name
        
        try:
            config.settingsfile = temp_ini
            config.GEDCOMinput = '/test/path/file.ged'
            config.ResultFile = 'output.html'
            config.resultpath = '/test/path'
            config.savesettings()
            
            assert os.path.exists(temp_ini)
            with open(temp_ini, 'r') as f:
                content = f.read()
                # INI file uses lowercase keys
                assert 'inputfile' in content.lower()
                assert '/test/path/file.ged' in content
        finally:
            if os.path.exists(temp_ini):
                os.unlink(temp_ini)
    
    def test_savesettings_saves_main_person_id(self):
        """Test that savesettings saves Main person ID to Gedcom.Main section."""
        config = GVConfig()
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
            temp_ini = f.name
        
        try:
            config.settingsfile = temp_ini
            config.GEDCOMinput = '/test/path/myfile.ged'
            config.Main = 'I001'
            config.resultpath = '/test/path'
            config.ResultFile = 'output.html'
            config.savesettings()
            
            # Verify the INI file contains the Main person ID
            with open(temp_ini, 'r') as f:
                content = f.read()
                assert '[Gedcom.Main]' in content
                assert 'myfile = I001' in content
        finally:
            if os.path.exists(temp_ini):
                os.unlink(temp_ini)
    
    def test_loadsettings_reads_ini(self):
        """Test that loadsettings reads from INI file."""
        config = GVConfig()
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
            temp_ini = f.name
            f.write('[Core]\n')
            f.write('InputFile = /test/input.ged\n')
            f.write('OutputFile = /test/output.html\n')
            f.write('_migration_version = 1\n')
            f.write('[HTML]\n')
            f.write('[Summary]\n')
            f.write('[KML]\n')
            f.write('[Logging]\n')
            f.write('[Gedcom.Main]\n')
        
        try:
            config.settingsfile = temp_ini
            config.loadsettings()
            assert config.GEDCOMinput == '/test/input.ged'
        finally:
            if os.path.exists(temp_ini):
                os.unlink(temp_ini)


class TestGVConfigHelpers:
    """Test helper methods."""
    
    def test_coerce_value_bool_true(self):
        """Test coercing string to bool (true)."""
        config = GVConfig()
        assert config._coerce_value_to_type('true', 'bool') == True
        assert config._coerce_value_to_type('1', 'bool') == True
        assert config._coerce_value_to_type('yes', 'bool') == True
    
    def test_coerce_value_bool_false(self):
        """Test coercing string to bool (false)."""
        config = GVConfig()
        assert config._coerce_value_to_type('false', 'bool') == False
        assert config._coerce_value_to_type('0', 'bool') == False
        assert config._coerce_value_to_type('no', 'bool') == False
    
    def test_coerce_value_int(self):
        """Test coercing string to int."""
        config = GVConfig()
        assert config._coerce_value_to_type('42', 'int') == 42
        assert config._coerce_value_to_type(42, 'int') == 42
    
    def test_coerce_value_str(self):
        """Test coercing value to str."""
        config = GVConfig()
        assert config._coerce_value_to_type(42, 'str') == '42'
        assert config._coerce_value_to_type('test', 'str') == 'test'
    
    def test_coerce_value_result_type(self):
        """Test coercing to ResultType enum."""
        config = GVConfig()
        result = config._coerce_value_to_type('HTML', 'result')
        assert result == ResultType.HTML
    
    def test_coerce_value_none_returns_none(self):
        """Test that None value returns None."""
        config = GVConfig()
        assert config._coerce_value_to_type(None, 'bool') is None
        assert config._coerce_value_to_type(None, 'int') is None
    
    def test_get_option_sections(self):
        """Test getting option sections from YAML."""
        config = GVConfig()
        sections = config._get_option_sections()
        assert isinstance(sections, list)
        assert len(sections) > 0
    
    def test_build_section_keys(self):
        """Test building section keys dictionary."""
        config = GVConfig()
        keys = config._build_section_keys('Core')
        assert isinstance(keys, dict)
