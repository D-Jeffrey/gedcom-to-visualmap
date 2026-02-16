"""Tests for ColourManager."""

import pytest

wx = pytest.importorskip("wx")


class TestApp:
    """Helper to manage wx.App for testing."""

    @classmethod
    def setup_class(cls):
        """Initialize wx.App once for all tests."""
        if not wx.App.Get():
            cls.app = wx.App()

    @classmethod
    def teardown_class(cls):
        """Clean up wx.App after all tests."""
        if hasattr(cls, "app"):
            cls.app.Destroy()


class TestColourManagerInit(TestApp):
    """Test ColourManager initialization."""

    def test_init_empty(self):
        """Test ColourManager initialization with no colour definitions."""
        from gui.layout.colour_manager import ColourManager

        manager = ColourManager()
        assert manager._colors == {}

    def test_init_with_definitions(self):
        """Test ColourManager initialization with colour definitions."""
        from gui.layout.colour_manager import ColourManager

        color_defs = {"BTN_PRESS": "TAN", "GRID_BACK": "WHITE", "GRID_TEXT": "BLACK"}
        manager = ColourManager(color_defs)
        assert len(manager._colors) == 3
        assert "BTN_PRESS" in manager._colors
        assert "GRID_BACK" in manager._colors
        assert "GRID_TEXT" in manager._colors

    def test_init_with_invalid_color(self):
        """Test ColourManager handles invalid colour names gracefully."""
        from gui.layout.colour_manager import ColourManager

        color_defs = {"VALID_COLOR": "RED", "INVALID_COLOR": "NOT_A_COLOR_XYZ"}
        manager = ColourManager(color_defs)
        # Should have both colors, invalid one falls back to WHITE
        assert len(manager._colors) == 2
        assert manager.has_color("VALID_COLOR")
        assert manager.has_color("INVALID_COLOR")


class TestColourManagerGetColor(TestApp):
    """Test ColourManager.get_color() method."""

    def test_get_color_valid(self):
        """Test getting a valid colour returns wx.Colour."""
        from gui.layout.colour_manager import ColourManager

        manager = ColourManager({"TEST_COLOR": "RED"})
        color = manager.get_color("TEST_COLOR")
        assert isinstance(color, wx.Colour)
        assert color.IsOk()

    def test_get_color_not_defined(self):
        """Test getting undefined colour raises ValueError."""
        from gui.layout.colour_manager import ColourManager

        manager = ColourManager({"TEST_COLOR": "RED"})
        with pytest.raises(ValueError, match="Color not defined: UNDEFINED"):
            manager.get_color("UNDEFINED")

    def test_get_color_returns_correct_color(self):
        """Test that get_color returns the correct wx.Colour."""
        from gui.layout.colour_manager import ColourManager

        manager = ColourManager({"RED_COLOR": "RED", "BLUE_COLOR": "BLUE", "WHITE_COLOR": "WHITE"})
        red = manager.get_color("RED_COLOR")
        blue = manager.get_color("BLUE_COLOR")
        white = manager.get_color("WHITE_COLOR")

        # Check colors are different
        assert red.Red() > blue.Red()
        assert blue.Blue() > red.Blue()
        assert white.Red() == 255 and white.Green() == 255 and white.Blue() == 255


class TestColourManagerHasColor(TestApp):
    """Test ColourManager.has_color() method."""

    def test_has_color_true(self):
        """Test has_color returns True for defined colour."""
        from gui.layout.colour_manager import ColourManager

        manager = ColourManager({"TEST_COLOR": "RED"})
        assert manager.has_color("TEST_COLOR") is True

    def test_has_color_false(self):
        """Test has_color returns False for undefined colour."""
        from gui.layout.colour_manager import ColourManager

        manager = ColourManager({"TEST_COLOR": "RED"})
        assert manager.has_color("UNDEFINED") is False

    def test_has_color_empty_manager(self):
        """Test has_color on empty manager returns False."""
        from gui.layout.colour_manager import ColourManager

        manager = ColourManager()
        assert manager.has_color("ANY_COLOR") is False


class TestColourManagerLoadColors(TestApp):
    """Test ColourManager._load_colors() private method."""

    def test_load_colors_valid(self):
        """Test _load_colors with valid colour names."""
        from gui.layout.colour_manager import ColourManager

        manager = ColourManager()
        color_defs = {"COLOR1": "RED", "COLOR2": "GREEN", "COLOR3": "BLUE"}
        manager._load_colors(color_defs)
        assert len(manager._colors) == 3
        assert all(isinstance(c, wx.Colour) for c in manager._colors.values())
        assert all(c.IsOk() for c in manager._colors.values())

    def test_load_colors_fallback_to_white(self):
        """Test _load_colors falls back to WHITE or dark gray for invalid colours."""
        from gui.layout.colour_manager import ColourManager

        manager = ColourManager()
        color_defs = {"INVALID": "NOT_A_REAL_COLOR_XYZ123"}
        manager._load_colors(color_defs)
        color = manager.get_color("INVALID")
        # Should be white (255, 255, 255) in light mode or dark gray (#2A2A2A) in dark mode
        is_white = color.Red() == 255 and color.Green() == 255 and color.Blue() == 255
        is_dark_gray = color.Red() == 42 and color.Green() == 42 and color.Blue() == 42
        assert (
            is_white or is_dark_gray
        ), f"Expected WHITE or #2A2A2A, got RGB({color.Red()}, {color.Green()}, {color.Blue()})"


class TestColourManagerIntegration(TestApp):
    """Integration tests for ColourManager with typical usage patterns."""

    def test_typical_usage_pattern(self):
        """Test typical usage pattern matching production code."""
        from gui.layout.colour_manager import ColourManager

        # Simulate colour definitions from gedcom_options.yaml
        color_defs = {
            "BTN_PRESS": "TAN",
            "BTN_DONE": "LIGHT GREEN",
            "BTN_DEFAULT": "LIGHT GREY",
            "GRID_TEXT": "BLACK",
            "GRID_BACK": "WHITE",
            "INFO_BOX_BACKGROUND": "WHEAT",
            "TITLE_BACK": "LIGHT BLUE",
            "BUSY_BACK": "YELLOW",
            "MAINPERSON": "PALE GREEN",
            "ANCESTOR": "LIGHT STEEL BLUE",
            "OTHERPERSON": "LIGHT GREY",
        }
        manager = ColourManager(color_defs)

        # Verify all colours are accessible
        for color_name in color_defs:
            assert manager.has_color(color_name)
            color = manager.get_color(color_name)
            assert isinstance(color, wx.Colour)
            assert color.IsOk()

    def test_multiple_managers_independent(self):
        """Test multiple ColourManager instances are independent."""
        from gui.layout.colour_manager import ColourManager

        manager1 = ColourManager({"COLOR1": "RED"})
        manager2 = ColourManager({"COLOR2": "BLUE"})

        assert manager1.has_color("COLOR1")
        assert not manager1.has_color("COLOR2")
        assert manager2.has_color("COLOR2")
        assert not manager2.has_color("COLOR1")
