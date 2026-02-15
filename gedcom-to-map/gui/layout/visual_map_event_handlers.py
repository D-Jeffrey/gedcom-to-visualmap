from render.result_type import ResultType

"""
visual_map_event_handlers.py

Delegate class that owns the event handling logic extracted from VisualMapPanel.

Each handler method takes the wx.Event and operates on the supplied panel
via self.panel (a VisualMapPanel instance). Keeping handlers in a separate
class improves testability and separates UI layout from behaviour.
"""
import os
from typing import Any, Optional
import logging
import time
import wx


_log = logging.getLogger(__name__.lower())


class VisualMapEventHandler:
    """Lightweight, readable event-handler delegate for VisualMapPanel.

    This version centralises common patterns (attr lookup, action dispatch)
    so individual event handlers are short and easier to maintain.
    """

    def __init__(self, panel: Any) -> None:
        self.panel = panel
        # map radio-index -> ResultType for the results-type radiobox
        self._results_type_map = (
            ResultType.HTML,
            ResultType.KML,
            ResultType.KML2,
            ResultType.SUM,
        )

    def bind(self) -> None:
        """Bind events for all known IDs using the id metadata on the panel."""
        p = self.panel
        for wid in p.id.IDs.values():
            attrs = p.id.get_id_attributes(wid) or {}
            wtype = attrs.get("type", "").lower()
            if wtype == "button":
                p.Bind(wx.EVT_BUTTON, self.EvtButton, id=wid)
            elif wtype == "checkbox":
                p.Bind(wx.EVT_CHECKBOX, self.EvtCheckBox, id=wid)
            elif wtype == "radiobutton":
                p.Bind(wx.EVT_RADIOBOX, self.EvtRadioBox, id=wid)
            elif wtype == "text":
                p.Bind(wx.EVT_TEXT, self.EvtText, id=wid)
            elif wtype == "slider":
                p.Bind(wx.EVT_SLIDER, self.EvtSlider, id=wid)
            elif wtype == "spinctrl":
                p.Bind(wx.EVT_SPINCTRL, self.EvtSpinCtrl, id=wid)
            elif wtype == "list":
                p.Bind(wx.EVT_CHOICE, self.EvtListBox, id=wid)
            else:
                _log.debug("No binding for widget id %s (type=%r)", wid, wtype)

        # panel-level close remains panel's responsibility
        top = p.GetTopLevelParent()
        if top:
            top.Bind(wx.EVT_CLOSE, p.OnCloseWindow)

        # restore initial UI state after binding
        try:
            p.OnBusyStop(-1)
            p.NeedReload()
            p.NeedRedraw()
        except Exception:
            _log.exception("Initial UI state calls failed")

    # ---- helpers --------------------------------------------------------
    def _id_attrs(self, event_id: int) -> Optional[Any]:
        try:
            return self.panel.id.IDtoAttr.get(event_id)
        except Exception:
            _log.exception("_id_attrs lookup failed for %s", event_id)
            return None

    def _do_action_for_attr(self, action: str) -> None:
        """Dispatch simple button-like actions to panel methods."""
        mapping = {
            "Load": "LoadGEDCOM",
            "CreateFiles": "DrawGEDCOM",
            "OpenCSV": "OpenCSV",
            "Trace": "SaveTrace",
            "OpenBrowser": "OpenBrowser",
            "OpenConfig": "OpenConfig",
            # 'Stop' handled inline because it manipulates state service
        }
        fn_name = mapping.get(action)
        if fn_name:
            fn = getattr(self.panel.actions, fn_name, None)
            if callable(fn):
                try:
                    fn()
                except Exception:
                    _log.exception("Action %s failed", fn_name)
            else:
                _log.error("Panel missing handler %s for action %s", fn_name, action)
        else:
            _log.debug("No mapped panel action for %s", action)

    # ---- event handlers -----------------------------------------------
    def EvtRadioBox(self, event: wx.CommandEvent) -> None:
        """Handle radiobox changes (ResultType, GroupBy, KML mode)."""
        try:
            event_id = event.GetId()
            # Results-type radiobox: map index -> ResultType
            if event_id == self.panel.id.IDs.get("RBResultType"):
                idx = max(0, min(len(self._results_type_map) - 1, event.GetInt()))
                outType = self._results_type_map[idx]
                # Update ResultType and recompute ResultFile via services
                try:
                    enforced = ResultType.ResultTypeEnforce(outType)
                    ext = ResultType.file_extension(enforced)
                    if hasattr(self.panel.svc_config, "set"):
                        self.panel.svc_config.set("ResultType", enforced)
                        current_result = self.panel.svc_config.get("ResultFile", "")
                        base, _ = os.path.splitext(current_result or "")
                        new_result = (base or "output") + "." + ext
                        self.panel.svc_config.set("ResultFile", new_result)
                        # mirror to text field
                        try:
                            self.panel.id.TEXTResultFile.SetValue(new_result)
                        except Exception:
                            pass
                except Exception:
                    _log.exception("Failed to set ResultType/ResultFile via services")
                self.panel.SetupButtonState()
                return

            # GroupBy and KML mode are simple integer selections
            if event_id == self.panel.id.IDs.get("RBGroupBy"):
                try:
                    self.panel.svc_config.set("GroupBy", event.GetSelection())
                except Exception:
                    _log.exception("Failed to set GroupBy")
                return

            if event_id == self.panel.id.IDs.get("RBKMLMode"):
                try:
                    self.panel.svc_config.set("KMLsort", event.GetSelection())
                except Exception:
                    _log.exception("Failed to set KMLsort")
                return

            _log.debug("Unhandled radio id %s", event_id)
        except Exception:
            _log.exception("EvtRadioBox failed")

    def EvtText(self, event: wx.CommandEvent) -> None:
        """Handle text changes for configured text controls."""
        try:
            tx = event.GetEventObject()
            event_id = event.GetId()
            attributes = self.panel.id.get_id_attributes(event_id)
            attrname = attributes.get("config_attribute", None)
            if event_id == self.panel.id.IDs.get("TEXTResultFile"):
                # special case: results text needs to update svc_config ResultFile and ResultType
                self.panel.svc_config.set(attrname, event.GetString())
                self.panel.svc_config.set(attrname, event.GetString())
            else:
                pass  # no other text controls currently handled
            self.panel.SetupButtonState()
        except Exception:
            _log.exception("EvtText failed")

    def EvtCheckBox(self, event: wx.CommandEvent) -> None:
        """Handle checkbox toggles and forward changes to services / trigger updates."""
        try:
            cb = event.GetEventObject()
            event_id = event.GetId()
            attributes = self.panel.id.get_id_attributes(event_id)
            attrname = attributes.get("config_attribute", None)
            action = attributes.get("action", None)
            if not attrname:
                _log.error("Uncontrolled checkbox id %s", event_id)
            else:
                # compute attribute name (handle legacy 'CBSummary' extra name)
                # attrname = mapping[0] if isinstance(mapping, tuple) else None
                # extra = cb.Name if event_id == self.panel.id.IDs.get("CBSummary") else ""
                # attrname = attrname + (extra or "")
                value = cb.GetValue()
                self.panel.svc_config.set(attrname, value)
                _log.debug("Checkbox %s -> %s", attrname, value)

                # action dispatch
                if event_id in (
                    self.panel.id.IDs.get("CBHeatMap"),
                    self.panel.id.IDs.get("CBMapTimeLine"),
                    self.panel.id.IDs.get("CBMarksOn"),
                ):
                    self.panel.SetupButtonState()
                if action == "Redraw":
                    self.panel.NeedRedraw()
                elif action == "Reload":
                    self.panel.NeedReload()
                elif action == "Render":
                    if getattr(self.panel, "background_process", None):
                        self.panel.background_process.updategrid = True
                elif action:
                    _log.debug("Checkbox action '%s' not explicitly handled", action)

                # special-case large-tree warning for AllEntities
                if event_id == self.panel.id.IDs.get("CBAllEntities") and value:
                    people = getattr(self.panel.background_process, "people", None)
                    if people and len(people) > 200:
                        people_count = len(people)
                        if people_count > 10000:
                            warning_msg = (
                                f"CRITICAL WARNING: {people_count:,} people in your tree!\n\n"
                                "Enabling 'Map all people' will:\n"
                                "• Take HOURS to generate KML files\n"
                                "• Use gigabytes of memory\n"
                                "• May cause the application to crash\n\n"
                                "For large datasets, disable this option and only map ancestors.\n\n"
                                "Do you really want to enable this?"
                            )
                            dlg = wx.MessageDialog(
                                self.panel,
                                warning_msg,
                                "Large Dataset Warning",
                                wx.YES_NO | wx.NO_DEFAULT | wx.ICON_ERROR,
                            )
                            try:
                                if dlg.ShowModal() == wx.ID_NO:
                                    # User clicked No, uncheck the box
                                    checkbox = wx.FindWindowById(event_id)
                                    if checkbox:
                                        checkbox.SetValue(False)
                                        self.panel.svc_config.set("AllEntities", False)
                            finally:
                                dlg.Destroy()
                        else:
                            dlg = wx.MessageDialog(
                                self.panel,
                                f"Caution: {people_count:,} people in your tree.\n"
                                "This may create very large files and take several minutes.",
                                "Warning",
                                wx.OK | wx.ICON_WARNING,
                            )
                            try:
                                dlg.ShowModal()
                            finally:
                                dlg.Destroy()
        except Exception:
            _log.exception("EvtCheckBox failed")

    def EvtButton(self, event: wx.CommandEvent) -> None:
        """Handle button clicks and dispatch panel actions."""
        try:
            event_id = event.GetId()
            attributes = self.panel.id.get_id_attributes(event_id)
            action = attributes.get("action", None)
            if action == "Stop":
                self.panel.svc_state.stopping = True
                self.panel.svc_state.parsed = False
                self.panel.NeedRedraw()
                self.panel.NeedReload()
                return

            if action:
                self._do_action_for_attr(action)
                return

            _log.error("uncontrolled BUTTON id: %s action=%r", event_id, action)
        except Exception:
            _log.exception("EvtButton failed")

    def EvtListBox(self, event: wx.CommandEvent) -> None:
        """Handle choice/listbox selection changes (map style etc)."""
        try:
            event_id = event.GetId()
            attributes = self.panel.id.get_id_attributes(event_id)
            attrname = attributes.get("config_attribute", None)
            if attributes and attrname == "MapStyle":
                # MapStyle stored as set/list of types; UI stores selection index
                try:
                    self.panel.svc_config.set("MapStyle", sorted(self.panel.svc_config.map_types)[event.GetSelection()])
                    self.panel.NeedRedraw()
                    return
                except Exception:
                    _log.exception("EvtListBox MapStyle handling failed")
            _log.error("Uncontrolled LISTbox %s", event_id)
        except Exception:
            _log.exception("EvtListBox failed")

    def EvtSpinCtrl(self, event: wx.CommandEvent) -> None:
        """Handle spin control changes (MaxLineWeight etc)."""
        try:
            event_id = event.GetId()
            attributes = self.panel.id.get_id_attributes(event_id)
            attrname = attributes.get("config_attribute", None)
            if attributes and attrname == "MaxLineWeight":
                self.panel.svc_config.set("MaxLineWeight", event.GetSelection())
                self.panel.NeedRedraw()
                return
            _log.error("Uncontrolled SPIN %s", event_id)
        except Exception:
            _log.exception("EvtSpinCtrl failed")

    def EvtSlider(self, event: wx.CommandEvent) -> None:
        """Handle slider changes (heatmap timestep)."""
        try:
            self.panel.svc_config.set("HeatMapTimeStep", event.GetSelection())
        except Exception:
            _log.exception("EvtSlider failed")

    def OnCreateFiles(self, evt: Any) -> None:
        """Apply updates coming from the background worker to the UI."""
        try:
            panel = self.panel
            # process event state hand off (busy/done)
            if hasattr(evt, "state"):
                if evt.state == "busy":
                    panel.OnBusyStart(evt)
                elif evt.state == "done":
                    panel.OnBusyStop(evt)
                    panel.UpdateTimer()

            # grid/list update
            if getattr(panel.background_process, "updategrid", False):
                panel.background_process.updategrid = False
                saveBusy = panel.busystate
                panel.OnBusyStart(evt)
                try:
                    panel.peopleList.list.PopulateList(
                        panel.background_process.people, panel.svc_config.get("Main"), True
                    )
                except Exception:
                    _log.exception("PopulateList failed")

                if panel.svc_state.newload:
                    # Refresh processing options before ShowSelectedLinage (which sets newload=False)
                    try:
                        panel.refresh_processing_options()
                    except Exception:
                        _log.exception("refresh_processing_options failed")
                    try:
                        panel.peopleList.list.ShowSelectedLinage(panel.svc_config.get("Main"))
                    except Exception:
                        _log.exception("ShowSelectedLinage failed")
                if not saveBusy:
                    panel.OnBusyStop(evt)

            # infobox and error aggregation
            newinfo = None
            if getattr(panel.background_process, "updateinfo", None):
                newinfo = panel.background_process.updateinfo
                panel.background_process.updateinfo = None
            if getattr(panel.background_process, "errorinfo", None):
                einfo = f"<span foreground='red'><b>{panel.background_process.errorinfo}</b></span>"
                newinfo = (newinfo + "\n" + einfo) if newinfo else einfo
                panel.background_process.errorinfo = None
            if newinfo:
                panel.peopleList.append_info_box(newinfo)
        except Exception:
            _log.exception("OnCreateFiles failed")
