"""
GVProgress: Implements IProgressTracker (progress tracking) for gedcom-to-visualmap.
"""
import threading
import time
from datetime import datetime
from typing import Optional
from services import IProgressTracker

class GVProgress(IProgressTracker):
    """Progress tracking service for gedcom-to-visualmap."""
    def __init__(self):
        self._stop_lock = threading.Lock()
        self.running = False
        self.stopping = False
        self.counter = 0
        self.countertarget = 0
        self.state = ""
        self.stepinfo = None
        self.runningSinceStep = None
        self.lastmax = 0
        self.time = time.ctime()
    def KeepGoing(self) -> bool:
        return not self.ShouldStop()
    def ShouldStop(self) -> bool:
        return self.stopping
    def stopstep(self, state: str) -> bool:
        self.state = state
        return True
    def stepCounter(self, newcounter: int) -> None:
        self.counter = newcounter
    def step(self, state: Optional[str] = None, info: Optional[str] = None, target: int = -1, resetCounter: bool = True, plusStep: int = 1) -> bool:
        if state:
            self.state = state
            if resetCounter:
                self.counter = 0
                self.runningSinceStep = datetime.now().timestamp()
            self.running = True
        else:
            self.counter += plusStep
            self.stepinfo = info
        if target>-1:
            self.runningSinceStep = datetime.now().timestamp()
            self.countertarget = target
        return self.ShouldStop()
    def stop(self) -> None:
        with self._stop_lock:
            self.running = False
            self.stopping = False
            time.sleep(.1)
            self.lastmax = self.counter
            self.time = time.ctime()
            self.counter = 0
            self.state = ""
            self.running = False
            self.stopping = False
