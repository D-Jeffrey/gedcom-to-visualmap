"""
VisualGedcomIds moved out of gedcomVisualGUI.py
"""
import logging
import os
import wx
from wx.lib.embeddedimage import PyEmbeddedImage
from typing import Any

from gedcom_options import gvOptions  # type: ignore

_log = logging.getLogger(__name__.lower())


class VisualGedcomIds:
    """
    Small helper that centralises control IDs used by the UI.

    Adjust or extend attributes below to match the names used across the project.
    Using wx.NewIdRef() when available yields unique IDs compatible with modern wx.
    """
    def __init__(self) -> None:
        new_id = getattr(wx, "NewIdRef", None)
        if callable(new_id):
            make = lambda: new_id()
        else:
            make = lambda: wx.NewId()

        id_attributes = [ # ID name: (type, gOp attribute, action)
            ('CBMarksOn', ('CheckBox', 'MarksOn', 'Redraw')),
            ('CBHeatMap', ('CheckBox', 'HeatMap', '')),
            ('CBFlyTo', ('CheckBox', 'UseBalloonFlyto', 'Redraw')),
            ('CBBornMark', ('CheckBox', 'BornMark', 'Redraw')),
            ('CBDieMark', ('CheckBox', 'DieMark', 'Redraw')),

            ('LISTMapStyle', ('List', 'MapStyle', 'Redraw')),

            ('CBMarkStarOn', ('CheckBox', 'MarkStarOn', 'Redraw')),

            ('RBGroupBy', ('RadioButton', 'GroupBy', 'Redraw')),

            ('CBUseAntPath', ('CheckBox', 'UseAntPath', 'Redraw')),
            ('CBMapTimeLine', ('CheckBox', 'MapTimeLine', 'Redraw')),
            ('CBHomeMarker', ('CheckBox', 'HomeMarker', 'Redraw')),

            ('LISTHeatMapTimeStep', ('Slider', 'HeatMapTimeStep', 'Redraw')),

            ('TEXTGEDCOMinput', ('Text', 'GEDCOMinput', 'Reload')),
            ('TEXTResult', ('Text', 'Result', 'Redraw')),

            ('RBResultsType', ('RadioButton', 'ResultType', 'Redraw')),

            ('TEXTMain', ('Text', 'Main', 'Reload')),
            ('TEXTName', ('Text', 'Name', '')),

            ('RBKMLMode', ('RadioButton', 'KMLMode', 'Redraw')),

            ('INTMaxMissing', ('Int', 'MaxMissing', 'Reload')),
            ('INTMaxLineWeight', ('SpinCtrl', 'MaxLineWeight', 'Reload')),

            ('CBUseGPS', ('CheckBox', 'UseGPS', 'Reload')),
            ('CBCacheOnly', ('CheckBox', 'CacheOnly', 'Reload')),
            ('CBAllEntities', ('CheckBox', 'AllEntities', 'Redraw')),
            ('CBMapControl', ('CheckBox', 'showLayerControl', 'Redraw')),
            ('CBMapMini', ('CheckBox', 'mapMini', 'Redraw')),

            ('BTNLoad', ('Button', None, 'Load')),
            ('BTNCreateFiles', ('Button', None, 'CreateFiles')),
            ('BTNCSV', ('Button', None, 'OpenCSV')),
            ('BTNTRACE', ('Button', None, 'Trace')),
            ('BTNSTOP', ('Button', None, 'Stop')),
            ('BTNBROWSER', ('Button', None, 'OpenBrowser')),
            ('CBGridView', ('CheckBox', 'GridView', 'Render')),
            ('CBSummary', ('CheckBox', 'Summary', 'Redraw')),

            ('TEXTDefaultCountry', ('Text', 'defaultCountry', 'Reload', 'defaultCountry')),
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
            0: 'SummaryOpen',
            1: 'SummaryPlaces',
            2: 'SummaryPeople',
            3: 'SummaryCountries',
            4: 'SummaryCountriesGrid',
            5: 'SummaryGeocode',
            6: 'SummaryAltPlaces'
        }
        for row, attr in summary_row_attribute_mapping.items():
            idref = wx.NewIdRef()
            name = f'CBSummary{row}'
            self.IDs[name] = idref
            self.IDtoAttr[idref] = ('CheckBox', attr, 'Redraw')

        # Define color defaults as (name, default_colour_string) pairs and build
        # COLORs (name->idref) and COLORid (idref -> [colour_name, wx.Colour])
        color_pairs = [
            ('BTN_PRESS', 'TAN'),
            ('BTN_DIRECTORY', 'WHEAT'),
            ('BTN_DONE', 'WHITE'),
            ('SELECTED', 'NAVY'),
            ('SELECTED_TEXT', 'BLACK'),
            ('ANCESTOR', 'MEDIUM GOLDENROD'),
            ('MAINPERSON', 'KHAKI'),
            ('OTHERPERSON', 'WHITE'),
            ('INFO_BOX_BACKGROUND', 'GOLDENROD'),
            ('GRID_TEXT', 'BLACK'),
            ('GRID_BACK', 'WHITE'),
            ('TITLE_TEXT', 'WHITE'),
            ('TITLE_BACK', 'KHAKI'),
            ('BUSY_BACK', 'YELLOW'),
        ]

        self.colors = [name for name, _ in color_pairs]
        self.COLORs = {}
        self.COLORid = {}
        for name, default in color_pairs:
            idref = wx.NewIdRef()
            self.COLORs[name] = idref
            # store [default_name, wx.Colour_or_None]
            try:
                col = wx.TheColourDatabase.FindColour(default)
            except Exception:
                col = None
            self.COLORid[idref] = [default, col]
        
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
        self.AllMapTypes = ["CartoDB.Voyager", 
            "OpenStreetMap.Mapnik", 
            "OpenStreetMap.HOT", 
            "Esri.WorldTerrain",
            "Esri.NatGeoWorldMap",
            "OpenTopoMap",
            "Esri.WorldStreetMap",
            "CartoDB.VoyagerNoLabels",
            "CartoDB.Positron",
            "CartoDB.PositronOnlyLabels",
            "CartoDB.VoyagerOnlyLabels",
            "CartoDB.DarkMatter"
            ]

    def GetColor(self, colorID):
        if colorID in self.colors:
            return self.COLORid[self.COLORs[colorID]][1]
        _log.error(f'Color not defined : {colorID}')
        raise ValueError(f'Color not defined : {colorID} Color to Attributer table error')
    
    def iter_controls(self):
        """
        Yield metadata for controls defined by this helper.

        Yields tuples: (control_name, idref, widget_type, gop_attribute, action)
        This keeps VisualGedcomIds purely a metadata provider. Actual UI
        updates should be performed by the panel (apply_controls_from_options).
        """
        for name, idref in getattr(self, "IDs", {}).items():
            mapping = self.IDtoAttr.get(idref)
            if not mapping:
                continue
            wtype = mapping[0] if len(mapping) > 0 else None
            gop_attr = mapping[1] if len(mapping) > 1 else None
            action = mapping[2] if len(mapping) > 2 else None
            yield name, idref, wtype, gop_attr, action

    def get_id_attributes(self, idref: Any) -> dict:
        """Get the (type, gOp attribute, action) tuple for a given control ID."""
        attr: dict = {}
        try:
            attr = self.IDtoAttr[idref]
        except Exception:
            _log.error(f"ID {idref} not found in IDtoAttr mapping.")
        return {'type': attr[0], 'gOp_attribute': attr[1], 'action': attr[2]}