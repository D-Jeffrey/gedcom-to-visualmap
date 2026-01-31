"""
colour_manager.py

Manages GUI colour definitions loaded from configuration and converts them
to wx.Colour objects. Separates wx-specific colour handling from the config service.
"""
import logging
import wx
from typing import Dict, Optional

_log = logging.getLogger(__name__.lower())


class ColourManager:
    """Manages GUI colours by converting colour name strings to wx.Colour objects."""
    
    def __init__(self, color_definitions: Optional[Dict[str, str]] = None):
        """Initialize ColourManager with colour definitions.
        
        Args:
            color_definitions: Dictionary mapping color names to wx color database names
                             (e.g., {'BTN_PRESS': 'TAN', 'GRID_BACK': 'WHITE'}).
        """
        self._colors: Dict[str, wx.Colour] = {}
        if color_definitions:
            self._load_colors(color_definitions)
    
    def _load_colors(self, color_definitions: Dict[str, str]) -> None:
        """Convert color name strings to wx.Colour objects.
        
        Args:
            color_definitions: Dictionary of color name to wx.TheColourDatabase name.
        """
        for name, color_name in color_definitions.items():
            try:
                col = wx.TheColourDatabase.FindColour(color_name)
                self._colors[name] = col if col and col.IsOk() else wx.WHITE
            except Exception:
                _log.warning(f"Failed to load color '{name}': '{color_name}', using WHITE")
                self._colors[name] = wx.WHITE
    
    def get_color(self, color_name: str) -> wx.Colour:
        """Get a wx.Colour for the given color name.
        
        Args:
            color_name: Name of the color (e.g., 'BTN_PRESS', 'GRID_BACK').
            
        Returns:
            wx.Colour object.
            
        Raises:
            ValueError: If color_name is not defined.
        """
        if color_name in self._colors:
            return self._colors[color_name]
        _log.error(f'Color not defined: {color_name}')
        raise ValueError(f'Color not defined: {color_name}')
    
    def has_color(self, color_name: str) -> bool:
        """Check if a color name is defined.
        
        Args:
            color_name: Name of the color to check.
            
        Returns:
            True if color is defined, False otherwise.
        """
        return color_name in self._colors
