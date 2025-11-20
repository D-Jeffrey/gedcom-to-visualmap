"""
VisualGedcomIds moved out of gedcomVisualGUI.py
"""
import logging
import wx
from wx.lib.embeddedimage import PyEmbeddedImage

_log = logging.getLogger(__name__.lower())


class VisualGedcomIds():
    def __init__(self):
        
        self.ids = [
            'ID_CBMarksOn', 'ID_CBHeatMap', 'ID_CBFlyTo', 'ID_CBBornMark', 'ID_CBDieMark', 'ID_LISTMapStyle',
            'ID_CBMarkStarOn', 'ID_RBGroupBy', 'ID_CBUseAntPath', 'ID_CBMapTimeLine',
            'ID_CBHomeMarker', 'ID_LISTHeatMapTimeStep', 'ID_TEXTGEDCOMinput', 'ID_TEXTResult',
            'ID_RBResultsType', 'ID_TEXTMain', 'ID_TEXTName', 'ID_RBKMLMode', 'ID_INTMaxMissing', 'ID_INTMaxLineWeight',
            'ID_CBUseGPS', 'ID_CBCacheOnly', 'ID_CBAllEntities',  'ID_CBMapControl',
            'ID_CBMapMini', 'ID_BTNLoad', 'ID_BTNCreateFiles', 'ID_BTNCSV', 'ID_BTNTRACE', 'ID_BTNSTOP', 'ID_BTNBROWSER',
            'ID_CBGridView', 'CBYougeAge', 'ID_CBSummary', 'ID_TEXTDefaultCountry'
        ]
        self.IDs = {name: wx.NewIdRef() for name in self.ids}
        # ID = Attribute (in gOp), Action impact
        self.IDtoAttr = {
            self.IDs['ID_CBMarksOn']: ('MarksOn', 'Redraw'),
            self.IDs['ID_CBHeatMap']: ('HeatMap', ''),
            self.IDs['ID_CBBornMark']: ('BornMark', 'Redraw'),
            self.IDs['ID_CBDieMark']: ('DieMark', 'Redraw'),
            self.IDs['ID_LISTMapStyle']: ('MapStyle', 'Redraw'),
            self.IDs['ID_CBMarkStarOn']: ('MarkStarOn', 'Redraw'),
            self.IDs['ID_RBGroupBy']: ('GroupBy', 'Redraw'),
            self.IDs['ID_CBUseAntPath']: ('UseAntPath', 'Redraw'),
            self.IDs['ID_CBMapTimeLine']: ('MapTimeLine', 'Redraw'),
            self.IDs['ID_CBHomeMarker']: ('HomeMarker', 'Redraw'),
            self.IDs['ID_CBFlyTo']: ('UseBalloonFlyto', 'Redraw'),
            self.IDs['ID_LISTHeatMapTimeStep']: ('MapTimeLine', 'Redraw'),
            self.IDs['ID_TEXTGEDCOMinput']: ('GEDCOMinput', 'Reload'),
            self.IDs['ID_TEXTResult']: ('Result', 'Redraw', 'Result'),
            self.IDs['ID_RBResultsType']: ('ResultType', 'Redraw'),
            self.IDs['ID_TEXTMain']: ('Main', 'Reload'),
            self.IDs['ID_TEXTName']: ('Name', ''),
            self.IDs['ID_RBKMLMode']: ('KMLMode', 'Redraw'),
            self.IDs['ID_INTMaxMissing']: ('MaxMissing', 'Reload'),
            self.IDs['ID_INTMaxLineWeight']: ('MaxLineWeight', 'Reload'),
            self.IDs['ID_CBUseGPS']: ('UseGPS', 'Reload'),
            self.IDs['ID_CBCacheOnly']: ('CacheOnly', 'Reload'),
            self.IDs['ID_CBAllEntities']: ('AllEntities', 'Redraw'),
            self.IDs['ID_CBMapControl']: ('showLayerControl', 'Redraw'),
            self.IDs['ID_CBMapMini']: ('mapMini', 'Redraw'),
            self.IDs['ID_BTNLoad']: 'Load',
            self.IDs['ID_BTNCreateFiles']: 'CreateFiles',
            self.IDs['ID_BTNCSV']: 'OpenCSV',
            self.IDs['ID_BTNTRACE']: 'Trace',
            self.IDs['ID_BTNSTOP']: 'Stop',
            self.IDs['ID_BTNBROWSER']: 'OpenBrowser',
            self.IDs['ID_CBGridView']: ('GridView', 'Render'),
            self.IDs['ID_TEXTDefaultCountry']: ('defaultCountry', 'Reload', 'defaultCountry'),
            self.IDs['ID_CBSummary']: ('Summary','Redraw')
        }

        self.colors = [
            'BTN_PRESS', 'BTN_DIRECTORY', 'BTN_DONE', 'SELECTED', 'ANCESTOR', 'MAINPERSON', 'INFO_BOX_BACKGROUND', 'OTHERPERSON', 
            'GRID_TEXT', 'GRID_BACK', 'SELECTED_TEXT', 'TITLE_TEXT', 'TITLE_BACK', 'BUSY_BACK'
        ]
        self.COLORs = {name: wx.NewIdRef() for name in self.colors}
        # For color selections see https://docs.wxpython.org/wx.ColourDatabase.html#wx-colourdatabase
        self.COLORid = {
            self.COLORs['BTN_PRESS']: ['TAN'],              # Alternate WHITE or THISTLE
            self.COLORs['BTN_DIRECTORY']: ['WHEAT'],
            self.COLORs['BTN_DONE']: ['WHITE'],
            self.COLORs['SELECTED']: ['NAVY'],              # Does not currently work
            self.COLORs['SELECTED_TEXT']: ['BLACK'],        # Does not currently work
            self.COLORs['ANCESTOR']: ['MEDIUM GOLDENROD'],
            self.COLORs['MAINPERSON']: ['KHAKI'],
            self.COLORs['OTHERPERSON']: ['WHITE'],
            self.COLORs['INFO_BOX_BACKGROUND']: ['GOLDENROD'],
            self.COLORs['GRID_TEXT']: ['BLACK'],            # Alternate DIM GREY
            self.COLORs['GRID_BACK']: ['WHITE'],            # Alternate DARK SLATE GREY
            self.COLORs['TITLE_TEXT']: ['WHITE'],
            self.COLORs['TITLE_BACK']: ['KHAKI'],
            self.COLORs['BUSY_BACK']: ['YELLOW']

        }
        for colorToValue in self.colors:
            self.COLORid[self.COLORs[colorToValue]].append( wx.TheColourDatabase.FindColour(self.COLORid[self.COLORs[colorToValue]][0]))
        
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