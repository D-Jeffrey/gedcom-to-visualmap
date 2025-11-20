"""
visual_map_event_handlers.py

Delegate class that owns the event handling logic extracted from VisualMapPanel.

Each handler method takes the wx.Event and operates on the supplied panel
via self.panel (a VisualMapPanel instance). Keeping handlers in a separate
class improves testability and separates UI layout from behaviour.
"""
from typing import Any, Optional
import logging
import time
import wx

from gedcom_options import ResultsType  # type: ignore

_log = logging.getLogger(__name__.lower())


class VisualMapEventHandler:
    """Event handler delegate for VisualMapPanel. Holds a reference to the panel."""

    def __init__(self, panel: Any) -> None:
        self.panel = panel

    def bind(self) -> None:
        """Wire up wx event bindings that delegate to handler methods or panel handlers."""
        p = self.panel
        # Radio / checkbox / choice / spin / slider / text / button bindings
        p.Bind(wx.EVT_RADIOBOX, self.EvtRadioBox, id=p.id.IDs["ID_RBResultsType"])
        p.Bind(wx.EVT_CHECKBOX, self.EvtCheckBox, id=p.id.IDs["ID_CBMapControl"])
        p.Bind(wx.EVT_CHECKBOX, self.EvtCheckBox, id=p.id.IDs["ID_CBMapMini"])
        p.Bind(wx.EVT_CHECKBOX, self.EvtCheckBox, id=p.id.IDs["ID_CBMarksOn"])
        p.Bind(wx.EVT_CHECKBOX, self.EvtCheckBox, id=p.id.IDs["ID_CBBornMark"])
        p.Bind(wx.EVT_CHECKBOX, self.EvtCheckBox, id=p.id.IDs["ID_CBDieMark"])
        p.Bind(wx.EVT_CHECKBOX, self.EvtCheckBox, id=p.id.IDs["ID_CBHomeMarker"])
        p.Bind(wx.EVT_CHECKBOX, self.EvtCheckBox, id=p.id.IDs["ID_CBMarkStarOn"])
        p.Bind(wx.EVT_CHECKBOX, self.EvtCheckBox, id=p.id.IDs["ID_CBHeatMap"])
        p.Bind(wx.EVT_CHECKBOX, self.EvtCheckBox, id=p.id.IDs["ID_CBFlyTo"])
        p.Bind(wx.EVT_CHECKBOX, self.EvtCheckBox, id=p.id.IDs["ID_CBMapTimeLine"])
        p.Bind(wx.EVT_CHECKBOX, self.EvtCheckBox, id=p.id.IDs["ID_CBUseAntPath"])
        p.Bind(wx.EVT_CHECKBOX, self.EvtCheckBox, id=p.id.IDs["ID_CBUseGPS"])
        p.Bind(wx.EVT_CHECKBOX, self.EvtCheckBox, id=p.id.IDs["ID_CBCacheOnly"])
        p.Bind(wx.EVT_CHECKBOX, self.EvtCheckBox, id=p.id.IDs["ID_CBAllEntities"])
        p.Bind(wx.EVT_CHECKBOX, self.EvtCheckBox, id=p.id.IDs["ID_CBGridView"])
        p.Bind(wx.EVT_CHECKBOX, self.EvtCheckBox, id=p.id.IDs["ID_CBSummary"])
        p.Bind(wx.EVT_RADIOBOX, self.EvtRadioBox, id=p.id.IDs["ID_RBKMLMode"])
        p.Bind(wx.EVT_SPINCTRL, self.EvtSpinCtrl, id=p.id.IDs["ID_INTMaxLineWeight"])
        p.Bind(wx.EVT_CHOICE, self.EvtListBox, id=p.id.IDs["ID_LISTMapStyle"])
        p.Bind(wx.EVT_BUTTON, self.EvtButton, id=p.id.IDs["ID_BTNLoad"])
        p.Bind(wx.EVT_BUTTON, self.EvtButton, id=p.id.IDs["ID_BTNCreateFiles"])
        p.Bind(wx.EVT_BUTTON, self.EvtButton, id=p.id.IDs["ID_BTNCSV"])
        p.Bind(wx.EVT_BUTTON, self.EvtButton, id=p.id.IDs["ID_BTNTRACE"])
        p.Bind(wx.EVT_BUTTON, self.EvtButton, id=p.id.IDs["ID_BTNSTOP"])
        p.Bind(wx.EVT_BUTTON, self.EvtButton, id=p.id.IDs["ID_BTNBROWSER"])
        p.Bind(wx.EVT_TEXT, self.EvtText, id=p.id.IDs["ID_TEXTResult"])
        p.Bind(wx.EVT_TEXT, self.EvtText, id=p.id.IDs["ID_TEXTDefaultCountry"])
        # GroupBy and slider
        p.Bind(wx.EVT_RADIOBOX, self.EvtRadioBox, id=p.id.IDs["ID_RBGroupBy"])
        p.Bind(wx.EVT_SLIDER, self.EvtSlider, id=p.id.IDs["ID_LISTHeatMapTimeStep"])
        # Keep panel-level close handling (panel implements safe destroy)
        p.Bind(wx.EVT_CLOSE, p.OnCloseWindow)
        # initial UI state calls previously in panel.bind_events:
        p.OnBusyStop(-1)
        p.NeedReload()
        p.NeedRedraw()

    def EvtRadioBox(self, event: wx.CommandEvent) -> None:
        """Handle RadioBox changes (ResultType / GroupBy / KML mode)."""
        try:
            if event.GetId() == self.panel.id.IDs["ID_RBResultsType"]:
                if event.GetInt() == 0:
                    outType = ResultsType.HTML
                elif event.GetInt() == 1:
                    outType = ResultsType.KML
                elif event.GetInt() == 2:
                    outType = ResultsType.KML2
                elif event.GetInt() == 3:
                    outType = ResultsType.SUM
                else:
                    outType = ResultsType.HTML
                self.panel.gOp.setResults(self.panel.gOp.get("Result"), outType)
                self.panel.id.TEXTResult.SetValue(self.panel.gOp.get("Result"))
                self.panel.SetupButtonState()
                return

            if event.GetId() == self.panel.id.IDs["ID_RBGroupBy"]:
                self.panel.gOp.GroupBy = event.GetSelection()
                return

            if event.GetId() == self.panel.id.IDs["ID_RBKMLMode"]:
                self.panel.gOp.KMLsort = event.GetSelection()
                return

            _log.error("Unhandled radio id %s", event.GetId())
        except Exception:
            _log.exception("EvtRadioBox failed")

    def EvtText(self, event: wx.CommandEvent) -> None:
        """Handle text changes for configured text controls."""
        try:
            cbid = event.GetId()
            if cbid in (self.panel.id.IDs["ID_TEXTResult"], self.panel.id.IDs["ID_TEXTDefaultCountry"]):
                attr = self.panel.id.IDtoAttr[cbid][2]
                self.panel.gOp.set(attr, event.GetString())
                _log.debug("TXT %s set value %s", self.panel.id.IDtoAttr[cbid][0], attr)
            else:
                _log.error("uncontrolled TEXT %s", cbid)
            self.panel.SetupButtonState()
        except Exception:
            _log.exception("EvtText failed")

    def EvtCheckBox(self, event: wx.CommandEvent) -> None:
        """Handle checkbox toggles and forward changes to gOp / trigger UI updates."""
        try:
            cb = event.GetEventObject()
            cbid = event.GetId()
            _log.debug("checkbox %s for %i", cb.GetValue(), cbid)
            if cb.Is3State():
                _log.debug("3StateValue: %s", cb.Get3StateValue())

            if cbid == self.panel.id.IDs["ID_CBSummary"]:
                extra = cb.Name
            else:
                extra = ""

            attrname = self.panel.id.IDtoAttr[cbid][0] + extra
            self.panel.gOp.set(attrname, cb.GetValue())
            _log.debug("set %s to %s (%s)", self.panel.id.IDtoAttr[cbid][0], cb.GetValue(), self.panel.id.IDtoAttr[cbid][1])

            # Actions depending on attribute semantics
            action = self.panel.id.IDtoAttr[cbid][1]
            if cbid in (
                self.panel.id.IDs["ID_CBHeatMap"],
                self.panel.id.IDs["ID_CBMapTimeLine"],
                self.panel.id.IDs["ID_CBMarksOn"],
            ):
                self.panel.SetupButtonState()
            if action == "Redraw":
                self.panel.NeedRedraw()
            elif action == "Reload":
                self.panel.NeedReload()
            elif action == "Render":
                self.panel.background_process.updategrid = True
            elif action == "":
                pass
            else:
                _log.error("uncontrolled CB %d with '%s'", cbid, action)

            # Special-case AllEntities: warn about large trees
            if cbid == self.panel.id.IDs["ID_CBAllEntities"] and cb.GetValue():
                dlg = None
                if self.panel.background_process and getattr(self.panel.background_process, "people", None):
                    if len(self.panel.background_process.people) > 200:
                        dlg = wx.MessageDialog(
                            self.panel,
                            f"Caution, {len(self.panel.background_process.people)} people in your tree\n it may create very large HTML files and may not open in the browser",
                            "Warning",
                            wx.OK | wx.ICON_WARNING,
                        )
                else:
                    dlg = wx.MessageDialog(
                        self.panel,
                        "Caution, if you load a GEDCOM with lots of people in your tree\n it may create very large HTML files and may not open in the browser",
                        "Warning",
                        wx.OK | wx.ICON_WARNING,
                    )
                if dlg:
                    dlg.ShowModal()
                    dlg.Destroy()
        except Exception:
            _log.exception("EvtCheckBox failed")

    def EvtButton(self, event: wx.CommandEvent) -> None:
        """Handle button clicks and dispatch panel actions."""
        try:
            myid = event.GetId()
            _log.debug("Click! (%d)", myid)
            if myid == self.panel.id.IDs["ID_BTNLoad"]:
                self.panel.LoadGEDCOM()
            elif myid == self.panel.id.IDs["ID_BTNCreateFiles"]:
                self.panel.DrawGEDCOM()
            elif myid == self.panel.id.IDs["ID_BTNCSV"]:
                self.panel.OpenCSV()
            elif myid == self.panel.id.IDs["ID_BTNTRACE"]:
                self.panel.SaveTrace()
            elif myid == self.panel.id.IDs["ID_BTNSTOP"]:
                self.panel.gOp.set("stopping", True)
                self.panel.gOp.set("parsed", False)
                self.panel.NeedRedraw()
                self.panel.NeedReload()
            elif myid == self.panel.id.IDs["ID_BTNBROWSER"]:
                self.panel.OpenBrowser()
            else:
                _log.error("uncontrolled ID : %d", myid)
        except Exception:
            _log.exception("EvtButton failed")

    def EvtListBox(self, event: wx.CommandEvent) -> None:
        """Handle choice/listbox selection changes."""
        try:
            eventid = event.GetId()
            _log.debug("%s, %s, %s", event.GetString(), event.IsSelection(), event.GetSelection())
            if eventid == self.panel.id.IDs["ID_LISTMapStyle"]:
                self.panel.gOp.MapStyle = sorted(self.panel.id.AllMapTypes)[event.GetSelection()]
                self.panel.NeedRedraw()
            else:
                _log.error("Uncontrolled LISTbox %s", eventid)
        except Exception:
            _log.exception("EvtListBox failed")

    def EvtSpinCtrl(self, event: wx.CommandEvent) -> None:
        """Handle spin control changes."""
        try:
            eventid = event.GetId()
            if eventid == self.panel.id.IDs["ID_INTMaxLineWeight"]:
                self.panel.gOp.MaxLineWeight = event.GetSelection()
                self.panel.NeedRedraw()
            else:
                _log.error("Uncontrol SPINbox %s", eventid)
        except Exception:
            _log.exception("EvtSpinCtrl failed")

    def EvtSlider(self, event: wx.CommandEvent) -> None:
        """Handle slider changes (heatmap timestep)."""
        try:
            self.panel.gOp.HeatMapTimeStep = event.GetSelection()
        except Exception:
            _log.exception("EvtSlider failed")

    def OnCreateFiles(self, evt: Any) -> None:
        """Handle background updates: grid refresh, infobox messages, errors."""
        try:
            panel = self.panel
            # process evt state hand off
            if hasattr(evt, "state"):
                if evt.state == "busy":
                    panel.OnBusyStart(evt)
                if evt.state == "done":
                    panel.OnBusyStop(evt)
                    panel.UpdateTimer()
            if panel.background_process.updategrid:
                panel.background_process.updategrid = False
                saveBusy = panel.busystate
                panel.OnBusyStart(evt)
                panel.peopleList.list.PopulateList(panel.background_process.people, panel.gOp.get("Main"), True)
                if panel.gOp.newload:
                    panel.peopleList.list.ShowSelectedLinage(panel.gOp.get("Main"))
                if not saveBusy:
                    panel.OnBusyStop(evt)
            newinfo = None
            if panel.background_process.updateinfo:
                _log.debug("Infobox: %s", panel.background_process.updateinfo)
                newinfo = panel.background_process.updateinfo
                panel.background_process.updateinfo = None
            if panel.background_process.errorinfo:
                _log.debug("Infobox-Err: %s", panel.background_process.errorinfo)
                einfo = f"<span foreground='red'><b>{panel.background_process.errorinfo}</b></span>"
                newinfo = newinfo + "\n" + einfo if newinfo else einfo
                panel.background_process.errorinfo = None
            if newinfo:
                panel.peopleList.append_info_box(newinfo)
        except Exception:
            _log.exception("OnCreateFiles failed")