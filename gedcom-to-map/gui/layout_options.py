"""
layout_options.py

Contains LayoutOptions which encapsulates the large LayoutOptions UI building
logic previously located in VisualMapPanel.LayoutOptions.

API:
    LayoutOptions.build(vm_panel, panel)
        vm_panel: instance of VisualMapPanel (used for id, font_manager, gOp, etc)
        panel: the wx.Panel instance where options controls are created
"""
from typing import Any
import logging
import wx

_log = logging.getLogger(__name__.lower())

class LayoutOptions:
    """Helper to construct the options UI previously embedded in VisualMapPanel.

    The original large `LayoutOptions` function is decomposed into focused
    static helper methods to improve readability and enable targeted testing.
    """

    @staticmethod
    def build(vm_panel: Any, panel: wx.Panel) -> None:
        """Top-level builder: assemble the options UI into `panel` using vm_panel state."""
        box = wx.BoxSizer(wx.VERTICAL)

        LayoutOptions._add_title_area(vm_panel, panel, box)
        LayoutOptions._add_file_controls(vm_panel, panel, box)
        LayoutOptions._add_basic_checks(vm_panel, panel, box)
        LayoutOptions._add_html_options(vm_panel, panel, box)
        LayoutOptions._add_kml_options(vm_panel, panel, box)
        LayoutOptions._add_kml2_options(vm_panel, panel, box)
        LayoutOptions._add_summary_options(vm_panel, panel, box)
        LayoutOptions._add_grid_options(vm_panel, panel, box)
        LayoutOptions._add_result_type_and_stack(vm_panel, panel, box)
        LayoutOptions._add_buttons_row(vm_panel, panel, box)

        # Finalize layout, wire events and start background activity
        panel.SetSizer(box)
        # Note: binding and starting threads/timers is performed by the caller
        # after the handler is instantiated to avoid ordering/circular issues.
        # vm_panel.bind_events() and vm_panel.start_threads_and_timer() removed.
        panel.Layout()
        panel.Refresh()

    @staticmethod
    def _add_title_area(vm_panel: Any, panel: wx.Panel, sizer: wx.Sizer) -> None:
        """Create title bar area and add to the main sizer."""
        titleFont = vm_panel.font_manager.get_font(bold=True, size_delta=0)
        fh = titleFont.GetPixelSize()[1]
        titleArea = wx.Panel(panel, size=(-1, fh + 10))
        titleArea.SetBackgroundColour(vm_panel.id.GetColor("TITLE_BACK"))
        title = wx.StaticText(titleArea, label="Visual Mapping Options", style=wx.ALIGN_CENTER)
        title.SetFont(titleFont)
        titleSizer = wx.BoxSizer(wx.HORIZONTAL)
        titleSizer.Add(title, 1, wx.ALIGN_CENTER)
        titleArea.SetSizer(titleSizer)

        sizer.Add(titleArea, 0, wx.EXPAND | wx.BOTTOM, 0)
        sizer.Add(wx.StaticLine(panel), 0, wx.EXPAND)

    @staticmethod
    def _add_multi_horizontal_by_id(vm_panel: Any, sizer: wx.Sizer, id_name_list: list[str], spacer: int = 0) -> None:
        """Helper to add multiple controls in a horizontal box to the main sizer."""
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        for id_name in id_name_list:
            ctrl = getattr(vm_panel.id, id_name, None)
            if ctrl:
                hbox.Add(window=ctrl, proportion=0, flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL, border=2)
                if spacer > 0:
                    hbox.AddSpacer(spacer)
        return hbox

    #staticmethod
    def _add_button_with_id(vm_panel: Any, panel: wx.Panel, id_name: str, label: str = "", color: str = "BTN_DIRECTORY") -> wx.Button:
        """Create a button with the given id name and label, register it, and return it."""
        id = -1
        if id_name in vm_panel.id.IDs:
            id = vm_panel.id.IDs[id_name]
        btn = wx.Button(panel, id=id, label=label)
        if color:
            btn.SetBackgroundColour(vm_panel.id.GetColor(color))
        setattr(vm_panel.id, id_name, btn)
        return btn
    
    def _add_textctrl_with_id(vm_panel: Any, panel: wx.Panel, id_name: str, size: tuple[int, int] = (250, 20), enable: bool = True) -> wx.TextCtrl:
        """Create a TextCtrl with the given id name, register it, and return it."""
        id = -1
        if id_name in vm_panel.id.IDs:
            id = vm_panel.id.IDs[id_name]
        txt = wx.TextCtrl(panel, id=id, size=size)
        txt.Enable(enable)
        setattr(vm_panel.id, id_name, txt)
        return txt
    
    def _add_checkbox_with_id(vm_panel: Any, panel: wx.Panel, id_name: str, label: str) -> wx.CheckBox:
        """Create a CheckBox with the given id name and label, register it, and return it."""
        id = -1
        if id_name in vm_panel.id.IDs:
            id = vm_panel.id.IDs[id_name]
        cb = wx.CheckBox(panel, id=id, label=label)
        setattr(vm_panel.id, id_name, cb)
        return cb

    def _add_static_text_with_id(vm_panel: Any, panel: wx.Panel, id_name: str, label: str) -> wx.StaticText:
        """Create a StaticText with the given id name and label, register it, and return it."""
        id = -1
        if id_name in vm_panel.id.IDs:
            id = vm_panel.id.IDs[id_name]
        st = wx.StaticText(panel, id=id, label=label)
        setattr(vm_panel.id, id_name, st)
        return st

    def _add_radio_box_with_id(vm_panel: Any, panel: wx.Panel, id_name: str, label: str, choices: list[str], majorDimension: int = 1) -> wx.RadioBox:
        """Create a RadioBox with the given id name, label, and choices, register it, and return it."""
        id = -1
        if id_name in vm_panel.id.IDs:
            id = vm_panel.id.IDs[id_name]
        rb = wx.RadioBox(panel, id=id, label=label, choices=choices, majorDimension=majorDimension)
        setattr(vm_panel.id, id_name, rb)
        return rb
    
    def _add_many_to_sizer(vm_panel: Any, sizer: wx.Sizer, controls: list[Any]) -> None:
        """Add multiple controls to the given sizer."""
        sizer.AddMany(controls)

    def _add_busy_indicator(vm_panel: Any, panel: wx.Panel, name: str, color: str = "BUSY_BACK") -> None:
        """Create and add a busy indicator."""
        ai = wx.ActivityIndicator(panel)
        ai.SetBackgroundColour(vm_panel.id.GetColor("BUSY_BACK"))
        setattr(vm_panel.id, name, ai)
        return ai

    @staticmethod
    def _add_file_controls(vm_panel: Any, panel: wx.Panel, sizer: wx.Sizer) -> None:
        """Create input/output file controls and add to sizer."""
        LayoutOptions._add_button_with_id(vm_panel, panel, "txtinfile", "Input file:   ", "BTN_DIRECTORY")
        LayoutOptions._add_textctrl_with_id(vm_panel, panel, "TEXTGEDCOMinput", size=(250, 20), enable=False)
        LayoutOptions._add_button_with_id(vm_panel, panel, "txtoutfile", "Output file: ", "BTN_DIRECTORY")
        LayoutOptions._add_textctrl_with_id(vm_panel, panel, "TEXTResult", size=(250, 20))
        vm_panel.id.txtinfile.Bind(wx.EVT_LEFT_DOWN, vm_panel.frame.OnFileOpenDialog)
        vm_panel.id.txtoutfile.Bind(wx.EVT_LEFT_DOWN, vm_panel.frame.OnFileResultDialog)

        l1 = LayoutOptions._add_multi_horizontal_by_id(vm_panel, sizer, ["txtinfile", "TEXTGEDCOMinput"], spacer=6)
        l2 = LayoutOptions._add_multi_horizontal_by_id(vm_panel, sizer, ["txtoutfile", "TEXTResult"], spacer=6)
        sizer.Add(l1, proportion=0, flag=wx.EXPAND | wx.ALL, border=2)
        sizer.Add(l2, proportion=0, flag=wx.EXPAND | wx.ALL, border=2)

    @staticmethod
    def _add_basic_checks(vm_panel: Any, panel: wx.Panel, sizer: wx.Sizer) -> None:
        """Add the top-level checkbox controls (GPS, cache, defaults, entity flags)."""
        cb_use_gps = LayoutOptions._add_checkbox_with_id(vm_panel, panel, "CBUseGPS", "Lookup all address (ignore cache)")
        cb_cache_only = LayoutOptions._add_checkbox_with_id(vm_panel, panel, "CBCacheOnly", "Cache Only, do not lookup addresses")
        _ = LayoutOptions._add_static_text_with_id(vm_panel, panel, "labelDefCountry", "Default Country:   ")
        _ = LayoutOptions._add_textctrl_with_id(vm_panel, panel, "TEXTDefaultCountry", size=(250, 20))

        defCountryBox = LayoutOptions._add_multi_horizontal_by_id(vm_panel, sizer, ["labelDefCountry", "TEXTDefaultCountry"], spacer=6)

        cb_all_entities = LayoutOptions._add_checkbox_with_id(vm_panel, panel, "CBAllEntities", "Map all people")
        cb_born_mark = LayoutOptions._add_checkbox_with_id(vm_panel, panel, "CBBornMark", "Marker for when Born")
        cb_die_mark = LayoutOptions._add_checkbox_with_id(vm_panel, panel, "CBDieMark", "Marker for when Died")

        LayoutOptions._add_busy_indicator(vm_panel, panel, "busyIndicator", color="BUSY_BACK")
        LayoutOptions._add_radio_box_with_id(vm_panel, panel, "RBResultsType", "Result Type",
                                            vm_panel.gOp.ResultType.list_values(), majorDimension=5)

        LayoutOptions._add_many_to_sizer(vm_panel, sizer,
                                         [cb_use_gps, cb_cache_only, defCountryBox,
                                          cb_all_entities, cb_born_mark, cb_die_mark])

    @staticmethod
    def _add_html_options(vm_panel: Any, panel: wx.Panel, sizer: wx.Sizer) -> None:
        """Create and add the HTML-specific option group."""
        hbox_container = wx.Panel(panel)
        hbox = wx.StaticBox(hbox_container, -1, "HTML Options")
        hsizer = wx.StaticBoxSizer(hbox, wx.VERTICAL)
        hboxIn = wx.BoxSizer(wx.VERTICAL)

        mapchoices = sorted(vm_panel.id.AllMapTypes)
        mapboxsizer = wx.BoxSizer(wx.HORIZONTAL)
        mapStyleLabel = wx.StaticText(hbox, -1, " Map Style")
        # vm_panel.id.CBMarksOn = wx.CheckBox(hbox_container, vm_panel.id.IDs["CBMarksOn"], "Markers", name="MarksOn")
        cb_marks_on = LayoutOptions._add_checkbox_with_id(vm_panel, hbox_container, "CBMarksOn", "Markers")
        cb_home_marker = LayoutOptions._add_checkbox_with_id(vm_panel, hbox_container, "CBHomeMarker", "Marker point or homes")
        cb_mark_star_on = LayoutOptions._add_checkbox_with_id(vm_panel, hbox_container, "CBMarkStarOn", "Marker starter with Star")
        cb_map_time_line = LayoutOptions._add_checkbox_with_id(vm_panel, hbox_container, "CBMapTimeLine", "Add Timeline")
        vm_panel.id.LISTMapType = wx.Choice(hbox_container, vm_panel.id.IDs["LISTMapStyle"], name="MapStyle",
                                           choices=mapchoices)
        
        vm_panel.id.CBMapControl = wx.CheckBox(hbox_container, vm_panel.id.IDs["CBMapControl"], "Open Map Controls",
                                              name="MapControl")
        vm_panel.id.CBMapMini = wx.CheckBox(hbox_container, vm_panel.id.IDs["CBMapMini"], "Add Mini Map",
                                            name="MapMini")
        vm_panel.id.CBHeatMap = wx.CheckBox(hbox_container, vm_panel.id.IDs["CBHeatMap"], "Heatmap",
                                            style=wx.NO_BORDER)
        vm_panel.id.CBUseAntPath = wx.CheckBox(hbox_container, vm_panel.id.IDs["CBUseAntPath"], "Ant paths")
        TimeStepVal = 5
        vm_panel.id.LISTHeatMapTimeStep = wx.Slider(hbox_container, vm_panel.id.IDs["LISTHeatMapTimeStep"],
                                                    TimeStepVal, 1, 100, size=(250, 45),
                                                    style=wx.SL_HORIZONTAL | wx.SL_AUTOTICKS | wx.SL_LABELS)
        vm_panel.id.LISTHeatMapTimeStep.SetTickFreq(5)
        vm_panel.id.RBGroupBy = wx.RadioBox(hbox_container, vm_panel.id.IDs["RBGroupBy"], "Group by:",
                                           choices=["None", "Last Name", "Last Name (Soundex)", "Person"],
                                           majorDimension=2)
        mapboxsizer.Add(vm_panel.id.LISTMapType)
        mapboxsizer.Add(mapStyleLabel)

        hboxIn.AddMany(
            [
                (cb_marks_on, 0, wx.ALL, 2),
                (cb_home_marker, 0, wx.ALL, 2),
                (cb_mark_star_on, 0, wx.ALL, 2),
                (cb_map_time_line, 0, wx.ALL, 2),
                (vm_panel.id.RBGroupBy, 0, wx.ALL, 2),
                (mapboxsizer, 0, wx.EXPAND | wx.ALL, 4),
                (vm_panel.id.CBMapControl, 0, wx.ALL, 2),
                (vm_panel.id.CBMapMini, 0, wx.ALL, 2),
                (vm_panel.id.CBUseAntPath, 0, wx.ALL, 2),
                (vm_panel.id.CBHeatMap, 0, wx.ALL, 2),
                (vm_panel.id.LISTHeatMapTimeStep, 0, wx.EXPAND | wx.ALL, 4),
            ]
        )
        hsizer.Add(hboxIn, 0, wx.EXPAND | wx.ALL, 4)
        hbox_container.SetSizer(hsizer)
        vm_panel.optionHbox = hbox_container

    @staticmethod
    def _add_kml_options(vm_panel: Any, panel: wx.Panel, sizer: wx.Sizer) -> None:
        """Create and add the KML options group."""
        kbox_container = wx.Panel(panel)
        kbox = wx.StaticBox(kbox_container, -1, "KML Options")
        ksizer = wx.StaticBoxSizer(kbox, wx.VERTICAL)
        kboxIn = wx.BoxSizer(wx.VERTICAL)

        vm_panel.id.RBKMLMode = wx.RadioBox(kbox, vm_panel.id.IDs["RBKMLMode"], "Organize by:",
                                           choices=["None", "Folder"], majorDimension=2)

        kboxs = [vm_panel.id.RBKMLMode, wx.BoxSizer(wx.HORIZONTAL), (4, 4), wx.BoxSizer(wx.HORIZONTAL)]
        vm_panel.id.CBFlyTo = wx.CheckBox(kbox, vm_panel.id.IDs["CBFlyTo"], "FlyTo Balloon", style=wx.NO_BORDER)
        vm_panel.id.INTMaxLineWeight = wx.SpinCtrl(kbox, vm_panel.id.IDs["INTMaxLineWeight"], "",
                                                     min=1, max=100, initial=20)

        kboxs[1].AddMany([wx.StaticText(kbox, -1, "        "), vm_panel.id.CBFlyTo])
        kboxs[3].AddMany([vm_panel.id.INTMaxLineWeight, wx.StaticText(kbox, -1, " Max Line Weight")])
        kboxIn.AddMany(kboxs)

        ksizer.Add(kboxIn, 0, wx.EXPAND | wx.ALL, 4)
        kbox_container.SetSizer(ksizer)
        vm_panel.optionKbox = kbox_container

    @staticmethod
    def _add_kml2_options(vm_panel: Any, panel: wx.Panel, sizer: wx.Sizer) -> None:
        """Create the KML2 option group (placeholder for future controls)."""
        k2box_container = wx.Panel(panel)
        k2box = wx.StaticBox(k2box_container, -1, "KML2 Options")
        k2sizer = wx.StaticBoxSizer(k2box, wx.VERTICAL)
        k2boxIn = wx.BoxSizer(wx.VERTICAL)
        k2sizer.Add(k2boxIn, 0, wx.EXPAND | wx.ALL, 4)
        k2box_container.SetSizer(k2sizer)
        vm_panel.optionK2box = k2box_container

    @staticmethod
    def _add_summary_options(vm_panel: Any, panel: wx.Panel, sizer: wx.Sizer) -> None:
        """Create and add the summary options group (multiple checkboxes)."""
        sbox_container = wx.Panel(panel)
        sbox = wx.StaticBox(sbox_container, -1, "Summary Options")
        ssizer = wx.StaticBoxSizer(sbox, wx.VERTICAL)
        sboxIn = wx.BoxSizer(wx.VERTICAL)

        # Parent controls to the container panel (not to the StaticBox object)
        vm_panel.id.CBSummary = [
            wx.CheckBox(sbox_container, vm_panel.id.IDs["CBSummary0"], label="Open files after created", name="Open"),
            wx.CheckBox(sbox_container, vm_panel.id.IDs["CBSummary1"], label="Places", name="Places"),
            wx.CheckBox(sbox_container, vm_panel.id.IDs["CBSummary2"], label="People", name="People"),
            wx.CheckBox(sbox_container, vm_panel.id.IDs["CBSummary3"], label="Countries", name="Countries"),
            wx.CheckBox(sbox_container, vm_panel.id.IDs["CBSummary4"], label="Countries Grid", name="CountriesGrid"),
            wx.CheckBox(sbox_container, vm_panel.id.IDs["CBSummary5"], label="Geocode", name="Geocode"),
            wx.CheckBox(sbox_container, vm_panel.id.IDs["CBSummary6"], label="Alternate Places", name="AltPlaces"),
        ]

        # Add with padding so the checkboxes are not flush against each other
        sboxIn.AddMany([(cb, 0, wx.ALL, 2) for cb in vm_panel.id.CBSummary])
        ssizer.Add(sboxIn, 0, wx.EXPAND | wx.ALL, 4)
        sbox_container.SetSizer(ssizer)
        vm_panel.optionSbox = sbox_container

    @staticmethod
    def _add_grid_options(vm_panel: Any, panel: wx.Panel, sizer: wx.Sizer) -> None:
        """Create and add grid view options."""
        # Use font height computed earlier via title font when available
        try:
            fh = vm_panel.font_manager.get_font(bold=True, size_delta=0).GetPixelSize()[1]
        except Exception:
            fh = 12
        gbox_min_height = max(40, int(fh * 4))
        gbox_container = wx.Panel(panel, size=(300, gbox_min_height))
        gbox = wx.StaticBox(gbox_container, -1, "Grid View Options")
        gsizer = wx.StaticBoxSizer(gbox, wx.VERTICAL)
        gboxIn = wx.BoxSizer(wx.VERTICAL)
        vm_panel.id.CBGridView = wx.CheckBox(gbox_container, vm_panel.id.IDs["CBGridView"], "View Only Direct Ancestors")
        gboxIn.AddMany([vm_panel.id.CBGridView])
        gsizer.Add(gboxIn, 0, wx.EXPAND | wx.ALL, 4)

        gbox_container.SetSizer(gsizer)
        vm_panel.optionGbox = gbox_container

    @staticmethod
    def _add_result_type_and_stack(vm_panel: Any, panel: wx.Panel, sizer: wx.Sizer) -> None:
        """Add result type radio and the options stack (HMTL/KML/KML2/Summary)."""
        vm_panel.optionsStack = wx.BoxSizer(wx.VERTICAL)
        vm_panel.optionsStack.Add(vm_panel.optionHbox, 1, wx.EXPAND)
        vm_panel.optionHbox.Hide()
        vm_panel.optionsStack.Add(vm_panel.optionKbox, 1, wx.EXPAND)
        vm_panel.optionKbox.Hide()
        vm_panel.optionsStack.Add(vm_panel.optionK2box, 1, wx.EXPAND)
        vm_panel.optionK2box.Hide()
        vm_panel.optionsStack.Add(vm_panel.optionSbox, 1, wx.EXPAND)
        vm_panel.optionSbox.Hide()

        sizer.Add(vm_panel.optionGbox, 0, wx.LEFT | wx.TOP, 5)
        sizer.AddMany([vm_panel.id.RBResultsType])
        sizer.Add(vm_panel.optionsStack, 1, wx.EXPAND | wx.ALL, 5)
        vm_panel.optionsStack.Layout()

    @staticmethod
    def _add_buttons_row(vm_panel: Any, panel: wx.Panel, sizer: wx.Sizer) -> None:
        """Create the action buttons row (Load, Create, CSV, Trace, Stop, Browser)."""
        l1 = wx.BoxSizer(wx.HORIZONTAL)
        vm_panel.id.BTNLoad = wx.Button(panel, vm_panel.id.IDs["BTNLoad"], "Load")
        vm_panel.id.BTNCreateFiles = wx.Button(panel, vm_panel.id.IDs["BTNCreateFiles"], "Create Files")
        vm_panel.id.BTNCSV = wx.Button(panel, vm_panel.id.IDs["BTNCSV"], "Geo Table")
        vm_panel.id.BTNTRACE = wx.Button(panel, vm_panel.id.IDs["BTNTRACE"], "Trace")
        vm_panel.id.BTNSTOP = wx.Button(panel, vm_panel.id.IDs["BTNSTOP"], "Stop")
        vm_panel.id.BTNBROWSER = wx.Button(panel, vm_panel.id.IDs["BTNBROWSER"], "Browser")
        l1.Add(vm_panel.id.BTNLoad, 0, wx.EXPAND | wx.ALL, 5)
        l1.Add(vm_panel.id.BTNCreateFiles, 0, wx.EXPAND | wx.ALL, 5)
        l1.Add(vm_panel.id.BTNCSV, 0, wx.EXPAND | wx.ALL, 5)
        l1.Add(vm_panel.id.BTNTRACE, 0, wx.EXPAND | wx.ALL, 5)
        sizer.Add(l1, 0, wx.EXPAND | wx.ALL, 0)

        l1 = wx.BoxSizer(wx.HORIZONTAL)
        l1.Add(vm_panel.id.busyIndicator, 0, wx.ALL | wx.RESERVE_SPACE_EVEN_IF_HIDDEN, 5)
        l1.Add(vm_panel.id.BTNSTOP, 0, wx.EXPAND | wx.LEFT, 20)
        l1.AddSpacer(20)
        l1.Add(vm_panel.id.BTNBROWSER, proportion=0, flag=wx.EXPAND | wx.ALL, border=5)
        l1.AddSpacer(20)
        sizer.Add((0, 10))
        sizer.Add(l1, 0, wx.EXPAND | wx.ALL, 0)

    @staticmethod
    def adjust_panel_width(vm_panel: Any) -> None:
        """
        Compute and apply a sensible minimum width for panel based on
        font metrics and representative control captions.
        """
        sample_texts = [
            "Input file:   ", "Output file: ", "Default Country:   ",
            "Default Country:", "Map Style", "HTML Options", "Create Files", "Geo Table"
        ]
        try:
            max_text_len = max(len(s) for s in sample_texts)
            text_px = vm_panel.font_manager.get_text_width(max_text_len)
        except Exception:
            # Fallback conservative estimate if font manager fails
            text_px = 300
        try:
            font_size = getattr(vm_panel, "font_size", 10) or 10
            extra_for_controls = int(220 + (font_size * 6))
            desired = max(300, text_px + extra_for_controls)
            vm_panel.panelB.SetMinSize((desired, -1))
            vm_panel.Layout()
            vm_panel.Refresh()
        except Exception:
            # best-effort only; errors should not crash UI build
            _log.debug("adjust_panel_width failed", exc_info=True)