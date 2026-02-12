"""Test service attribute consistency used by GUI code.

These tests verify that GUI code expectations match service layer attributes,
preventing AttributeError bugs like using 'selected_people' instead of
'selectedpeople'.
"""

import pytest
from unittest.mock import Mock
from services.state_service import GVState


class TestOnInfoServiceIntegration:
    """Test attribute consistency between GUI and service layer."""

    def test_oninfo_uses_correct_selectedpeople_attribute(self):
        """Verify GVState has 'selectedpeople' not 'selected_people'.

        This test catches the bug where gui/core/visual_map_frame.py OnInfo()
        tried to access svc_state.selected_people instead of selectedpeople.
        """
        state = GVState()

        # Verify the correct attribute exists
        assert hasattr(state, "selectedpeople"), "GVState must have 'selectedpeople' attribute for OnInfo()"
        assert not hasattr(state, "selected_people"), "GVState should not have 'selected_people' (note underscore)"

        # Verify attribute works correctly
        state.selectedpeople = 42
        assert state.selectedpeople == 42

    def test_oninfo_required_attributes_exist(self):
        """Verify GVState has all attributes that OnInfo() accesses.

        GUI code in visual_map_frame.py OnInfo() directly accesses these
        attributes. This test ensures they exist to prevent AttributeError.
        """
        state = GVState()

        # These are accessed by OnInfo() method
        required_attrs = ["people", "selectedpeople", "lookup"]

        for attr in required_attrs:
            assert hasattr(state, attr), f"GVState missing '{attr}' attribute required by OnInfo()"

    def test_selectedpeople_type_and_default(self):
        """Verify selectedpeople has correct type and default value."""
        state = GVState()

        # Should default to 0
        assert state.selectedpeople == 0
        assert isinstance(state.selectedpeople, int)

        # Should accept integer assignments
        state.selectedpeople = 100
        assert state.selectedpeople == 100
