"""Tests for GVProgress progress tracking service."""
import pytest
import time
from services.progress_service import GVProgress


class TestGVProgressInit:
    """Test GVProgress initialization."""
    
    def test_gvprogress_init_default_values(self):
        """Test that GVProgress initializes with correct default values."""
        progress = GVProgress()
        assert progress.counter == 0
        assert progress.state == ""
        assert not progress.running
        assert not progress.stopping
        assert progress.target == 0
        assert progress.step_info is None
        assert progress.running_since_step == 0.0
        assert progress.running_last == 0.0
    
    def test_gvprogress_init_has_lock(self):
        """Test that GVProgress has thread lock for synchronization."""
        progress = GVProgress()
        assert hasattr(progress, '_stop_lock')


class TestGVProgressCounterState:
    """Test counter and state properties."""
    
    def test_counter_getter_setter(self):
        """Test counter property getter and setter."""
        progress = GVProgress()
        progress.counter = 42
        assert progress.counter == 42
    
    def test_state_getter_setter(self):
        """Test state property getter and setter."""
        progress = GVProgress()
        progress.state = "Processing"
        assert progress.state == "Processing"
    
    def test_target_property(self):
        """Test target property."""
        progress = GVProgress()
        progress.target = 100
        assert progress.target == 100
    
    def test_step_counter_legacy_method(self):
        """Test stepCounter legacy method for compatibility."""
        progress = GVProgress()
        progress.stepCounter(25)
        assert progress.counter == 25


class TestGVProgressStep:
    """Test step() method."""
    
    def test_step_with_state_sets_state(self):
        """Test that step with state sets new state."""
        progress = GVProgress()
        progress.step('Processing')
        assert progress.state == 'Processing'
        assert progress.running == True
    
    def test_step_with_state_resets_counter(self):
        """Test that step with state resets counter by default."""
        progress = GVProgress()
        progress.counter = 50
        progress.step('New Step')
        assert progress.counter == 0
    
    def test_step_with_state_no_reset(self):
        """Test that step can preserve counter."""
        progress = GVProgress()
        progress.counter = 50
        progress.step('New Step', resetCounter=False)
        assert progress.counter == 50
    
    def test_step_without_state_increments_counter(self):
        """Test that step without state increments counter."""
        progress = GVProgress()
        progress.step()
        assert progress.counter == 1
        progress.step()
        assert progress.counter == 2
    
    def test_step_with_plus_step(self):
        """Test step with custom increment amount."""
        progress = GVProgress()
        progress.step(plusStep=5)
        assert progress.counter == 5
        progress.step(plusStep=3)
        assert progress.counter == 8
    
    def test_step_with_target(self):
        """Test step with target sets target."""
        progress = GVProgress()
        progress.step('Loading', target=100)
        assert progress.target == 100
    
    def test_step_with_info(self):
        """Test step with additional info."""
        progress = GVProgress()
        progress.step(info='Loading file.txt')
        assert progress.step_info == 'Loading file.txt'
    
    def test_step_returns_stop_status(self):
        """Test that step returns True if stop requested."""
        progress = GVProgress()
        result = progress.step('Processing')
        assert result == False
        progress.stopping = True
        result = progress.step()
        assert result == True
    
    def test_step_snake_case_parameters(self):
        """Test step with snake_case parameter names."""
        progress = GVProgress()
        progress.counter = 10
        # When state is not provided, counter increments
        progress.step(reset_counter=False, plus_step=5)
        assert progress.counter == 15


class TestGVProgressStopControl:
    """Test stop control methods."""
    
    def test_keep_going_when_not_stopping(self):
        """Test keep_going returns True when not stopping."""
        progress = GVProgress()
        assert progress.keep_going() == True
    
    def test_keep_going_when_stopping(self):
        """Test keep_going returns False when stopping."""
        progress = GVProgress()
        progress.stopping = True
        assert progress.keep_going() == False
    
    def test_should_stop_when_not_stopping(self):
        """Test should_stop returns False initially."""
        progress = GVProgress()
        assert progress.should_stop() == False
    
    def test_should_stop_when_stopping(self):
        """Test should_stop returns True when stopping."""
        progress = GVProgress()
        progress.stopping = True
        assert progress.should_stop() == True
    
    def test_stopstep_sets_state(self):
        """Test stopstep can set state."""
        progress = GVProgress()
        result = progress.stopstep('Stopped')
        assert progress.state == 'Stopped'
        assert result == True
    
    def test_stopstep_without_state(self):
        """Test stopstep without parameter."""
        progress = GVProgress()
        progress.state = 'Running'
        result = progress.stopstep()
        assert progress.state == 'Running'  # State unchanged
        assert result == True


class TestGVProgressStopReset:
    """Test stop() and reset() methods."""
    
    def test_stop_resets_state(self):
        """Test stop() resets all state."""
        progress = GVProgress()
        progress.running = True
        progress.stopping = True
        progress.counter = 42
        progress.state = 'Processing'
        
        progress.stop()
        
        assert progress.running == False
        assert progress.stopping == False
        assert progress.counter == 0
        assert progress.state == ""
    
    def test_stop_records_last_counter(self):
        """Test stop() records last counter value."""
        progress = GVProgress()
        progress.counter = 75
        progress.stop()
        assert progress.running_last == 75
    
    def test_reset_clears_all_state(self):
        """Test reset() clears all progress state."""
        progress = GVProgress()
        progress.running = True
        progress.stopping = True
        progress.counter = 50
        progress.target = 100
        progress.state = 'Working'
        progress.step_info = 'Details'
        
        progress.reset()
        
        assert progress.counter == 0
        assert progress.target == 0
        assert progress.state == ""
        assert progress.step_info is None
        assert progress.running == False
        assert progress.stopping == False


class TestGVProgressWorkflow:
    """Test complete workflow scenarios."""
    
    def test_full_operation_workflow(self):
        """Test complete operation workflow."""
        progress = GVProgress()
        
        # Start operation
        progress.step('Loading', target=100)
        assert progress.state == 'Loading'
        assert progress.running == True
        assert progress.target == 100
        assert progress.counter == 0
        
        # Simulate progress
        for i in range(10):
            progress.step()
        assert progress.counter == 10
        
        # Change to new step
        progress.step('Processing', target=50)
        assert progress.state == 'Processing'
        assert progress.counter == 0
        assert progress.target == 50
        
        # Complete operation
        progress.stop()
        assert progress.counter == 0
        assert progress.state == ""
        assert not progress.running
    
    def test_interrupted_operation(self):
        """Test operation with stop request."""
        progress = GVProgress()
        progress.step('Working', target=100)
        
        # Simulate some work
        for i in range(5):
            if progress.step():
                break
        
        # Request stop
        progress.stopping = True
        
        # Check that step returns True
        assert progress.step() == True
        assert progress.should_stop() == True
        
        # Clean up
        progress.stop()
        assert not progress.stopping
