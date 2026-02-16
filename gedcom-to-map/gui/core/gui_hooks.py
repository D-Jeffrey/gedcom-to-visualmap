from typing import Protocol, TYPE_CHECKING
from geo_gedcom.app_hooks import AppHooks
from geo_gedcom.gedcom_date import GedcomDate

if TYPE_CHECKING:
    from services.interfaces import IProgressTracker, IState


class GuiHooks(AppHooks, Protocol):
    """Implements AppHooks using services architecture (IProgressTracker, IState)."""

    def __init__(self, svc_progress: "IProgressTracker", svc_state: "IState"):
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
            info: Progress message/description.
            target: Target count for progress tracking.
            reset_counter: Whether to reset the counter.
            plus_step: Incremental step count.
            set_counter: Directly set the counter value.
        """
        if self.svc_progress and callable(getattr(self.svc_progress, "step", None)):
            if set_counter is not None:
                self.svc_progress.counter = set_counter
            else:
                is_new_step = bool(reset_counter) or (target is not None and target > -1)
                if is_new_step:
                    self.svc_progress.step(state=info, target=target, resetCounter=reset_counter, plusStep=plus_step)
                else:
                    self.svc_progress.step(info=info, target=-1, resetCounter=reset_counter, plusStep=plus_step)

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
