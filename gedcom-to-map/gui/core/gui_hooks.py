from typing import Protocol, TYPE_CHECKING
from geo_gedcom.app_hooks import AppHooks
from geo_gedcom.gedcom_date import GedcomDate

if TYPE_CHECKING:
    from gedcom_options import gvOptions

class GuiHooks(AppHooks, Protocol):
    def __init__(self, gOp: 'gvOptions'):
        self.gOp = gOp

    def report_step(self, state: str = None, info: str = None, target: int = -1, reset_counter: bool = False, plus_step: int = 1, set_counter: int = None) -> None:
        if self.gOp and callable(self.gOp.step):
            if set_counter is not None:
                self.gOp.stepCounter(set_counter)
            else:
                self.gOp.step(state=state, info=info, target=target, resetCounter=reset_counter, plusStep=plus_step)
                
    def stop_requested(self) -> bool:
        if self.gOp and callable(self.gOp.ShouldStop):
            return self.gOp.ShouldStop()
        return False
    
    def update_key_value(self, key: str, value) -> None:
        if self.gOp and hasattr(self.gOp, key):
            setattr(self.gOp, key, value)

    def add_time_reference(self, gedcom_date: GedcomDate) -> None:
        if self.gOp and callable(getattr(self.gOp, "addtimereference", None)):
            self.gOp.addtimereference(gedcom_date)
