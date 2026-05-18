"""image_cache_dialog.py

Dialog for managing the image / media cache for the currently loaded GEDCOM file.

Features
--------
* Display the effective cache directory (configured alternate or GEDCOM folder).
* Allow the user to choose an alternate cache directory via a folder picker.
* Reset the cache directory back to the default (same folder as the GEDCOM file).
* Toggle the filename preservation strategy (preserve original name vs SHA-1 hash).
* Download all remote photos in the background with live progress feedback.
"""

import logging
import threading
from pathlib import Path
from typing import Optional

import wx

from ..layout.font_manager import FontManager

_log = logging.getLogger(__name__.lower())

__all__ = ["ImageCacheDialog"]


class ImageCacheDialog(wx.Dialog):
    """Dialog for configuring and triggering GEDCOM image caching.

    Shows:
    - Effective cache directory with a "Browse" picker and "Reset" button.
    - Checkbox to toggle filename preservation strategy.
    - "Download" button that runs ``ImageCacheService.download_all`` in a background
      thread, updating a status/progress text area in the dialog.

    Args:
        parent: Parent wx.Window.
        svc_config: Configuration service (GVConfig / IConfig).
        svc_state: Runtime state service (IState) – used to access loaded people.
        font_manager: Optional FontManager for dialog font styling.
        color_manager: Optional colour manager for dark-mode support.
    """

    def __init__(
        self,
        parent: wx.Window,
        svc_config,
        svc_state=None,
        font_manager: Optional["FontManager"] = None,
        color_manager=None,
    ) -> None:
        super().__init__(
            parent,
            title="Image Caching",
            size=(560, 420),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.svc_config = svc_config
        self.svc_state = svc_state
        self.font_manager: Optional["FontManager"] = font_manager
        self.color_manager = color_manager
        self._stop_requested = False
        self._download_thread: Optional[threading.Thread] = None

        self._build_ui()
        self._apply_current_font()
        self.refresh_dialog_background()
        if self.font_manager and hasattr(self.font_manager, "register_font_change_callback"):
            self.font_manager.register_font_change_callback(self._on_font_changed)
        self.Bind(wx.EVT_ACTIVATE, self.OnActivate)
        self.Bind(wx.EVT_WINDOW_DESTROY, self._on_destroy)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        panel = wx.Panel(self)
        self._panel = panel

        # --- Cache directory row ---
        dir_label = wx.StaticText(panel, label="Cache directory:")
        cur_dir = self._effective_cache_dir()
        self._dir_text = wx.TextCtrl(panel, value=cur_dir, size=(340, -1))
        self._browse_btn = wx.Button(panel, label="Browse…")
        self._reset_btn = wx.Button(panel, label="Reset to Default")
        self._browse_btn.Bind(wx.EVT_BUTTON, self._on_browse)
        self._reset_btn.Bind(wx.EVT_BUTTON, self._on_reset_dir)

        dir_row = wx.BoxSizer(wx.HORIZONTAL)
        dir_row.Add(self._dir_text, 1, wx.EXPAND | wx.RIGHT, 4)
        dir_row.Add(self._browse_btn, 0, wx.RIGHT, 4)
        dir_row.Add(self._reset_btn, 0)

        # --- Filename preservation checkbox ---
        preserve = self.svc_config.get_image_cache_preserve_name() if hasattr(
            self.svc_config, "get_image_cache_preserve_name"
        ) else True
        self._preserve_cb = wx.CheckBox(panel, label="Preserve original filename (unchecked = use URL hash)")
        self._preserve_cb.SetValue(preserve)
        self._preserve_cb.Bind(wx.EVT_CHECKBOX, self._on_preserve_changed)

        # --- Progress / status area ---
        self._status_text = wx.TextCtrl(
            panel,
            value="",
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2,
            size=(-1, 140),
        )
        self._status_text.SetValue("Ready. Press Download to begin caching remote photos.\n")

        # --- Buttons ---
        self._download_btn = wx.Button(panel, label="Download")
        self._stop_btn = wx.Button(panel, label="Stop")
        self._stop_btn.Disable()
        self._close_btn = wx.Button(panel, wx.ID_CLOSE, label="Close")

        self._download_btn.Bind(wx.EVT_BUTTON, self._on_download)
        self._stop_btn.Bind(wx.EVT_BUTTON, self._on_stop)
        self._close_btn.Bind(wx.EVT_BUTTON, lambda _: self.Close())

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        btn_row.Add(self._download_btn, 0, wx.RIGHT, 8)
        btn_row.Add(self._stop_btn, 0, wx.RIGHT, 8)
        btn_row.AddStretchSpacer()
        btn_row.Add(self._close_btn, 0)

        # --- Main sizer ---
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(dir_label, 0, wx.ALL, 6)
        sizer.Add(dir_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)
        sizer.Add(self._preserve_cb, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)
        sizer.Add(wx.StaticText(panel, label="Status:"), 0, wx.LEFT | wx.TOP, 6)
        sizer.Add(self._status_text, 1, wx.EXPAND | wx.ALL, 6)
        sizer.Add(btn_row, 0, wx.EXPAND | wx.ALL, 8)

        panel.SetSizer(sizer)
        dlg_sizer = wx.BoxSizer(wx.VERTICAL)
        dlg_sizer.Add(panel, 1, wx.EXPAND)
        self.SetSizer(dlg_sizer)
        self.Layout()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _effective_cache_dir(self) -> str:
        if hasattr(self.svc_config, "get_effective_cache_dir"):
            return self.svc_config.get_effective_cache_dir()
        gedcom = getattr(self.svc_config, "GEDCOMinput", None) or ""
        return str(Path(gedcom).parent) if gedcom else str(Path.cwd())

    def refresh_dialog_background(self) -> None:
        if not self.color_manager:
            return
        try:
            bg = self.color_manager.get_color("DIALOG_BACKGROUND") if self.color_manager.has_color("DIALOG_BACKGROUND") else None
            fg = self.color_manager.get_color("DIALOG_TEXT") if self.color_manager.has_color("DIALOG_TEXT") else None
            if bg is not None:
                self.SetBackgroundColour(bg)
                self._panel.SetBackgroundColour(bg)
            if fg is not None:
                self.SetForegroundColour(fg)
                self._panel.SetForegroundColour(fg)
                self._apply_foreground_recursive(self._panel, fg)

            status_bg = self.color_manager.get_color("GRID_BACK") if self.color_manager.has_color("GRID_BACK") else bg
            status_fg = self.color_manager.get_color("GRID_TEXT") if self.color_manager.has_color("GRID_TEXT") else fg
            if status_bg is not None:
                self._status_text.SetBackgroundColour(status_bg)
                if hasattr(self._status_text, "SetOwnBackgroundColour"):
                    self._status_text.SetOwnBackgroundColour(status_bg)
            if status_fg is not None:
                self._status_text.SetForegroundColour(status_fg)
                if hasattr(self._status_text, "SetOwnForegroundColour"):
                    self._status_text.SetOwnForegroundColour(status_fg)

            btn_back = self.color_manager.get_color("BTN_BACK") if self.color_manager.has_color("BTN_BACK") else None
            for btn in (self._browse_btn, self._reset_btn, self._download_btn, self._stop_btn, self._close_btn):
                self._apply_button_colors(btn, btn_back, fg)

            self.Refresh()
        except Exception:
            _log.debug("Failed to refresh colors in ImageCacheDialog", exc_info=True)

    def _apply_current_font(self) -> None:
        if not self.font_manager:
            return
        try:
            self.font_manager.apply_current_font_recursive(self)
            self.Layout()
        except Exception:
            _log.debug("Failed to apply font in ImageCacheDialog", exc_info=True)

    def _on_font_changed(self) -> None:
        try:
            wx.CallAfter(self._apply_current_font)
        except Exception:
            _log.debug("Failed to schedule font refresh in ImageCacheDialog", exc_info=True)

    def _apply_foreground_recursive(self, root: wx.Window, color: wx.Colour) -> None:
        try:
            root.SetForegroundColour(color)
            if hasattr(root, "SetOwnForegroundColour"):
                root.SetOwnForegroundColour(color)
        except Exception:
            pass

        if isinstance(root, wx.TextCtrl) and root is not self._status_text:
            try:
                bg = self.color_manager.get_color("DIALOG_BACKGROUND") if self.color_manager.has_color("DIALOG_BACKGROUND") else None
                if bg is not None:
                    root.SetBackgroundColour(bg)
                    if hasattr(root, "SetOwnBackgroundColour"):
                        root.SetOwnBackgroundColour(bg)
            except Exception:
                pass

        for child in root.GetChildren():
            self._apply_foreground_recursive(child, color)

    def _apply_button_colors(self, button: wx.Button, background: Optional[wx.Colour], foreground: Optional[wx.Colour]) -> None:
        try:
            if background is not None:
                button.SetBackgroundColour(background)
                if hasattr(button, "SetOwnBackgroundColour"):
                    button.SetOwnBackgroundColour(background)
            if foreground is not None:
                button.SetForegroundColour(foreground)
                if hasattr(button, "SetOwnForegroundColour"):
                    button.SetOwnForegroundColour(foreground)
        except Exception:
            pass

    def OnActivate(self, event: wx.ActivateEvent) -> None:
        if event.GetActive() and self.color_manager:
            try:
                if hasattr(self.color_manager, "refresh_colors") and self.color_manager.refresh_colors():
                    self.refresh_dialog_background()
            except Exception:
                _log.debug("Failed to refresh dialog theme on activation", exc_info=True)
        event.Skip()

    def _append_status(self, msg: str) -> None:
        """Append *msg* (newline added automatically) to the status area.

        Must be called from the **main thread** (or via ``wx.CallAfter``).
        """
        try:
            self._status_text.AppendText(msg + "\n")
        except Exception:
            pass

    def _set_busy(self, busy: bool) -> None:
        """Enable or disable buttons based on whether a download is running."""
        try:
            self._download_btn.Enable(not busy)
            self._stop_btn.Enable(busy)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_browse(self, event: wx.CommandEvent) -> None:
        cur = self._dir_text.GetValue() or str(Path.cwd())
        dlg = wx.DirDialog(
            self,
            message="Choose image cache directory",
            defaultPath=cur,
            style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST,
        )
        if dlg.ShowModal() == wx.ID_OK:
            chosen = dlg.GetPath()
            self._dir_text.SetValue(chosen)
            self._apply_cache_dir(chosen)
        dlg.Destroy()

    def _on_reset_dir(self, event: wx.CommandEvent) -> None:
        """Clear the alternate cache directory so the GEDCOM folder is used."""
        if hasattr(self.svc_config, "set_image_cache_dir"):
            self.svc_config.set_image_cache_dir(None)
            if hasattr(self.svc_config, "savesettings"):
                try:
                    self.svc_config.savesettings()
                except Exception:
                    pass
        default_dir = self._effective_cache_dir()
        self._dir_text.SetValue(default_dir)
        self._append_status(f"Cache directory reset to: {default_dir}")

    def _on_preserve_changed(self, event: wx.CommandEvent) -> None:
        value = self._preserve_cb.GetValue()
        if hasattr(self.svc_config, "set_image_cache_preserve_name"):
            self.svc_config.set_image_cache_preserve_name(value)
            if hasattr(self.svc_config, "savesettings"):
                try:
                    self.svc_config.savesettings()
                except Exception:
                    pass

    def _apply_cache_dir(self, path: str) -> None:
        """Persist the chosen cache directory."""
        if hasattr(self.svc_config, "set_image_cache_dir"):
            self.svc_config.set_image_cache_dir(path)
            if hasattr(self.svc_config, "savesettings"):
                try:
                    self.svc_config.savesettings()
                except Exception:
                    pass
        self._append_status(f"Cache directory set to: {path}")

    def _on_download(self, event: wx.CommandEvent) -> None:
        """Start the background download thread."""
        from gui.services.image_cache_service import ImageCacheService

        people = None
        if self.svc_state is not None:
            people = getattr(self.svc_state, "people", None)

        if not people:
            wx.MessageBox(
                "No GEDCOM data loaded.\nLoad a GEDCOM file first, then download images.",
                "No Data",
                wx.OK | wx.ICON_INFORMATION,
                self,
            )
            return

        cache_dir = self._dir_text.GetValue().strip() or self._effective_cache_dir()
        preserve_name = self._preserve_cb.GetValue()
        local_patterns = (
            self.svc_config.get_local_photo_hosts()
            if hasattr(self.svc_config, "get_local_photo_hosts")
            else ["localhost"]
        )

        # Ensure cache directory persisted
        self._apply_cache_dir(cache_dir)

        self._stop_requested = False
        self._status_text.SetValue("")
        self._append_status(f"Starting download into: {cache_dir}")
        self._append_status(f"Filename mode: {'preserve original' if preserve_name else 'URL hash'}\n")
        self._set_busy(True)

        def _worker():
            def _progress(current, total, msg):
                wx.CallAfter(self._append_status, msg)

            def _stop():
                return self._stop_requested

            try:
                stats = ImageCacheService.download_all(
                    people=people,
                    cache_dir=cache_dir,
                    preserve_name=preserve_name,
                    local_host_patterns=local_patterns,
                    progress_cb=_progress,
                    stop_cb=_stop,
                )
                summary = (
                    f"\nDone.  Found: {stats['found']}  |  "
                    f"Downloaded: {stats['downloaded']}  |  "
                    f"Already cached: {stats['cached']}  |  "
                    f"Failed: {stats['failed']}"
                )
                wx.CallAfter(self._append_status, summary)
            except Exception as exc:
                _log.exception("Image cache download thread failed")
                wx.CallAfter(self._append_status, f"\nError: {exc}")
            finally:
                wx.CallAfter(self._set_busy, False)

        self._download_thread = threading.Thread(target=_worker, daemon=True, name="ImageCacheDownload")
        self._download_thread.start()

    def _on_stop(self, event: wx.CommandEvent) -> None:
        self._stop_requested = True
        self._append_status("Stop requested – finishing current file…")

    def _on_destroy(self, event: wx.WindowDestroyEvent) -> None:
        self._stop_requested = True
        if self.font_manager and hasattr(self.font_manager, "unregister_font_change_callback"):
            try:
                self.font_manager.unregister_font_change_callback(self._on_font_changed)
            except Exception:
                _log.debug("Failed to unregister font callback in ImageCacheDialog", exc_info=True)
        event.Skip()
