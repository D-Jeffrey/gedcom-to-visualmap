import logging
from io import BytesIO
from pathlib import Path

import requests
import wx

from models.Person import Person, LifeEvent
from gedcom.gedcomdate import CheckAge
from gedrecdisplay import show_gedpy_record_dialog
from .family_panel import FamilyPanel
from .gedcomvisual import doTraceTo

_log = logging.getLogger(__name__.lower())

__all__ = ['PersonDialog', 'formatPersonName']

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
    def __init__(self, parent, person: Person, panel, font_manager, gOp, showrefences=True):
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
        
        people = self.gOp.BackgroundProcess.people if self.gOp and getattr(self.gOp, "BackgroundProcess", None) else {}
        # Display the marriage information including the marriage location and date                
        marrying = []
        if person.marriages:
            for marry in person.marriages:
                if marry:
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
    
        self.nameTextCtrl.SetValue(formatPersonName(person))

        # Should be conditional
        self.titleTextCtrl.SetValue(person.title if person.title else "")

        if person.father:
            try:
                self.fatherTextCtrl.SetValue(formatPersonName(people[person.father]))
            except Exception:
                pass
        if person.mother:
            try:
                self.motherTextCtrl.SetValue(formatPersonName(people[person.mother]))
            except Exception:
                pass
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

        # lineage / family panel creation is deferred and imports FamilyPanel at runtime
        self.related = None
        if self.gOp and getattr(self.gOp, "Referenced", None) and showrefences:
            if FamilyPanel and panel and getattr(panel, "gOp", None) and panel.gOp.Referenced.exists(person.xref_id):
                if doTraceTo:
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
                        self.related = FamilyPanel(self, hertiageSet)
            if not self.related:
               self.related = wx.StaticText(self, label="No lineage to selected main person")
            
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
            childsize = None
            if FamilyPanel:
                childsize = FamilyPanel(self, childSet, isChildren=True)
            else:
                childsize = wx.StaticText(self, label="Children panel unavailable")
            # add to sizer
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
                infile = panel.gOp.get('GEDCOMinput') if panel and getattr(panel, "gOp", None) else None
                if infile is not None:
                    dDir =  Path(infile).parent
                else:
                    dDir = Path.cwd()
                image_content = Path(photourl) if Path(photourl).is_absolute() else dDir / photourl
            if image_content:
                try:
                    image = wx.Image(str(image_content), wx.BITMAP_TYPE_ANY)
                except Exception as e:
                    _log.error(f"Error reading photo {photourl}:\n      {e}")
                    image = None
            if image:
                maxPhotoWidth = 400
                maxPhotoHeight = 500
                if image.GetWidth() > maxPhotoWidth:
                    image.Rescale(maxPhotoWidth, int(image.GetHeight()*maxPhotoWidth/image.GetWidth()))
                if image.GetHeight() > maxPhotoHeight:
                    image.Rescale(int(image.GetWidth()*maxPhotoHeight/image.GetHeight()),maxPhotoHeight)
                self.photo = wx.StaticBitmap(self, bitmap=wx.Bitmap(image))

        mainSizer = wx.BoxSizer(wx.VERTICAL)
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
        ok_btn.Bind(wx.EVT_BUTTON, lambda evt: self.Close())
        btn_sizer.AddButton(ok_btn)

        self.person = person
        # BUG This BUTTON DOES NOT RENDER IN the Right spot
        btn2_sizer = wx.StdDialogButtonSizer()
        details_btn2 = wx.Button(self, -1, label="Record")
        details_btn2.Bind(wx.EVT_BUTTON, lambda evt: self._displayrecord())
        btn2_sizer.AddButton(details_btn2)

        btn_sizer.Realize()
        btn2_sizer.Realize()

        btn_box = wx.BoxSizer(wx.HORIZONTAL)
        btn_box.Add(btn_sizer, 0, wx.LEFT, 10)
        btn_box.Add(btn2_sizer, 0, wx.RIGHT)

        mainSizer.Add(btn_box, 0, wx.ALIGN_LEFT|wx.LEFT| wx.BOTTOM, border=10)

        self.SetSizer(mainSizer)
        self.SetBackgroundColour(wx.TheColourDatabase.FindColour('WHITE'))
        self.Fit()

    def _displayrecord(self):
        show_gedpy_record_dialog(None, self.person.xref_id, self.gOp, title=f"Record of {self.person.name}")