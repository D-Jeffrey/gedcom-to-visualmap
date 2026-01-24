"""
Unit tests for file_operations module.

Tests platform-agnostic file opening utilities, command parsing,
and security features like shell injection prevention.
"""

import pytest
import sys
from unittest.mock import Mock, patch, MagicMock, call
from pathlib import Path

from gui.file_operations import FileOpener


class MockFileOpenCommands:
    """Mock for FileOpenCommandLines configuration."""
    
    def __init__(self):
        self.commands = {}
    
    def get_command_for_file_type(self, file_type: str) -> str:
        return self.commands.get(file_type.upper(), '')
    
    def add_command(self, file_type: str, command: str):
        self.commands[file_type.upper()] = command


@pytest.fixture
def file_opener():
    """Create FileOpener with mock configuration."""
    commands = MockFileOpenCommands()
    commands.add_command('HTML', 'webbrowser $n')
    commands.add_command('CSV', 'excel $n')
    commands.add_command('KML', '$n')
    commands.add_command('DEFAULT', '$n')
    return FileOpener(commands)


class TestFileOpenerInit:
    """Tests for FileOpener initialization."""
    
    def test_init_stores_commands(self):
        commands = MockFileOpenCommands()
        opener = FileOpener(commands)
        assert opener.file_open_commands is commands


class TestOpenFile:
    """Tests for open_file() method."""
    
    @patch.object(FileOpener, 'run_command')
    def test_open_file_with_configured_command(self, mock_run, file_opener):
        file_opener.open_file('csv', '/path/to/file.csv')
        mock_run.assert_called_once_with('excel $n', '/path/to/file.csv', False)
    
    @patch.object(FileOpener, 'run_command')
    def test_open_file_html_uses_browser(self, mock_run, file_opener):
        file_opener.open_file('html', '/path/to/file.html')
        mock_run.assert_called_once_with('webbrowser $n', '/path/to/file.html', True)
    
    @patch.object(FileOpener, 'run_command')
    def test_open_file_kml_uses_browser(self, mock_run, file_opener):
        file_opener.open_file('kml', '/path/to/file.kml')
        mock_run.assert_called_once_with('$n', '/path/to/file.kml', True)
    
    @patch.object(FileOpener, 'run_command')
    def test_open_file_case_insensitive(self, mock_run, file_opener):
        file_opener.open_file('CsV', '/path/to/file.csv')
        mock_run.assert_called_once()
    
    @patch.object(FileOpener, 'run_command')
    def test_open_file_no_command_html_fallback(self, mock_run):
        commands = MockFileOpenCommands()
        opener = FileOpener(commands)
        opener.open_file('html', '/path/to/file.html')
        mock_run.assert_called_once_with('$n', '/path/to/file.html', True)
    
    @patch.object(FileOpener, 'run_command')
    def test_open_file_no_command_non_html_logs_error(self, mock_run, caplog):
        commands = MockFileOpenCommands()
        opener = FileOpener(commands)
        opener.open_file('unknown', '/path/to/file.txt')
        assert 'No command configured for file type: unknown' in caplog.text
        mock_run.assert_not_called()


class TestRunCommand:
    """Tests for run_command() routing logic."""
    
    @patch.object(FileOpener, '_open_in_browser')
    def test_run_command_force_browser(self, mock_browser, file_opener):
        file_opener.run_command('$n', '/path/to/file.html', force_browser=True)
        mock_browser.assert_called_once_with('$n', '/path/to/file.html')
    
    @patch.object(FileOpener, '_open_with_default_handler')
    def test_run_command_platform_default(self, mock_default, file_opener):
        file_opener.run_command('$n', '/path/to/file.csv', force_browser=False)
        mock_default.assert_called_once_with('/path/to/file.csv')
    
    @patch.object(FileOpener, '_open_url')
    def test_run_command_http_url(self, mock_url, file_opener):
        # When cmdline starts with 'http', it's treated as a URL to open
        file_opener.run_command('https://example.com', 'https://example.com', force_browser=False)
        mock_url.assert_called_once_with('https://example.com')
    
    @patch.object(FileOpener, '_open_with_custom_command')
    def test_run_command_custom_command(self, mock_custom, file_opener):
        file_opener.run_command('code "$n"', '/path/to/file.py', force_browser=False)
        mock_custom.assert_called_once_with('code "$n"', '/path/to/file.py')
    
    def test_run_command_empty_datafile_logs_error(self, file_opener, caplog):
        file_opener.run_command('$n', '', force_browser=False)
        assert 'empty datafile' in caplog.text
    
    @patch.object(FileOpener, '_open_in_browser', side_effect=Exception("Test error"))
    def test_run_command_exception_logged(self, mock_browser, file_opener, caplog):
        with pytest.raises(Exception):
            file_opener.run_command('$n', '/path/to/file.html', force_browser=True)
        assert 'Failed to open file/URL' in caplog.text


class TestOpenInBrowser:
    """Tests for _open_in_browser() method."""
    
    @patch('gui.file_operations.webbrowser.open')
    def test_open_in_browser_default(self, mock_wb, file_opener):
        file_opener._open_in_browser('$n', '/path/to/file.html')
        mock_wb.assert_called_once()
        args = mock_wb.call_args[0]
        assert args[0].startswith('file://')
    
    @patch('gui.file_operations.subprocess.Popen')
    @patch('gui.file_operations.shutil.which', return_value='/usr/bin/firefox')
    def test_open_in_browser_custom_command(self, mock_which, mock_popen, file_opener):
        file_opener._open_in_browser('firefox "$n"', '/path/to/file.html')
        mock_popen.assert_called_once()
        assert 'firefox' in mock_popen.call_args[0][0]
    
    @patch('gui.file_operations.webbrowser.open')
    @patch('gui.file_operations.shutil.which', return_value=None)
    def test_open_in_browser_custom_command_not_found_fallback(self, mock_which, mock_wb, file_opener, caplog):
        file_opener._open_in_browser('nonexistent "$n"', '/path/to/file.html')
        assert 'not found, falling back' in caplog.text
        mock_wb.assert_called_once()
    
    @patch('gui.file_operations.webbrowser.open')
    def test_open_in_browser_http_url_unchanged(self, mock_wb, file_opener):
        file_opener._open_in_browser('$n', 'http://example.com/file.html')
        mock_wb.assert_called_once()
        args = mock_wb.call_args[0]
        assert args[0] == 'http://example.com/file.html'


class TestOpenUrl:
    """Tests for _open_url() method."""
    
    @patch('gui.file_operations.webbrowser.open')
    def test_open_url(self, mock_wb, file_opener):
        file_opener._open_url('https://example.com')
        mock_wb.assert_called_once_with('https://example.com', new=0, autoraise=True)


class TestOpenWithDefaultHandler:
    """Tests for _open_with_default_handler() platform routing."""
    
    @patch('gui.file_operations.platform.system', return_value='Windows')
    @patch.object(FileOpener, '_open_with_startfile')
    def test_default_handler_windows(self, mock_startfile, mock_platform, file_opener):
        file_opener._open_with_default_handler('/path/to/file.pdf')
        mock_startfile.assert_called_once_with('/path/to/file.pdf')
    
    @patch('gui.file_operations.platform.system', return_value='Darwin')
    @patch.object(FileOpener, '_open_with_platform_default')
    def test_default_handler_macos_no_custom(self, mock_platform_default, mock_platform, file_opener):
        file_opener._open_with_default_handler('/path/to/file.pdf')
        mock_platform_default.assert_called_once_with('/path/to/file.pdf')
    
    @patch('gui.file_operations.platform.system', return_value='Linux')
    @patch.object(FileOpener, '_open_with_custom_command')
    def test_default_handler_linux_with_custom(self, mock_custom, mock_platform):
        commands = MockFileOpenCommands()
        commands.add_command('DEFAULT', 'xdg-open "$n"')
        opener = FileOpener(commands)
        opener._open_with_default_handler('/path/to/file.pdf')
        mock_custom.assert_called_once_with('xdg-open "$n"', '/path/to/file.pdf')
    
    @patch('gui.file_operations.platform.system', return_value='FreeBSD')
    @patch.object(FileOpener, '_open_with_platform_default')
    def test_default_handler_unknown_platform(self, mock_platform_default, mock_platform, file_opener):
        file_opener._open_with_default_handler('/path/to/file.pdf')
        mock_platform_default.assert_called_once()


class TestOpenWithStartfile:
    """Tests for _open_with_startfile() Windows-specific method."""
    
    @pytest.mark.skipif(not hasattr(__builtins__, 'WindowsError'), reason="Windows-only test")
    @patch('gui.file_operations.os.startfile')
    def test_startfile_available(self, mock_startfile, file_opener):
        file_opener._open_with_startfile('/path/to/file.pdf')
        mock_startfile.assert_called_once_with('/path/to/file.pdf')
    
    def test_startfile_not_available_raises(self, file_opener):
        with patch('gui.file_operations.os', spec=[]):  # os without startfile
            with pytest.raises(EnvironmentError, match='Windows-only'):
                file_opener._open_with_startfile('/path/to/file.pdf')


class TestOpenWithPlatformDefault:
    """Tests for _open_with_platform_default() system-specific commands."""
    
    @patch('gui.file_operations.sys.platform', 'darwin')
    @patch('gui.file_operations.subprocess.Popen')
    def test_platform_default_macos(self, mock_popen, file_opener):
        file_opener._open_with_platform_default('/path/to/file.pdf')
        mock_popen.assert_called_once_with(['open', '/path/to/file.pdf'])
    
    @patch('gui.file_operations.sys.platform', 'linux')
    @patch('gui.file_operations.subprocess.Popen')
    @patch('gui.file_operations.shutil.which', return_value='/usr/bin/xdg-open')
    def test_platform_default_linux(self, mock_which, mock_popen, file_opener):
        file_opener._open_with_platform_default('/path/to/file.pdf')
        mock_popen.assert_called_once_with(['xdg-open', '/path/to/file.pdf'])
    
    @patch('gui.file_operations.sys.platform', 'linux')
    @patch('gui.file_operations.shutil.which', return_value=None)
    def test_platform_default_linux_no_xdg_open_raises(self, mock_which, file_opener):
        with pytest.raises(EnvironmentError, match='xdg-open not found'):
            file_opener._open_with_platform_default('/path/to/file.pdf')
    
    @pytest.mark.skipif(sys.platform != 'win32', reason="Windows-only test")
    @patch('gui.file_operations.sys.platform', 'win32')
    @patch('gui.file_operations.os.startfile')
    def test_platform_default_windows_fallback(self, mock_startfile, file_opener):
        file_opener._open_with_platform_default('/path/to/file.pdf')
        mock_startfile.assert_called_once_with('/path/to/file.pdf')


class TestOpenWithCustomCommand:
    """Tests for _open_with_custom_command() command parsing and execution."""
    
    @patch('gui.file_operations.subprocess.Popen')
    @patch('gui.file_operations.shutil.which', return_value='/usr/bin/code')
    def test_custom_command_with_placeholder(self, mock_which, mock_popen, file_opener):
        file_opener._open_with_custom_command('code "$n"', '/path/to/file.py')
        mock_popen.assert_called_once()
        args = mock_popen.call_args[0][0]
        assert args == ['code', '/path/to/file.py']
    
    @patch('gui.file_operations.subprocess.Popen')
    @patch('gui.file_operations.shutil.which', return_value='/usr/bin/code')
    def test_custom_command_without_placeholder(self, mock_which, mock_popen, file_opener):
        file_opener._open_with_custom_command('code', '/path/to/file.py')
        mock_popen.assert_called_once()
        args = mock_popen.call_args[0][0]
        assert args == ['code', '/path/to/file.py']
    
    @patch('gui.file_operations.subprocess.Popen')
    @patch('gui.file_operations.sys.platform', 'darwin')
    @patch('gui.file_operations.shutil.which', return_value=None)
    @patch('gui.file_operations.os.path.isabs', return_value=False)
    def test_custom_command_macos_app_name(self, mock_isabs, mock_which, mock_popen, file_opener):
        file_opener._open_with_custom_command('Numbers', '/path/to/file.csv')
        mock_popen.assert_called_once()
        args = mock_popen.call_args[0][0]
        assert args[:3] == ['open', '-a', 'Numbers']
    
    @patch('gui.file_operations.subprocess.Popen')
    @patch('gui.file_operations.sys.platform', 'darwin')
    @patch('gui.file_operations.shutil.which', return_value='/usr/bin/code')
    def test_custom_command_macos_executable_not_wrapped(self, mock_which, mock_popen, file_opener):
        file_opener._open_with_custom_command('code', '/path/to/file.py')
        mock_popen.assert_called_once()
        args = mock_popen.call_args[0][0]
        assert args[0] != 'open'  # Should not wrap with 'open -a'
    
    def test_custom_command_empty_raises(self, file_opener):
        with pytest.raises(ValueError, match='empty'):
            file_opener._open_with_custom_command('', '/path/to/file.txt')
    
    def test_custom_command_none_raises(self, file_opener):
        with pytest.raises(ValueError, match='empty'):
            file_opener._open_with_custom_command(None, '/path/to/file.txt')
    
    @patch('gui.file_operations.subprocess.Popen', side_effect=FileNotFoundError())
    @patch('gui.file_operations.sys.platform', 'darwin')
    def test_custom_command_not_found_macos_helpful_error(self, mock_popen, file_opener):
        with pytest.raises(EnvironmentError, match='For macOS apps'):
            file_opener._open_with_custom_command('nonexistent', '/path/to/file.txt')
    
    @patch('gui.file_operations.subprocess.Popen')
    def test_custom_command_shell_false_security(self, mock_popen, file_opener):
        """Verify shell=False is used to prevent shell injection."""
        file_opener._open_with_custom_command('code "$n"', '/path/to/file.py')
        mock_popen.assert_called_once()
        assert mock_popen.call_args[1]['shell'] is False
    
    @patch('gui.file_operations.subprocess.Popen')
    @patch('gui.file_operations.shutil.which', return_value='/usr/bin/myapp')
    def test_custom_command_complex_quoting(self, mock_which, mock_popen, file_opener):
        """Test that shlex properly handles complex quoted arguments."""
        file_opener._open_with_custom_command('myapp --flag "value with spaces" "$n"', '/path/to/file.txt')
        mock_popen.assert_called_once()
        args = mock_popen.call_args[0][0]
        assert args == ['myapp', '--flag', 'value with spaces', '/path/to/file.txt']


class TestEdgeCases:
    """Tests for edge cases and error conditions."""
    
    def test_file_opener_with_spaces_in_path(self, file_opener):
        """Verify paths with spaces are handled correctly."""
        with patch.object(FileOpener, '_open_with_custom_command') as mock:
            file_opener.run_command('code "$n"', '/path with spaces/file.txt')
            mock.assert_called_once()
    
    def test_file_opener_with_special_chars(self, file_opener):
        """Verify paths with special characters are handled."""
        with patch.object(FileOpener, '_open_with_custom_command') as mock:
            file_opener.run_command('code "$n"', '/path/with/[brackets]/file.txt')
            mock.assert_called_once()
    
    @patch('gui.file_operations.webbrowser.open')
    def test_browser_with_query_params(self, mock_wb, file_opener):
        """Verify URLs with query parameters work."""
        file_opener._open_url('https://example.com/path?foo=bar&baz=qux')
        mock_wb.assert_called_once()
        assert '?foo=bar&baz=qux' in mock_wb.call_args[0][0]
