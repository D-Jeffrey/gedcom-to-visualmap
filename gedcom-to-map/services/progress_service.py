"""
GVProgress: Implements IProgressTracker (progress tracking) for gedcom-to-visualmap.
"""
import threading
import time
from datetime import datetime
from typing import Optional
from services.interfaces import IProgressTracker


class GVProgress(IProgressTracker):
    """
    Progress tracking service for gedcom-to-visualmap.
    
    Provides thread-safe progress tracking for long-running operations with:
    - Progress counter and target tracking
    - State descriptions and additional info
    - Timing information (start time, duration)
    - Stop request handling
    
    Attributes:
        counter: Current progress counter value
        target: Target/total value for progress (same as countertarget)
        state: Current state description
        running: Whether an operation is currently running
        stopping: Whether a stop has been requested
        step_info: Additional information about current step
        running_since: Timestamp when current operation started
        running_since_step: Timestamp when current step with target started
        running_last: Duration in seconds of last completed operation
    """
    
    def __init__(self) -> None:
        """Initialize progress tracker with default values."""
        self._stop_lock = threading.Lock()
        self.counter: int = 0
        self.state: str = ""
        self.target: int = 0
        self.running: bool = False
        self.stopping: bool = False
        self.step_info: Optional[str] = None
        self.running_since: float = time.time()
        self.running_since_step: float = 0.0
        self.running_last: float = 0.0
        self.time: str = time.ctime()
    
    def keep_going(self) -> bool:
        """Check if operation should continue (not stopped).
        
        Returns:
            bool: True if operation should continue, False if stopped.
        """
        return not self.stopping
    
    def should_stop(self) -> bool:
        """Check if operation should stop.
        
        Returns:
            bool: True if stop requested, False otherwise.
        """
        return self.stopping
    
    def stopstep(self, state: Optional[str] = None) -> bool:
        """Mark the current step as complete.
        
        Args:
            state: Optional state description (legacy parameter, for compatibility).
        
        Returns:
            bool: Always returns True for legacy compatibility.
        """
        if state is not None:
            self.state = state
        return True
    
    def stepCounter(self, newcounter: int) -> None:
        """Set progress counter directly (legacy method).
        
        Args:
            newcounter: New counter value.
        """
        self.counter = newcounter
    
    def step(self, state: Optional[str] = None, info: Optional[str] = None, 
             target: int = -1, resetCounter: bool = True, plusStep: int = 1,
             reset_counter: bool = None, plus_step: int = None) -> bool:
        """Advance to a new step in the operation.
        
        Args:
            state: New state description. If provided, starts a new step.
            info: Additional information about the step.
            target: Target/total value for this step (-1 or None means no target).
            resetCounter: Whether to reset counter to 0 (legacy parameter).
            plusStep: Amount to increment counter if not resetting (legacy parameter).
            reset_counter: Whether to reset counter (snake_case version).
            plus_step: Amount to increment counter (snake_case version).
        
        Returns:
            bool: True if stop requested, False otherwise.
        """
        # Handle both snake_case and camelCase parameters
        if reset_counter is not None:
            resetCounter = reset_counter
        if plus_step is not None:
            plusStep = plus_step
        
        if state:
            self.state = state
            if resetCounter:
                self.counter = 0
                self.running_since_step = datetime.now().timestamp()
            self.running = True
        else:
            self.counter += plusStep
            if info is not None:
                self.step_info = info
        
        if target is not None and target > -1:
            self.running_since_step = datetime.now().timestamp()
            self.target = target
        
        return self.should_stop()
    
    def reset(self) -> None:
        """Reset all progress tracking to initial state."""
        with self._stop_lock:
            self.counter = 0
            self.target = 0
            self.state = ""
            self.step_info = None
            self.running = False
            self.stopping = False
            self.running_since_step = 0.0
            self.running_last = 0.0
    
    def stop(self) -> None:
        """Stop the current operation and reset state.
        
        Thread-safe method that:
        - Stops the running operation
        - Resets running and stopping flags
        - Resets progress counters and state
        - Records the last counter value before reset
        """
        with self._stop_lock:
            self.running = False
            self.stopping = False
            time.sleep(0.1)  # Brief pause for thread coordination
            self.running_last = float(self.counter)  # Save last counter value
            self.time = time.ctime()
            self.counter = 0
            self.state = ""
