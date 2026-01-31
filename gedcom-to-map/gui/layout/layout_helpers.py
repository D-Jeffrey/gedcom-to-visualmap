import logging
from typing import Any, List, Tuple
import wx

_log = logging.getLogger(__name__.lower())


class LayoutHelpers:
    """Collection of small UI construction helpers moved out of layout_options."""

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
        return hbox

    @staticmethod
    def add_button_with_id(vm_panel: Any, panel: wx.Panel, id_name: str, label: str = "", color: str = "BTN_DIRECTORY") -> wx.Button:
        id_ = -1
        if id_name in vm_panel.id.IDs:
            id_ = vm_panel.id.IDs[id_name]
        btn = wx.Button(panel, id=id_, label=label)
        if color:
            try:
                btn.SetBackgroundColour(vm_panel.color_manager.get_color(color))
            except Exception:
                _log.debug("add_button_with_id: GetColor failed for %s", color)
        setattr(vm_panel.id, id_name, btn)
        return btn

    @staticmethod
    def add_textctrl_with_id(vm_panel: Any, panel: wx.Panel, id_name: str, size: Tuple[int, int] = (250, 20), enable: bool = True) -> wx.TextCtrl:
        id_ = -1
        if id_name in vm_panel.id.IDs:
            id_ = vm_panel.id.IDs[id_name]
        txt = wx.TextCtrl(panel, id=id_, size=size)
        txt.Enable(enable)
        setattr(vm_panel.id, id_name, txt)
        return txt

    @staticmethod
    def add_checkbox_with_id(vm_panel: Any, panel: wx.Panel, id_name: str, label: str, style: int = 0) -> wx.CheckBox:
        id_ = -1
        if id_name in vm_panel.id.IDs:
            id_ = vm_panel.id.IDs[id_name]
        cb = wx.CheckBox(panel, id=id_, label=label, style=style)
        setattr(vm_panel.id, id_name, cb)
        return cb

    @staticmethod
    def add_static_text_with_id(vm_panel: Any, panel: wx.Panel, id_name: str, label: str) -> wx.StaticText:
        id_ = -1
        if id_name in vm_panel.id.IDs:
            id_ = vm_panel.id.IDs[id_name]
        st = wx.StaticText(panel, id=id_, label=label)
        setattr(vm_panel.id, id_name, st)
        return st

    @staticmethod
    def add_radio_box_with_id(vm_panel: Any, panel: wx.Panel, id_name: str, label: str, choices: List[str], majorDimension: int = 1) -> wx.RadioBox:
        id_ = -1
        if id_name in vm_panel.id.IDs:
            id_ = vm_panel.id.IDs[id_name]
        rb = wx.RadioBox(panel, id=id_, label=label, choices=choices, majorDimension=majorDimension)
        setattr(vm_panel.id, id_name, rb)
        return rb

    @staticmethod
    def add_slider_with_id(vm_panel: Any, panel: wx.Panel, id_name: str, value: int, min_val: int, max_val: int, size: Tuple[int, int] = (250, 45), tick_freq: int = 5) -> wx.Slider:
        id_ = -1
        if id_name in vm_panel.id.IDs:
            id_ = vm_panel.id.IDs[id_name]
        slider = wx.Slider(panel, id=id_, value=value, minValue=min_val, maxValue=max_val,
                           size=size, style=wx.SL_HORIZONTAL | wx.SL_AUTOTICKS | wx.SL_LABELS)
        slider.SetTickFreq(tick_freq)
        setattr(vm_panel.id, id_name, slider)
        return slider

    @staticmethod
    def add_choice_with_id(vm_panel: Any, panel: wx.Panel, id_name: str, choices: List[str]) -> wx.Choice:
        id_ = -1
        if id_name in vm_panel.id.IDs:
            id_ = vm_panel.id.IDs[id_name]
        choice = wx.Choice(panel, id=id_, choices=choices)
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
        setattr(vm_panel.id, name, ai)
        return ai
