"""
test_config_io.py

Unit tests for config_io.py functions.
Tests the configuration file loading, saving, and parsing functionality.
"""
import pytest
import os
import tempfile
import configparser
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from services import config_io
from geo_gedcom.lat_lon import LatLon


class TestSettingsFilePathname:
    """Tests for settings_file_pathname function."""
    
    @patch('platform.system', return_value='Darwin')
    @patch('os.path.expanduser', return_value='/tmp/test')
    @patch('pathlib.Path.mkdir')
    def test_darwin_path(self, mock_mkdir, mock_expanduser, mock_system):
        result = config_io.settings_file_pathname('test.ini')
        # Normalize path separators for cross-platform testing
        normalized_result = result.replace('\\', '/')
        assert '/tmp/test/Library/Application Support/test.ini' in normalized_result
        mock_mkdir.assert_called_once()
    
    @patch('platform.system', return_value='Linux')
    @patch('os.path.expanduser', return_value='/tmp/test')
    @patch('pathlib.Path.mkdir')
    def test_linux_path(self, mock_mkdir, mock_expanduser, mock_system):
        result = config_io.settings_file_pathname('test.ini')
        # Normalize path separators for cross-platform testing
        normalized_result = result.replace('\\', '/')
        assert '/tmp/test/.config/test.ini' in normalized_result
        mock_mkdir.assert_called_once()
    
    @patch('platform.system', return_value='Windows')
    @patch('os.getenv', return_value='C:\\Users\\test\\AppData\\Local')
    @patch('pathlib.Path.mkdir')
    def test_windows_path(self, mock_mkdir, mock_getenv, mock_system):
        result = config_io.settings_file_pathname('test.ini')
        assert 'gedcomvisual' in result
        assert 'test.ini' in result
        mock_mkdir.assert_called_once()
    
    @patch('platform.system', return_value='Unknown')
    def test_unsupported_os(self, mock_system):
        result = config_io.settings_file_pathname('test.ini')
        assert result == 'test.ini'


class TestCoerceValueToType:
    """Tests for coerce_value_to_type function."""
    
    def test_none_value(self):
        result = config_io.coerce_value_to_type(None, 'str')
        assert result is None
    
    def test_bool_type_true_values(self):
        for value in ['1', 'true', 'True', 'yes', 'on', 'y', 't', True]:
            result = config_io.coerce_value_to_type(value, 'bool')
            assert result is True, f"Failed for value: {value}"
    
    def test_bool_type_false_values(self):
        for value in ['0', 'false', 'False', 'no', 'off', 'n', 'f', False]:
            result = config_io.coerce_value_to_type(value, 'bool')
            assert result is False, f"Failed for value: {value}"
    
    def test_int_type(self):
        assert config_io.coerce_value_to_type('42', 'int') == 42
        assert config_io.coerce_value_to_type(42, 'int') == 42
        assert config_io.coerce_value_to_type('  99  ', 'int') == 99
    
    def test_int_from_bool_string(self):
        assert config_io.coerce_value_to_type('true', 'int', 'test') == 1
        assert config_io.coerce_value_to_type('false', 'int', 'test') == 0
    
    def test_str_type(self):
        assert config_io.coerce_value_to_type(42, 'str') == '42'
        assert config_io.coerce_value_to_type('test', 'str') == 'test'
    
    def test_list_type(self):
        result = config_io.coerce_value_to_type('[1, 2, 3]', 'list')
        assert result == [1, 2, 3]
        
        result = config_io.coerce_value_to_type([4, 5, 6], 'list')
        assert result == [4, 5, 6]
    
    def test_dict_type(self):
        result = config_io.coerce_value_to_type("{'key': 'value'}", 'dict')
        assert result == {'key': 'value'}
        
        result = config_io.coerce_value_to_type({'a': 1}, 'dict')
        assert result == {'a': 1}
    
    def test_result_type(self):
        # ResultType is imported late in coerce_value_to_type from render.result_type module
        # Just test that it processes the value correctly
        with patch('render.result_type.ResultType') as mock_result_type:
            mock_result_type.ResultTypeEnforce.return_value = 'HTML'
            result = config_io.coerce_value_to_type('HTML', 'result')
            mock_result_type.ResultTypeEnforce.assert_called_once()
    
    def test_result_type_with_prefix(self):
        with patch('render.result_type.ResultType') as mock_result_type:
            mock_result_type.ResultTypeEnforce.return_value = 'HTML'
            result = config_io.coerce_value_to_type('ResultType.HTML', 'result')
            mock_result_type.ResultTypeEnforce.assert_called_once_with('HTML')
    
    def test_latlon_type(self):
        result = config_io.coerce_value_to_type('LatLon(40.7, -74.0)', 'latlon')
        assert isinstance(result, LatLon)
        assert result.latitude == 40.7
        assert result.longitude == -74.0
    
    def test_latlon_with_none_values(self):
        result = config_io.coerce_value_to_type('LatLon(None, None)', 'latlon')
        # Should handle None values gracefully
        assert result is not None
    
    def test_yaml_parsing(self):
        result = config_io.coerce_value_to_type('{"nested": {"key": "value"}}', 'other')
        assert result == {"nested": {"key": "value"}}
    
    def test_literal_eval_fallback(self):
        result = config_io.coerce_value_to_type('(1, 2, 3)', 'other')
        assert result == (1, 2, 3)
    
    def test_error_handling(self):
        # Should not raise, should log and return original or safe value
        result = config_io.coerce_value_to_type('invalid_int', 'int', 'test_context')
        # May return original value or raise - depends on implementation


class TestGetOptionSections:
    """Tests for get_option_sections function."""
    
    def test_empty_options(self):
        result = config_io.get_option_sections({})
        assert result == []
    
    def test_valid_sections(self):
        options = {
            'Core': {
                'option1': {'type': 'str', 'default': 'value1'},
                'option2': {'type': 'int', 'default': 42}
            },
            'HTML': {
                'option3': {'type': 'bool', 'default': True}
            },
            'not_a_section': 'plain_value'
        }
        result = config_io.get_option_sections(options)
        assert 'Core' in result
        assert 'HTML' in result
        assert 'not_a_section' not in result
    
    def test_mixed_content(self):
        options = {
            'ValidSection': {
                'key': {'type': 'str', 'default': 'val'}
            },
            'InvalidSection': {
                'key': 'not_a_dict'
            }
        }
        result = config_io.get_option_sections(options)
        assert 'ValidSection' in result
        assert 'InvalidSection' not in result


class TestSetOptions:
    """Tests for set_options function."""
    
    def test_set_single_option(self):
        obj = Mock()
        options_types = {'test_attr': 'str'}
        options_defaults = {'test_attr': 'test_value'}
        
        config_io.set_options(obj, options_types, options_defaults)
        assert obj.test_attr == 'test_value'
    
    def test_set_multiple_options(self):
        obj = Mock()
        options_types = {
            'str_opt': 'str',
            'int_opt': 'int',
            'bool_opt': 'bool'
        }
        options_defaults = {
            'str_opt': 'hello',
            'int_opt': '42',
            'bool_opt': 'true'
        }
        
        config_io.set_options(obj, options_types, options_defaults)
        assert obj.str_opt == 'hello'
        assert obj.int_opt == 42
        assert obj.bool_opt is True
    
    def test_missing_default(self):
        obj = Mock()
        options_types = {'test_attr': 'str'}
        options_defaults = {}
        
        config_io.set_options(obj, options_types, options_defaults)
        assert obj.test_attr is None


class TestSetMarkerDefaults:
    """Tests for set_marker_defaults function."""
    
    def test_set_marker_defaults(self):
        obj = Mock()
        obj.options = {
            'html_display_options': {
                'marker1': {'default': 'value1'},
                'marker2': {'default': 'value2'}
            }
        }
        
        config_io.set_marker_defaults(obj)
        assert obj.marker1 == 'value1'
        assert obj.marker2 == 'value2'
    
    def test_empty_marker_options(self):
        obj = Mock()
        obj.options = {'html_display_options': {}}
        
        config_io.set_marker_defaults(obj)
        # Should not raise


class TestSetMarkerOptions:
    """Tests for set_marker_options function."""
    
    def test_set_valid_markers(self):
        obj = Mock()
        obj.options = {
            'html_display_options': {
                'marker1': {},
                'marker2': {}
            }
        }
        marker_options = {'marker1': 'val1', 'marker2': 'val2'}
        
        config_io.set_marker_options(obj, marker_options)
        assert obj.marker1 == 'val1'
        assert obj.marker2 == 'val2'
    
    def test_unknown_marker_warning(self, caplog):
        obj = Mock()
        obj.options = {'html_display_options': {'known_marker': {}}}
        marker_options = {'unknown_marker': 'value'}
        
        config_io.set_marker_options(obj, marker_options)
        assert 'Unknown marker option' in caplog.text
    
    def test_missing_marker_attribute(self):
        obj = Mock(spec=[])
        obj.options = {'html_display_options': {'marker1': {}}}
        
        with patch('services.config_io.hasattr', return_value=False):
            config_io.set_marker_options(obj, {})
            # Should set missing marker to None


class TestBuildSectionKeys:
    """Tests for build_section_keys function."""
    
    def test_build_section_keys(self):
        options = {
            'Core': {
                'option1': {'type': 'str', 'default': 'val', 'ini_section': 'Core'},
                'option2': {'type': 'int', 'default': 42, 'ini_section': 'Core'}
            },
            'HTML': {
                'option3': {'type': 'bool', 'default': True, 'ini_section': 'HTML'}
            }
        }
        
        result = config_io.build_section_keys(options, 'Core')
        assert 'option1' in result
        assert 'option2' in result
        assert result['option1'] == 'str'
        assert result['option2'] == 'int'
        assert 'option3' not in result
    
    def test_ini_type_override(self):
        options = {
            'Core': {
                'option1': {
                    'type': 'str',
                    'default': 'val',
                    'ini_section': 'Core',
                    'ini_type': 'int'
                }
            }
        }
        
        result = config_io.build_section_keys(options, 'Core')
        assert result['option1'] == 'int'


class TestLoadSection:
    """Tests for loadsection function."""
    
    def test_load_section_basic(self):
        obj = Mock()
        obj.gvConfig = {
            'TestSection': {
                'key1': '42',
                'key2': 'true'
            }
        }
        keys = {'key1': 'int', 'key2': 'bool'}
        
        config_io.loadsection(obj, 'TestSection', keys)
        assert obj.key1 == 42
        assert obj.key2 is True
    
    def test_load_section_missing_value(self):
        obj = Mock()
        obj.gvConfig = {'TestSection': {}}
        keys = {'key1': 'str'}
        
        config_io.loadsection(obj, 'TestSection', keys)
        # Should not set attribute for missing values


class TestLoadSettings:
    """Tests for loadsettings function."""
    
    def test_load_settings_integration(self):
        # Create a temporary INI file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False, encoding='utf-8') as f:
            f.write('[Core]\n')
            f.write('InputFile = /path/to/file.ged\n')
            f.write('_migration_version = 1\n')
            temp_file = f.name
        
        try:
            obj = Mock()
            obj.settingsfile = temp_file
            obj.options = {
                'Core': {
                    'InputFile': {'type': 'str', 'default': '', 'ini_section': 'Core'}
                }
            }
            obj.ResultType = Mock()
            obj.file_open_commands = Mock()
            obj.file_open_commands.list_file_types.return_value = []
            obj.setInput = Mock()
            obj.setResultsFile = Mock()
            
            config_io.loadsettings(obj)
            
            assert obj.gvConfig is not None
            obj.setInput.assert_called_once()
        finally:
            os.unlink(temp_file)
    
    def test_load_settings_migration(self):
        # Test migration from version 0 to 1
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False, encoding='utf-8') as f:
            f.write('[Core]\n')
            f.write('OldSetting = value\n')
            temp_file = f.name
        
        try:
            obj = Mock()
            obj.settingsfile = temp_file
            obj.options = {
                'old_ini_settings': {'OldSetting': 'Core'}
            }
            obj.ResultType = Mock()
            obj.file_open_commands = Mock()
            obj.file_open_commands.list_file_types.return_value = []
            obj.setInput = Mock()
            obj.setResultsFile = Mock()
            
            config_io.loadsettings(obj)
            
            # Should have migrated
            assert obj.gvConfig['Core'].get('_migration_version') == '2'
        finally:
            os.unlink(temp_file)


class TestSaveSettings:
    """Tests for savesettings function."""
    
    def test_save_settings_basic(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False, encoding='utf-8') as f:
            temp_file = f.name
        
        try:
            obj = Mock()
            obj.settingsfile = temp_file
            obj.gvConfig = configparser.ConfigParser()
            # Initialize sections
            for section in ['Core', 'HTML', 'Summary', 'KML', 'Logging', 'Gedcom.Main']:
                obj.gvConfig[section] = {}
            obj.options = {
                'Core': {
                    'TestKey': {'type': 'str', 'default': 'val', 'ini_section': 'Core'}
                },
                'HTML': {},
                'Summary': {},
                'KML': {}
            }
            obj.TestKey = 'test_value'
            obj.GEDCOMinput = '/path/to/file.ged'
            obj.resultpath = '/path/to'
            obj.ResultFile = 'output.html'
            obj.Main = None
            obj.file_open_commands = Mock()
            obj.file_open_commands.list_file_types.return_value = []
            
            config_io.savesettings(obj)
            
            # Verify file was written
            assert os.path.exists(temp_file)
            
            # Read back and verify
            config = configparser.ConfigParser()
            config.read(temp_file)
            assert 'Core' in config.sections()
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    def test_save_settings_creates_config(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False, encoding='utf-8') as f:
            temp_file = f.name
        
        try:
            obj = Mock()
            obj.settingsfile = temp_file
            obj.gvConfig = None  # No existing config
            obj.options = {}
            obj.GEDCOMinput = '/test.ged'
            obj.resultpath = '/test'
            obj.ResultFile = 'output.html'
            obj.Main = None
            obj.file_open_commands = Mock()
            obj.file_open_commands.list_file_types.return_value = []
            
            config_io.savesettings(obj)
            
            # Should have created config
            assert obj.gvConfig is not None
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)


class TestIntegration:
    """Integration tests combining multiple functions."""
    
    def test_load_save_roundtrip(self):
        """Test that settings can be saved and loaded back."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False, encoding='utf-8') as f:
            temp_file = f.name
        
        try:
            # Create object with some values
            obj = Mock()
            obj.settingsfile = temp_file
            obj.gvConfig = None
            obj.options = {
                'Core': {
                    'TestOption': {
                        'type': 'str',
                        'default': 'default_val',
                        'ini_section': 'Core'
                    }
                }
            }
            obj.TestOption = 'saved_value'
            obj.GEDCOMinput = '/path/to/test.ged'
            obj.resultpath = '/path/to'
            obj.ResultFile = 'test.html'
            obj.Main = 'I001'
            obj.ResultType = Mock()
            obj.file_open_commands = Mock()
            obj.file_open_commands.list_file_types.return_value = []
            
            # Save
            config_io.savesettings(obj)
            
            # Create new object to load into
            obj2 = Mock()
            obj2.settingsfile = temp_file
            obj2.options = obj.options
            obj2.ResultType = Mock()
            obj2.file_open_commands = Mock()
            obj2.file_open_commands.list_file_types.return_value = []
            obj2.setInput = Mock()
            obj2.setResultsFile = Mock()
            
            # Load
            config_io.loadsettings(obj2)
            
            # Verify
            assert obj2.TestOption == 'saved_value'
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
