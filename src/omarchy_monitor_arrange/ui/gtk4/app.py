from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, GLib, Gtk

from omarchy_monitor_arrange.ui.gtk4.canvas import MonitorCanvas
from omarchy_monitor_arrange.ui.gtk4.statusbar import StatusBar

if TYPE_CHECKING:
    from omarchy_monitor_arrange.core.manager import MonitorManager

APP_ID = "org.omarchy.monitor-arrange"


class MonitorArrangeGtkUI:
    """GTK4 implementation of MonitorArrangeUI protocol."""

    def __init__(self, colors: dict):
        self._colors = colors

    def run(self, manager: MonitorManager) -> None:
        app = _App(manager, self._colors)
        app.run(None)


class _App(Gtk.Application):

    def __init__(self, manager: MonitorManager, colors: dict):
        super().__init__(application_id=APP_ID)
        self._manager = manager
        self._colors = colors
        self._canvas: MonitorCanvas | None = None
        self._statusbar: StatusBar | None = None

    def do_activate(self):
        win = Gtk.ApplicationWindow(application=self)
        win.set_title("Monitor Arrangement")
        win.set_default_size(875, 600)

        self._apply_css()

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        self._canvas = MonitorCanvas(self._manager, self._colors)
        self._statusbar = StatusBar(self._manager, self._colors)

        box.append(self._canvas)
        box.append(Gtk.Separator())
        box.append(self._statusbar)

        win.set_child(box)

        key_ctrl = Gtk.EventControllerKey()
        key_ctrl.connect("key-pressed", self._on_key_pressed)
        win.add_controller(key_ctrl)

        self._manager.on_change(self._on_manager_change)
        self._statusbar.update()
        self._manager.highlight_selected()

        win.present()

    def _apply_css(self):
        bg = self._colors["status_bg"]
        css = f"""
            window {{
                background-color: rgba({int(bg[0]*255)},{int(bg[1]*255)},{int(bg[2]*255)},{bg[3]});
            }}
        """
        provider = Gtk.CssProvider()
        provider.load_from_string(css)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def _relaunch(self):
        """Close the app and spawn a fresh instance so the window re-centers on the new layout."""
        subprocess.Popen(["omarchy-monitor-arrange"])
        win = self.get_active_window()
        if win:
            win.close()
        return False

    def _on_manager_change(self):
        if self._canvas:
            self._canvas.queue_draw()
        if self._statusbar:
            self._statusbar.update()

    def _on_key_pressed(self, ctrl, keyval, keycode, state):
        shift = bool(state & Gdk.ModifierType.SHIFT_MASK)
        ctrl_held = bool(state & Gdk.ModifierType.CONTROL_MASK)
        mgr = self._manager

        if keyval == Gdk.KEY_Tab:
            if shift:
                mgr.select_prev()
            else:
                mgr.select_next()
            mgr.highlight_selected()
            return True

        if keyval == Gdk.KEY_ISO_Left_Tab:
            mgr.select_prev()
            mgr.highlight_selected()
            return True

        step = mgr.FINE_STEP if shift else mgr.COARSE_STEP
        snap = not shift

        if keyval == Gdk.KEY_Left:
            mgr.move_selected(-step, 0, snap=snap)
            return True
        if keyval == Gdk.KEY_Right:
            mgr.move_selected(step, 0, snap=snap)
            return True
        if keyval == Gdk.KEY_Up:
            mgr.move_selected(0, -step, snap=snap)
            return True
        if keyval == Gdk.KEY_Down:
            mgr.move_selected(0, step, snap=snap)
            return True

        if keyval in (Gdk.KEY_r, Gdk.KEY_R) and ctrl_held and shift:
            mgr.hard_reset()
            GLib.timeout_add(1000, self._relaunch)
            return True
        if keyval == Gdk.KEY_r and ctrl_held:
            mgr.reset()
            return True
        if keyval == Gdk.KEY_r:
            mgr.cycle_resolution()
            return True
        if keyval == Gdk.KEY_s:
            mgr.cycle_scale()
            return True
        if keyval == Gdk.KEY_f:
            mgr.cycle_refresh_rate()
            return True
        if keyval == Gdk.KEY_t:
            mgr.cycle_transform()
            return True

        if keyval == Gdk.KEY_p:
            mgr.set_primary()
            return True
        if keyval == Gdk.KEY_i:
            mgr.identify()
            return True
        if keyval == Gdk.KEY_u:
            mgr.undo()
            return True

        if keyval in (Gdk.KEY_h, Gdk.KEY_question):
            if self._canvas:
                self._canvas.show_help = not self._canvas.show_help
            return True

        if keyval == Gdk.KEY_Return:
            mgr.apply()
            GLib.timeout_add(1000, self._relaunch)
            return True

        if keyval == Gdk.KEY_Escape:
            mgr.clear_highlight()
            self.get_active_window().close()
            return True

        return False
