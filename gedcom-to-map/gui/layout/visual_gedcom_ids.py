"""
VisualGedcomIds moved out of gedcomVisualGUI.py
"""

import logging
import os
import wx
from wx.lib.embeddedimage import PyEmbeddedImage
from typing import Any, Optional

_log = logging.getLogger(__name__.lower())


class VisualGedcomIds:
    """
    Small helper that centralises control IDs used by the UI.

    Adjust or extend attributes below to match the names used across the project.
    Using wx.NewIdRef() when available yields unique IDs compatible with modern wx.
    """

    def __init__(self, svc_config=None) -> None:
        """Initialize VisualGedcomIds.

        Args:
            svc_config: Config service instance (optional, kept for compatibility).
        """
        self.svc_config = svc_config
        new_id = getattr(wx, "NewIdRef", None)
        if callable(new_id):
            make = lambda: new_id()
        else:
            make = lambda: wx.NewId()

        id_attributes = [  # ID name: (type, config/state attribute, action)
            ("CBMarksOn", ("CheckBox", "MarksOn", "Redraw")),
            ("CBHeatMap", ("CheckBox", "HeatMap", "")),
            ("CBShowAllPeople", ("CheckBox", "ShowAllPeople", "Redraw")),
            ("CBFlyTo", ("CheckBox", "UseBalloonFlyto", "Redraw")),
            ("CBBornMark", ("CheckBox", "BornMark", "Redraw")),
            ("CBDieMark", ("CheckBox", "DieMark", "Redraw")),
            ("LISTMapStyle", ("List", "MapStyle", "Redraw")),
            ("CBMarkStarOn", ("CheckBox", "MarkStarOn", "Redraw")),
            ("RBGroupBy", ("RadioButton", "GroupBy", "Redraw")),
            ("CBUseAntPath", ("CheckBox", "UseAntPath", "Redraw")),
            ("CBMapTimeLine", ("CheckBox", "MapTimeLine", "Redraw")),
            ("CBHomeMarker", ("CheckBox", "HomeMarker", "Redraw")),
            ("LISTHeatMapTimeStep", ("Slider", "HeatMapTimeStep", "Redraw")),
            ("txtinfile", ("Button", None, "OpenGEDCOM")),
            ("TEXTGEDCOMinput", ("Text", "GEDCOMinput", "Reload")),
            ("txtoutfile", ("Button", None, "OpenOutput")),
            ("TEXTResultFile", ("Text", "ResultFile", "Redraw")),
            ("RBResultType", ("RadioButton", "ResultType", "Redraw")),
            ("TEXTMain", ("Text", "Main", "Reload")),
            ("TEXTName", ("Text", "Name", "")),
            ("RBKMLMode", ("RadioButton", "KMLMode", "Redraw")),
            ("INTMaxLineWeight", ("SpinCtrl", "MaxLineWeight", "Reload")),
            ("CBAllEntities", ("CheckBox", "AllEntities", "Redraw")),
            ("CBMapControl", ("CheckBox", "showLayerControl", "Redraw")),
            ("CBMapMini", ("CheckBox", "mapMini", "Redraw")),
            ("CBEnableTracemalloc", ("CheckBox", "EnableTracemalloc", "")),
            ("BTNLoad", ("Button", None, "Load")),
            ("BTNCreateFiles", ("Button", None, "CreateFiles")),
            ("BTNCSV", ("Button", None, "OpenCSV")),
            ("BTNTRACE", ("Button", None, "Trace")),
            ("BTNSTOP", ("Button", None, "Stop")),
            ("BTNBROWSER", ("Button", None, "OpenBrowser")),
            ("BTNConfig", ("Button", None, "OpenConfig")),
            ("CBGridView", ("CheckBox", "GridView", "Render")),
            ("CBSummary", ("CheckBox", "Summary", "Redraw")),
        ]
        # Build id lookup and id->attribute mapping in a single pass
        self.IDs = {}
        self.IDtoAttr = {}
        for name, mapping in id_attributes:
            idref = wx.NewIdRef()
            self.IDs[name] = idref
            if mapping is not None:
                self.IDtoAttr[idref] = mapping

        summary_row_attribute_mapping = {
            0: "SummaryOpen",
            1: "SummaryPlaces",
            2: "SummaryPeople",
            3: "SummaryCountries",
            4: "SummaryCountriesGrid",
            5: "SummaryGeocode",
            6: "SummaryAltPlaces",
            7: "SummaryEnrichmentIssues",
            8: "SummaryStatistics",
        }
        for row, attr in summary_row_attribute_mapping.items():
            idref = wx.NewIdRef()
            name = f"CBSummary{row}"
            self.IDs[name] = idref
            self.IDtoAttr[idref] = ("CheckBox", attr, "Redraw")

        self.SmallUpArrow = PyEmbeddedImage(
            b"iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABHNCSVQICAgIfAhkiAAAADxJ"
            b"REFUOI1jZGRiZqAEMFGke2gY8P/f3/9kGwDTjM8QnAaga8JlCG3CAJdt2MQxDCAUaOjyjKMp"
            b"cRAYAABS2CPsss3BWQAAAABJRU5ErkJggg=="
        )
        self.SmallDnArrow = PyEmbeddedImage(
            b"iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABHNCSVQICAgIfAhkiAAAAEhJ"
            b"REFUOI1jZGRiZqAEMFGke9QABgYGBgYWdIH///7+J6SJkYmZEacLkCUJacZqAD5DsInTLhDR"
            b"bcPlKrwugGnCFy6Mo3mBAQChDgRlP4RC7wAAAABJRU5ErkJggg=="
        )

        self.m = {1: ()}

    def iter_controls(self):
        """
        Yield metadata for controls defined by this helper.

        Yields tuples: (control_name, idref, widget_type, config_attribute, action)
        This keeps VisualGedcomIds purely a metadata provider. Actual UI
        updates should be performed by the panel (apply_controls_from_options).
        """
        for name, idref in getattr(self, "IDs", {}).items():
            mapping = self.IDtoAttr.get(idref)
            if not mapping:
                continue
            wtype = mapping[0] if len(mapping) > 0 else None
            config_attr = mapping[1] if len(mapping) > 1 else None
            action = mapping[2] if len(mapping) > 2 else None
            yield name, idref, wtype, config_attr, action

    def get_id_attributes(self, idref: Any) -> dict:
        """Get the (type, config/state attribute, action) tuple for a given control ID."""
        attr: dict = {}
        try:
            attr = self.IDtoAttr[idref]
        except Exception:
            _log.error(f"ID {idref} not found in IDtoAttr mapping.")
        return {"type": attr[0], "config_attribute": attr[1], "action": attr[2]}
