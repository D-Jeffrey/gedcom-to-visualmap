import logging
from typing import Any, List, Tuple
import wx
from wx.lib.buttons import GenButton, GenToggleButton
from wx.lib.checkbox import GenCheckBox

_log = logging.getLogger(__name__.lower())


class CustomRadioBox(wx.Panel):
    """Custom radio group that mimics wx.RadioBox API for selection/events."""

    def __init__(self, parent: wx.Window, id: int, label: str, choices: List[str], majorDimension: int = 1):
        super().__init__(parent, id=id)
        self._selection = 0
        self._option_buttons: list[GenToggleButton] = []

        outer = wx.BoxSizer(wx.VERTICAL)
        self._static_box = wx.StaticBox(self, label=label)
        box_sizer = wx.StaticBoxSizer(self._static_box, wx.VERTICAL)

        line = wx.BoxSizer(wx.HORIZONTAL)
        per_row = max(1, int(majorDimension or 1))

        for index, choice in enumerate(choices):
            btn = GenToggleButton(self, id=wx.ID_ANY, label=choice)
            btn.Bind(wx.EVT_BUTTON, self._on_radio_selected)
            self._option_buttons.append(btn)
            line.Add(btn, 0, wx.ALL, 2)

            if (index + 1) % per_row == 0 or index == len(choices) - 1:
                box_sizer.Add(line, 0, wx.EXPAND | wx.ALL, 2)
                line = wx.BoxSizer(wx.HORIZONTAL)

        outer.Add(box_sizer, 0, wx.EXPAND)
        self.SetSizer(outer)
        self.SetSelection(0)

    def _on_radio_selected(self, event: wx.CommandEvent) -> None:
        source = event.GetEventObject()
        for i, btn in enumerate(self._option_buttons):
            if btn is source:
                self._selection = i
                break

        self.SetSelection(self._selection)

        cmd = wx.CommandEvent(wx.EVT_RADIOBOX.typeId, self.GetId())
        cmd.SetInt(self._selection)
        cmd.SetEventObject(self)
        wx.PostEvent(self, cmd)
        event.Skip()

    def SetSelection(self, n: int) -> None:
        if not self._option_buttons:
            self._selection = 0
            return
        idx = max(0, min(int(n), len(self._option_buttons) - 1))
        self._selection = idx
        for i, btn in enumerate(self._option_buttons):
            btn.SetValue(i == idx)

    def GetSelection(self) -> int:
        return self._selection

    def Enable(self, enable: bool = True) -> bool:
        for btn in self._option_buttons:
            btn.Enable(enable)
        return super().Enable(enable)

    def SetForegroundColour(self, colour: wx.Colour) -> bool:
        ok = super().SetForegroundColour(colour)
        try:
            self._static_box.SetForegroundColour(colour)
            self._static_box.SetOwnForegroundColour(colour)
            self._static_box.Refresh()
        except Exception:
            pass
        try:
            self.SetOwnForegroundColour(colour)
        except Exception:
            pass
        for btn in self._option_buttons:
            btn.SetForegroundColour(colour)
            try:
                btn.SetOwnForegroundColour(colour)
            except Exception:
                pass
            try:
                btn.Refresh()
            except Exception:
                pass
        self.Refresh()
        return ok

    def SetBackgroundColour(self, colour: wx.Colour) -> bool:
        ok = super().SetBackgroundColour(colour)
        try:
            self._static_box.SetBackgroundColour(colour)
            self._static_box.SetOwnBackgroundColour(colour)
            self._static_box.Refresh()
        except Exception:
            pass
        try:
            self.SetOwnBackgroundColour(colour)
        except Exception:
            pass
        for btn in self._option_buttons:
            btn.SetBackgroundColour(colour)
            try:
                btn.SetOwnBackgroundColour(colour)
            except Exception:
                pass
            try:
                btn.Refresh()
            except Exception:
                pass
        self.Refresh()
        return ok


class LayoutHelpers:
    """Collection of small UI construction helpers moved out of layout_options."""

    @staticmethod
    def _apply_dialog_text_color(vm_panel: Any, ctrl: wx.Window) -> None:
        """Apply configured DIALOG_TEXT foreground color to a control if available."""
        try:
            color_manager = getattr(vm_panel, "color_manager", None)
            if color_manager and color_manager.has_color("DIALOG_TEXT"):
                color = color_manager.get_color("DIALOG_TEXT")
                ctrl.SetForegroundColour(color)
                # Use SetOwnForegroundColour for Windows compatibility
                if hasattr(ctrl, "SetOwnForegroundColour"):
                    ctrl.SetOwnForegroundColour(color)
        except Exception:
            _log.debug("_apply_dialog_text_color: failed for %s", type(ctrl).__name__)

    @staticmethod
    def _apply_choice_colors(vm_panel: Any, choice: wx.Choice, selected: bool = False) -> None:
        """Apply default/selected color styling to a wx.Choice when supported by platform."""
        try:
            color_manager = getattr(vm_panel, "color_manager", None)
            if not color_manager:
                return

            if selected:
                if color_manager.has_color("GRID_SELECTED_BACK"):
                    choice.SetBackgroundColour(color_manager.get_color("GRID_SELECTED_BACK"))
                elif color_manager.has_color("DIALOG_BACKGROUND"):
                    choice.SetBackgroundColour(color_manager.get_color("DIALOG_BACKGROUND"))

                if color_manager.has_color("GRID_SELECTED_TEXT"):
                    choice.SetForegroundColour(color_manager.get_color("GRID_SELECTED_TEXT"))
                elif color_manager.has_color("DIALOG_TEXT"):
                    choice.SetForegroundColour(color_manager.get_color("DIALOG_TEXT"))
            else:
                if color_manager.has_color("DIALOG_BACKGROUND"):
                    choice.SetBackgroundColour(color_manager.get_color("DIALOG_BACKGROUND"))
                if color_manager.has_color("DIALOG_TEXT"):
                    choice.SetForegroundColour(color_manager.get_color("DIALOG_TEXT"))
        except Exception:
            _log.debug("_apply_choice_colors: failed for %s", type(choice).__name__)

    @staticmethod
    def _bind_choice_selection_colors(vm_panel: Any, choice: wx.Choice) -> None:
        """Bind focus and selection events to keep wx.Choice colors consistent."""

        def _on_focus(event: wx.FocusEvent) -> None:
            LayoutHelpers._apply_choice_colors(vm_panel, choice, selected=True)
            event.Skip()

        def _on_blur(event: wx.FocusEvent) -> None:
            LayoutHelpers._apply_choice_colors(vm_panel, choice, selected=False)
            event.Skip()

        def _on_choice(event: wx.CommandEvent) -> None:
            LayoutHelpers._apply_choice_colors(vm_panel, choice, selected=True)
            event.Skip()

        choice.Bind(wx.EVT_SET_FOCUS, _on_focus)
        choice.Bind(wx.EVT_KILL_FOCUS, _on_blur)
        choice.Bind(wx.EVT_CHOICE, _on_choice)

    @staticmethod
    def add_multi_horizontal_by_id(vm_panel: Any, id_name_list: List[str], spacer: int = 0) -> wx.BoxSizer:
        """Create a horizontal sizer containing controls looked up on vm_panel.id by name."""
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        for id_name in id_name_list:
            ctrl = getattr(vm_panel.id, id_name, None)
            if ctrl:
                hbox.Add(window=ctrl, proportion=0, flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL, border=2)
                if spacer > 0:
                    hbox.AddSpacer(spacer)
            else:
                _log.warning(f"Control {id_name} not found in vm_panel.id")
        return hbox

    @staticmethod
    def add_button_with_id(
        vm_panel: Any,
        panel: wx.Panel,
        id_name: str,
        label: str = "",
        color: str = "BTN_BACK",
        force_custom: bool = False,
    ) -> wx.Window:
        id_ = -1
        if id_name in vm_panel.id.IDs:
            id_ = vm_panel.id.IDs[id_name]

        use_custom_colors = True
        try:
            if vm_panel.color_manager and hasattr(vm_panel.color_manager, "use_custom_colors"):
                use_custom_colors = bool(vm_panel.color_manager.use_custom_colors())
        except Exception:
            use_custom_colors = True

        if not use_custom_colors and not force_custom:
            btn = wx.Button(panel, id=id_, label=label)
            setattr(vm_panel.id, id_name, btn)
            return btn

        # Use native button for color=None to preserve platform-default contrast/styling
        # (important for key controls like Output file and Configuration Options).
        if color is None and not force_custom:
            btn = wx.Button(panel, id=id_, label=label)
            setattr(vm_panel.id, id_name, btn)
            return btn

        # Create generic custom-drawn button when explicit color theming is requested
        btn = GenButton(panel, id=id_, label=label)

        # Store color key for refresh_colors usage
        btn._color_key = color

        # Apply color BEFORE sizing to ensure proper rendering
        if color:
            try:
                btn_color = vm_panel.color_manager.get_color(color)
                btn.SetBackgroundColour(btn_color)
                # For GenButton, set explicit text color for contrast
                if vm_panel.color_manager.has_color("DIALOG_TEXT"):
                    text_color = vm_panel.color_manager.get_color("DIALOG_TEXT")
                    btn.SetForegroundColour(text_color)
            except Exception as e:
                _log.warning(f"add_button_with_id: Failed to set color for {id_name}/{color}: {e}")
        else:
            try:
                if vm_panel.color_manager and vm_panel.color_manager.has_color("DIALOG_BACKGROUND"):
                    btn.SetBackgroundColour(vm_panel.color_manager.get_color("DIALOG_BACKGROUND"))
            except Exception:
                pass
            LayoutHelpers._apply_dialog_text_color(vm_panel, btn)

        # Configure GenButton appearance and ensure it calculates proper size
        btn.SetBezelWidth(1)
        btn.SetUseFocusIndicator(False)
        btn.SetInitialSize()  # Calculate best size from label
        btn.InvalidateBestSize()  # Force recalc
        btn.SetMinSize(btn.GetBestSize())  # Use computed size as minimum

        # Explicitly show and force initial paint
        btn.Show(True)
        btn.Refresh(True)  # True = erase background
        btn.Update()  # Force immediate redraw

        setattr(vm_panel.id, id_name, btn)
        return btn

    @staticmethod
    def add_textctrl_with_id(
        vm_panel: Any, panel: wx.Panel, id_name: str, size: Tuple[int, int] = (250, 20), enable: bool = True
    ) -> wx.TextCtrl:
        id_ = -1
        if id_name in vm_panel.id.IDs:
            id_ = vm_panel.id.IDs[id_name]
        # Use TE_READONLY instead of disabling for better color control
        style = 0
        if not enable:
            style = wx.TE_READONLY
        txt = wx.TextCtrl(panel, id=id_, size=size, style=style)
        # Don't call Enable(False) - use TE_READONLY style instead for color consistency
        LayoutHelpers._apply_dialog_text_color(vm_panel, txt)
        # Also set background color for consistency
        try:
            color_manager = getattr(vm_panel, "color_manager", None)
            if color_manager and color_manager.has_color("DIALOG_BACKGROUND"):
                bg_color = color_manager.get_color("DIALOG_BACKGROUND")
                txt.SetBackgroundColour(bg_color)
                # Use SetOwnBackgroundColour for Windows compatibility
                txt.SetOwnBackgroundColour(bg_color)
        except Exception:
            pass
        setattr(vm_panel.id, id_name, txt)
        return txt

    @staticmethod
    def add_checkbox_with_id(vm_panel: Any, panel: wx.Panel, id_name: str, label: str, style: int = 0) -> wx.Window:
        id_ = -1
        if id_name in vm_panel.id.IDs:
            id_ = vm_panel.id.IDs[id_name]
        # Use native wx.CheckBox for better dark mode support on Windows
        # GenCheckBox uses wx.RendererNative which draws hardcoded black borders
        cb = wx.CheckBox(panel, id=id_, label=label)
        try:
            if vm_panel.color_manager and vm_panel.color_manager.has_color("DIALOG_BACKGROUND"):
                bg_color = vm_panel.color_manager.get_color("DIALOG_BACKGROUND")
                cb.SetBackgroundColour(bg_color)
                # Use SetOwnBackgroundColour for Windows compatibility
                if hasattr(cb, "SetOwnBackgroundColour"):
                    cb.SetOwnBackgroundColour(bg_color)
        except Exception:
            _log.debug("add_checkbox_with_id: Failed to set DIALOG_BACKGROUND for %s", id_name)
        LayoutHelpers._apply_dialog_text_color(vm_panel, cb)
        # Store reference so it can be refreshed later
        setattr(vm_panel.id, id_name, cb)
        # Force immediate refresh to apply colors
        try:
            cb.Refresh()
        except Exception:
            pass
        return cb

    @staticmethod
    def add_static_text_with_id(vm_panel: Any, panel: wx.Panel, id_name: str, label: str) -> wx.StaticText:
        id_ = -1
        if id_name in vm_panel.id.IDs:
            id_ = vm_panel.id.IDs[id_name]
        st = wx.StaticText(panel, id=id_, label=label)
        LayoutHelpers._apply_dialog_text_color(vm_panel, st)
        setattr(vm_panel.id, id_name, st)
        return st

    @staticmethod
    def add_radio_box_with_id(
        vm_panel: Any, panel: wx.Panel, id_name: str, label: str, choices: List[str], majorDimension: int = 1
    ) -> wx.Window:
        id_ = -1
        if id_name in vm_panel.id.IDs:
            id_ = vm_panel.id.IDs[id_name]
        rb = CustomRadioBox(panel, id=id_, label=label, choices=choices, majorDimension=majorDimension)
        try:
            if vm_panel.color_manager and vm_panel.color_manager.has_color("DIALOG_BACKGROUND"):
                bg_color = vm_panel.color_manager.get_color("DIALOG_BACKGROUND")
                rb.SetBackgroundColour(bg_color)
                # Use SetOwnBackgroundColour for Windows compatibility
                if hasattr(rb, "SetOwnBackgroundColour"):
                    rb.SetOwnBackgroundColour(bg_color)
        except Exception:
            _log.debug("add_radio_box_with_id: Failed to set DIALOG_BACKGROUND for %s", id_name)
        LayoutHelpers._apply_dialog_text_color(vm_panel, rb)
        setattr(vm_panel.id, id_name, rb)
        return rb

    @staticmethod
    def add_slider_with_id(
        vm_panel: Any,
        panel: wx.Panel,
        id_name: str,
        value: int,
        min_val: int,
        max_val: int,
        size: Tuple[int, int] = (250, 45),
        tick_freq: int = 5,
    ) -> wx.Slider:
        id_ = -1
        if id_name in vm_panel.id.IDs:
            id_ = vm_panel.id.IDs[id_name]
        slider = wx.Slider(
            panel,
            id=id_,
            value=value,
            minValue=min_val,
            maxValue=max_val,
            size=size,
            style=wx.SL_HORIZONTAL | wx.SL_AUTOTICKS | wx.SL_LABELS,
        )
        slider.SetTickFreq(tick_freq)
        LayoutHelpers._apply_dialog_text_color(vm_panel, slider)
        setattr(vm_panel.id, id_name, slider)
        return slider

    @staticmethod
    def add_choice_with_id(vm_panel: Any, panel: wx.Panel, id_name: str, choices: List[str]) -> wx.Choice:
        id_ = -1
        if id_name in vm_panel.id.IDs:
            id_ = vm_panel.id.IDs[id_name]
        choice = wx.Choice(panel, id=id_, choices=choices)
        LayoutHelpers._apply_choice_colors(vm_panel, choice, selected=False)
        LayoutHelpers._bind_choice_selection_colors(vm_panel, choice)
        setattr(vm_panel.id, id_name, choice)
        return choice

    @staticmethod
    def add_many_to_sizer(sizer: wx.Sizer, controls: list) -> None:
        sizer.AddMany(controls)

    @staticmethod
    def add_busy_indicator(vm_panel: Any, panel: wx.Panel, name: str, color: str = "BUSY_BACK") -> wx.ActivityIndicator:
        ai = wx.ActivityIndicator(panel)
        try:
            ai.SetBackgroundColour(vm_panel.color_manager.get_color(color))
        except Exception:
            _log.debug("add_busy_indicator: GetColor failed for %s", color)
        try:
            if vm_panel.color_manager and vm_panel.color_manager.has_color("BUSY_TEXT"):
                ai.SetForegroundColour(vm_panel.color_manager.get_color("BUSY_TEXT"))
        except Exception:
            _log.debug("add_busy_indicator: GetColor failed for BUSY_TEXT")
        setattr(vm_panel.id, name, ai)
        return ai
