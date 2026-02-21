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
        titleArea.SetBackgroundColour(vm_panel.color_manager.get_color("TITLE_BACK"))
        title = wx.StaticText(titleArea, label="Visual Mapping Options", style=wx.ALIGN_CENTER)
        try:
            if vm_panel.color_manager.has_color("TITLE_TEXT"):
                title.SetForegroundColour(vm_panel.color_manager.get_color("TITLE_TEXT"))
            elif vm_panel.color_manager.has_color("DIALOG_TEXT"):
                title.SetForegroundColour(vm_panel.color_manager.get_color("DIALOG_TEXT"))
        except Exception:
            _log.debug("Failed to apply title text color", exc_info=True)
        title.SetFont(titleFont)
        titleSizer = wx.BoxSizer(wx.HORIZONTAL)
        titleSizer.Add(title, 1, wx.ALIGN_CENTER)
        titleArea.SetSizer(titleSizer)

        sizer.Add(titleArea, 0, wx.EXPAND | wx.BOTTOM, 0)
        sizer.Add(wx.StaticLine(panel), 0, wx.EXPAND)

    @staticmethod
    def _add_file_controls(vm_panel: Any, panel: wx.Panel, sizer: wx.Sizer) -> None:
        """Create input/output file controls and add to sizer."""
        # Match bottom action-row button implementation exactly.
        force_custom = bool(vm_panel.color_manager and vm_panel.color_manager.use_custom_colors())
        button_color = "BTN_BACK" if force_custom else None

        # Create both buttons before text controls (critical for macOS GenButton rendering)
        btn_in = LayoutHelpers.add_button_with_id(
            vm_panel, panel, "txtinfile", "Input file:   ", color=button_color, force_custom=force_custom
        )
        btn_out = LayoutHelpers.add_button_with_id(
            vm_panel, panel, "txtoutfile", "Output file: ", color=button_color, force_custom=force_custom
        )

        # Create text controls after buttons
        txt_in = LayoutHelpers.add_textctrl_with_id(vm_panel, panel, "TEXTGEDCOMinput", size=(250, 20), enable=False)
        txt_out = LayoutHelpers.add_textctrl_with_id(vm_panel, panel, "TEXTResultFile", size=(250, 20))

        vm_panel.id.txtinfile.Bind(wx.EVT_LEFT_DOWN, vm_panel.frame.OnFileOpenDialog)
        vm_panel.id.txtoutfile.Bind(wx.EVT_LEFT_DOWN, vm_panel.frame.OnFileResultDialog)

        # Create horizontal layouts for button+textbox pairs
        input_row = wx.BoxSizer(wx.HORIZONTAL)
        input_row.Add(btn_in, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 2)
        input_row.Add(txt_in, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 2)
        sizer.Add(input_row, 0, wx.EXPAND | wx.ALL, 2)

        output_row = wx.BoxSizer(wx.HORIZONTAL)
        output_row.Add(btn_out, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 2)
        output_row.Add(txt_out, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 2)
        sizer.Add(output_row, 0, wx.EXPAND | wx.ALL, 2)

        # Deferred refresh for GenButtons (macOS rendering fix)
        def refresh_buttons():
            for btn in [btn_in, btn_out]:
                btn.Show(True)
                btn.Raise()
                btn.Refresh(True)
                btn.Update()
            panel.Layout()
            panel.Refresh()
            # Additional delayed refresh for stubborn buttons
            wx.CallLater(100, lambda: [btn_out.Refresh(True), btn_out.Update()])

        wx.CallAfter(refresh_buttons)

    @staticmethod
    def _add_basic_checks(vm_panel: Any, panel: wx.Panel, sizer: wx.Sizer) -> None:
        """Add the top-level checkbox controls and configuration button."""
        # Configuration button
        force_custom = bool(vm_panel.color_manager and vm_panel.color_manager.use_custom_colors())
        button_color = "BTN_BACK" if force_custom else None
        btn_config = LayoutHelpers.add_button_with_id(
            vm_panel,
            panel,
            "BTNConfig",
            "Configuration Options...",
            color=button_color,
            force_custom=force_custom,
        )
        sizer.Add(btn_config, 0, wx.ALL, 2)

        # Deferred refresh for GenButton (macOS rendering fix)
        def refresh_config():
            btn_config.Show(True)
            btn_config.Raise()
            btn_config.Refresh(True)
            btn_config.Update()
            panel.Layout()
            panel.Refresh()
            # Additional delayed refresh
            wx.CallLater(100, lambda: [btn_config.Refresh(True), btn_config.Update()])

        wx.CallAfter(refresh_config)

        # General Options section
        general_container = wx.Panel(panel)
        general_box = wx.StaticBox(general_container, -1, "General Options")
        general_sizer = wx.StaticBoxSizer(general_box, wx.VERTICAL)
        general_boxIn = wx.BoxSizer(wx.VERTICAL)

        cb_all_entities = LayoutHelpers.add_checkbox_with_id(
            vm_panel, general_container, "CBAllEntities", "Map all people"
        )

        general_boxIn.Add(cb_all_entities, 0, wx.ALL, 2)
        general_sizer.Add(general_boxIn, 0, wx.EXPAND | wx.ALL, 4)
        general_container.SetSizer(general_sizer)

        sizer.Add(general_container, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 5)

        # Result Type radio box (referenced later in _add_result_type_and_stack)
        LayoutHelpers.add_radio_box_with_id(
            vm_panel, panel, "RBResultType", "Result Type", ResultType.list_values(), majorDimension=5
        )

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

        mapchoices = sorted(vm_panel.svc_config.map_types)
        mapboxsizer = wx.BoxSizer(wx.HORIZONTAL)
        mapStyleLabel = wx.StaticText(hbox, -1, " Map Style")
        cb_marks_on = LayoutHelpers.add_checkbox_with_id(vm_panel, hbox_container, "CBMarksOn", "Markers")
        cb_home_marker = LayoutHelpers.add_checkbox_with_id(
            vm_panel, hbox_container, "CBHomeMarker", "Marker point or homes"
        )
        cb_mark_star_on = LayoutHelpers.add_checkbox_with_id(
            vm_panel, hbox_container, "CBMarkStarOn", "Marker starter with Star"
        )
        cb_map_time_line = LayoutHelpers.add_checkbox_with_id(vm_panel, hbox_container, "CBMapTimeLine", "Add Timeline")
        ch_map_style = LayoutHelpers.add_choice_with_id(vm_panel, hbox_container, "LISTMapStyle", choices=mapchoices)

        cb_map_control = LayoutHelpers.add_checkbox_with_id(
            vm_panel, hbox_container, "CBMapControl", "Open Map Controls"
        )
        cb_map_mini = LayoutHelpers.add_checkbox_with_id(vm_panel, hbox_container, "CBMapMini", "Add Mini Map")
        cb_heat_map = LayoutHelpers.add_checkbox_with_id(
            vm_panel, hbox_container, "CBHeatMap", "Select Heatmap", style=wx.NO_BORDER
        )
        cb_show_all_people = LayoutHelpers.add_checkbox_with_id(
            vm_panel, hbox_container, "CBShowAllPeople", "Select All"
        )
        cb_use_ant_path = LayoutHelpers.add_checkbox_with_id(vm_panel, hbox_container, "CBUseAntPath", "Ant paths")
        sl_heat_map_time_step = LayoutHelpers.add_slider_with_id(
            vm_panel, hbox_container, "LISTHeatMapTimeStep", value=5, min_val=1, max_val=100, tick_freq=5
        )
        rb_group_by = LayoutHelpers.add_radio_box_with_id(
            vm_panel,
            hbox_container,
            "RBGroupBy",
            "Group by:",
            choices=["None", "Last Name", "Last Name (Soundex)", "Person"],
            majorDimension=2,
        )
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
                (cb_show_all_people, 0, wx.ALL, 2),
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

        # Add marker checkboxes at the top
        cb_born_mark = LayoutHelpers.add_checkbox_with_id(
            vm_panel, kbox_container, "CBBornMark", "Marker for when Born"
        )
        cb_die_mark = LayoutHelpers.add_checkbox_with_id(vm_panel, kbox_container, "CBDieMark", "Marker for when Died")

        rb_kml_mode = LayoutHelpers.add_radio_box_with_id(
            vm_panel, kbox_container, "RBKMLMode", "Organize by:", choices=["None", "Folder"], majorDimension=2
        )

        cb_fly_to = LayoutHelpers.add_checkbox_with_id(vm_panel, kbox_container, "CBFlyTo", "FlyTo Balloon")

        # Max Line Weight control with label
        max_line_sizer = wx.BoxSizer(wx.HORIZONTAL)
        max_line_label = wx.StaticText(kbox_container, -1, "Max Line Weight")
        vm_panel.id.INTMaxLineWeight = wx.SpinCtrl(
            kbox_container, vm_panel.id.IDs["INTMaxLineWeight"], "", min=1, max=100, initial=20
        )
        max_line_sizer.Add(max_line_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        max_line_sizer.Add(vm_panel.id.INTMaxLineWeight, 0, wx.ALIGN_CENTER_VERTICAL)

        kboxIn.AddMany(
            [
                (cb_born_mark, 0, wx.ALL, 2),
                (cb_die_mark, 0, wx.ALL, 2),
                (rb_kml_mode, 0, wx.ALL, 2),
                (cb_fly_to, 0, wx.ALL, 2),
                (max_line_sizer, 0, wx.ALL, 2),
            ]
        )

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

        vm_panel.id.CBSummary = [
            LayoutHelpers.add_checkbox_with_id(vm_panel, sbox_container, "CBSummary0", "Open files after created"),
            LayoutHelpers.add_checkbox_with_id(vm_panel, sbox_container, "CBSummary1", "Places"),
            LayoutHelpers.add_checkbox_with_id(vm_panel, sbox_container, "CBSummary2", "People"),
            LayoutHelpers.add_checkbox_with_id(vm_panel, sbox_container, "CBSummary3", "Countries"),
            LayoutHelpers.add_checkbox_with_id(vm_panel, sbox_container, "CBSummary4", "Countries Grid"),
            LayoutHelpers.add_checkbox_with_id(vm_panel, sbox_container, "CBSummary5", "Geocode"),
            LayoutHelpers.add_checkbox_with_id(vm_panel, sbox_container, "CBSummary6", "Alternate Places"),
            LayoutHelpers.add_checkbox_with_id(vm_panel, sbox_container, "CBSummary7", "Enrichment Issues"),
            LayoutHelpers.add_checkbox_with_id(vm_panel, sbox_container, "CBSummary8", "Statistics Summary"),
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
        vm_panel.id.CBGridView = LayoutHelpers.add_checkbox_with_id(
            vm_panel, gbox_container, "CBGridView", "View Only Direct Ancestors"
        )
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
        force_custom = bool(vm_panel.color_manager and vm_panel.color_manager.use_custom_colors())
        bt_load = LayoutHelpers.add_button_with_id(
            vm_panel, panel, "BTNLoad", "Load", color="BTN_BACK", force_custom=force_custom
        )
        bt_create = LayoutHelpers.add_button_with_id(
            vm_panel, panel, "BTNCreateFiles", "Create Files", color="BTN_BACK", force_custom=force_custom
        )
        bt_csv = LayoutHelpers.add_button_with_id(
            vm_panel, panel, "BTNCSV", "Geo Table", color="BTN_BACK", force_custom=force_custom
        )
        bt_trace = LayoutHelpers.add_button_with_id(
            vm_panel, panel, "BTNTRACE", "Trace", color="BTN_BACK", force_custom=force_custom
        )

        l1 = wx.BoxSizer(wx.HORIZONTAL)
        l1.Add(bt_load, 0, wx.EXPAND | wx.ALL, 5)
        l1.Add(bt_create, 0, wx.EXPAND | wx.ALL, 5)
        l1.Add(bt_csv, 0, wx.EXPAND | wx.ALL, 5)
        l1.Add(bt_trace, 0, wx.EXPAND | wx.ALL, 5)
        sizer.Add(l1, 0, wx.EXPAND | wx.ALL, 0)

        busy_indicator = LayoutHelpers.add_busy_indicator(vm_panel, panel, "busyIndicator", color="BUSY_BACK")
        bt_stop = LayoutHelpers.add_button_with_id(
            vm_panel, panel, "BTNSTOP", "Stop", color="BTN_BACK", force_custom=force_custom
        )
        bt_browser = LayoutHelpers.add_button_with_id(
            vm_panel, panel, "BTNBROWSER", "Browser", color="BTN_BACK", force_custom=force_custom
        )

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
            "Input file:   ",
            "Output file: ",
            "Default Country:   ",
            "Default Country:",
            "Map Style",
            "HTML Options",
            "Create Files",
            "Geo Table",
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
