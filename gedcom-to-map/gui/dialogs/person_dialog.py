import logging
from io import BytesIO
from pathlib import Path
from typing import Optional

import requests
import wx

from geo_gedcom.person import Person
from geo_gedcom.life_event import LifeEvent
from ..widgets.ged_rec_display import GedRecordDialog
from ..panels.family_panel import FamilyPanel
from ..layout.font_manager import FontManager

_log = logging.getLogger(__name__.lower())

__all__ = ["PersonDialog"]


class PersonDialog(wx.Dialog):
    """Dialog displaying detailed information about a person from the GEDCOM data.

    Shows personal details (name, birth, death, marriages, homes), lineage to the
    selected main person, children, and an optional photo. Provides buttons to
    close the dialog or view the raw GEDCOM record.

    Attributes:
        font_manager (FontManager): Font configuration for the UI.
        person (Person): The person whose details are displayed.
        panel (wx.Panel): Parent panel (used to access actions and context).
        showreferences (bool): Whether to show lineage information.
        font_size (int): Base font size for text controls.
        people (dict): Dictionary of all people keyed by xref_id.
        svc_state (IState): Runtime state service for accessing people data.
        svc_config (IConfig): Configuration service.
        svc_progress (IProgressTracker): Progress tracking service.
    """

    def __init__(
        self,
        parent: wx.Window,
        person: Person,
        panel: wx.Panel,
        font_manager: "FontManager",
        *,
        svc_config: Optional["IConfig"] = None,
        svc_state: Optional["IState"] = None,
        svc_progress: Optional["IProgressTracker"] = None,
        showreferences: bool = True,
    ) -> None:
        """Initialize the PersonDialog.

        Args:
            parent: Parent wxPython window.
            person: Person object to display details for.
            panel: Parent panel reference for context and actions.
            font_manager: FontManager instance for font configuration.
            svc_config: Configuration service (IConfig). Defaults to panel.svc_config if not provided.
            svc_state: Runtime state service (IState). Defaults to panel.svc_state if not provided.
            svc_progress: Progress tracker service (IProgressTracker). Defaults to panel.svc_progress if not provided.
            showreferences: Whether to display lineage and reference information.
        """
        super().__init__(
            parent, title="Person Details", size=(600, 600), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )

        # Prefer provided services; else pick from panel if available
        self.svc_config: Optional["IConfig"] = (
            svc_config if svc_config is not None else getattr(panel, "svc_config", None)
        )
        self.svc_state: Optional["IState"] = svc_state if svc_state is not None else getattr(panel, "svc_state", None)
        self.svc_progress: Optional["IProgressTracker"] = (
            svc_progress if svc_progress is not None else getattr(panel, "svc_progress", None)
        )
        self.font_manager: "FontManager" = font_manager
        self.person: Person = person
        self.panel: wx.Panel = panel
        self.showreferences: bool = showreferences
        self.font_size: int = getattr(font_manager, "size", 12) if font_manager else 12
        # Prefer service-backed people, then panel.background_process
        ppl = getattr(self.svc_state, "people", None) if self.svc_state is not None else None
        if ppl is None and panel is not None:
            bp = getattr(panel, "background_process", None)
            ppl = getattr(bp, "people", None) if bp is not None else None
        self.people = ppl or {}

        self.lineage_panel: FamilyPanel = None
        self.spouses_panel: FamilyPanel = None
        self.children_panel: FamilyPanel = None

        self.build(panel, self.people, person)

        # Register with font_manager to receive updates
        if self.font_manager and hasattr(self.font_manager, "register_font_change_callback"):
            self.font_manager.register_font_change_callback(self.update_fonts)

        # Clean up on close - use EVT_WINDOW_DESTROY instead
        self.Bind(wx.EVT_WINDOW_DESTROY, self.on_destroy)

    def on_destroy(self, event):
        """Clean up when dialog closes."""
        # Unregister from font_manager (safe to call multiple times)
        if self.font_manager and hasattr(self.font_manager, "unregister_font_change_callback"):
            try:
                self.font_manager.unregister_font_change_callback(self.update_fonts)
            except Exception:
                pass  # Already unregistered or font_manager gone
        event.Skip()

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
        self.lineage_panel = self._add_lineage_details(panel, people, person)
        self.spouses_panel = self._add_spouses_details(people, person)
        self.children_panel = self._add_children_details(people, person)
        photo = self._add_photo(panel, person)
        button_sizer = self._add_buttons()

        if self.lineage_panel:
            sizer.Add(wx.StaticText(self, label="Lineage: "), 0, wx.LEFT | wx.TOP, border=5)
            sizer.Add(self.lineage_panel, 1, wx.EXPAND, border=5)

        if self.spouses_panel:
            sizer.Add(wx.StaticText(self, label="Spouses: "), 0, wx.LEFT | wx.TOP, border=5)
            sizer.Add(self.spouses_panel, 1, wx.EXPAND, border=5)

        if self.children_panel:
            sizer.Add(wx.StaticText(self, label="Children: "), 0, wx.LEFT | wx.TOP, border=5)
            sizer.Add(self.children_panel, 1, wx.EXPAND, border=5)

        mainSizer = wx.BoxSizer(wx.VERTICAL)
        if photo:
            wrapper = wx.BoxSizer(wx.HORIZONTAL)
            wrapper.Add(sizer, 1, wx.ALL | wx.EXPAND, border=5)
            wrapper.Add(photo, 0, wx.TOP, border=5)
            mainSizer.Add(wrapper, 1, wx.EXPAND | wx.ALL, border=5)
        else:
            mainSizer.Add(sizer, 1, wx.EXPAND | wx.ALL, border=5)

        mainSizer.Add(button_sizer, 0, wx.ALIGN_LEFT | wx.LEFT | wx.BOTTOM, border=10)

        self.SetSizer(mainSizer)

        self.update_fonts()

        # Don't force white background - let system handle it for dark mode support
        # self.SetBackgroundColour(wx.TheColourDatabase.FindColour('WHITE'))
        self.Fit()

    def update_fonts(self) -> None:
        """Update fonts of all dialog components based on the current font manager."""
        if self.font_manager:
            grid_font = self.font_manager.get_font()
            if grid_font:
                # self.SetFont(grid_font)
                self.font_manager.apply_current_font_recursive(self)
            if self.lineage_panel:
                if hasattr(self.lineage_panel, "update_fonts"):
                    self.lineage_panel.update_fonts(self.font_manager)
            if self.spouses_panel:
                if hasattr(self.spouses_panel, "update_fonts"):
                    self.spouses_panel.update_fonts(self.font_manager)
            if self.children_panel:
                if hasattr(self.children_panel, "update_fonts"):
                    self.children_panel.update_fonts(self.font_manager)

    def _get_marriages_list(self, people: dict, person: Person) -> str:
        """Return a newline-separated string listing all marriages for the person.

        Args:
            people: Dictionary of all people keyed by xref_id.
            person: Person object to display details for.

        Returns:
            Formatted string with one marriage per line (partner name + date/place).
            Returns empty string if no marriages.
        """
        marrying = []
        marriages = person.get_events("marriage") if person else []
        if marriages:
            for marriage in marriages:
                partner = marriage.partner(person)
                marriage_event = marriage.event if marriage else None
                if not marriage_event or not partner:
                    continue
                if marriage and partner:
                    try:
                        marrying.append(
                            f"{self.formatPersonName(people[partner.xref_id], False)}{marriage_event.event_str}"
                        )
                    except KeyError:
                        _log.debug("Marriage partner %s not in people dict", partner.xref_id)
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
        residence_events = person.get_events("residence") if person else []
        if residence_events:
            for homedesc in residence_events:
                homes.append(f"{homedesc.event_str}")
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

        issues = person.check_age_problems(people)  # List of age problem strings

        extras = ["Has military Service records."] if person.get_events("military") else []

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
            (
                {"wx_name": "issuesTextCtrl", "label": "Of Note:", "size": (-1, sizeAttr(issues))}
                if issues or extras
                else None
            ),
        ]

        # Layout the relative grid
        sizer = wx.FlexGridSizer(cols=2, hgap=5, vgap=5)

        # Create all TextCtrls
        for line in grid_details:
            if line:
                style = wx.TE_READONLY
                proportion = 0
                if line["label"] in ["Marriages:", "Homes:", "Of Note:"]:
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

        birth_event = person.get_event("birth")
        death_event = person.get_event("death")
        self.birthTextCtrl.SetValue(f"{birth_event.event_str}" if birth_event else "")
        if death_event and birth_event and getattr(death_event, "when", None) and getattr(birth_event, "when", None):
            age = (
                f"(age ~{person.age})"
                if hasattr(person, "age")
                else f"(age ~{death_event.date.year_num - birth_event.date.year_num})"
            )
        else:
            age = ""

        self.deathTextCtrl.SetValue(f"{death_event.event_str}" if death_event else "")
        sex = person.sex if person.sex else ""
        self.sexTextCtrl.SetValue(f"{sex} {age}")
        self.marriageTextCtrl.SetValue(marriages)

        if issues or extras:
            self.issuesTextCtrl.SetValue("\n".join(issues) + "\n".join(extras))

        self.homeTextCtrl.SetValue(homelist)
        # Make the homes row growable if it has multiple entries (find actual row index dynamically)
        home_row_idx = None
        for idx, line in enumerate(grid_details):
            if line and line["label"] == "Homes:":
                home_row_idx = idx
                break
        if home_row_idx is not None and homelist.count("\n") > 2:
            sizer.AddGrowableRow(home_row_idx)

        return sizer

    def _add_lineage_details(
        self, panel: wx.Panel, people: dict = None, person: Person = None
    ) -> wx.Panel | wx.StaticText | None:
        """Build lineage/family panel showing ancestry path to the selected main person."""
        if not people or not person:
            return None

        related = None
        panel_actions = getattr(panel, "actions", None)
        showreferences = getattr(self, "showreferences", True)

        # Use service-backed state only
        referenced = getattr(self.svc_state, "Referenced", None)
        if referenced and showreferences and getattr(referenced, "exists", None):
            if FamilyPanel and panel and referenced.exists(person.xref_id):
                if (
                    panel_actions
                    and getattr(panel_actions, "doTraceTo", None)
                    and self.svc_config
                    and self.svc_state
                    and self.svc_progress
                ):
                    heritageList = panel_actions.doTraceTo(self.svc_config, self.svc_state, self.svc_progress, person)
                    if heritageList:
                        heritageSet = {}
                        for heritageparent, heritageperson, hyear, hid in heritageList:
                            try:
                                p = people.get(hid)
                                if not p:
                                    continue
                                descript = f"{p.title}" if getattr(p, "title", None) else ""
                                birth_event = p.get_event("birth")
                                death_event = p.get_event("death")
                                birth_year = birth_event.date.year_num if birth_event else None
                                death_year = death_event.date.year_num if death_event else None
                                birth_place = getattr(birth_event, "place", None) if birth_event else None
                                heritageSet[hid] = (
                                    heritageperson,
                                    heritageparent,
                                    birth_year,
                                    death_year,
                                    birth_place,
                                    descript,
                                    hid,
                                )
                            except Exception:
                                _log.exception("Error building lineage entry for %s", hid)
                        related = FamilyPanel(self, heritageSet, isLineage=True, font_manager=self.font_manager)
            if not related:
                related = wx.StaticText(self, label="No lineage to selected main person")
        return related

    def _add_spouses_details(self, people: dict = None, person: Person = None):
        """Build spouses panel showing all spouses/partners of the person."""
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
                    birth_event = p.get_event("birth")
                    death_event = p.get_event("death")
                    birth_year = birth_event.date.year_num if birth_event else None
                    death_year = death_event.date.year_num if death_event else None
                    birth_place = getattr(birth_event, "place", None) if birth_event else None
                    try:
                        spouse_name = p.name if hasattr(p, "name") else ""
                    except Exception:
                        spouse_name = ""
                    spouseSet[hid] = (spouse_name, "", birth_year, death_year, birth_place, descript, hid)
                except Exception:
                    _log.exception("Error building spouse entry for %s", hid)
            if FamilyPanel:
                spousesize = FamilyPanel(self, spouseSet, isLineage=False, font_manager=self.font_manager)
            else:
                spousesize = wx.StaticText(self, label="Spouses panel unavailable")

        return spousesize

    def _add_children_details(self, people: dict = None, person: Person = None):
        """Build children panel showing all children of the person."""
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
                    birth_event = p.get_event("birth")
                    death_event = p.get_event("death")
                    birth_year = birth_event.date.year_num if birth_event else None
                    death_year = death_event.date.year_num if death_event else None
                    birth_place = getattr(birth_event, "place", None) if birth_event else None
                    try:
                        child_name = p.name if hasattr(p, "name") else ""
                    except Exception:
                        child_name = ""
                    childSet[hid] = (child_name, "", birth_year, death_year, birth_place, descript, hid)
                except Exception:
                    _log.exception("Error building child entry for %s", hid)
            if FamilyPanel:
                childsize = FamilyPanel(self, childSet, isLineage=False, font_manager=self.font_manager)
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
            if photourl.find("http") == 0:
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
                # Prefer service config GEDCOMinput only
                try:
                    if self.svc_config is not None:
                        infile = self.svc_config.get("GEDCOMinput")
                except Exception:
                    infile = None
                if infile is not None:
                    dDir = Path(infile).parent
                else:
                    dDir = Path.cwd()
                # Normalize photourl to handle Windows paths in GEDCOM files on Unix systems
                normalized_photourl = photourl.replace("\\", "/")
                image_content = (
                    Path(normalized_photourl) if Path(normalized_photourl).is_absolute() else dDir / normalized_photourl
                )
            if image_content:
                try:
                    # Check if file exists before trying to load (for Path objects)
                    if isinstance(image_content, Path):
                        if not image_content.exists():
                            _log.warning(f"Photo file not found for {photourl}:\n      File: {image_content}")
                            image = None
                            image_content = None

                    # Handle both BytesIO (HTTP) and Path (local file)
                    if image_content:
                        if isinstance(image_content, BytesIO):
                            image = wx.Image(image_content, wx.BITMAP_TYPE_ANY)
                        else:
                            image = wx.Image(str(image_content), wx.BITMAP_TYPE_ANY)
                except Exception as e:
                    _log.error(f"Error reading photo from {image_content}:\n      {e}")
                    image = None
            if image:
                maxPhotoWidth = 400
                maxPhotoHeight = 500
                if image.GetWidth() > maxPhotoWidth:
                    image.Rescale(maxPhotoWidth, int(image.GetHeight() * maxPhotoWidth / image.GetWidth()))
                if image.GetHeight() > maxPhotoHeight:
                    image.Rescale(int(image.GetWidth() * maxPhotoHeight / image.GetHeight()), maxPhotoHeight)
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
        # Pass both configuration and state services
        svc_config = getattr(self, "svc_config", None)
        svc_state = getattr(self, "svc_state", None)
        GedRecordDialog.show_gedpy_record_dialog(
            None,
            self.person.xref_id,
            title=f"Record of {self.person.name}",
            svc_config=svc_config,
            svc_state=svc_state,
        )

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
