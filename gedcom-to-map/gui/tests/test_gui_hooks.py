"""Test GuiHooks integration with services."""

import pytest
from services.progress_service import GVProgress
from services.state_service import GVState
from geo_gedcom.gedcom_date import GedcomDate


class GuiHooksForTest:
    """Simplified GuiHooks implementation for testing without wxPython."""

    def __init__(self, svc_progress, svc_state):
        """Initialize hooks with services.

        Args:
            svc_progress: Progress tracking service (IProgressTracker).
            svc_state: Runtime state service (IState).
        """
        self.svc_progress = svc_progress
        self.svc_state = svc_state

    def report_step(
        self,
        info: str = None,
        target: int = None,
        reset_counter: bool = False,
        plus_step: int = 1,
        set_counter: int = None,
    ) -> None:
        """Report progress step using IProgressTracker service.

        Args:
            info: Progress message/description (used as state in progress_service).
            target: Target count for progress tracking.
            reset_counter: Whether to reset the counter.
            plus_step: Incremental step count.
            set_counter: Directly set the counter value.
        """
        if self.svc_progress and callable(getattr(self.svc_progress, "step", None)):
            if set_counter is not None:
                self.svc_progress.counter = set_counter
            else:
                # info from gedcom_parser is the step description, so use it as state
                self.svc_progress.step(state=info, target=target, resetCounter=reset_counter, plusStep=plus_step)

    def stop_requested(self) -> bool:
        """Check if stop was requested using IProgressTracker service."""
        if self.svc_progress and callable(getattr(self.svc_progress, "should_stop", None)):
            return self.svc_progress.should_stop()
        return False

    def update_key_value(self, key: str, value) -> None:
        """Update runtime state using IState service."""
        if self.svc_state and hasattr(self.svc_state, key):
            setattr(self.svc_state, key, value)

    def add_time_reference(self, gedcom_date: GedcomDate) -> None:
        """Add time reference using IState service."""
        if self.svc_state and callable(getattr(self.svc_state, "addtimereference", None)):
            self.svc_state.addtimereference(gedcom_date)


class TestGuiHooksReportStep:
    """Test report_step method of GuiHooks."""

    def test_report_step_updates_state(self):
        """Test that report_step updates progress state."""
        svc_progress = GVProgress()
        svc_state = GVState()
        hooks = GuiHooksForTest(svc_progress, svc_state)

        # Call report_step with info parameter
        hooks.report_step(info="Loading GEDCOM file", target=100, reset_counter=True)

        # Check that progress was updated
        assert svc_progress.state == "Loading GEDCOM file"
        assert svc_progress.target == 100
        assert svc_progress.counter == 0  # reset_counter=True

    def test_report_step_increments_counter(self):
        """Test that report_step increments counter."""
        svc_progress = GVProgress()
        svc_state = GVState()
        hooks = GuiHooksForTest(svc_progress, svc_state)

        # Set initial state
        svc_progress.state = "Processing"
        svc_progress.counter = 50

        # Call report_step without info (should increment counter)
        hooks.report_step(plus_step=10)

        # Check that counter was incremented
        assert svc_progress.counter == 60

    def test_report_step_with_set_counter(self):
        """Test that report_step can set counter directly."""
        svc_progress = GVProgress()
        svc_state = GVState()
        hooks = GuiHooksForTest(svc_progress, svc_state)

        # Set initial counter
        svc_progress.counter = 50

        # Call report_step with set_counter
        hooks.report_step(set_counter=75)

        # Check that counter was set directly
        assert svc_progress.counter == 75


class TestGuiHooksStopRequested:
    """Test stop_requested method of GuiHooks."""

    def test_stop_not_requested(self):
        """Test stop_requested when not stopping."""
        svc_progress = GVProgress()
        svc_state = GVState()
        hooks = GuiHooksForTest(svc_progress, svc_state)

        assert hooks.stop_requested() is False

    def test_stop_requested(self):
        """Test stop_requested when stopping flag is set."""
        svc_progress = GVProgress()
        svc_state = GVState()
        hooks = GuiHooksForTest(svc_progress, svc_state)

        # Manually set stopping flag (simulating a stop request)
        svc_progress.stopping = True

        assert hooks.stop_requested() is True


class TestGuiHooksAddTimeReference:
    """Test add_time_reference method of GuiHooks."""

    def test_add_time_reference_updates_state(self):
        """Test that add_time_reference updates state timeframe."""
        svc_progress = GVProgress()
        svc_state = GVState()
        hooks = GuiHooksForTest(svc_progress, svc_state)

        # Create a GEDCOM date with a date string
        gedcom_date = GedcomDate("1 JAN 1850")

        # Add time reference
        hooks.add_time_reference(gedcom_date)

        # Check that state was updated
        assert svc_state.timeframe["from"] == 1850
        assert svc_state.timeframe["to"] == 1850

    def test_add_time_reference_extends_range(self):
        """Test that add_time_reference extends existing range."""
        svc_progress = GVProgress()
        svc_state = GVState()
        hooks = GuiHooksForTest(svc_progress, svc_state)

        # Set initial timeframe
        svc_state.timeframe["from"] = 1850
        svc_state.timeframe["to"] = 1850

        # Create a GEDCOM date for 1900
        gedcom_date = GedcomDate("1 JAN 1900")

        # Add time reference
        hooks.add_time_reference(gedcom_date)

        # Check that range was extended
        assert svc_state.timeframe["from"] == 1850
        assert svc_state.timeframe["to"] == 1900


class TestGuiHooksUpdateKeyValue:
    """Test update_key_value method of GuiHooks."""

    def test_update_existing_attribute(self):
        """Test that update_key_value updates existing state attributes."""
        svc_progress = GVProgress()
        svc_state = GVState()
        hooks = GuiHooksForTest(svc_progress, svc_state)

        # Update existing attribute
        hooks.update_key_value("parsed", True)

        # Check that attribute was updated
        assert svc_state.parsed is True

    def test_update_nonexistent_attribute_ignored(self):
        """Test that update_key_value ignores nonexistent attributes."""
        svc_progress = GVProgress()
        svc_state = GVState()
        hooks = GuiHooksForTest(svc_progress, svc_state)

        # Try to update nonexistent attribute (should not raise error)
        hooks.update_key_value("nonexistent_key", "value")

        # Check that no attribute was created
        assert not hasattr(svc_state, "nonexistent_key")
