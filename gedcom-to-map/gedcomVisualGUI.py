# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
#
#
#  gedcomVisualGUI.py : GUI Interface main for gedcom-to-map
#    See https://github.com/D-Jeffrey/gedcom-to-visualmap
#
#
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 

#!/usr/bin/env python

import os
import subprocess
import sys
import os.path
import time
import re
import wx
# pylint: disable=no-member
import wx.lib.anchors as anchors
import wx.lib.newevent
import wx.lib.mixins.listctrl as listmix
import _thread
import webbrowser
import logging
import logging.config

from const import NAME, VERSION, LOG_CONFIG, KMLMAPSURL
from gedcomoptions import gvOptions
from gedcomvisual import doKML, doHTML, ParseAndGPS
from models.Human import Human, LifeEvent

logger = logging.getLogger(__name__)

[   ID_CBMarksOn,
    ID_CBHeatMap,
    ID_CBBornMark,
    ID_CBDieMark,
    ID_LISTMapStyle,
    ID_CBMarkStarOn,
    ID_RBGroupBy,
    ID_CBUseAntPath,
    ID_CBHeatMapTimeLine,
    ID_CBHomeMarker,
    ID_LISTHeatMapTimeStep,
    ID_TEXTGEDCOMinput,
    ID_TEXTResult,
    ID_RBResultHTML,
    ID_TEXTMain,
    ID_TEXTName,
    ID_INTMaxMissing,
    ID_INTMaxLineWeight,
    ID_CBUseGPS,
    ID_CBCacheOnly,
    ID_CBAllEntities,
    ID_LISTPlaceType,
    ID_CBMapControl,
    ID_CBMapMini,
    ID_BTNLoad,
    ID_BTNUpdate,
    ID_BTNCSV,
    ID_BTNSTOP,
    ID_BTNBROWSER
 ] = wx.NewIdRef(29)


IDtoAttr = {ID_CBMarksOn : ('MarksOn', 'Redraw'), 
    ID_CBHeatMap    : ('HeatMap', ''),
    ID_CBBornMark   : ('BornMark', 'Redraw'), 
    ID_CBDieMark    : ('DieMark', 'Redraw'),
    ID_LISTMapStyle : ('MapStyle', ''),
    ID_CBMarkStarOn : ('MarkStarOn', 'Redraw'),
    ID_RBGroupBy  : ('GroupBy', 'Redraw'),
    ID_CBUseAntPath : ('UseAntPath', 'Redraw'),
    ID_CBHeatMapTimeLine : ('HeatMapTimeLine', 'Redraw'),
    ID_CBHomeMarker : ('HomeMarker', 'Redraw'),
    ID_LISTHeatMapTimeStep : ('HeatMapTimeLine', 'Redraw'),
    ID_TEXTGEDCOMinput : ('GEDCOMinput', 'Reload'),
    ID_TEXTResult : ('Result', 'Redraw'),
    ID_RBResultHTML : ('ResultHTML',  'Redraw'),
    ID_TEXTMain : ('Main',  'Reload'),
    ID_TEXTName : ('Name',  ''),
    ID_INTMaxMissing : ('MaxMissing', 'Reload'),
    ID_INTMaxLineWeight : ('MaxMissing', 'Reload'),
    ID_CBUseGPS : ('UseGPS', 'Reload'),
    ID_CBCacheOnly : ('CacheOnly', 'Reload'),
    ID_CBAllEntities: ('AllEntities', 'Redraw'),
    ID_LISTPlaceType : ('PlaceType', 'Redraw'),
    ID_CBMapControl : ('showLayerControl',  'Redraw'),
    ID_CBMapMini : ('mapMini',  'Redraw'),
    ID_BTNLoad : 'Load',
    ID_BTNUpdate : 'Update',
    ID_BTNCSV : 'OpenCSV',
    ID_BTNSTOP: "Stop",
    ID_BTNBROWSER: "OpenBrowser"}

# This creates a new Event class and a EVT binder function
(UpdateBackgroundEvent, EVT_UPDATE_STATE) = wx.lib.newevent.NewEvent()

from wx.lib.embeddedimage import PyEmbeddedImage
SmallUpArrow = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABHNCSVQICAgIfAhkiAAAADxJ"
    b"REFUOI1jZGRiZqAEMFGke2gY8P/f3/9kGwDTjM8QnAaga8JlCG3CAJdt2MQxDCAUaOjyjKMp"
    b"cRAYAABS2CPsss3BWQAAAABJRU5ErkJggg==")

#----------------------------------------------------------------------
SmallDnArrow = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABHNCSVQICAgIfAhkiAAAAEhJ"
    b"REFUOI1jZGRiZqAEMFGke9QABgYGBgYWdIH///7+J6SJkYmZEacLkCUJacZqAD5DsInTLhDR"
    b"bcPlKrwugGnCFy6Mo3mBAQChDgRlP4RC7wAAAABJRU5ErkJggg==")


class Ids():
    def __init__(self):
        self.CLR_BTN_PRESS = wx.Colour(255, 230, 200, 255)
        self.CLR_BTN_DONE = wx.Colour(255, 255, 255, 255)
        pass


#=============================================================
class VisualMapFrame(wx.Frame):

    def __init__(self,  *args, **kw):
        # ensure the parent's __init__ is called so the wx.frame is created
        #
        super(VisualMapFrame, self).__init__(*args, **kw)

        self.SetMinSize((800,800))
        self.CreateStatusBar()
        self.SetStatusText("This is the statusbar")
        # create a menu bar
        self.makeMenuBar()
        # and a status bar
        self.SetStatusText("Visual Mapping ready")
        


    def makeMenuBar(self):
        """
        A menu bar is composed of menus, which are composed of menu items.
        This method builds a set of menus and binds handlers to be called
        when the menu item is selected.
        """
        
        # The "\t..." syntax defines an accelerator key that also triggers
        # Make the menu bar and add the two menus to it. The '&' defines
        # that the next letter is the "mnemonic" for the menu item. On the
        # platforms that support it those letters are underlined and can be
        # triggered from the keyboard.
        self.menuBar = menuBar = wx.MenuBar()
        self.fileMenu = fileMenu =  wx.Menu()
        fileMenu.Append(wx.ID_OPEN,    "&Open...\tCtrl-O", "Select a GEDCOM file")
        fileMenu.Append(wx.ID_CLOSE,   "&Close")
        # fileMenu.Append(wx.ID_SAVE,    "&Save")
        # fileMenu.Append(wx.ID_SAVEAS,  "Save &as...")
        # fileMenu.Enable(wx.ID_CLOSE, False)
        # fileMenu.Enable(wx.ID_SAVE, False)
        # fileMenu.Enable(wx.ID_SAVEAS, False)
        fileMenu.AppendSeparator()
        fileMenu.Append(wx.ID_EXIT)
        # and a file history
        self.filehistory = wx.FileHistory()
        self.filehistory.UseMenu(self.fileMenu)

        optionsMenu = wx.Menu()
        optionsMenu.Append(wx.ID_REVERT, "&Reset to Default")
        optionsMenu.Append(wx.ID_SETUP, "&Configuration")
        
        self.ActionMenu = ActionMenu =  wx.Menu()
        ActionMenu.Append(ID_BTNBROWSER,    "Open Result in &Browser")
        ActionMenu.Append(ID_BTNCSV, "Open &CSV")


        # Now a help menu for the about item
        helpMenu = wx.Menu()
        helpMenu.Append(wx.ID_ABOUT)

   

        menuBar.Append(self.fileMenu, "&File")
        menuBar.Append(ActionMenu, "&Actions")
        menuBar.Append(optionsMenu, "&Options")
        menuBar.Append(helpMenu, "&Help")

        # Give the menu bar to the frame
        self.SetMenuBar(menuBar)

        # Finally, associate a handler function with the EVT_MENU event for
        # each of the menu items. That means that when that menu item is
        # activated then the associated handler function will be called.
        
        self.Bind(wx.EVT_MENU, self.OnFileOpenDialog, id=wx.ID_OPEN)
        self.Bind(wx.EVT_MENU, self.OnExit,   id=wx.ID_EXIT)
        self.Bind(wx.EVT_MENU, self.OnAbout, id=wx.ID_ABOUT)
        self.Bind(wx.EVT_MENU_RANGE, self.OnFileHistory, id=wx.ID_FILE1, id2=wx.ID_FILE9)
        self.Bind(wx.EVT_MENU, self.onOptionsReset, id=wx.ID_REVERT)
        self.Bind(wx.EVT_MENU, self.onOptionsSetup, id=wx.ID_SETUP)
        self.Bind(wx.EVT_MENU, self.OnOpenCSV, id = ID_BTNCSV)
        self.Bind(wx.EVT_MENU, self.OnOpenBrowser, id = ID_BTNBROWSER)
    
        # More BIND below in main

        
        
    def OnExit(self, event):
        """Close the frame, terminating the application."""
        self.Close(True)

    def OnOpenCSV(self, event):
        panel.OpenCSV()
    def OnOpenBrowser(self, event):
        panel.OpenBrowser()

    
    def OnFileOpenDialog(self, evt):

        dDir = os.getcwd()
        if panel and panel.gO:
            infile = panel.gO.get('GEDCOMinput')
            if infile != '':
                dDir, filen  = os.path.split(infile)
        dlg = wx.FileDialog(self,
                           defaultDir = dDir,
                           wildcard = "GEDCOM source (*.ged)|*.ged|" \
                                      "All Files|*",
                           style = wx.FD_OPEN | wx.FD_CHANGE_DIR | wx.FD_FILE_MUST_EXIST)

        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            logger.debug("You selected %s", path)
            panel.setInputFile(path)

            # add it to the history
            self.filehistory.AddFileToHistory(path)
            self.filehistory.Save(panel.config)

        dlg.Destroy()

    def Cleanup(self, *args):
        # A little extra cleanup is required for the FileHistory control
        del self.filehistory
        self.menu.Destroy()

    def OnFileHistory(self, evt):

        # get the file based on the menu ID
        fileNum = evt.GetId() - wx.ID_FILE1
        path = self.filehistory.GetHistoryFile(fileNum)
        logger.debug("You selected %s", path)

        # add it back to the history so it will be moved up the list
        self.filehistory.AddFileToHistory(path)
        panel.setInputFile(path)

    def OnAbout(self, event):
        """Display an About Dialog"""
        wx.MessageBox("Visual GEDCOM mapping\n see Githib Repository\n\n https://github.com/D-Jeffrey/gedcom-to-visualmap",
                      "About gedcom-to-visualmap "+ VERSION,
                      wx.OK|wx.ICON_INFORMATION)


    
    def onOptionsReset(self, event):
        wx.MessageBox("Does nothing",
                      "reset options",
                      wx.OK|wx.ICON_INFORMATION)
        
    def onOptionsSetup(self, event):
        dialog = ConfigDialog(None, title='Configuration')
        result = dialog.ShowModal()
        if result == wx.ID_OK:
            logging_level = dialog.get_logging_level()
            logging.basicConfig(level=logging_level)
            logging.info('Logging level set to: %s', logging_level)
        dialog.Destroy()
        
#==============================================================
class ConfigDialog(wx.Dialog):
    
    def __init__(self, parent, title):
        wx.Dialog.__init__(self, parent, title=title)

        logging_level_choices = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        #TODO this does not work with getting the previous log level
        current_level = logging.getLevelName(logging.getLogger().getEffectiveLevel())
        self.radio_box = wx.RadioBox(self, label='Select Logging Level:', choices=logging_level_choices, majorDimension=5, style=wx.RA_SPECIFY_COLS)
        self.radio_box.SetStringSelection(current_level)

        ok_button = wx.Button(self, wx.ID_OK, label='OK')
        cancel_button = wx.Button(self, wx.ID_CANCEL, label='Cancel')

        button_box = wx.BoxSizer(wx.HORIZONTAL)
        button_box.Add(ok_button, 0, wx.ALL, 5)
        button_box.Add(cancel_button, 0, wx.ALL, 5)

        message = wx.StaticText(self, label='This does not work yet.  It does not correctly adjust the log level')
        message.SetForegroundColour(wx.Colour(255, 0, 0))

        main_box = wx.BoxSizer(wx.VERTICAL)
        main_box.Add(self.radio_box, 0, wx.ALL, 5)
        main_box.Add(message, 0, wx.ALIGN_CENTER|wx.ALL, 5)
        main_box.Add(button_box, 0, wx.ALIGN_CENTER|wx.ALL, 5)
        


        self.SetSizer(main_box)
        main_box.Fit(self)

    def get_logging_level(self):
        return self.radio_box.GetStringSelection()

        

#=============================================================
class PeopleListCtrl(wx.ListCtrl, listmix.ListCtrlAutoWidthMixin):
    def __init__(self, parent, ID, pos=wx.DefaultPosition,
                 size=wx.DefaultSize, style=0):
        wx.ListCtrl.__init__(self, parent, ID, pos, size, style)
        listmix.ListCtrlAutoWidthMixin.__init__(self)


class PeopleListCtrlPanel(wx.Panel, listmix.ColumnSorterMixin):
    def __init__(self, parent, humans):

        wx.Panel.__init__(self, parent, -1, style=wx.WANTS_CHARS)

        self.gO = None
        tID = wx.NewIdRef()

        sizer = wx.BoxSizer(wx.VERTICAL)
        self.InfoBox = wx.StaticText(parent, -1, "Select a file, Load it and Draw Update\nor change type to KML\nOpen Geo Table to edit addresses", size=wx.Size(500,2))
        self.InfoBox.SetFont(wx.FFont(10, wx.FONTFAMILY_SWISS ))
        sizer.Add(self.InfoBox, -1, wx.FIXED_MINSIZE | wx.LEFT)

        self.il = wx.ImageList(16, 16)
        
        self.sm_up = self.il.Add(SmallUpArrow.GetBitmap())
        self.sm_dn = self.il.Add(SmallDnArrow.GetBitmap())

        self.list = PeopleListCtrl(parent, tID,
                                 style=wx.LC_REPORT
                                 #| wx.BORDER_SUNKEN
                                 | wx.BORDER_NONE
                                 # | wx.LC_EDIT_LABELS
                                 #| wx.LC_SORT_ASCENDING    # disabling initial auto sort gives a
                                 #| wx.LC_NO_HEADER         # better illustration of col-click sorting
                                 # | wx.LC_VRULES
                                 # | wx.LC_HRULES
                                  | wx.LC_SINGLE_SEL
                                 ,size=wx.Size(600,600))

        self.list.SetImageList(self.il, wx.IMAGE_LIST_SMALL)
        sizer.Add(self.list, -1, wx.EXPAND)
        # self.list.EnableCheckBoxes(enable=False)

        # for normal, simple columns, you can add them like this:
        self.list.InsertColumn(0, "Name")
        self.list.InsertColumn(1, "Year", wx.LIST_FORMAT_RIGHT)
        self.list.InsertColumn(2, "ID")
        self.list.InsertColumn(3, "Geocode")
        self.list.InsertColumn(4, "Address")
        
        self.PopulateList(humans, None)
        self.currentItem = 0



        parent.SetSizer(sizer)
        # self.SetAutoLayout(True)

        parent.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self.OnItemRightClick, self.list)
        parent.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnItemActivated, self.list)
        parent.Bind(wx.EVT_LIST_COL_CLICK, self.OnColClick, self.list)
        #self.Bind(wx.EVT_LIST_COL_RIGHT_CLICK, self.OnColRightClick, self.list)
        parent.Bind(wx.EVT_LIST_COL_BEGIN_DRAG, self.OnColBeginDrag, self.list)
        parent.Bind(wx.EVT_LIST_COL_DRAGGING, self.OnColDragging, self.list)
        parent.Bind(wx.EVT_LIST_COL_END_DRAG, self.OnColEndDrag, self.list)
        # parent.Bind(wx.EVT_LIST_BEGIN_LABEL_EDIT, self.OnBeginEdit, self.list)
        # parent.Bind(wx.EVT_LIST_END_LABEL_EDIT, self.OnEndEdit, self.list)

        

    def setGOp(self, gOp):
        self.gO = gOp

    def OnUseNative(self, event):
        wx.SystemOptions.SetOption("mac.listctrl.always_use_generic", not event.IsChecked())
        wx.GetApp().GetTopWindow().LoadDemo("ListCtrl")

    def PopulateList(self, humans, mainperson):

        popdata = {}
        selectperson = 0
        i = 1
        for h in humans:
            if hasattr(humans[h], 'name'):
                d = humans[h].refyear()
                (location, where) = humans[h].bestlocation()
                    
                popdata[i] = (humans[h].name, d, humans[h].xref_id, location , where)
                if mainperson == humans[h].xref_id:
                    selectperson = i-1
                i += 1
        items = popdata.items()

        self.list.DeleteAllItems()
        for key, data in items:
            index = self.list.InsertItem(self.list.GetItemCount(), data[0]) # , self.idx1)
            self.list.SetItem(index, 1, data[1])
            self.list.SetItem(index, 2, data[2])
            self.list.SetItem(index, 3, data[3])
            self.list.SetItem(index, 4, data[4])
            self.list.SetItemData(index, key)
            if self.gO.Referenced:
                if self.gO.Referenced.exists(data[2]):
                    self.list.SetItemBackgroundColour(index, "LIME GREEN")


        self.list.SetColumnWidth(0, wx.LIST_AUTOSIZE_USEHEADER)
        self.list.SetColumnWidth(1, wx.LIST_AUTOSIZE_USEHEADER)
        self.list.SetColumnWidth(2, wx.LIST_AUTOSIZE_USEHEADER)
        self.list.SetColumnWidth(3, wx.LIST_AUTOSIZE_USEHEADER)
        self.list.SetColumnWidth(4, 60)

        # show how to select an item
   
               # Now that the list exists we can init the other base class,
        # see wx/lib/mixins/listctrl.py
        self.itemDataMap = popdata
        # Adjust Colums when adding colum
        listmix.ColumnSorterMixin.__init__(self, 5)
        #self.SortListItems(0, True)
        # self.list.CheckItem(item=selectperson, check=True)
        # NOTE: self.list can be empty (the global value, m, is empty and passed as humans).
        if 0 <= selectperson < self.list.GetItemCount():
            self.list.SetItemState(selectperson, wx.LIST_STATE_SELECTED, wx.LIST_STATE_SELECTED)

    # Used by the ColumnSorterMixin, see wx/lib/mixins/listctrl.py
    def GetListCtrl(self):
        return self.list

    # Used by the ColumnSorterMixin, see wx/lib/mixins/listctrl.py
    def GetSortImages(self):
        return (self.sm_dn, self.sm_up)

    def OnItemRightClick(self, event):

      
        self.currentItem = event.Index
        logger.debug("%s, %s, %s, %s", 
                           self.currentItem,
                            self.list.GetItemText(self.currentItem),
                            self.list.GetItemText(self.currentItem, 1),
                            self.list.GetItemText(self.currentItem, 2))
        if self.gO:
           self.gO.set('Main', self.list.GetItemText(self.currentItem, 2))
        event.Skip()
        
           

        dialog = PersonDialog(None, panel.threads[0].humans[self.list.GetItemText(self.currentItem, 2)])
        result = dialog.ShowModal()
        dialog.Destroy()

    def OnItemDeselected(self, event):

        item = event.GetItem()
        logger.debug("OnItemDeselected %d" % event.Index)

     
    def OnItemActivated(self, event):

        self.currentItem = event.Index
        logger.debug("%s TopItem: %s", self.list.GetItemText(self.currentItem), self.list.GetTopItem())
        if self.gO:
           self.gO.set('Main', self.list.GetItemText(self.currentItem, 2))

    def OnBeginEdit(self, event):

        logger.debug("")
        event.Allow()

    def OnEndEdit(self, event):

        logger.debug(event.GetText())
        event.Allow()

    def OnItemDelete(self, event):

        logger.debug("")

    def OnColClick(self, event):

        logger.debug("%s" % event.GetColumn())

        event.Skip()

    def OnColRightClick(self, event):

        item = self.list.GetColumn(event.GetColumn())
        logger.debug("%s %s", event.GetColumn(), (item.GetText(), item.GetAlign(), item.GetWidth(), item.GetImage()))
        if self.list.HasColumnOrderSupport():
            logger.debug("column order: %s", self.list.GetColumnOrder(event.GetColumn()))

    def OnColBeginDrag(self, event):

        logger.debug("")
        ## Show how to not allow a column to be resized
        #if event.GetColumn() == 0:
        #    event.Veto()

    def OnColDragging(self, event):

        logger.debug("")

    def OnColEndDrag(self, event):

        logger.debug("")

    

    def OnGetItemsChecked(self, event):

        itemcount = self.list.GetItemCount()
        itemschecked = [i for i in range(itemcount) if self.list.IsItemChecked(item=i)]
        logger.debug("%s ",  itemschecked)

    

        

m = {1: (),
     }

class VisualMapPanel(wx.Panel):
    """
    A Frame that says Visual Setup
    """

    def __init__(self,  *args, **kw):
        # ensure the parent's __init__ is called so the wx.frame is created
        #
        super(VisualMapPanel, self).__init__(*args, **kw)


        self.SetMinSize((800,800))
        self.frame = self.TopLevelParent        
        self.gO : gvOptions = None
        
        self.SetAutoLayout(True)
        
        
        # create a panel in the frame
        
        self.panelA = wx.Panel(self, -1, size=(760,420),style=wx.SIMPLE_BORDER  )
        # https://docs.wxpython.org/wx.ColourDatabase.html#wx-colourdatabase
        self.panelA.SetBackgroundColour(wx.TheColourDatabase.FindColour('GOLDENROD'))

        lc = wx.LayoutConstraints()
        lc.top.SameAs( self, wx.Top, 5)
        lc.left.SameAs( self, wx.Left, 5)
        lc.bottom.SameAs( self, wx.Bottom, 5)
        lc.right.PercentOf( self, wx.Right, 60)
        self.panelA.SetConstraints(lc)
        
        self.panelB = wx.Panel(self, -1, size=(760,420),style=wx.SIMPLE_BORDER  )
        self.panelB.SetBackgroundColour(wx.WHITE)
        lc = wx.LayoutConstraints()
        lc.top.SameAs( self, wx.Top, 5)
        lc.right.SameAs( self, wx.Right, 5)
        lc.bottom.SameAs( self, wx.Bottom, 5)
        lc.left.RightOf( self.panelA, 5)
        self.panelB.SetConstraints(lc)

        self.peopleList = PeopleListCtrlPanel(self.panelA, m)
                                              
        
        self.LayoutOptions(self.panelB)

        
        self.Layout()
    
   
   


    def LayoutOptions(self, panel):

        # Top of the Panel
        box = wx.BoxSizer(wx.VERTICAL)
        title = wx.StaticText(panel, -1, "Visual Mapping Options")#, (10, 10))
        title.SetFont(wx.FFont(16, wx.FONTFAMILY_SWISS, wx.FONTFLAG_BOLD))
        box.Add(title, 0, wx.ALIGN_CENTER|wx.ALL, 5)
        box.Add(wx.StaticLine(panel), 0, wx.EXPAND)
        self.d = Ids()
        
        txtinfile = wx.StaticText(panel, -1,  "Input file name:  ") 
        self.d.TEXTGEDCOMinput = wx.TextCtrl(panel, ID_TEXTGEDCOMinput, "", size=(200,20))
        self.d.TEXTGEDCOMinput.Enable(False) 
        txtoutfile = wx.StaticText(panel, -1, "Output file name: ")
        self.d.TEXTResult = wx.TextCtrl(panel, ID_TEXTResult, "")
        
        l1 = wx.BoxSizer(wx.HORIZONTAL)
        l1.AddMany([txtinfile,      (0,20),     self.d.TEXTGEDCOMinput])
        l2 = wx.BoxSizer(wx.HORIZONTAL)
        l2.AddMany([txtoutfile,     (0,20), self.d.TEXTResult])
        box.AddMany([l1, (4,4,), l2])

        # First select controls
        self.d.RBResultHTML =  wx.RadioBox(panel, ID_RBResultHTML, "Result Type", 
                                           choices = ['HTML', 'KML'] , majorDimension= 2)

        self.d.CBUseGPS = wx.CheckBox(panel, ID_CBUseGPS, "Use GPS lookup (uncheck if GPS is in file)")#,  wx.NO_BORDER)
        self.d.CBCacheOnly = wx.CheckBox(panel, ID_CBCacheOnly, "Cache Only, do not lookup addresses")#, , wx.NO_BORDER)
        self.d.CBAllEntities = wx.CheckBox(panel, ID_CBAllEntities, "Map all people")#, wx.NO_BORDER)
        self.d.ai = wx.ActivityIndicator(panel)
        
        
        box.AddMany( [ self.d.RBResultHTML,
                       self.d.CBUseGPS,
                       self.d.CBCacheOnly,
                       self.d.CBAllEntities])
                       
        #
        # HTML select controls in a Box
        #
        hbox = wx.StaticBox( panel, -1, "HTML Options")
        hTopBorder, hOtherBorder = hbox.GetBordersForSizer()
        hsizer = wx.BoxSizer(wx.VERTICAL)
        hsizer.AddSpacer(hTopBorder)
        hboxIn = wx.BoxSizer(wx.VERTICAL)
        self.d.CBMapControl = wx.CheckBox(hbox, ID_CBMapControl, "Open Map Controls",name='MapControl') 
        self.d.CBMapMini = wx.CheckBox(hbox, ID_CBMapMini, "Add Mini Map",name='MapMini') 
        self.d.CBMarksOn = wx.CheckBox(hbox, ID_CBMarksOn, "Markers",name='MarksOn')
        
        self.d.CBBornMark = wx.CheckBox(hbox, ID_CBBornMark, "Marker for when Born")
        self.d.CBDieMark = wx.CheckBox(hbox, ID_CBDieMark, "Marker for when Died")
        self.d.CBHomeMarker = wx.CheckBox(hbox, ID_CBHomeMarker, "Marker point or homes")
        self.d.CBMarkStarOn = wx.CheckBox(hbox, ID_CBMarkStarOn, "Marker starter with Star")
        
        self.d.CBHeatMap = wx.CheckBox(hbox, ID_CBHeatMap, "Heatmap", style = wx.NO_BORDER)
        self.d.CBHeatMapTimeLine = wx.CheckBox(hbox, ID_CBHeatMapTimeLine, "Heatmap Timeline")
        self.d.CBUseAntPath = wx.CheckBox(hbox, ID_CBUseAntPath, "Ant paths")
        
        TimeStepVal = 5
        self.d.LISTHeatMapTimeStep = wx.Slider(hbox, ID_LISTHeatMapTimeStep, TimeStepVal,1, 100, size=(250, -1),
                style=wx.SL_HORIZONTAL | wx.SL_AUTOTICKS | wx.SL_LABELS )
        self.d.LISTHeatMapTimeStep.SetTickFreq(5)
        self.d.RBGroupBy  = wx.RadioBox(hbox, ID_RBGroupBy, "Group by:", 
                                       choices = ['None', 'Last Name', 'Person'], majorDimension= 3)
        


        hboxIn.AddMany( [ 
                        self.d.RBGroupBy, 
                        self.d.CBMapControl,
                        self.d.CBMapMini,
                        self.d.CBMarksOn,
                        self.d.CBBornMark,
                        self.d.CBDieMark,
                        self.d.CBHomeMarker,
                        self.d.CBMarkStarOn,
                        self.d.CBUseAntPath,
                        self.d.CBHeatMap,
                        (0,5),
                        self.d.CBHeatMapTimeLine, 
                        (0,5),
                        self.d.LISTHeatMapTimeStep,
                        (0,5)
                         ])
        hsizer.Add( hboxIn, wx.EXPAND|wx.BOTTOM|wx.LEFT|wx.RIGHT, hOtherBorder+10)
        
        hbox.SetSizer(hsizer)
        self.hbox = hbox
        #
        # KML select controls in a Box
        #
        kbox = wx.StaticBox( panel, -1, "KML Options")
        kTopBorder, kOtherBorder = kbox.GetBordersForSizer()
        ksizer = wx.BoxSizer(wx.VERTICAL)
        ksizer.AddSpacer(kTopBorder)
        kboxIn = wx.BoxSizer(wx.VERTICAL)
        self.d.LISTPlaceType = wx.CheckListBox(kbox, ID_LISTPlaceType,  choices=['native','born','death'])
        kboxIn.AddMany( [self.d.LISTPlaceType])
        ksizer.Add( kboxIn, wx.EXPAND|wx.BOTTOM|wx.LEFT|wx.RIGHT, kOtherBorder+10)
        kbox.SetSizer(ksizer)
        self.kbox = kbox
        
        box.Add(hbox, 1, wx.EXPAND|wx.ALL, 15)
        box.Add(kbox, 1, wx.EXPAND|wx.ALL, 15)
        

        l1 = wx.BoxSizer(wx.HORIZONTAL)
        self.d.BTNLoad = wx.Button(panel, ID_BTNLoad, "Load")
        self.d.BTNUpdate = wx.Button(panel, ID_BTNUpdate, "Draw & Update")
        self.d.BTNCSV = wx.Button(panel, ID_BTNCSV, "Open Geo Table")
        self.d.BTNSTOP = wx.Button(panel, ID_BTNSTOP, "Stop")
        self.d.BTNBROWSER = wx.Button(panel, ID_BTNBROWSER, "Browser")
        l1.Add (self.d.BTNLoad, 0, wx.EXPAND | wx.ALL, 5)
        l1.Add (self.d.BTNUpdate, 0, wx.EXPAND | wx.ALL, 5)
        l1.Add (self.d.BTNCSV, 0, wx.EXPAND | wx.ALL, 5)
        box.Add(l1, 0, wx.EXPAND | wx.ALL,0)
        l1 = wx.BoxSizer(wx.HORIZONTAL)
        l1.Add (self.d.ai, 0, wx.EXPAND | wx.ALL | wx.RESERVE_SPACE_EVEN_IF_HIDDEN, 5)
        l1.Add (self.d.BTNSTOP, 0, wx.EXPAND | wx.LEFT, 30)
        l1.AddSpacer(20)
        l1.Add (self.d.BTNBROWSER, wx.EXPAND | wx.ALL, 5)
        l1.AddSpacer(30)
        box.Add((0,10))
        box.Add(l1, 0, wx.EXPAND | wx.ALL,0)
 
        """    
    ID_LISTMapStyle,
    
    ID_TEXTMain,
    ID_TEXTName,
    ID_INTMaxMissing,
    ID_INTMaxLineWeight,
        """
        
        # panel.SetSizeHints(box)
        panel.SetSizer(box)
        


        self.Bind(wx.EVT_RADIOBOX, self.EvtRadioBox, id = ID_RBResultHTML)
    
        self.Bind(wx.EVT_CHECKBOX, self.EvtCheckBox, id = ID_CBMapControl)
        self.Bind(wx.EVT_CHECKBOX, self.EvtCheckBox, id = ID_CBMapMini)
        self.Bind(wx.EVT_CHECKBOX, self.EvtCheckBox, id = ID_CBMarksOn)
        self.Bind(wx.EVT_CHECKBOX, self.EvtCheckBox, id = ID_CBBornMark)
        self.Bind(wx.EVT_CHECKBOX, self.EvtCheckBox, id = ID_CBDieMark)
        self.Bind(wx.EVT_CHECKBOX, self.EvtCheckBox, id = ID_CBHomeMarker)
        self.Bind(wx.EVT_CHECKBOX, self.EvtCheckBox, id = ID_CBMarkStarOn)
        self.Bind(wx.EVT_CHECKBOX, self.EvtCheckBox, id = ID_CBHeatMap)
        self.Bind(wx.EVT_CHECKBOX, self.EvtCheckBox, id = ID_CBHeatMapTimeLine)
        self.Bind(wx.EVT_CHECKBOX, self.EvtCheckBox, id = ID_CBUseAntPath)
        self.Bind(wx.EVT_CHECKBOX, self.EvtCheckBox, id = ID_CBUseGPS)
        self.Bind(wx.EVT_CHECKBOX, self.EvtCheckBox, id = ID_CBCacheOnly)
        self.Bind(wx.EVT_CHECKBOX, self.EvtCheckBox, id = ID_CBAllEntities)
        self.Bind(wx.EVT_CHECKLISTBOX, self.EvtListBox, id = ID_LISTPlaceType)
        self.Bind(wx.EVT_BUTTON, self.EvtButton, id = ID_BTNLoad)
        self.Bind(wx.EVT_BUTTON, self.EvtButton, id = ID_BTNUpdate)
        self.Bind(wx.EVT_BUTTON, self.EvtButton, id = ID_BTNCSV)
        self.Bind(wx.EVT_BUTTON, self.EvtButton, id = ID_BTNSTOP)
        self.Bind(wx.EVT_BUTTON, self.EvtButton, id = ID_BTNBROWSER)
        self.Bind(wx.EVT_TEXT, self.EvtText, id = ID_TEXTResult)
        self.OnBusyStop(-1)
        
        self.Bind(wx.EVT_RADIOBOX, self.EvtRadioBox, id = ID_RBGroupBy)
        self.Bind(wx.EVT_SLIDER, self.EvtSlider, id = ID_LISTHeatMapTimeStep)
        self.NeedReload()
        self.NeedRedraw()
        
        self.Bind(wx.EVT_CLOSE, self.OnCloseWindow)
        self.Bind(EVT_UPDATE_STATE, self.OnUpdate)
        
        self.threads = []
        self.threads.append(BackgroundActions(self, 0))
        
        for t in self.threads:
            t.Start()

        # Bind all EVT_TIMER events to self.OnMyTimer
        self.Bind(wx.EVT_TIMER, self.OnMyTimer)
        self.myTimer = wx.Timer(self)
        self.myTimer.Start(250)


    def NeedReload(self):
        if self.gO:
            self.gO.parsed= False
        self.d.BTNLoad.SetBackgroundColour(self.d.CLR_BTN_PRESS)
        self.NeedRedraw()

    def NeedRedraw(self):
        self.d.BTNUpdate.SetBackgroundColour(self.d.CLR_BTN_PRESS)
        pass

    def setInputFile(self, path):
            # set the state variables
            self.gO.setInput(path)
            d, filen = os.path.split(self.gO.get('GEDCOMinput'))
            # set the form field
            self.d.TEXTGEDCOMinput.SetValue(filen)
            self.config.Write("GEDCOMinput", path)
            #TODO Fix this
            self.gO.set('Main', None)
            #TODO Fix this
            self.NeedReload()

    def EvtRadioBox(self, event):

        logger.debug('%d is %d',  event.GetId(), event.GetInt())
        if event.GetId() == ID_RBResultHTML:
            self.gO.set('ResultHTML', event.GetInt() == 0)
            filename = self.gO.get('Result')
            newname = filename
            if self.gO.get('ResultHTML'):
                if '.kml' in filename.lower():
                    newname = self.gO.get('Result').replace('.kml', '.html', -1)
            else:
                if '.html' in filename.lower():
                    newname = self.gO.get('Result').replace('.html', '.kml', -1)
            if filename != newname:      
                self.gO.set('Result', newname)
                self.d.TEXTResult.SetValue(self.gO.get('Result'))

           
            self.SetupButtonState()
        elif event.GetId() ==  ID_RBGroupBy:
            self.gO.GroupBy = event.GetSelection()
        else:
            logger.debug.error('We have a Problem')
        

    def EvtText(self, event):

        if event.GetId() == ID_TEXTResult:
            event.GetString()
            self.gO.set('Result', event.GetString())
            logger.debug("Result %s", self.gO.get('Result') )
        else:
            logger.error("uncontrolled TEXT")

    def EvtCheckBox(self, event):

        logger.debug('%s for %i', event.IsChecked(), event.GetId() )
        cb = event.GetEventObject()
        if cb.Is3State():
            logger.debug("3StateValue: %s", cb.Get3StateValue())
        cbid = event.GetId()
        logger.debug('set %s to %s (%s)', IDtoAttr[cbid][0], cb.GetValue(), IDtoAttr[cbid][1] )
        panel.gO.set(IDtoAttr[cbid][0], cb.GetValue())
        if cbid == ID_CBHeatMap or cbid == ID_CBHeatMapTimeLine or cbid == ID_CBMarksOn:
            self.SetupButtonState()
        if (IDtoAttr[cbid][1] == 'Redraw'):
            self.NeedRedraw()
        elif (IDtoAttr[cbid][1] == 'Reload'):
            self.NeedReload()
        elif (IDtoAttr[cbid][1] == ''):
            pass # Nothing to do for this one
        else:
            logger.error("uncontrolled CB %d with '%s'", cbid,  IDtoAttr[cbid][1])
        if cbid == ID_CBAllEntities and cb.GetValue():
            dlg = None
            # TODO Fix this up
            if hasattr(self.threads[0], 'humans') and self.threads[0].humans:
                if len(self.threads[0].humans) > 200:
                    dlg = wx.MessageDialog(self, f'Caution, {len(self.threads[0].humans)} people in your tree\n it may create very large HTML files and may not open in the browser',
                               'Warning', wx.OK | wx.ICON_WARNING)
            else:
                dlg = wx.MessageDialog(self, 'Caution, if you load a GEDCOM with lots of people in your tree\n it may create very large HTML files and may not open in the browser',
                               'Warning', wx.OK | wx.ICON_WARNING)

            if dlg:                    
                dlg.ShowModal()
                dlg.Destroy()


    def EvtButton(self, event):
        id = event.GetId() 
        logger.debug("Click! (%d)", id)
        if id == ID_BTNLoad:
            self.LoadGEDCOM()
                
        elif id == ID_BTNUpdate:
            self.DrawGEDCOM()
                                
        elif id == ID_BTNCSV:
            self.OpenCSV()
        elif id == ID_BTNSTOP:
            self.gO.set('stopping', True)
            self.gO.set('parsed', False)
            self.NeedRedraw()
            self.NeedReload()
        elif id == ID_BTNBROWSER:
            self.OpenBrowser()
        else:
            logger.error("uncontrolled ID")
    

    def EvtListBox(self, event):

        eventid = event.GetId()
        logger.debug('%s, %s, %s', event.GetString(), event.IsSelection(), event.GetSelection())                            
        lb = event.GetEventObject()
        if eventid ==  ID_LISTPlaceType:
            places = {}
            for cstr in event.EventObject.CheckedStrings:
                places[cstr] = cstr
            if places == {}:
                places = {'native':'native'}
            panel.gO.PlaceType = places
        else:
            logger.error ("Uncontrol LISTbox")
    

    def EvtSlider(self, event):

        logger.debug('%s', event.GetSelection())
        panel.gO.HeatMapTimeStep = event.GetSelection()

    def OnMyTimer(self, evt):

        status = ''
        if self.gO:
            if self.gO.ShouldStop() or not self.gO.running:
                self.d.BTNSTOP.Disable()
            else:
                self.d.BTNSTOP.Enable()
            status = self.gO.state
            if self.gO.running:
                status = status + ' - Processing'
            if self.gO.counter > 0:
                status = status + ' : ' + str(panel.gO.counter)
                if panel.gO.stepinfo:
                    status = status + ' (' + panel.gO.stepinfo +')'
            if self.gO.ShouldStop():
                    self.d.BTNUpdate.Enable()
                    status = status + ' - please wait.. Stopping'

            mydir, filen = os.path.split(panel.gO.get('GEDCOMinput'))
            if filen == "":
                self.d.BTNLoad.Disable()
                self.d.BTNUpdate.Disable()

            else:
                self.d.BTNLoad.Enable()
                self.d.BTNUpdate.Enable()
            if self.gO.get('gpsfile') == '':
                self.d.BTNCSV.Disable()
            else:
                self.d.BTNCSV.Enable()
        if not status or status == '':
            status = 'Ready'
            self.OnBusyStop(-1)
        self.frame.SetStatusText(status)
        
        wx.Yield()
        

    def OnBusyStart(self, evt):
        self.d.ai.Start()
        self.d.ai.Show()
            
    def OnBusyStop(self, evt):
        self.d.ai.Stop()
        self.d.ai.Hide()

    def OnUpdate(self, evt):
        # proces evt state hand off
        if self.threads[0].updategrid:
            self.threads[0].updategrid = False
            self.peopleList.PopulateList(self.threads[0].humans, self.gO.get('Main'))
        if self.threads[0].updateinfo:
            messages = self.peopleList.InfoBox.GetLabel()
            logger.debug("Infobox: %s", self.threads[0].updateinfo)
            lines = messages.split("\n")
            if len(lines) > 15:
                messages = "\n".join(lines[:15])
            self.peopleList.InfoBox.SetLabel(self.threads[0].updateinfo + '\n' + messages)

            self.threads[0].updateinfo = ''
    
    def SetupButtonState(self):
        ResultTypeHTML = self.gO.get('ResultHTML')
        # Always enabled
            # self.d.CBUseGPS
            # self.d.CBAllEntities
            # self.d.CBCacheOnly
            
        if ResultTypeHTML:
            # self.kbox.SetBackgroundColour((230, 230, 230, 255))
            # self.hbox.SetBackgroundColour((255, 255, 255, 255)) 
            for ctrl in list([self.d.CBMarksOn,
                self.d.CBMapControl,
                self.d.CBMapMini,
                self.d.CBBornMark,
                self.d.CBDieMark,
                self.d.CBHomeMarker,
                self.d.CBMarkStarOn,
                self.d.CBHeatMap,
                self.d.CBUseAntPath,
                self.d.RBGroupBy]):
                ctrl.Enable()
            self.d.LISTPlaceType.Disable()
            self.d.CBHeatMapTimeLine.Disable()
            self.d.LISTHeatMapTimeStep.Disable()
            if self.gO.get('HeatMap'):
                self.d.CBHeatMapTimeLine.Enable()
                if self.gO.get('HeatMapTimeLine'):    
                    self.d.LISTHeatMapTimeStep.Enable()
            if not self.gO.get('MarksOn'):
                self.d.CBBornMark.Disable()
                self.d.CBDieMark.Disable()
                self.d.CBHomeMarker.Disable()
                
        else:
            # self.kbox.SetBackgroundColour((255, 255, 255, 255)) 
            # self.hbox.SetBackgroundColour((230, 230, 230, 255))
            for ctrl in list([self.d.CBMarksOn, 
                self.d.CBMapControl,
                self.d.CBMapMini,
                self.d.CBBornMark,
                self.d.CBDieMark,
                self.d.CBHomeMarker,
                self.d.CBMarkStarOn,
                self.d.CBHeatMap,
                self.d.CBHeatMapTimeLine,
                self.d.CBUseAntPath,
                self.d.LISTHeatMapTimeStep,
                self.d.RBGroupBy]):
                ctrl.Disable()
            self.d.LISTPlaceType.Enable()

    def SetupOptions(self):

        self.config = wx.Config("gedcomVisualGUI")
        
        
        self.gO = gvOptions()
        self.gO.setstatic( self.config.Read("GEDCOMinput"), self.config.Read("Result"), True, None)

        self.peopleList.setGOp(self.gO)

        self.d.RBResultHTML.SetSelection(0 if self.gO.get('ResultHTML') else 1)
        
        self.d.CBMapControl.SetValue(self.gO.get('showLayerControl'))
        self.d.CBMapMini.SetValue(self.gO.get('mapMini'))
        self.d.CBMarksOn.SetValue(self.gO.get('MarksOn'))
        self.d.CBBornMark.SetValue(self.gO.get('BornMark'))
        self.d.CBDieMark.SetValue(self.gO.get('DieMark'))
        self.d.CBHomeMarker.SetValue(self.gO.get('HomeMarker'))
        self.d.CBMarkStarOn.SetValue(self.gO.get('MarkStarOn'))
        self.d.CBHeatMap.SetValue(self.gO.get('HeatMap'))
        self.d.CBHeatMapTimeLine.SetValue(self.gO.get('HeatMapTimeLine'))
        self.d.CBUseAntPath.SetValue(self.gO.get('UseAntPath'))
        self.d.CBUseGPS.SetValue(self.gO.get('UseGPS'))
        self.d.CBAllEntities.SetValue(self.gO.get('AllEntities'))
        self.d.CBCacheOnly.SetValue(self.gO.get('CacheOnly'))
        self.d.LISTHeatMapTimeStep.SetValue(self.gO.get('HeatMapTimeStep'))
                
        
        places = self.gO.get('PlaceType')
        self.d.LISTPlaceType.SetCheckedStrings(places)
        self.d.RBGroupBy.SetSelection(self.gO.get('GroupBy'))
        
        
        self.d.TEXTResult.SetValue(self.gO.get('Result'))

        mydir, filen = os.path.split(self.gO.get('GEDCOMinput'))
        self.d.TEXTGEDCOMinput.SetValue(filen)
        self.SetupButtonState()


        for t in self.threads:
            t.DefgOps(self.gO)
        
        

    def updateOptions(self):
        pass

    def LoadGEDCOM(self):
        self.OnBusyStart(-1)
        
        self.threads[0].Trigger(1)
        pass
    def DrawGEDCOM(self):
        self.OnBusyStart(-1)
      
        self.threads[0].Trigger(2 | 4)
        
        pass
    
    def OpenCSV(self):

        csvfile = self.gO.get('gpsfile')
        if csvfile and csvfile != '':
            if sys.platform == 'win32':
                os.startfile(csvfile)
            elif sys.platform == 'darwin':
                subprocess.run(['open', csvfile])
            else:
                logger.error("Error: Unsupported platform, can not open CSV file")

    def OpenBrowser(self):
        if self.gO.get('ResultHTML'):
            webbrowser.open(os.path.join(self.gO.resultpath, self.gO.Result), new = 0, autoraise = True)
        else:
            webbrowser.open(KMLMAPSURL, new = 0, autoraise = True)
#################################################
#TODO FIX ME UP            

    def open_html_file(html_path):
        # Open the HTML file in a new tab and store the web browser instance
        browser = webbrowser.get()
        browser_tab = browser.open_new_tab(html_path)
    
        # Wait for the page to load
        time.sleep(1)
    
        # Find the browser window that contains the tab and activate it
        for window in browser.windows():
            for tab in window.tabs:
                if tab == browser_tab:
                    window.activate()
                    break
            else:
                continue
            break
    
        # Reload the tab
        browser_tab.reload()
    def OnCloseWindow(self, evt):
        busy = wx.BusyInfo("One moment please, waiting for threads to die...")
        wx.Yield()

        for t in self.threads:
            t.Stop()

        running = 1

        while running:
            running = 0

            for t in self.threads:
                running = running + t.IsRunning()

            time.sleep(0.1)

        self.Destroy()
    #==============================================================



class PersonDialog(wx.Dialog):
    def __init__(self, parent, human):
        super().__init__(parent, title="Person Details", size=(400, 300))
        
        humans = panel.threads[0].humans
        # create the UI controls to display the person's data
        name_label = wx.StaticText(self, label="Name: ")
        father_label = wx.StaticText(self, label="Father: ")
        mother_label = wx.StaticText(self, label="Mother: ")
        birth_label = wx.StaticText(self, label="Birth: ")
        death_label = wx.StaticText(self, label="Death: ")
        sex_label = wx.StaticText(self, label="Sex: ")
        marriage_label = wx.StaticText(self, label="Marriages: ")
        home_label = wx.StaticText(self, label="Homes: ")

        self.name_textctrl = wx.TextCtrl(self, style=wx.TE_READONLY, size=(350,-1))
        self.father_textctrl = wx.TextCtrl(self, style=wx.TE_READONLY|wx.TE_MULTILINE)
        self.mother_textctrl = wx.TextCtrl(self, style=wx.TE_READONLY|wx.TE_MULTILINE)
        self.birth_textctrl = wx.TextCtrl(self, style=wx.TE_READONLY)
        self.death_textctrl = wx.TextCtrl(self, style=wx.TE_READONLY)
        self.sex_textctrl = wx.TextCtrl(self, style=wx.TE_READONLY)
        self.marriage_textctrl = wx.TextCtrl(self, style=wx.TE_READONLY|wx.TE_MULTILINE)
        self.home_textctrl = wx.TextCtrl(self, style=wx.TE_READONLY|wx.TE_MULTILINE)

        # layout the UI controls using a grid sizer
        
        sizer = wx.FlexGridSizer(cols=2, hgap=5, vgap=5)
        # sizer = wx.StaticBoxSizer(wx.VERTICAL, self, "Person Details")
        sizer.Add(name_label, 0, wx.LEFT|wx.TOP, border=5)
        sizer.Add(self.name_textctrl, 0, wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM, border=5)
        sizer.Add(father_label, 0, wx.LEFT|wx.TOP, border=5)
        sizer.Add(self.father_textctrl, 1, wx.EXPAND)
        sizer.Add(mother_label, 0, wx.LEFT|wx.TOP, border=5)
        sizer.Add(self.mother_textctrl, 1, wx.EXPAND)
        sizer.Add(birth_label, 0, wx.LEFT|wx.TOP, border=5)
        sizer.Add(self.birth_textctrl, 0, wx.EXPAND)
        sizer.Add(death_label, 0, wx.LEFT|wx.TOP, border=5)
        sizer.Add(self.death_textctrl, 0, wx.EXPAND)
        sizer.Add(sex_label, 0, wx.LEFT|wx.TOP, border=5)
        sizer.Add(self.sex_textctrl, 0, wx.EXPAND)
        sizer.Add(marriage_label, 0, wx.LEFT|wx.TOP, border=5)
        sizer.Add(self.marriage_textctrl, 1, wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM, border=5)
        sizer.Add(home_label, 0, wx.LEFT|wx.TOP, border=5)
        sizer.Add(self.home_textctrl, 1, wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM, border=5)
        # self.SetSizer(sizer)

        # set the person's data in the UI controls
        self.name_textctrl.SetValue(str(human.surname))
      
        self.father_textctrl.SetValue(str(humans[human.father].first + " " + str(humans[human.father].surname)) if human.father else "<none>")
        self.mother_textctrl.SetValue(str(humans[human.mother].first + " " + str(humans[human.mother].surname)) if human.mother else "<none>")
        self.birth_textctrl.SetValue(str(human.birth))
        self.death_textctrl.SetValue(str(human.death))
        self.sex_textctrl.SetValue(str(human.sex) if human.sex else "")
        self.marriage_textctrl.SetValue(str(human.marriage))
        self.home_textctrl.SetValue(str(human.home))

        # create the OK button
        ok_btn = wx.Button(self, wx.ID_OK)
        btn_sizer = wx.StdDialogButtonSizer()
        btn_sizer.AddButton(ok_btn)
        btn_sizer.Realize()
        sizer.Add(btn_sizer, flag=wx.ALIGN_CENTER|wx.BOTTOM, border=10)
        self.SetSizer(sizer)
        self.SetBackgroundColour(wx.TheColourDatabase.FindColour('WHITE'))
        self.Fit()


    


class BackgroundActions:
    def __init__(self, win, threadnum):
        self.win = win
        self.gOptions = None
        self.humans = None
        self.threadnum = threadnum
        self.updategrid = False
        self.updateinfo = ''

    def DefgOps(self, gOps):
        self.gOptions = gOps

    def Start(self):
        self.keepGoing = self.running = True
        
        self.do = 0
        _thread.start_new_thread(self.Run, ())

    def Stop(self):
        self.keepGoing = False

    def IsRunning(self):
        return self.running

    def Trigger(self, dolevel):
        if dolevel & 1 or dolevel & 4:
            panel.d.BTNLoad.SetBackgroundColour(panel.d.CLR_BTN_DONE)
        if dolevel & 2:
            panel.d.BTNUpdate.SetBackgroundColour(panel.d.CLR_BTN_DONE)
        self.do = dolevel
        
    def AddInfo(self, line, newline= True):
        if newline and self.updateinfo and self.updateinfo != '':
            self.updateinfo = self.updateinfo + "\n"
        self.updateinfo = self.updateinfo + line
        
    def Run(self):

        while self.keepGoing:
            # We communicate with the UI by sending events to it. There can be
            # no manipulation of UI objects from the worker thread.
            if self.do != 0:
                logger.info(f"triggered thread {self.do}")
                self.gOptions.stopping = False
                if self.do & 1 or (self.do & 4 and not self.gOptions.parsed):
                    logger.info("start ParseAndGPS")
                    if hasattr(self, 'humans'):
                        if self.humans:                            
                            del self.humans
                            self.gOptions.humans = None
                    logger.info("ParseAndGPS")
                    self.humans = ParseAndGPS(self.gOptions, 1)
                    self.updategrid = True
                    evt = UpdateBackgroundEvent(value='busy')
                    wx.PostEvent(self.win, evt)
                    time.sleep(0.25)
                    

                    logger.info("human count %d", len(self.humans))
                    self.humans = ParseAndGPS(self.gOptions, 2)
                    self.updategrid = True
                    
                    self.AddInfo(f"Loaded {len(self.humans)} people")
                    if self.gOptions.Main:
                        self.AddInfo(f" with '{self.gOptions.Main}' as starting person", False)
                    
                    
                if self.do & 2:
                    logger.info("start do 2")
                    if (self.gOptions.parsed):
                        logger.info("doHTML or doKML")
                        if (self.gOptions.ResultHTML):
                            doHTML(self.gOptions, self.humans)
                            self.AddInfo(f"HTML generated resulting in {self.gOptions.totalpeople} people")
                        else: 
                            doKML(self.gOptions, self.humans)
                    else:
                        logger.info("not parsed")
                    logger.info("done draw")
                    self.updategrid = True

                
                self.do = 0
                self.gOptions.stop()
                evt = UpdateBackgroundEvent(value='done')
                wx.PostEvent(self.win, evt)
                
            else:
                time.sleep(0.25)

        self.running = False





if __name__ == '__main__':
    # When this module is run (not imported) then create the app, the
    # frame, show it, and start the event loop.

    logging.config.dictConfig(LOG_CONFIG)

    logger.setLevel(logging.DEBUG)
    logger.info("Starting up %s %s", NAME, VERSION)
    app = wx.App()
    frm = VisualMapFrame(None, title='GEDCOM Visual Map', size=(800, 800), style = wx.DEFAULT_FRAME_STYLE)
    panel = VisualMapPanel(frm)
    panel.SetupOptions()
    frm.filehistory.Load(panel.config)
        
    frm.Show()
    app.MainLoop()
    logger.info('Finished')
    exit(0)