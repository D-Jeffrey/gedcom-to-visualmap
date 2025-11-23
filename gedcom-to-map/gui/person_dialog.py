import logging
from io import BytesIO
from pathlib import Path

import requests
import wx

from models.Person import Person, LifeEvent
from gedcom.gedcomdate import CheckAge
from gedrecdisplay import show_gedpy_record_dialog
from .family_panel import FamilyPanel
from gedcom_options import gvOptions
from style.stylemanager import FontManager

_log = logging.getLogger(__name__.lower())

__all__ = ['PersonDialog']

class PersonDialog(wx.Dialog):
    """Dialog displaying detailed information about a person from the GEDCOM data.
    
    Shows personal details (name, birth, death, marriages, homes), lineage to the
    selected main person, children, and an optional photo. Provides buttons to
    close the dialog or view the raw GEDCOM record.
    
    Attributes:
        gOp (gvOptions): Global options and settings.
        font_manager (FontManager): Font configuration for the UI.
        person (Person): The person whose details are displayed.
        panel (wx.Panel): Parent panel (used to access actions and context).
        showreferences (bool): Whether to show lineage information.
        font_size (int): Base font size for text controls.
        people (dict): Dictionary of all people keyed by xref_id.
    """

    def __init__(self, parent: wx.Window, person: Person, panel: wx.Panel, font_manager: FontManager, gOp: gvOptions, showreferences: bool = True):
        """Initialize the PersonDialog.
        
        Args:
            parent: Parent window.
            person: Person object to display details for.
            panel: Parent panel (provides access to gOp and actions).
            font_manager: FontManager instance for UI text sizing.
            gOp: Global options containing GEDCOM data and settings.
            showreferences: If True, display lineage/ancestry panel (default: True).
        
        Note:
            font_manager is required; ensures text sizing is consistent with the rest of the UI.
        """
        super().__init__(parent, title="Person Details", size=(600, 600), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        
        self.gOp = gOp
        self.font_manager = font_manager
        self.person = person
        self.panel = panel
        self.showreferences = showreferences
        self.font_size = getattr(font_manager, "size", 12) if font_manager else 12
        self.people = gOp.BackgroundProcess.people if gOp and getattr(gOp, "BackgroundProcess", None) else {}

        self.build(panel, self.people, person)

    def build(self, panel: wx.Panel, people: dict, person: Person):
        """Build and layout all dialog components.
        
        Creates person details grid, lineage panel, children panel, photo, and buttons.
        Arranges them in sizers and applies to the dialog.
        
        Args:
            panel: Parent panel (for context/actions).
            people: Dictionary of all people keyed by xref_id.
            person: Person object to display.
        """
        # Build person, lineage and children details sections
        sizer = self._add_person_details(people, person)
        lineage_sizer = self._add_lineage_details(panel, people, person)
        spouses_sizer = self._add_spouses_details(people, person)
        children_sizer = self._add_children_details(people, person)
        photo = self._add_photo(panel, person)
        button_sizer = self._add_buttons()

        if lineage_sizer:
            sizer.Add(wx.StaticText(self, label="Lineage: "), 0, wx.LEFT|wx.TOP, border=5)
            sizer.Add(lineage_sizer, 1, wx.EXPAND, border=5)

        if spouses_sizer:
            sizer.Add(wx.StaticText(self, label="Spouses: "), 0, wx.LEFT|wx.TOP, border=5)
            sizer.Add(spouses_sizer, 1, wx.EXPAND, border=5)

        if children_sizer:
             sizer.Add(wx.StaticText(self, label="Children: "), 0, wx.LEFT|wx.TOP, border=5)
             sizer.Add(children_sizer, 1, wx.EXPAND, border=5)

        mainSizer = wx.BoxSizer(wx.VERTICAL)
        if photo:
            wrapper = wx.BoxSizer(wx.HORIZONTAL)
            wrapper.Add(sizer, 1, wx.ALL|wx.EXPAND, border=5)
            wrapper.Add(photo, 0, wx.TOP, border=5)
            mainSizer.Add(wrapper, 1, wx.EXPAND| wx.ALL, border=5)
        else:
            mainSizer.Add(sizer, 1, wx.EXPAND| wx.ALL, border=5)
        
        mainSizer.Add(button_sizer, 0, wx.ALIGN_LEFT|wx.LEFT| wx.BOTTOM, border=10)

        self.SetSizer(mainSizer)
        self.SetBackgroundColour(wx.TheColourDatabase.FindColour('WHITE'))
        self.Fit()

    def _get_marriages_list(self, people: dict, person: Person) -> str:
        """Return a newline-separated string listing all marriages for the person.
        
        Args:
            people: Dictionary of all people keyed by xref_id.
            person: Person whose marriages to list.
        
        Returns:
            Formatted string with one marriage per line (partner name + date/place).
            Returns empty string if no marriages.
        """
        marrying = []
        if person.marriages:
            for marry in person.marriages:
                if marry and getattr(marry, 'record', None):
                    try:
                        marrying.append(f"{self.formatPersonName(people[marry.record.xref_id], False)}{marry.asEventstr()}")
                    except KeyError:
                        _log.debug("Marriage partner %s not in people dict", marry.record.xref_id)
                    except Exception:
                        _log.exception("Error formatting marriage for %s", person.xref_id)
        return "\n".join(marrying)
    
    def _get_homes_list(self, person: Person) -> str:
        """Return a newline-separated string listing all home/residence events.
        
        Args:
            person: Person whose home events to list.
        
        Returns:
            Formatted string with one home event per line (date + place).
            Returns empty string if no home events.
        """
        homes = []
        if person.home:
            for homedesc in person.home:
                homes.append(f"{LifeEvent.asEventstr(homedesc)}")
        return "\n".join(homes)
    
    def _add_person_details(self, people, person) -> wx.FlexGridSizer:
        """Build and populate the person detail grid (name, birth, death, etc.).
        
        Creates read-only TextCtrls for name, title, parents, birth, death, sex,
        marriages, homes, and age problems. Arranges them in a two-column FlexGridSizer.
        
        Args:
            people: Dictionary of all people keyed by xref_id.
            person: Person whose details to display.
        
        Returns:
            wx.FlexGridSizer containing all detail controls.
        """
        if not people or not person:
            _log.error("_add_person_details: missing people dict or person")
            return wx.FlexGridSizer(cols=2)
        
        def sizeAttr(attr, pad=1):
            return (min(len(attr), 3) + pad) * (self.font_size + 5) if attr else self.font_size

        marriages = self._get_marriages_list(people, person)
        homelist = self._get_homes_list(person)

        issues = CheckAge(people, person.xref_id)

        grid_details = [
            {"wx_name": "nameTextCtrl", "label": "Name:", "size": (550, -1)},
            {"wx_name": "titleTextCtrl", "label": "Title:"},
            {"wx_name": "fatherTextCtrl", "label": "Father:"},
            {"wx_name": "motherTextCtrl", "label": "Mother:"},
            {"wx_name": "birthTextCtrl", "label": "Birth:"},
            {"wx_name": "deathTextCtrl", "label": "Death:"},
            {"wx_name": "sexTextCtrl", "label": "Sex:"},
            {"wx_name": "marriageTextCtrl", "label": "Marriages:", "size": (-1, sizeAttr(marriages))},
            {"wx_name": "homeTextCtrl", "label": "Homes:", "size": (-1, sizeAttr(homelist))},
            {"wx_name": "issuesTextCtrl", "label": "Age Problems:", "size": (-1, sizeAttr(issues))} if issues else None,
        ]

        # Layout the relative grid
        sizer = wx.FlexGridSizer(cols=2, hgap=5, vgap=5)

        # Create all TextCtrls
        for line in grid_details:
            if line:
                style = wx.TE_READONLY
                proportion = 0
                if line["label"] in ["Marriages:", "Homes:", "Age Problems:"]:
                    style |= wx.TE_MULTILINE
                    proportion = 1
                sizer.Add(wx.StaticText(self, label=line["label"]), 0, wx.LEFT | wx.TOP, border=5)
                setattr(self, line["wx_name"], wx.TextCtrl(self, style=style, size=line.get("size", (-1, -1))))
                sizer.Add(getattr(self, line["wx_name"]), proportion, wx.EXPAND, border=5)

        if issues:
            self.issuesTextCtrl.SetBackgroundColour(wx.YELLOW)

        # Populate values
        self.nameTextCtrl.SetValue(self.formatPersonName(person))
        self.titleTextCtrl.SetValue(person.title if person.title else "")

        if person.father:
            try:
                self.fatherTextCtrl.SetValue(self.formatPersonName(people[person.father]))
            except KeyError:
                _log.debug("Father %s not in people dict", person.father)
            except Exception:
                _log.exception("Error setting father for %s", person.xref_id)

        if person.mother:
            try:
                self.motherTextCtrl.SetValue(self.formatPersonName(people[person.mother]))
            except KeyError:
                _log.debug("Mother %s not in people dict", person.mother)
            except Exception:
                _log.exception("Error setting mother for %s", person.xref_id)

        self.birthTextCtrl.SetValue(f"{person.birth.asEventstr()}" if person.birth else "")
        if person.death and person.birth and person.death.when and person.birth.when:
            age = f"(age ~{person.age})" if hasattr(person, "age") else f"(age ~{person.death.whenyearnum() - person.birth.whenyearnum()})"
        else:
            age = ""

        self.deathTextCtrl.SetValue(f"{LifeEvent.asEventstr(person.death)}" if person.death else "")
        sex = person.sex if person.sex else ""
        self.sexTextCtrl.SetValue(f"{sex} {age}")
        self.marriageTextCtrl.SetValue(marriages)

        if issues:
            self.issuesTextCtrl.SetValue("\n".join(issues))

        self.homeTextCtrl.SetValue(homelist)
        # Make the homes row growable if it has multiple entries (find actual row index dynamically)
        home_row_idx = None
        for idx, line in enumerate(grid_details):
            if line and line["label"] == "Homes:":
                home_row_idx = idx
                break
        if home_row_idx is not None and homelist.count('\n') > 2:
            sizer.AddGrowableRow(home_row_idx)

        return sizer

    def _add_lineage_details(self, panel: wx.Panel, people: dict = None, person: Person = None):
        """Build lineage/family panel showing ancestry path to the selected main person.
        
        Uses panel.actions.doTraceTo() to compute ancestry and displays it in a FamilyPanel.
        Only shown if showreferences=True and the person is referenced in the current map.
        
        Args:
            panel: Parent panel (provides access to gOp and actions).
            people: Dictionary of all people keyed by xref_id.
            person: Person whose lineage to display.
        
        Returns:
            FamilyPanel widget or wx.StaticText with message, or None if not applicable.
        """
        if not people or not person:
            return None
        
        related = None
        panel_actions = getattr(getattr(self.gOp, "panel", None), "actions", None)
        showreferences = getattr(self, "showreferences", True)
        
        referenced = getattr(self.gOp, "Referenced", None)
        if referenced and showreferences and getattr(referenced, "exists", None):
            if FamilyPanel and panel and getattr(panel, "gOp", None) and referenced.exists(person.xref_id):
                if panel_actions and getattr(panel_actions, "doTraceTo", None):
                    hertiageList = panel_actions.doTraceTo(panel.gOp, person)
                    if hertiageList:
                        hertiageSet = {}
                        for (hertiageparent, hertiageperson, hyear, hid) in hertiageList:
                            try:
                                p = people.get(hid)
                                if not p:
                                    continue
                                descript = f"{p.title}" if getattr(p, "title", None) else ""
                                birth_year = p.birth.whenyear() if getattr(p, "birth", None) else None
                                death_year = p.death.whenyear() if getattr(p, "death", None) else None
                                birth = getattr(p, "birth", None)
                                birth_place = getattr(birth, 'place', None) if birth else None
                                hertiageSet[hid] = (hertiageperson,
                                                    hertiageparent,
                                                    birth_year,
                                                    death_year,
                                                    birth_place,
                                                    descript,
                                                    hid)
                            except Exception:
                                _log.exception("Error building lineage entry for %s", hid)
                        related = FamilyPanel(self, hertiageSet, isLineage=True)
            if not related:
                related = wx.StaticText(self, label="No lineage to selected main person")
        return related

    def _add_spouses_details(self, people: dict = None, person: Person = None):
        """Build spouses panel showing all spouses/partners of the person.
        
        Creates a FamilyPanel displaying name, birth, death, and title for each spouse/partner.
        Uses person.partners list to identify all marriage partners.
        
        Args:
            people: Dictionary of all people keyed by xref_id.
            person: Person whose spouses to display.
        
        Returns:
            FamilyPanel widget or wx.StaticText fallback, or None if no spouses.
        """
        if not people or not person:
            return None
        
        spousesize = None
        if person.partners:
            spouseSet = {}
            for hid in person.partners:
                try:
                    p = people.get(hid)
                    if not p:
                        continue
                    descript = f"{p.title}" if getattr(p, "title", None) else ""
                    birth_year = p.birth.whenyear() if getattr(p, "birth", None) else None
                    death_year = p.death.whenyear() if getattr(p, "death", None) else None
                    birth = getattr(p, "birth", None)
                    birth_place = getattr(birth, 'place', None) if birth else None
                    # Person.name may be a property/method, handle both
                    try:
                        spouse_name = p.name if hasattr(p, "name") else ""
                    except Exception:
                        spouse_name = ""
                    spouseSet[hid] = (spouse_name,
                                     "",
                                     birth_year,
                                     death_year,
                                     birth_place,
                                     descript,
                                     hid)
                except Exception:
                    _log.exception("Error building spouse entry for %s", hid)
            if FamilyPanel:
                spousesize = FamilyPanel(self, spouseSet, isLineage=False)
            else:
                spousesize = wx.StaticText(self, label="Spouses panel unavailable")

        return spousesize
    
    def _add_children_details(self, people: dict = None, person: Person = None):
        """Build children panel showing all children of the person.
        
        Creates a FamilyPanel (in children mode) displaying name, birth, death, and
        title for each child.
        
        Args:
            people: Dictionary of all people keyed by xref_id.
            person: Person whose children to display.
        
        Returns:
            FamilyPanel widget or wx.StaticText fallback, or None if no children.
        """
        if not people or not person:
            return None
        
        childsize = None
        if person.children:
            childSet = {}
            for hid in person.children:
                try:
                    p = people.get(hid)
                    if not p:
                        continue
                    descript = f"{p.title}" if getattr(p, "title", None) else ""
                    birth_year = p.birth.whenyear() if getattr(p, "birth", None) else None
                    death_year = p.death.whenyear() if getattr(p, "death", None) else None
                    birth = getattr(p, "birth", None)
                    birth_place = getattr(birth, 'place', None) if birth else None
                    # Person.name may be a property/method, handle both
                    try:
                        child_name = p.name if hasattr(p, "name") else ""
                    except Exception:
                        child_name = ""
                    childSet[hid] = (child_name,
                                     "",
                                     birth_year,
                                     death_year,
                                     birth_place,
                                     descript,
                                     hid)
                except Exception:
                    _log.exception("Error building child entry for %s", hid)
            if FamilyPanel:
                childsize = FamilyPanel(self, childSet, isLineage=False)
            else:
                childsize = wx.StaticText(self, label="Children panel unavailable")

        return childsize
    
    def _add_photo(self, panel: wx.Panel, person: Person = None):
        """Fetch and display the person's photo if available.
        
        Supports both HTTP URLs and local file paths. Images are scaled to fit
        within 400x500 pixels.
        
        Args:
            panel: Parent panel (used to resolve relative photo paths).
            person: Person whose photo to display (uses person.photo URL/path).
        
        Returns:
            wx.StaticBitmap with the photo, or None if unavailable or error.
        """
        image = None
        image_content = None
        photo = None

        photourl = person.photo if person else None
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
                infile = None
                if panel and getattr(panel, "gOp", None):
                    try:
                        infile = panel.gOp.get('GEDCOMinput')
                    except Exception:
                        pass
                if infile is not None:
                    dDir =  Path(infile).parent
                else:
                    dDir = Path.cwd()
                image_content = Path(photourl) if Path(photourl).is_absolute() else dDir / photourl
            if image_content:
                try:
                    # Handle both BytesIO (HTTP) and Path (local file)
                    if isinstance(image_content, BytesIO):
                        image = wx.Image(image_content, wx.BITMAP_TYPE_ANY)
                    else:
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
                photo = wx.StaticBitmap(self, bitmap=wx.Bitmap(image))
        return photo

    def _add_buttons(self):
        """Create and bind OK and Record buttons.
        
        Returns:
            wx.BoxSizer containing OK and Record buttons arranged horizontally.
        """
        btn_ok = wx.Button(self, wx.ID_OK)
        btn_ok.Bind(wx.EVT_BUTTON, lambda evt: self.Close())

        btn_record = wx.Button(self, -1, label="Record")
        btn_record.Bind(wx.EVT_BUTTON, lambda evt: self._displayrecord())

        btn_box = wx.BoxSizer(wx.HORIZONTAL)
        btn_box.Add(btn_ok, 0, wx.RIGHT, border=10)
        btn_box.Add(btn_record, 0, wx.RIGHT, border=10)

        return btn_box
    
    def _displayrecord(self):
        """Display the raw GEDCOM record for the person in a separate dialog."""
        show_gedpy_record_dialog(None, self.person.xref_id, self.gOp, title=f"Record of {self.person.name}")

    def formatPersonName(self, person: Person, longForm=True):
        """Format a person's name for display.
        
        Args:
            person: Person whose name to format.
            longForm: If True, include maiden name and title (default: True).
        
        Returns:
            Formatted name string, or "<none>" if person is None.
        """
        if not person:
             return "<none>"
        
        if longForm:
            maidenname = f" ({person.maidenname})" if getattr(person, "maidenname", None) else ""
            title = f" - {person.title}" if getattr(person, "title", None) else ""
        else:
            maidenname = ""
            title = ""
        
        firstname = getattr(person, "firstname", "")
        surname = getattr(person, "surname", "")
        return f"{firstname} {surname}{maidenname}{title}".strip()