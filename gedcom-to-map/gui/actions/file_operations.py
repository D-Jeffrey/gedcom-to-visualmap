"""
file_operations.py - Platform-agnostic file opening utilities.

Handles opening files with appropriate applications across different platforms:
- Windows (os.startfile)
- macOS (open command)
- Linux (xdg-open)

Supports custom commands, web browsers, and platform defaults.

Author: @colin0brass
"""

import os
import sys
import platform
import subprocess
import webbrowser
import shutil
import logging
import shlex
from pathlib import Path
from typing import Optional

_log = logging.getLogger(__name__)


class FileOpener:
    """Handles opening files and URLs with platform-appropriate handlers.
    
    Provides unified interface for opening files across platforms, supporting:
    - Web browsers for HTML/KML files
    - Platform default file handlers
    - Custom commands with configurable templates
    - URL opening in browsers
    
    Example:
        opener = FileOpener(svc_config)
        opener.open_file('html', '/path/to/map.html')
        opener.open_file('csv', '/path/to/data.csv')
    """
    
    def __init__(self, config_service):
        """Initialize FileOpener with configuration service.
        
        Args:
            config_service: IConfig service with get_file_command method
        """
        self.config_service = config_service
    
    def open_file(self, file_type: str = 'html', datafile: str = '') -> None:
        """Open file using command configured for specified file type.
        
        Looks up command for file_type in file_open_commands configuration and
        opens datafile using that command. For HTML/KML file types, can force
        opening in web browser. Falls back to default browser for HTML/KML if
        no command is configured.
        
        Args:
            file_type: Type of file to open. Case-insensitive, uppercased for lookup.
                      Common types: 'html', 'kml', 'kml2', 'csv', 'trace', 'default'.
            datafile: Path to file to open.
        
        Example:
            # Open HTML in browser
            opener.open_file('html', '/path/to/map.html')
            
            # Open CSV in configured viewer
            opener.open_file('csv', '/path/to/data.csv')
        
        Note:
            If no command is configured for file_type and it's not HTML/KML,
            logs error and returns without opening file.
        """
        cmd = self.config_service.get_file_command(file_type) if hasattr(self.config_service, 'get_file_command') else None
        if not cmd:
            # Fallback to default browser for HTML/KML
            if file_type.lower() in ('html', 'kml', 'kml2'):
                cmd = '$n'
            else:
                _log.error("No command configured for file type: %s", file_type)
                return
        use_browser = file_type.lower() in ('html', 'kml', 'kml2')
        self.run_command(cmd, datafile, use_browser)
    
    def run_command(self, cmdline: str, datafile: str, force_browser: bool = False) -> None:
        """Run external command or open file/URL using platform-appropriate handler.
        
        Core file opening method that routes to appropriate handler based on:
        - force_browser flag: Always use web browser
        - cmdline='$n': Use platform default file handler
        - cmdline starts with 'http': Open URL in browser
        - Other cmdline: Execute custom command with file as argument
        
        Args:
            cmdline: Command line template. Special values:
                     - '$n': Use platform default handler (open/xdg-open/os.startfile)
                     - 'http://...': Open URL in browser
                     - Other: Custom command, '$n' placeholder replaced with datafile
            datafile: Path to file or URL to open.
            force_browser: If True, always use web browser (for HTML/KML files).
        
        Raises:
            EnvironmentError: If required file opener is not available on platform.
            ValueError: If cmdline is empty when custom command is expected.
            Exception: Other file opening errors (logged).
        
        Example:
            # Open with platform default
            opener.run_command('$n', '/path/to/file.csv')
            
            # Open in browser
            opener.run_command('$n', '/path/to/map.html', force_browser=True)
            
            # Custom command
            opener.run_command('excel "$n"', '/path/to/data.csv')
        """
        if not datafile:
            _log.error("run_command: empty datafile provided")
            return
        
        try:
            if force_browser:
                self._open_in_browser(cmdline, datafile)
            elif cmdline == '$n':
                self._open_with_default_handler(datafile)
            elif cmdline.startswith('http'):
                self._open_url(cmdline)
            else:
                self._open_with_custom_command(cmdline, datafile)
        except Exception as e:
            _log.exception("Failed to open file/URL")
            _log.error("Failed to open: %s", e)
            raise
    
    def _open_in_browser(self, cmdline: str, datafile: str) -> None:
        """Open file in web browser, trying custom command first.
        
        If cmdline specifies a custom browser command (not '$n' and not a URL),
        attempts to use it. Falls back to webbrowser.open() if custom command
        fails or is not configured.
        
        Args:
            cmdline: Browser command template with '$n' placeholder, or '$n' for default.
            datafile: Path to HTML/KML file to open.
        
        Example:
            # Use default browser
            _open_in_browser('$n', '/path/to/map.html')
            
            # Use custom browser
            _open_in_browser('firefox "$n"', '/path/to/map.html')
        """
        _log.info('Opening in browser: %s (cmdline: %s)', datafile, cmdline)
        
        # Try custom command if configured
        done = False
        if cmdline != '$n' and cmdline and not cmdline.startswith('http'):
            try:
                cmd_parts = shlex.split(cmdline.replace('$n', datafile))
                cmd_name = cmd_parts[0]
                if shutil.which(cmd_name):
                    subprocess.Popen(cmd_parts, shell=False)
                    done = True
                else:
                    _log.warning("Custom HTML command '%s' not found, falling back to webbrowser", cmd_name)
            except Exception as e:
                _log.warning("Custom HTML command failed, falling back to webbrowser: %s", e)

        if not done:        
            # Fallback to default browser
            # Convert file path to proper file:// URI if needed
            if not datafile.startswith(('http://', 'https://', 'file://')):
                datafile = Path(datafile).resolve().as_uri()
            
            _log.info('Opening URI in browser: %s', datafile)
            webbrowser.open(datafile, new=0, autoraise=True)
    
    def _open_url(self, url: str) -> None:
        """Open HTTP/HTTPS URL in default web browser.
        
        Args:
            url: URL to open (must start with 'http://' or 'https://').
        
        Example:
            _open_url('https://example.com')
        """
        _log.info('Opening URL in browser: %s', url)
        webbrowser.open(url, new=0, autoraise=True)
    
    def _open_with_default_handler(self, datafile: str) -> None:
        """Open file with platform's default handler.
        
        Routes to appropriate handler based on detected platform:
        - Windows: Uses os.startfile()
        - macOS/Linux: Checks for custom command in settings, falls back to
                       platform default (open/xdg-open)
        - Other: Attempts platform default
        
        Args:
            datafile: Path to file to open.
        
        Raises:
            EnvironmentError: If required file opener is not available on platform.
        
        Note:
            Uses platform.system() for detection:
            - 'Windows': Windows OS
            - 'Darwin': macOS
            - 'Linux': Linux
        """
        system = platform.system()
        if system == 'Windows':
            self._open_with_startfile(datafile)
        elif system in ('Darwin', 'Linux'):
            cmd = self.config_service.get_file_command('default')
            if cmd and cmd != '$n':
                self._open_with_custom_command(cmd, datafile)
            else:
                # No custom command, use platform default
                self._open_with_platform_default(datafile)
        else:
            # Unknown platform, try platform default
            self._open_with_platform_default(datafile)
    
    def _open_with_startfile(self, datafile: str) -> None:
        """Open file using Windows-specific os.startfile() function.
        
        Args:
            datafile: Path to file to open.
        
        Raises:
            EnvironmentError: If os.startfile is not available (non-Windows platform).
                              Error message instructs user to change settings to use
                              'subprocess.popen' option instead.
        
        Note:
            os.startfile() only exists on Windows. On other platforms, this method
            will always raise EnvironmentError.
        """
        if not hasattr(os, 'startfile'):
            raise EnvironmentError(
                "os.startfile is Windows-only. "
                "Change process option in Settings to 'subprocess.popen'"
            )
        _log.info('Opening with os.startfile: %s', datafile)
        os.startfile(datafile)
    
    def _open_with_platform_default(self, datafile: str) -> None:
        """Open file with platform-specific default file opener.
        
        Uses platform-appropriate commands:
        - macOS: 'open' command (always available)
        - Windows: os.startfile() (fallback if reached via this path)
        - Linux/Unix: 'xdg-open' command (requires xdg-utils package)
        
        Args:
            datafile: Path to file to open.
        
        Raises:
            EnvironmentError: If platform-specific opener is not available.
                              For Linux, provides distro-specific installation
                              instructions for xdg-utils package.
        
        Example:
            # macOS
            _open_with_platform_default('/path/to/file.pdf')  # Uses 'open'
            
            # Linux
            _open_with_platform_default('/path/to/file.pdf')  # Uses 'xdg-open'
        """
        _log.info('Opening with platform default: %s', datafile)
        
        if sys.platform == "darwin":
            # macOS
            subprocess.Popen(["open", datafile])
        
        elif sys.platform.startswith("win"):
            # Windows fallback
            if not hasattr(os, 'startfile'):
                raise EnvironmentError("No file opener available on Windows")
            os.startfile(datafile)
        
        else:
            # Linux/Unix
            opener = "xdg-open"
            if not shutil.which(opener):
                raise EnvironmentError(
                    f"{opener} not found. Install xdg-utils package:\n"
                    "  Ubuntu/Debian: sudo apt install xdg-utils\n"
                    "  Fedora/RHEL: sudo dnf install xdg-utils\n"
                    "  Arch: sudo pacman -S xdg-utils"
                )
            subprocess.Popen([opener, datafile])
    
    def _open_with_custom_command(self, cmdline: str, datafile: str) -> None:
        """Open file with user-configured custom command.
        
        Safely executes custom command by parsing with shlex to prevent shell
        injection. Supports '$n' placeholder for filename in command template.
        
        On macOS, if the command is an application name (e.g., 'Numbers', 'Excel'),
        automatically uses 'open -a' to launch it properly.
        
        Args:
            cmdline: Command line template. If contains '$n', placeholder is replaced
                    with datafile path. Otherwise, datafile is passed as argument.
            datafile: Path to file to open.
        
        Raises:
            ValueError: If cmdline is None or empty string.
            subprocess.SubprocessError: If command execution fails.
        
        Example:
            # With placeholder
            _open_with_custom_command('code "$n"', '/path/to/file.txt')
            # Executes: code "/path/to/file.txt"
            
            # Without placeholder
            _open_with_custom_command('code', '/path/to/file.txt')
            # Executes: code /path/to/file.txt
            
            # macOS app (automatically uses 'open -a')
            _open_with_custom_command('Numbers', '/path/to/file.csv')
            # Executes: open -a Numbers /path/to/file.csv
        
        Security:
            Uses shlex.split() and shell=False to prevent shell injection attacks.
        """
        if not cmdline:
            raise ValueError("Custom command is empty or None")
        
        if '$n' in cmdline:
            # Replace placeholder and parse safely
            full_command = cmdline.replace('$n', datafile)
            cmd_parts = shlex.split(full_command)
        else:
            # Command doesn't use placeholder, pass file as argument
            cmd_parts = [cmdline, datafile]
        
        # On macOS, check if command is an app name (not an executable path)
        if sys.platform == "darwin" and len(cmd_parts) > 0:
            cmd_name = cmd_parts[0]
            # Check if it's not an executable in PATH and not an absolute path
            if not shutil.which(cmd_name) and not os.path.isabs(cmd_name) and not cmd_name.startswith('./'):
                # Likely an app name - use 'open -a'
                _log.info('macOS: Using "open -a" for app: %s', cmd_name)
                cmd_parts = ['open', '-a', cmd_name] + cmd_parts[1:]
        
        _log.info('Opening with custom command: %s', cmd_parts)
        try:
            subprocess.Popen(cmd_parts, shell=False)
        except FileNotFoundError as e:
            if sys.platform == "darwin":
                # Provide helpful error message for macOS
                raise EnvironmentError(
                    f"Command '{cmd_parts[0]}' not found. "
                    f"For macOS apps, use format like 'Numbers' or 'Microsoft Excel'. "
                    f"For command-line tools, ensure they're in PATH or use full path."
                ) from e
            else:
                raise
