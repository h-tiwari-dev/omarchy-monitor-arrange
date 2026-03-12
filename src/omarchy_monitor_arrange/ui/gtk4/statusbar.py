from __future__ import annotations

from typing import TYPE_CHECKING

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from omarchy_monitor_arrange.core.models import TRANSFORM_LABELS

if TYPE_CHECKING:
    from omarchy_monitor_arrange.core.manager import MonitorManager


class StatusBar(Gtk.Box):
    """Bottom bar showing selected monitor info and keyboard shortcuts."""

    def __init__(self, manager: MonitorManager, colors: dict):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self._manager = manager
        self._colors = colors

        self.set_margin_start(16)
        self.set_margin_end(16)
        self.set_margin_top(10)
        self.set_margin_bottom(10)

        self._info_label = Gtk.Label(xalign=0)
        self._info_label.set_wrap(True)
        self.append(self._info_label)

        self._detail_label = Gtk.Label(xalign=0)
        self._detail_label.add_css_class("dim-label")
        self.append(self._detail_label)

        sep = Gtk.Separator()
        self.append(sep)

        self._shortcut_label = Gtk.Label(xalign=0)
        self._shortcut_label.add_css_class("dim-label")
        self._shortcut_label.set_markup(
            "<small>"
            "[Tab] Select  [←→↑↓] Move  [r] Res  [s] Scale  "
            "[f] Refresh  [t] Rotate  [p] Primary  "
            "[i] Identify  [u] Undo  [Ctrl+r] Reset  [Ctrl+Shift+r] Hard Reset  [Enter] Apply  [Esc] Close  [h] Help"
            "</small>"
        )
        self.append(self._shortcut_label)

        self._warning_label = Gtk.Label(xalign=0)
        self.append(self._warning_label)

    def update(self) -> None:
        mon = self._manager.selected
        if mon is None:
            self._info_label.set_text("No monitors")
            self._detail_label.set_text("")
            self._warning_label.set_text("")
            return

        primary_tag = " ★" if mon.name == self._manager.primary_name else ""
        self._info_label.set_markup(
            f"<b>Selected: {mon.name}{primary_tag}</b>"
        )

        transform_str = TRANSFORM_LABELS.get(mon.transform, str(mon.transform))
        self._detail_label.set_text(
            f"Resolution: {mon.width}x{mon.height}  "
            f"Refresh: {mon.refresh_rate:.0f}Hz  "
            f"Scale: {mon.scale}x  "
            f"Position: {mon.x}x{mon.y}  "
            f"Transform: {transform_str}"
        )

        parts: list[str] = []
        if self._manager.overlaps:
            names = ", ".join(
                f"{o.monitor_a}↔{o.monitor_b}" for o in self._manager.overlaps
            )
            parts.append(f"⚠ Overlap: {names}")
        if self._manager.has_unsaved_changes:
            parts.append("● Unsaved changes")

        self._warning_label.set_markup(
            f"<span foreground='#ff6666'>{' | '.join(parts)}</span>" if parts else ""
        )
