from typing import Protocol, TYPE_CHECKING
from geo_gedcom.app_hooks import AppHooks
from geo_gedcom.gedcom_date import GedcomDate

if TYPE_CHECKING:
    from services import IProgressTracker, IState

class GuiHooks(AppHooks, Protocol):
    """Implements AppHooks using services architecture (IProgressTracker, IState)."""
    
    def __init__(self, svc_progress: 'IProgressTracker', svc_state: 'IState'):
        """Initialize hooks with services.
        
        Args:
            svc_progress: Progress tracking service (IProgressTracker).
            svc_state: Runtime state service (IState).
        """
        self.svc_progress = svc_progress
        self.svc_state = svc_state

    def report_step(self, state: str = None, info: str = None, target: int = -1, reset_counter: bool = False, plus_step: int = 1, set_counter: int = None) -> None:
        """Report progress step using IProgressTracker service."""
        if self.svc_progress and callable(getattr(self.svc_progress, 'step', None)):
            if set_counter is not None:
                self.svc_progress.stepCounter(set_counter)
            else:
                self.svc_progress.step(state=state, info=info, target=target, resetCounter=reset_counter, plusStep=plus_step)
                
    def stop_requested(self) -> bool:
        """Check if stop was requested using IProgressTracker service."""
        if self.svc_progress and callable(getattr(self.svc_progress, 'ShouldStop', None)):
            return self.svc_progress.ShouldStop()
        return False
    
    def update_key_value(self, key: str, value) -> None:
        """Update runtime state using IState service."""
        if self.svc_state and hasattr(self.svc_state, key):
            setattr(self.svc_state, key, value)

    def add_time_reference(self, gedcom_date: GedcomDate) -> None:
        """Add time reference using IState service."""
        if self.svc_state and callable(getattr(self.svc_state, "addtimereference", None)):
            self.svc_state.addtimereference(gedcom_date)
