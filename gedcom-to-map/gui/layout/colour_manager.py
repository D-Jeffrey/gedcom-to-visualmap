"""
colour_manager.py

Manages GUI colour definitions loaded from configuration and converts them
to wx.Colour objects. Separates wx-specific colour handling from the config service.
Supports automatic dark mode detection.
"""

import logging
import wx
import sys
from typing import Dict, Optional

_log = logging.getLogger(__name__.lower())


class ColourManager:
    """Manages GUI colours by converting colour name strings to wx.Colour objects.

    Automatically detects system dark mode and selects appropriate color scheme.
    """

    def __init__(
        self,
        color_definitions: Optional[Dict[str, str]] = None,
        dark_color_definitions: Optional[Dict[str, str]] = None,
        use_custom_colors: bool = True,
    ):
        """Initialize ColourManager with colour definitions.

        Args:
            color_definitions: Light mode color dictionary mapping color names
                             to wx color database names or hex values.
            dark_color_definitions: Dark mode color dictionary. If None, uses light colors.
        """
        self._colors: Dict[str, wx.Colour] = {}
        # Store both color schemes for dynamic switching
        self._light_color_definitions = color_definitions or {}
        self._dark_color_definitions = dark_color_definitions or color_definitions or {}
        self._use_custom_colors = bool(use_custom_colors)

        self._is_dark_mode = self._detect_dark_mode()

        # Load initial colors based on current appearance
        self._reload_colors()

    def _detect_dark_mode(self) -> bool:
        """Detect if the system is in dark mode.

        Returns:
            True if dark mode is detected, False otherwise.
        """
        try:
            # Try wxPython system appearance (wx 4.1+)
            if hasattr(wx, "SystemAppearance"):
                appearance = wx.SystemSettings.GetAppearance()
                if appearance.IsDark():
                    return True
            # macOS dark mode detection
            if sys.platform == "darwin":
                import subprocess

                result = subprocess.run(
                    ["defaults", "read", "-g", "AppleInterfaceStyle"], capture_output=True, text=True
                )
                return result.returncode == 0 and "Dark" in result.stdout

            # Windows dark mode detection (Windows 10+)
            elif sys.platform == "win32":
                try:
                    import winreg

                    key = winreg.OpenKey(
                        winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
                    )
                    value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                    winreg.CloseKey(key)
                    return value == 0  # 0 = dark mode, 1 = light mode
                except Exception:
                    pass

        except Exception as e:
            _log.debug(f"Dark mode detection failed: {e}")

        return False

    def is_dark_mode(self) -> bool:
        """Check if dark mode is currently active.

        Returns:
            True if dark mode, False otherwise.
        """
        return self._is_dark_mode

    def refresh_colors(self) -> bool:
        """Re-detect system appearance and reload colors if mode changed.

        Returns:
            True if mode changed and colors were reloaded, False otherwise.
        """
        new_mode = self._detect_dark_mode()
        if new_mode != self._is_dark_mode:
            _log.info(
                f"System appearance changed from {'dark' if self._is_dark_mode else 'light'} "
                f"to {'dark' if new_mode else 'light'} mode"
            )
            self._is_dark_mode = new_mode
            self._reload_colors()
            return True
        return False

    def _reload_colors(self) -> None:
        """Reload colors based on current dark mode setting."""
        if not self._use_custom_colors:
            self._colors.clear()
            _log.info("Custom GUI colors disabled; using platform defaults")
            return

        # Select appropriate color definitions based on system appearance
        if self._is_dark_mode:
            active_definitions = self._dark_color_definitions
            _log.info("Loading dark mode color scheme")
        else:
            active_definitions = self._light_color_definitions
            _log.info("Loading light mode color scheme")

        # Clear existing colors
        self._colors.clear()

        # Load new colors
        if active_definitions:
            self._load_colors(active_definitions)

    def _load_colors(self, color_definitions: Dict[str, str]) -> None:
        """Convert color name strings to wx.Colour objects.

        Supports hex colors and wxPython color database names.
        wx.Colour recognizes standard X11 names (case-insensitive).

        Args:
            color_definitions: Dictionary of color name to color value (hex or name).
        """
        for name, color_value in color_definitions.items():
            try:
                # wx.Colour handles both hex values and standard color names
                col = wx.Colour(str(color_value))

                if col.IsOk():
                    self._colors[name] = col
                else:
                    # Fall back to sensible default
                    self._colors[name] = wx.WHITE if not self._is_dark_mode else wx.Colour("#2A2A2A")
                    _log.warning(f"Failed to load color '{name}': '{color_value}', using default")
            except Exception as e:
                _log.warning(f"Exception loading color '{name}': '{color_value}' - {e}")
                self._colors[name] = wx.WHITE if not self._is_dark_mode else wx.Colour("#2A2A2A")

    def get_color(self, color_name: str) -> wx.Colour:
        """Get a wx.Colour for the given color name.

        Args:
            color_name: Name of the color (e.g., 'BTN_PRESS', 'GRID_BACK').

        Returns:
            wx.Colour object.

        Raises:
            ValueError: If color_name is not defined.
        """
        if not self._use_custom_colors:
            return wx.NullColour
        if color_name in self._colors:
            return self._colors[color_name]
        _log.error(f"Color not defined: {color_name}")
        raise ValueError(f"Color not defined: {color_name}")

    def has_color(self, color_name: str) -> bool:
        """Check if a color name is defined.

        Args:
            color_name: Name of the color to check.

        Returns:
            True if color is defined, False otherwise.
        """
        if not self._use_custom_colors:
            return False
        return color_name in self._colors

    def set_use_custom_colors(self, use_custom_colors: bool) -> None:
        """Enable or disable custom colors and reload active palette."""
        new_value = bool(use_custom_colors)
        if new_value == self._use_custom_colors:
            return
        self._use_custom_colors = new_value
        self._reload_colors()

    def use_custom_colors(self) -> bool:
        """Return whether custom GUI colors are currently enabled."""
        return self._use_custom_colors
