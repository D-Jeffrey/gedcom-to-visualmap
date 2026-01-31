from render.result_type import ResultType
"""
layout_options.py

Contains LayoutOptions which encapsulates the large LayoutOptions UI building
logic previously located in VisualMapPanel.LayoutOptions.

API:
    LayoutOptions.build(vm_panel, panel)
        vm_panel: instance of VisualMapPanel (used for id, font_manager, services, etc)
        panel: the wx.Panel instance where options controls are created
"""
from typing import Any
import logging
import wx
from .layout_helpers import LayoutHelpers

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
    def _add_file_controls(vm_panel: Any, panel: wx.Panel, sizer: wx.Sizer) -> None:
        """Create input/output file controls and add to sizer."""
        LayoutHelpers.add_button_with_id(vm_panel, panel, "txtinfile", "Input file:   ", "BTN_DIRECTORY")
        LayoutHelpers.add_textctrl_with_id(vm_panel, panel, "TEXTGEDCOMinput", size=(250, 20), enable=False)
        LayoutHelpers.add_button_with_id(vm_panel, panel, "txtoutfile", "Output file: ", "BTN_DIRECTORY")
        LayoutHelpers.add_textctrl_with_id(vm_panel, panel, "TEXTResultFile", size=(250, 20))
        vm_panel.id.txtinfile.Bind(wx.EVT_LEFT_DOWN, vm_panel.frame.OnFileOpenDialog)
        vm_panel.id.txtoutfile.Bind(wx.EVT_LEFT_DOWN, vm_panel.frame.OnFileResultDialog)

        l1 = LayoutHelpers.add_multi_horizontal_by_id(vm_panel, ["txtinfile", "TEXTGEDCOMinput"], spacer=6)
        l2 = LayoutHelpers.add_multi_horizontal_by_id(vm_panel, ["txtoutfile", "TEXTResultFile"], spacer=6)
        sizer.Add(l1, proportion=0, flag=wx.EXPAND | wx.ALL, border=2)
        sizer.Add(l2, proportion=0, flag=wx.EXPAND | wx.ALL, border=2)

    @staticmethod
    def _add_basic_checks(vm_panel: Any, panel: wx.Panel, sizer: wx.Sizer) -> None:
        """Add the top-level checkbox controls (GPS, cache, defaults, entity flags)."""
        cb_use_gps = LayoutHelpers.add_checkbox_with_id(vm_panel, panel, "CBUseGPS", "Lookup all address (ignore cache)")
        cb_cache_only = LayoutHelpers.add_checkbox_with_id(vm_panel, panel, "CBCacheOnly", "Cache Only, do not lookup addresses")
        _ = LayoutHelpers.add_static_text_with_id(vm_panel, panel, "labelDefCountry", "Default Country:   ")
        _ = LayoutHelpers.add_textctrl_with_id(vm_panel, panel, "TEXTDefaultCountry", size=(250, 20))

        defCountryBox = LayoutHelpers.add_multi_horizontal_by_id(vm_panel, ["labelDefCountry", "TEXTDefaultCountry"], spacer=6)

        cb_all_entities = LayoutHelpers.add_checkbox_with_id(vm_panel, panel, "CBAllEntities", "Map all people")
        cb_born_mark = LayoutHelpers.add_checkbox_with_id(vm_panel, panel, "CBBornMark", "Marker for when Born")
        cb_die_mark = LayoutHelpers.add_checkbox_with_id(vm_panel, panel, "CBDieMark", "Marker for when Died")

        LayoutHelpers.add_radio_box_with_id(vm_panel, panel, "RBResultType", "Result Type",
                                           ResultType.list_values(), majorDimension=5)

        LayoutHelpers.add_many_to_sizer(sizer,
                                        [cb_use_gps, cb_cache_only, defCountryBox,
                                         cb_all_entities, cb_born_mark, cb_die_mark])

    @staticmethod
    def get_marks_controls_list(vm_panel: Any) -> list:
        """Return the list of marker-dependent controls for enabling/disabling."""
        return [
            vm_panel.id.CBBornMark,
            vm_panel.id.CBDieMark,
            vm_panel.id.CBHomeMarker,
            vm_panel.id.CBMarkStarOn,
        ]
    
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
        cb_marks_on = LayoutHelpers.add_checkbox_with_id(vm_panel, hbox_container, "CBMarksOn", "Markers")
        cb_home_marker = LayoutHelpers.add_checkbox_with_id(vm_panel, hbox_container, "CBHomeMarker", "Marker point or homes")
        cb_mark_star_on = LayoutHelpers.add_checkbox_with_id(vm_panel, hbox_container, "CBMarkStarOn", "Marker starter with Star")
        cb_map_time_line = LayoutHelpers.add_checkbox_with_id(vm_panel, hbox_container, "CBMapTimeLine", "Add Timeline")
        ch_map_style = LayoutHelpers.add_choice_with_id(vm_panel, hbox_container, "LISTMapStyle", choices=mapchoices)
        
        cb_map_control = LayoutHelpers.add_checkbox_with_id(vm_panel, hbox_container, "CBMapControl", "Open Map Controls")
        cb_map_mini = LayoutHelpers.add_checkbox_with_id(vm_panel, hbox_container, "CBMapMini", "Add Mini Map")
        cb_heat_map = LayoutHelpers.add_checkbox_with_id(vm_panel, hbox_container, "CBHeatMap", "Heatmap", style=wx.NO_BORDER)
        cb_use_ant_path = LayoutHelpers.add_checkbox_with_id(vm_panel, hbox_container, "CBUseAntPath", "Ant paths")
        sl_heat_map_time_step = LayoutHelpers.add_slider_with_id(vm_panel, hbox_container, "LISTHeatMapTimeStep", value=5, min_val=1, max_val=100, tick_freq=5)
        rb_group_by = LayoutHelpers.add_radio_box_with_id(vm_panel, hbox_container, "RBGroupBy", "Group by:",
                                                          choices=["None", "Last Name", "Last Name (Soundex)", "Person"],
                                                          majorDimension=2)
        mapboxsizer.Add(ch_map_style)
        mapboxsizer.Add(mapStyleLabel)

        hboxIn.AddMany(
            [
                (cb_marks_on, 0, wx.ALL, 2),
                (cb_home_marker, 0, wx.ALL, 2),
                (cb_mark_star_on, 0, wx.ALL, 2),
                (cb_map_time_line, 0, wx.ALL, 2),
                (rb_group_by, 0, wx.ALL, 2),
                (mapboxsizer, 0, wx.EXPAND | wx.ALL, 4),
                (cb_map_control, 0, wx.ALL, 2),
                (cb_map_mini, 0, wx.ALL, 2),
                (cb_use_ant_path, 0, wx.ALL, 2),
                (cb_heat_map, 0, wx.ALL, 2),
                (sl_heat_map_time_step, 0, wx.EXPAND | wx.ALL, 4),
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

        rb_kml_mode = LayoutHelpers.add_radio_box_with_id(vm_panel, kbox_container, "RBKMLMode", "Organize by:",
                                                          choices=["None", "Folder"], majorDimension=2)

        kboxs = [rb_kml_mode, wx.BoxSizer(wx.HORIZONTAL), (4, 4), wx.BoxSizer(wx.HORIZONTAL)]
        cb_fly_to = LayoutHelpers.add_checkbox_with_id(vm_panel, kbox, "CBFlyTo", "FlyTo Balloon", style=wx.NO_BORDER)
        vm_panel.id.INTMaxLineWeight = wx.SpinCtrl(kbox, vm_panel.id.IDs["INTMaxLineWeight"], "",
                                                     min=1, max=100, initial=20)

        kboxs[1].AddMany([wx.StaticText(kbox, -1, "        "), cb_fly_to])
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
            wx.CheckBox(sbox_container, vm_panel.id.IDs["CBSummary7"], label="Enrichment Issues", name="EnrichmentIssues"),
            wx.CheckBox(sbox_container, vm_panel.id.IDs["CBSummary8"], label="Statistics Summary", name="StatisticsSummary"),
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
        sizer.AddMany([vm_panel.id.RBResultType])
        sizer.Add(vm_panel.optionsStack, 1, wx.EXPAND | wx.ALL, 5)
        vm_panel.optionsStack.Layout()

    @staticmethod
    def _add_buttons_row(vm_panel: Any, panel: wx.Panel, sizer: wx.Sizer) -> None:
        """Create the action buttons row (Load, Create, CSV, Trace, Stop, Browser)."""
        bt_load = LayoutHelpers.add_button_with_id(vm_panel, panel, "BTNLoad", "Load", color=None)
        bt_create = LayoutHelpers.add_button_with_id(vm_panel, panel, "BTNCreateFiles", "Create Files", color=None)
        bt_csv = LayoutHelpers.add_button_with_id(vm_panel, panel, "BTNCSV", "Geo Table", color=None)
        bt_trace = LayoutHelpers.add_button_with_id(vm_panel, panel, "BTNTRACE", "Trace", color=None)

        l1 = wx.BoxSizer(wx.HORIZONTAL)
        l1.Add(bt_load, 0, wx.EXPAND | wx.ALL, 5)
        l1.Add(bt_create, 0, wx.EXPAND | wx.ALL, 5)
        l1.Add(bt_csv, 0, wx.EXPAND | wx.ALL, 5)
        l1.Add(bt_trace, 0, wx.EXPAND | wx.ALL, 5)
        sizer.Add(l1, 0, wx.EXPAND | wx.ALL, 0)

        busy_indicator = LayoutHelpers.add_busy_indicator(vm_panel, panel, "busyIndicator", color="BUSY_BACK")
        bt_stop = LayoutHelpers.add_button_with_id(vm_panel, panel, "BTNSTOP", "Stop", color=None)
        bt_browser = LayoutHelpers.add_button_with_id(vm_panel, panel, "BTNBROWSER", "Browser", color=None)

        l2 = wx.BoxSizer(wx.HORIZONTAL)
        l2.Add(busy_indicator, 0, wx.ALL | wx.RESERVE_SPACE_EVEN_IF_HIDDEN, 5)
        l2.Add(bt_stop, 0, wx.EXPAND | wx.LEFT, 20)
        l2.AddSpacer(20)
        l2.Add(bt_browser, proportion=0, flag=wx.EXPAND | wx.ALL, border=5)
        l2.AddSpacer(20)
        sizer.Add((0, 10))
        sizer.Add(l2, 0, wx.EXPAND | wx.ALL, 0)

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
