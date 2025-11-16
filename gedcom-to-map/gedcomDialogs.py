__all__ = ['AboutDialog', 'HelpDialog', 'ConfigDialog', 'PersonDialog', 'FindDialog', 'BackgroundActions', 'formatPersonName']

import _thread
import logging
import logging.config
import time

import requests
from io import BytesIO
from pathlib import Path
import os
import platform
import wx
import wx.lib.newevent
import wx.html
import wx.grid as gridlib
from models.LatLon import LatLon
from models.Person import Person, LifeEvent
from gedcom.gedcomdate import CheckAge, maxage
from gedcomoptions import gvOptions, ResultsType
from style.stylemanager import FontManager

from const import VERSION, GUINAME, ABOUTLINK, NAME
from gedcomvisual import ParseAndGPS, doHTML, doKML, doKML2, doSUM, doTraceTo

maxPhotoWidth = 400  # Maximum width for photos in the PersonDialog
maxPhotoHeight = 500  # Maximum Height for photos in the PersonDialog

_log = logging.getLogger(__name__.lower())

UpdateBackgroundEvent = None

class HTMLDialog(wx.Dialog):
    def __init__(self, parent, title, icontype, htmlbody, width: int, font_manager: FontManager):
        # font_manager is required; caller must pass a valid FontManager instance
        self.font_manager = font_manager
        self.font_name, self.font_size = self.font_manager.get_font_name_size()
        super().__init__(parent, title=title, size=(self.font_size * width, self.font_size * 45))

        self.icon = wx.ArtProvider.GetBitmap(icontype, wx.ART_OTHER, (32, 32))
        self.icon_ctrl = wx.StaticBitmap(self, bitmap=self.icon)
        self.html = wx.html.HtmlWindow(self)
        self.set_current_font()
        self.html.SetPage(f"<html><body>{htmlbody}</body></html>".replace('VERVER', f"{GUINAME} {VERSION}").replace('PROJECTLINK', f"{ABOUTLINK}{NAME}"))

        self.okButton = wx.Button(self, wx.ID_OK, "OK")
        # ensure OK ends the modal loop cleanly
        self.okButton.Bind(wx.EVT_BUTTON, lambda evt: self.EndModal(wx.ID_OK))

        sizer = wx.BoxSizer(wx.VERTICAL)
        icon_sizer = wx.BoxSizer(wx.HORIZONTAL)

        icon_sizer.Add(self.icon_ctrl, 0, wx.ALL, 10)
        icon_sizer.Add(self.html, 1, wx.EXPAND | wx.ALL, 7)
        
        sizer.Add(icon_sizer, 1, wx.EXPAND)
        sizer.Add(self.okButton, 0, wx.ALIGN_CENTER | wx.ALL, 5)

        self.SetSizer(sizer)

        self.Bind(wx.html.EVT_HTML_LINK_CLICKED, self.on_link_clicked, self.html)

    def set_current_font(self):
        self.html.SetFonts(self.font_name, self.font_name, [self.font_size]*7)

    def on_link_clicked(self, event):
        wx.LaunchDefaultBrowser(event.GetLinkInfo().GetHref())

    def on_ok(self, event):
        # Defensive: end modal loop; caller will Destroy() after ShowModal returns
        try:
            if self.IsModal():
                self.EndModal(wx.ID_OK)
            else:
                self.Close()
        except Exception:
            # fallback: ensure dialog is closed
            self.Destroy()

class AboutDialog(HTMLDialog):
    def __init__(self, parent, title, font_manager: FontManager):

        abouttype = """
<h1><a href="PROJECTLINK">VERVER</a></h1>
<b>Orginal project:</b> Originally forked from <a href="https://github.com/lmallez/gedcom-to-map/">gedcom-to-map.</a><p />
<h2>Contributors:</h2> 
<ul><li><b>Darren Jeffrey</b> (<a href="https://github.com/D-Jeffrey/">D-Jeffrey</a>)</li>
<li><b>Colin Osborne</b> (<a href="https://github.com/colin0brass/">colin0brass</a>)</li>
<li><b>Laurent Mallez</b> (<a href="https://github.com/lmallez/">lmallez</a>)</li>
</ul>
<h3>Major Packages:</h3>
<ul>
<li><b>ged4py</b> (<a href="https://ged4py.readthedocs.io/en/latest/">ged4py</a>) - For parsing GEDCOM files</li>
<li><b>wxPython</b> (<a href="https://wxpython.org/">wxPython</a>) - For building the graphical user interface (GUI)</li>
<li><b>folium</b> (<a href="https://python-visualization.github.io/folium/">folium</a>) - For creating interactive maps with Leaflet.js</li>
<li><b>simplekml</b> (<a href="https://simplekml.readthedocs.io/en/latest/">simplekml</a>) - For generating KML files for Google Earth</li>
<li><b>geopy</b> (<a href="https://geopy.readthedocs.io/en/stable/">geopy</a>) - For geocoding and reverse geocoding</li>
</ul>
<p />
<b>License:</b> <a href="https://github.com/D-Jeffrey/gedcom-to-visualmap/blob/main/LICENSE">MIT License.</a>

<p />
For more details and to contribute, visit the <a href="PROJECTLINK">GitHub repository.</a></li>
"""

        super().__init__(parent, title=title, icontype=wx.ART_INFORMATION, htmlbody=abouttype, width=55, font_manager=font_manager)

class HelpDialog(HTMLDialog):
    def __init__(self, parent, title, font_manager: FontManager):

        helppage = """
<h2><a href="PROJECTLINK">VERVER</a></h2>
<p>The "GEDCOM to Visual Map" project is a powerful tool designed to read <a href="https://gedcom.io/">GEDCOM files</a> and translate the locations into GPS addresses. It produces different KML map types that show timelines and movements around the earth. The project includes both command-line and GUI interfaces (tested on Windows) to provide flexibility in usage.</p>
<h3>Key Features:</h3>
<ul><li><b>Interactive Maps:</b> Generates interactive HTML files that display relationships between children and parents, and where people lived over the years.</li>
<li><b>Heatmaps:</b> Includes heatmaps to show busier places, with markers overlayed for detailed views.</li>
<li><b>Geocoding:</b> Converts place names into GPS coordinates, allowing for accurate mapping.</li>
<li><b>Multiple Output Formats:</b> Supports both <a href="https://python-visualization.github.io/folium/latest/">HTML</a> and <a href="https://support.google.com/earth/answer/7365595">KML</a> output formats for versatile map visualization.  KML2 is an alternate and improved version of the orginal way of generating the relationship(Not all Options work with this mode yet)</li>
<li><b>User-Friendly GUI:</b> The GUI version allows users to easily load GEDCOM files, set options, and generate maps with a few clicks.</li>
<li><b>Customizable Options:</b> Offers various options to customize the map, such as grouping by family name, turning on/off markers, and adjusting heatmap settings.</li>
</ul>
<h3>Things to know</h3>
<ul><li><b>Right-click:</b> Right-click on (Activate) a person in the list to view more details.</li>
<li><b>Double-click</b> Double-click on a person in the list to set them as the main person and find all their associcated parents</li>
<li><b>click parent</b> Click on a parent in the person dialog to open that parent's details</li>
<li><b>Trace</b> For the selected person save to a text file all the associcated parents(tab seperated)</li>
<li><b>Geo Table</b> Edit the file and translates so that next time it does better location lookups by putting replacement values in the 'alt' column or by filling in the 'Country', 
then blank the lat, long and boundary have it looked up again. Do not convert it to another format and close Excel so the file can be access.</li>
<li><b>Logging Options</b> Can be updated while the application is loading or resolves addresses.</li>
<li><b>Relatives</b> Can Activate a person and the bring up the Person and if they are in a direct line, it will list the father & mother trace along with the children.</li>                          
<li><b>Photos</b> Photos can be a URL or a local file path.  If a URL it must start with http:// or https://.  If a local file path it can be absolute or relative to the gedcom file.</li>                          
<li><b>Timelines</b> The KML output has a timeline that can be used to show the movement of people over time.  The timeline can be used to filter the display of people on the map.</li>
                          </ul>                          
</ul>
For more details and to contribute, visit the <a href="PROJECTLINK">GitHub repository.</a></li>
<p>

</p>
"""

        super().__init__(parent, title=title, icontype=wx.ART_INFORMATION, htmlbody=helppage, width=55, font_manager=font_manager)

#==============================================================
class ConfigDialog(wx.Frame):
    def __init__(self, parent, title, gOp):
        super().__init__(parent, title=title, size=(500, 650))

        includeNOTSET = True
        self.gOp = gOp               # DEFAULT Disabled with False
        self.loggerNames = list(logging.root.manager.loggerDict.keys())
        cfgpanel = wx.Panel(self,style=wx.SIMPLE_BORDER  )
        
        TEXTkmlcmdlinelbl = wx.StaticText(cfgpanel, -1,  " KML Editor Command line:   ") 
        self.TEXTkmlcmdline = wx.TextCtrl(cfgpanel, wx.ID_FILE1, "", size=(250,20))
        if gOp.KMLcmdline:
            self.TEXTkmlcmdline.SetValue(gOp.KMLcmdline)
        TEXTcsvcmdlinelbl = wx.StaticText(cfgpanel, -1,  " CSV Table Editor Command line:   ") 
        self.TEXTcsvcmdline = wx.TextCtrl(cfgpanel, wx.ID_FILE1, "", size=(250,20))
        if gOp.CSVcmdline:
            self.TEXTcsvcmdline.SetValue(gOp.CSVcmdline)            
        TEXTtracecmdlinelbl = wx.StaticText(cfgpanel, -1,  " Trace Table Editor Command line:   ") 
        self.TEXTtracecmdline = wx.TextCtrl(cfgpanel, wx.ID_FILE1, "", size=(250,20))
        if gOp.Tracecmdline:
            self.TEXTtracecmdline.SetValue(gOp.Tracecmdline)
        self.CBBadAge = wx.CheckBox(cfgpanel, -1,  'Flag if age is off')
        self.CBBadAge.SetValue(gOp.badAge)
        self.badAge = True            
        GRIDctl = gridlib.Grid(cfgpanel)
        if includeNOTSET:
            gridlen = len(logging.root.manager.loggerDict)
        else:
            gridlen =  sum(1 for erow, loggerName in enumerate(self.loggerNames) if logging.getLogger(loggerName).level != 0)     # Hack NOTSET

        GRIDctl.CreateGrid(gridlen, 2)
        GRIDctl.SetColLabelValue(0, "Logger Name")
        GRIDctl.SetColLabelValue(1, "Log Level")
    
        self.logging_levels = ['NOTSET', 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']

        def makeCells():
            GRIDctl.SetCellValue(self.row, 0, loggerName)
            GRIDctl.SetCellBackgroundColour(self.row, 0, wx.LIGHT_GREY)
            GRIDctl.SetCellValue(self.row, 1, logging.getLevelName(updatelog.level))
            GRIDctl.SetCellEditor(self.row, 1, gridlib.GridCellChoiceEditor(self.logging_levels))
            if updatelog.level == 0:
                GRIDctl.SetCellBackgroundColour(self.row, 1, wx.LIGHT_GREY)

            GRIDctl.SetReadOnly(self.row, 0)
            self.row += 1


        self.row = 0
        for erow, loggerName in enumerate(self.loggerNames):
            updatelog = logging.getLogger(loggerName)
            if logging.getLevelName(updatelog.level) != "NOTSET" and loggerName in self.gOp.logging_keys:
                makeCells()
                
        # The following only is relavent for modules that could have `logging`` added to them
        if includeNOTSET:
            for erow, loggerName in enumerate(self.loggerNames):
                updatelog = logging.getLogger(loggerName)
                if logging.getLevelName(updatelog.level) == "NOTSET" and loggerName in self.gOp.logging_keys:
                    makeCells()
                    
            for erow, loggerName in enumerate(self.loggerNames):
                updatelog = logging.getLogger(loggerName)
                if loggerName not in self.gOp.logging_keys:
                    makeCells()
                    
            
        GRIDctl.AutoSizeColumn(0,True)
        GRIDctl.AutoSizeColumn(1,True)
        
        

        saveBTN = wx.Button(cfgpanel, label="Save Changes")
        saveBTN.Bind(wx.EVT_BUTTON, self.onSave)
        cancelBTN = wx.Button(cfgpanel, label="Cancel")
        cancelBTN.Bind(wx.EVT_BUTTON, self.onCancel)
        parts = [(5,20),  wx.BoxSizer(wx.HORIZONTAL), (5,20), wx.BoxSizer(wx.HORIZONTAL), (5,20), wx.BoxSizer(wx.HORIZONTAL), self.CBBadAge, (10,20)]
        parts[1].AddMany([TEXTkmlcmdlinelbl,      (3,20),     self.TEXTkmlcmdline])
        parts[3].AddMany([TEXTcsvcmdlinelbl,      (3,20),     self.TEXTcsvcmdline])
        parts[5].AddMany([TEXTtracecmdlinelbl,      (3,20),     self.TEXTtracecmdline])
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.AddMany(parts)
        

        sizer.AddMany([ 
            wx.StaticText(cfgpanel, -1,  "Use   $n  for the name of the file within a command line - such as    notepad $n"),    
            wx.StaticText(cfgpanel, -1,  "Use   $n  without any command to open default application for that file type") ])  
        sizer.AddSpacer(20)
        sizer.Add(wx.StaticText(cfgpanel, -1,  " Logging Options:"))
        # l3 = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(GRIDctl, 1, wx.EXPAND | wx.ALL, 20)
        # l3.AddMany([(20,20),      GRIDctl,     (20,20)])
        # TODO This is wrong but it works for now
        # sizer.Add(l3, 400, 5)
        buttonsizer = wx.BoxSizer(wx.HORIZONTAL)
        buttonsizer.Add(saveBTN, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        buttonsizer.Add(cancelBTN, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        sizer.Add(buttonsizer, 0, wx.ALIGN_CENTER | wx.ALL, 5)

        cfgpanel.SetSizer(sizer)
        self.GRIDctl = GRIDctl
        self.Show(True)

    def onSave(self, event):
        for row in range(self.GRIDctl.GetNumberRows()):
            loggerName = self.GRIDctl.GetCellValue(row, 0)
            logLevel = self.GRIDctl.GetCellValue(row, 1)
            updatelog = logging.getLogger(loggerName)
            updatelog.setLevel(getattr(logging, logLevel))
        self.gOp.KMLcmdline = self.TEXTkmlcmdline.GetValue()
        self.gOp.CSVcmdline = self.TEXTcsvcmdline.GetValue()
        self.gOp.Tracecmdline = self.TEXTtracecmdline.GetValue()
        self.gOp.badAge = self.CBBadAge.GetValue()
        self.gOp.savesettings()
        self.Close()
        self.DestroyLater()

    def onCancel(self, event):
        self.Close()
        self.DestroyLater()

class FamilyPanel(wx.Panel):
    def __init__(self, parent, hertiageData, isChildren=False, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        # Data structure: Family data with parent-child relationships
        # Example: {"parent_id": ("Name", "Mother/Father", BornYear, DeathYear, BornAddress, [children_born_years])}
        self.hertiageData = hertiageData
        self.gOp = parent.gOp

        # Create a grid
        self.grid = gridlib.Grid(self)
        self.grid.CreateGrid(len(self.hertiageData), 8)  # Number of rows based on family data
        
        # Set column labels
        self.grid.SetColLabelValue(0, "Name")
        if not isChildren:
            self.grid.SetColLabelValue(1, "Mom/Dad")
        self.grid.SetColLabelValue(2, "Born Yr")
        self.grid.SetColLabelValue(3, "Death Yr")
        if isChildren:
            self.grid.SetColLabelValue(4, "Life Age")
        else:
            self.grid.SetColLabelValue(4, "Childbirth Age")
        self.grid.SetColLabelValue(5, "Born Address")
        self.grid.SetColLabelValue(6, "Description")
        self.grid.SetColLabelValue(7, "ID")

        self.grid.MaxSize = (-1,400)    
        # Populate the grid with family data
        self.populateGrid(isChildren)

        # Layout
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.grid, 1, wx.EXPAND | wx.ALL, 10)
        self.SetSizer(sizer)
        
        self.visual_map_panel = self.GetParent().GetParent()
        

    def populateGrid(self, isChildren=False):
        """Populate the grid with family data and calculate the age dynamically."""
        child_born_year = None  # Initialize child_born_year to None for the first iteration
        for row, (parent_id, details) in enumerate(self.hertiageData.items()):
            name, mother_father, born_year, death_year, born_address, descrip, id = details
            
            if isChildren:
                if born_year and death_year:
                    age = int(death_year) - int(born_year)
                else:
                    age = "?"
            else:
                # Calculate age dynamically based on the oldest child's birth year
                if child_born_year and born_year:
                    age =   int(child_born_year) - int(born_year)
                else:
                    age = "?"  # No children provided

            # Set cell values
            self.grid.SetCellValue(row, 0, name)  # Name
            self.grid.SetCellValue(row, 1, mother_father)  # Mother/Father
            self.grid.SetCellValue(row, 2, str(born_year) if born_year else "?") # Born Year
            self.grid.SetCellValue(row, 3, str(death_year) if death_year else "?")  # Death Year
            self.grid.SetCellValue(row, 4, str(age))  # Age
            self.grid.SetCellValue(row, 5, born_address if born_address else "")  # Born Address
            self.grid.SetCellValue(row, 6, descrip)  # Description
            self.grid.SetCellValue(row, 7, id)  # ID
            if age != "?":
                if age < 0 or age > maxage:
                    self.grid.SetCellBackgroundColour(row, 4, wx.RED)
                    self.grid.SetCellTextColour(row, 4, wx.WHITE)
                elif (age > 60 or age < 13) and not isChildren:
                    self.grid.SetCellBackgroundColour(row, 4, wx.YELLOW)
            child_born_year = born_year     # Use for next loop

        self.grid.AutoSizeColumns()
        for row in range(self.grid.GetNumberRows()):
            self.grid.SetCellAlignment(row, 2, wx.ALIGN_RIGHT, wx.ALIGN_CENTER)  # Right-align numbers in the third column
            self.grid.SetCellAlignment(row, 3, wx.ALIGN_RIGHT, wx.ALIGN_CENTER)  # Right-align numbers in the third column
            self.grid.SetCellAlignment(row, 4, wx.ALIGN_RIGHT, wx.ALIGN_CENTER)  # Right-align numbers in the third column
        # Right Click for consisntancy with main grid  (That allose lieft click to select and copy text)
        self.grid.Bind(wx.grid.EVT_GRID_CELL_RIGHT_CLICK, self.OnRowClick)
        self.grid.Bind(wx.grid.EVT_GRID_LABEL_RIGHT_CLICK, self.OnRowClick)

    def OnRowClick(self, event: wx.grid.GridEvent):
        """Handle item activation (double-click) in the grid."""
        row = event.GetRow()
        # Get the ID of the selected person
        person_id = self.grid.GetCellValue(row, 7)
        # Open the person dialog with the selected person's details
        person = self.gOp.BackgroundProcess.people.get(person_id)
        if person:
            # pass the shared FontManager from the VisualMapPanel into the dialog
            fm = getattr(self.gOp.panel, "font_manager", None)
            dialog = PersonDialog(self, person, self.visual_map_panel, font_manager=fm, gOp=self.gOp, showrefences=False)
            dialog.Show(True)
            dialog.Bind(wx.EVT_CLOSE, lambda evt: dialog.Destroy())
        else:
            wx.MessageBox("Person not found.", "Error", wx.OK | wx.ICON_ERROR)

def formatPersonName(person: Person, longForm=True):
    if person:
        if longForm:
            maidenname = f" ({person.maidenname})" if person.maidenname else ""
            title = f" - {person.title}" if person.title else ""
        else:
            maidenname = ""
            title = ""
        return f"{person.firstname} {person.surname}{maidenname}{title}" 
    else:
        return "<none>"

class PersonDialog(wx.Dialog):
    def __init__(self, parent, person: Person, panel, font_manager: FontManager, gOp: gvOptions, showrefences=True):
        """
        NOTE: font_manager is required by callers; pass the FontManager instance used by the UI.
        Keep signature backwards-compatible in source order but require font_manager parameter.
        """
        if font_manager is None:
            raise ValueError("font_manager is required for PersonDialog")
        super().__init__(parent, title="Person Details", size=(600, 600), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        
        self.gOp = gOp
        self.font_manager = font_manager
        self.font_name, self.font_size = self.font_manager.get_font_name_size()

        def sizeAttr(attr,pad=1):
            return (min(len(attr),3)+pad)*(self.font_size+5)  if attr else self.font_size
        
        people = self.gOp.BackgroundProcess.people
        # Display the marriage information including the marriage location and date                
        marrying = []
        if person.marriages:
            for marry in person.marriages:
                marrying.append(f"{formatPersonName(people[marry.record.xref_id], False)}{marry.asEventstr()}")
        marriages = "\n".join(marrying)        

        homes = []
        if person.home:
            for homedesc in person.home:
                homes.append(f"{LifeEvent.asEventstr(homedesc)}")
        homelist = "\n".join(homes)
        photourl = person.photo
        issues = CheckAge(people, person.xref_id)
        self.nameTextCtrl = wx.TextCtrl(self, style=wx.TE_READONLY, size=(550,-1))
        self.titleTextCtrl = wx.TextCtrl(self, style=wx.TE_READONLY)
        self.fatherTextCtrl = wx.TextCtrl(self, style=wx.TE_READONLY)
        self.motherTextCtrl = wx.TextCtrl(self, style=wx.TE_READONLY)
        self.birthTextCtrl = wx.TextCtrl(self, style=wx.TE_READONLY)
        self.deathTextCtrl = wx.TextCtrl(self, style=wx.TE_READONLY)
        self.sexTextCtrl = wx.TextCtrl(self, style=wx.TE_READONLY)
        self.marriageTextCtrl = wx.TextCtrl(self, style=wx.TE_READONLY|wx.TE_MULTILINE, size=(-1,sizeAttr(marriages)))
        self.homeTextCtrl = wx.TextCtrl(self, style=wx.TE_READONLY|wx.TE_MULTILINE, size=(-1,sizeAttr(homelist)))
        if issues:
            self.issuesTextCtrl = wx.TextCtrl(self, style=wx.TE_READONLY|wx.TE_MULTILINE, size=(-1,sizeAttr(issues)))

        # Layout the relative grid
        sizer = wx.FlexGridSizer(cols=2, hgap=5, vgap=5)

        sizer.Add(wx.StaticText(self, label="Name: "), 0, wx.LEFT|wx.TOP, border=5)
        sizer.Add(self.nameTextCtrl, 0, wx.EXPAND, border=5)
        sizer.Add(wx.StaticText(self, label="Title: "), 0, wx.LEFT|wx.TOP, border=5)
        sizer.Add(self.titleTextCtrl, 0, wx.EXPAND)
        sizer.Add(wx.StaticText(self, label="Father: "), 0, wx.LEFT|wx.TOP, border=5)
        sizer.Add(self.fatherTextCtrl, 1, wx.EXPAND)
        sizer.Add(wx.StaticText(self, label="Mother: "), 0, wx.LEFT|wx.TOP, border=5)
        sizer.Add(self.motherTextCtrl, 1, wx.EXPAND)
        sizer.Add(wx.StaticText(self, label="Birth: "), 0, wx.LEFT|wx.TOP, border=5)
        sizer.Add(self.birthTextCtrl, 0, wx.EXPAND)
        sizer.Add(wx.StaticText(self, label="Death: "), 0, wx.LEFT|wx.TOP, border=5)
        sizer.Add(self.deathTextCtrl, 0, wx.EXPAND)
        sizer.Add(wx.StaticText(self, label="Sex: "), 0, wx.LEFT|wx.TOP, border=5)
        sizer.Add(self.sexTextCtrl, 0, wx.EXPAND)
        sizer.Add(wx.StaticText(self, label="Marriages: "), 0, wx.LEFT|wx.TOP, border=5)
        sizer.Add(self.marriageTextCtrl, 1, wx.EXPAND|wx.ALL, border=5)
        sizer.Add(wx.StaticText(self, label="Homes: "), 0, wx.LEFT|wx.TOP, border=5)
        sizer.Add(self.homeTextCtrl, 1, wx.EXPAND|wx.ALL, border=5)
        if issues:
            sizer.Add(wx.StaticText(self, label="Age Problems:"), 0, wx.LEFT|wx.TOP, border=5)
            sizer.Add(self.issuesTextCtrl, 1, wx.EXPAND|wx.ALL, border=5)
            self.issuesTextCtrl.SetBackgroundColour(wx.YELLOW)
    

        # set the person's data in the UI controls
        self.nameTextCtrl.SetValue(formatPersonName(person))

        # Should be conditional
        self.titleTextCtrl.SetValue(person.title if person.title else "")

        if person.father:
            self.fatherTextCtrl.SetValue(formatPersonName(people[person.father]))
        if person.mother:
            self.motherTextCtrl.SetValue(formatPersonName(people[person.mother]))
        self.birthTextCtrl.SetValue(f"{person.birth.asEventstr()}" if person.birth else "")  
        if person.death and person.birth and person.death.when and person.birth.when:
            age = f"(age ~{person.age})" if hasattr( person, "age") else f"(age ~{person.death.whenyearnum() - person.birth.whenyearnum()})" 
        else:
            age = ""
        self.deathTextCtrl.SetValue(f"{LifeEvent.asEventstr(person.death)}" if person.death else "")
        sex = person.sex if person.sex else ""
        self.sexTextCtrl.SetValue(f"{sex} {age}")
        self.marriageTextCtrl.SetValue(marriages)
        
        if issues:
            self.issuesTextCtrl.SetValue("\n".join(issues))
        
        self.homeTextCtrl.SetValue(homelist)
        if len(homes) > 3:
            sizer.AddGrowableRow(8)
        if self.gOp.Referenced and showrefences:
            self.related = None
            if panel.gOp.Referenced.exists(person.xref_id):
                hertiageList = doTraceTo(panel.gOp, person)
                if hertiageList:
                    hertiageSet = {}
                    for (hertiageparent, hertiageperson, hyear, hid) in hertiageList:
                        descript = f"{people[hid].title}"
                        hertiageSet[hid] = (hertiageperson, 
                                            hertiageparent, 
                                            people[hid].birth.whenyear() if people[hid].birth else None, 
                                            people[hid].death.whenyear() if people[hid].death else None, 
                                            people[hid].birth.getattr('place') if people[hid].birth else None, 
                                            descript, 
                                            hid)
                    # Create the panel and pass the data
                    self.related = FamilyPanel(self, hertiageSet)
                
            if not self.related:
               self.related = wx.StaticText(self, label="No lineage to selected main person")
            
            sizer.Add(wx.StaticText(self, label="Lineage: "), 0, wx.LEFT|wx.TOP, border=5)
            sizer.Add(self.related, 1, wx.EXPAND, border=5)
        if person.children:
            childSet = {}
            for hid in person.children:
                descript = f"{people[hid].title}"
                childSet[hid] = (people[hid].name, 
                                    "", 
                                    people[hid].birth.whenyear() if people[hid].birth else None, 
                                    people[hid].death.whenyear() if people[hid].death else None, 
                                    people[hid].birth.getattr('place') if people[hid].birth else None, 
                                    descript, 
                                    hid)
                # Create the panel and pass the data
            childsize = FamilyPanel(self, childSet, isChildren=True)
            
            sizer.Add(wx.StaticText(self, label="Childred: "), 0, wx.LEFT|wx.TOP, border=5)
            sizer.Add(childsize, 1, wx.EXPAND, border=5)
        image = None
        image_content = None
        if photourl:
            if photourl.find("http")==0:
                try:
                    response = requests.get(photourl, timeout=10)
                    response.raise_for_status()  # Raise an error for bad responses
                    image_content = BytesIO(response.content)
                except requests.RequestException as e:
                    _log.error(f"Error fetching photo from {photourl}:\n      {e}")
                    image = None
                    image_content = None
            else:
                infile = panel.gOp.get('GEDCOMinput')
                if infile is not None:
                    dDir =  os.path.dirname(infile)
                image_content = Path(photourl) if Path(photourl).is_absolute() else os.path.join(dDir, photourl)
            if image_content:
                try:
                    image = wx.Image(image_content, wx.BITMAP_TYPE_ANY)
                except Exception as e:
                    _log.error(f"Error reading photo {photourl}:\n      {e}")
                    image = None
            if image:
                if image.GetWidth() > maxPhotoWidth:
                    image.Rescale(maxPhotoWidth, int(image.GetHeight()*maxPhotoWidth/image.GetWidth()))
                if image.GetHeight() > maxPhotoHeight:
                    image.Rescale(int(image.GetWidth()*maxPhotoHeight/image.GetHeight()),maxPhotoHeight)
                self.photo = wx.StaticBitmap(self, bitmap=wx.Bitmap(image))

                
        mainSizer = wx.BoxSizer(wx.VERTICAL)
        # mainSizer.Add (sizer, 1, wx.EXPAND | wx.ALL, border=5)
        if image:
            wrapper = wx.BoxSizer(wx.HORIZONTAL)
            wrapper.Add(sizer, 1, wx.ALL|wx.EXPAND, border=5)
            wrapper.Add(self.photo, 0, wx.TOP, border=5)
            mainSizer.Add(wrapper, 1, wx.EXPAND| wx.ALL, border=5)
        else:
            mainSizer.Add(sizer, 1, wx.EXPAND| wx.ALL, border=5)
        
        # create the OK button
        ok_btn = wx.Button(self, wx.ID_OK)
        btn_sizer = wx.StdDialogButtonSizer()
        # ensure OK ends the windows dialog reliably
        ok_btn.Bind(wx.EVT_BUTTON, lambda evt: self.Close())
        btn_sizer.AddButton(ok_btn)
        btn_sizer.Realize()
        mainSizer.Add(btn_sizer, 0, wx.ALIGN_LEFT|wx.ALL, border=10)
        self.SetSizer(mainSizer)
        self.SetBackgroundColour(wx.TheColourDatabase.FindColour('WHITE'))
        self.Fit()

    
        
        
    
class FindDialog(wx.Dialog):
    def __init__(self, parent, title, LastSearch=""):
        super().__init__(parent, title=title, size=(300, 150))
        
        self.LastSearch = LastSearch
        
        # Layout
        Findpanel = wx.Panel(self, style=wx.SIMPLE_BORDER)
        vbox = wx.BoxSizer(wx.VERTICAL)
        
        self.SearchLabel = wx.StaticText(Findpanel, label="Enter search string:")
        vbox.Add(self.SearchLabel, flag=wx.ALL, border=10)
        
        self.SearchText = wx.TextCtrl(Findpanel)
        self.SearchText.SetValue(self.LastSearch)
        vbox.Add(self.SearchText, flag=wx.EXPAND | wx.LEFT | wx.RIGHT, border=10)
        
        self.okButton = wx.Button(Findpanel, label="OK")
        self.cancelButton = wx.Button(Findpanel, label="Cancel")
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(self.okButton, flag=wx.RIGHT, border=10)
        hbox.Add(self.cancelButton, flag=wx.LEFT, border=10)
        vbox.Add(hbox, flag=wx.ALIGN_CENTER | wx.ALL, border=10)
        
        Findpanel.SetSizer(vbox)
        # Set OK button as default
        self.okButton.SetDefault()
        
        # Event bindings
        self.okButton.Bind(wx.EVT_BUTTON, self.OnOk)
        self.cancelButton.Bind(wx.EVT_BUTTON, self.OnCancel)
    
    def OnOk(self, event):
        self.LastSearch = self.SearchText.GetValue()
        self.EndModal(wx.ID_OK)
    
    def OnCancel(self, event):
        self.EndModal(wx.ID_CANCEL)
    
    def GetSearchString(self):
        return self.LastSearch








class BackgroundActions:
    """
This runs the backgrund tasks on another thread.
This includes update messages, running of load, calling gpslookups, 
and generating the output so that the GUI can continue to be responsive

"""
    def __init__(self, win, threadnum):
        self.win = win
        self.gOp = None
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
        

    def DefgOps(self, gOp):
        # Pull the global variables into this thread - Critical to do this
        self.gOp = gOp
        

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
        if dolevel & 1 or dolevel & 4:
            self.gOp.panel.id.BTNLoad.SetBackgroundColour(self.gOp.panel.id.GetColor('BTN_DONE'))
        if dolevel & 2:
            self.gOp.panel.id.BTNCreateFiles.SetBackgroundColour(self.gOp.panel.id.GetColor('BTN_DONE'))
        self.do = dolevel
        
    def SayInfoMessage(self, line, newline= True):
        if newline and self.updateinfo and self.updateinfo != '':
            self.updateinfo = self.updateinfo + "\n"
        self.updateinfo = self.updateinfo + line if self.updateinfo else line
        
    def SayErrorMessage(self, line, newline= True):
        if newline and self.errorinfo and self.errorinfo != '':
            self.errorinfo = self.errorinfo + "\n"
        self.errorinfo = self.errorinfo + line if self.errorinfo else line

    def Run(self):
        global UpdateBackgroundEvent
        self.SayInfoMessage(' ',True)      # prime the InfoBox
        while self.keepGoing:
            # We communicate with the UI by sending events to it. There can be
            # no manipulation of UI objects from the worker thread.
            if self.do != 0 and self.readyToDo:
                self.readyToDo = False          # Avoid a Race
                _log.info("triggered thread %d (Thread# %d / %d)", self.do, self.threadnum, _thread.get_ident())
                if not UpdateBackgroundEvent:
                    UpdateBackgroundEvent = self.gOp.UpdateBackgroundEvent
                self.gOp.stopping = False
                wx.Yield()
                if self.do & 1 or (self.do & 4 and not self.gOp.parsed):
                    wx.PostEvent(self.win, UpdateBackgroundEvent(state='busy'))
                    wx.Yield()
                    _log.info("start ParseAndGPS")
                    if hasattr(self, 'people'):
                        if self.people:                            
                            del self.people
                            self.gOp.people = None
                            self.people = None
                    _log.info("ParseAndGPS")
                    try:
                        self.people = ParseAndGPS(self.gOp, 1)
                    
                    except Exception as e:
                        _log.exception("Issues in ParseAndGPS")
                        # Capture other exceptions
                        if hasattr(self, 'people'):
                            if self.people:                            
                                del self.people
                                self.people = None
                        self.do = 0
                        _log.warning(str(e))
                        self.gOp.stopping = False
                        self.SayErrorMessage('Failed to Parse', True)
                        self.SayErrorMessage(str(e), True)
                        
                    if self.do & 1 and self.gOp.Referenced:
                        del self.gOp.Referenced
                        self.gOp.Referenced = None 
                    # self.updategrid = True
                    wx.PostEvent(self.win, UpdateBackgroundEvent(state='busy'))
                    wx.Yield()
                    if hasattr (self, 'people') and self.people:                            
                        _log.info("person count %d", len(self.people))
                        # self.people = ParseAndGPS(self.gOp, 2)
                        self.updategrid = True
                        if self.people:
                            self.SayInfoMessage(f"Loaded {len(self.people)} people")
                        else:
                            self.SayInfoMessage(f"Cancelled loading people")
                        if self.gOp.Main:
                            self.SayInfoMessage(f" with '{self.gOp.Main}' as starting person from {Path(self.gOp.GEDCOMinput).name}", False)
                    else:
                        if self.gOp.stopping:
                            self.SayErrorMessage(f"Error: Aborted loading GEDCOM file", True)
                        else:
                            self.SayErrorMessage(f"Error: file could not read as a GEDCOM file", True)
                    
                if self.do & 2:
                    _log.info("start do 2")
                    if (self.gOp.parsed):
                        _log.info("doHTML or doKML")
                        fname = self.gOp.Result
                        if (self.gOp.ResultType is ResultsType.HTML):
                            ### needAGridUpdate = not self.gOp.Referenced
                            doHTML(self.gOp, self.people, True)
                            # We only need to update the Grid if we have not calculated the Referenced before
                            ### self.updategridmain = needAGridUpdate
                            self.SayInfoMessage(f"HTML generated for {self.gOp.totalpeople} people ({fname})")
                        elif (self.gOp.ResultType is ResultsType.KML):  
                            doKML(self.gOp, self.people)
                            self.SayInfoMessage(f"KML file generated for {self.gOp.totalpeople} people/points ({fname})")
                        elif (self.gOp.ResultType is ResultsType.KML2):  
                            doKML2(self.gOp, self.people)
                            self.SayInfoMessage(f"KML2 file generated for {self.gOp.totalpeople} people/points ({fname})")
                        elif (self.gOp.ResultType is ResultsType.SUM):  
                            doSUM(self.gOp)
                            self.SayInfoMessage(f"Summary files generated ({fname})")
                    else:
                        _log.info("not parsed")
                    _log.info("done draw")
                    

                _log.debug("=======================GOING TO IDLE %d", self.threadnum)
                self.do = 0
                self.readyToDo = True
                self.gOp.stop()
                wx.PostEvent(self.win, UpdateBackgroundEvent(state='done'))
            else:
                time.sleep(0.3)
                # _log.info("background Do:%d  &  Running:%d  %d", self.do , self.gOp.running, self.gOp.counter)

        self.threadrunning = False

