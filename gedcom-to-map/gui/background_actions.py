import _thread
import logging
import time
from pathlib import Path

import wx

from .gedcomvisual import ParseAndGPS, doHTML, doKML, doKML2, doSUM, doTraceTo  # type: ignore

_log = logging.getLogger(__name__.lower())


class BackgroundActions:
    """
    Background worker for parsing, geocoding and generating output.

    Designed to be imported without causing circular imports; heavy helpers
    (ParseAndGPS, doHTML, doKML, doKML2, doSUM, doTraceTo) are imported
    lazily inside Run().
    """
    def __init__(self, win, threadnum, gOp):
        self.win = win
        self.gOp = gOp
        self.people = None
        self.threadnum = threadnum
        self.updategrid = False
        self.updategridmain = True
        self.updateinfo = ''  # This will prime the update
        self.errorinfo = None
        self.keepGoing = True
        self.threadrunning = True
        self.do = -1
        self.readyToDo = True

    def Start(self):
        self.keepGoing = self.threadrunning = True
        self.do = 0
        logging.info("Started thread %d from thread %d", self.threadnum, _thread.get_ident())
        _thread.start_new_thread(self.Run, ())

    def Stop(self):
        self.keepGoing = False

    def IsRunning(self):
        return self.threadrunning

    def IsTriggered(self):
        return self.do != 0

    def Trigger(self, dolevel):
        try:
            if dolevel & 1 or dolevel & 4:
                self.gOp.panel.id.BTNLoad.SetBackgroundColour(self.gOp.panel.id.GetColor('BTN_DONE'))
            if dolevel & 2:
                self.gOp.panel.id.BTNCreateFiles.SetBackgroundColour(self.gOp.panel.id.GetColor('BTN_DONE'))
        except Exception:
            _log.exception("Trigger: failed to update button colours")
        self.do = dolevel

    def SayInfoMessage(self, line, newline=True):
        if newline and self.updateinfo and self.updateinfo != '':
            self.updateinfo = self.updateinfo + "\n"
        self.updateinfo = self.updateinfo + line if self.updateinfo else line

    def SayErrorMessage(self, line, newline=True):
        if newline and self.errorinfo and self.errorinfo != '':
            self.errorinfo = self.errorinfo + "\n"
        self.errorinfo = self.errorinfo + line if self.errorinfo else line

    def Run(self):
        """
        Main worker loop. Imports processing functions lazily to avoid import-time
        circular dependencies with the GUI package.
        """
        self.SayInfoMessage(' ', True)  # prime the InfoBox

        while self.keepGoing:
            if self.do != 0 and self.readyToDo:
                self.readyToDo = False  # Avoid a Race
                _log.info("triggered thread %d (Thread# %d / %d)", self.do, self.threadnum, _thread.get_ident())
                self.gOp.stopping = False
                wx.Yield()
                # Obtain event type from gOp if available
                UpdateBackgroundEvent = getattr(self.gOp, "UpdateBackgroundEvent", None)
                try:
                    if self.do & 1 or (self.do & 4 and not getattr(self.gOp, "parsed", False)):
                        if UpdateBackgroundEvent:
                            wx.PostEvent(self.win, UpdateBackgroundEvent(state='busy'))
                        wx.Yield()
                        _log.info("start ParseAndGPS")
                        if hasattr(self, "people") and self.people:
                            try:
                                del self.people
                            except Exception:
                                pass
                            self.gOp.people = None
                            self.people = None
                        _log.info("ParseAndGPS")
                        try:
                            if ParseAndGPS:
                                # ParseAndGPS may take time; ensure it can be interrupted by cooperative checks in that code
                                self.people = ParseAndGPS(self.gOp, 1)
                            else:
                                self.people = None
                        except Exception as e:
                            _log.exception("Issues in ParseAndGPS")
                            if hasattr(self, "people") and self.people:
                                try:
                                    del self.people
                                except Exception:
                                    pass
                                self.people = None
                            self.do = 0
                            _log.warning(str(e))
                            self.gOp.stopping = False
                            self.SayErrorMessage('Failed to Parse', True)
                            self.SayErrorMessage(str(e), True)

                        if self.do & 1 and getattr(self.gOp, "Referenced", None):
                            try:
                                del self.gOp.Referenced
                                self.gOp.Referenced = None
                            except Exception:
                                pass

                        if hasattr(self, "people") and self.people:
                            _log.info("person count %d", len(self.people))
                            self.updategrid = True
                            if self.people:
                                self.SayInfoMessage(f"Loaded {len(self.people)} people")
                            else:
                                self.SayInfoMessage(f"Cancelled loading people")
                            if getattr(self.gOp, "Main", None):
                                try:
                                    self.SayInfoMessage(f" with '{self.gOp.Main}' as starting person from {Path(self.gOp.GEDCOMinput).name}", False)
                                except Exception:
                                    pass
                        else:
                            if getattr(self.gOp, "stopping", False):
                                self.SayErrorMessage(f"Error: Aborted loading GEDCOM file", True)
                            else:
                                self.SayErrorMessage(f"Error: file could not read as a GEDCOM file", True)

                    if self.do & 2:
                        _log.info("start do 2")
                        if getattr(self.gOp, "parsed", False):
                            fname = getattr(self.gOp, "Result", None)
                            if getattr(self.gOp, "ResultType", None) is not None:
                                # call appropriate generation function if available
                                result_type_name = getattr(self.gOp, "ResultType", None).name
                                try:
                                    if getattr(self.gOp, "ResultType", None) and result_type_name == "HTML":
                                        if doHTML:
                                            doHTML(self.gOp, self.people, True)
                                        self.SayInfoMessage(f"HTML generated for {getattr(self.gOp, 'totalpeople', '?')} people ({fname})")
                                    elif getattr(self.gOp, "ResultType", None) and result_type_name == "KML":
                                        if doKML:
                                            doKML(self.gOp, self.people)
                                        self.SayInfoMessage(f"KML file generated for {getattr(self.gOp, 'totalpeople', '?')} people/points ({fname})")
                                    elif getattr(self.gOp, "ResultType", None) and result_type_name == "KML2":
                                        if doKML2:
                                            doKML2(self.gOp, self.people)
                                        self.SayInfoMessage(f"KML2 file generated for {getattr(self.gOp, 'totalpeople', '?')} people/points ({fname})")
                                    elif getattr(self.gOp, "ResultType", None) and result_type_name == "SUM":
                                        if doSUM:
                                            doSUM(self.gOp)
                                        self.SayInfoMessage(f"Summary files generated ({fname})")
                                    else:
                                        self.SayErrorMessage(f"Error: Unknown Result Type {result_type_name}", True)
                                except Exception:
                                    _log.exception("Error while generating output")
                        else:
                            _log.info("not parsed")

                    _log.debug("=======================GOING TO IDLE %d", self.threadnum)
                    # reset work flags
                    self.do = 0
                    self.readyToDo = True
                    try:
                        self.gOp.stop()
                    except Exception:
                        _log.exception("BackgroundActions: gOp.stop() failed")
                    if UpdateBackgroundEvent:
                        wx.PostEvent(self.win, UpdateBackgroundEvent(state='done'))
                except Exception:
                    _log.exception("BackgroundActions.Run main loop failed")
            else:
                time.sleep(0.3)
        self.threadrunning = False
        _log.info("BackgroundActions thread %d exiting", self.threadnum)