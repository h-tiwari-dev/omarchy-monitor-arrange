from __future__ import annotations

import math
from typing import TYPE_CHECKING

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

if TYPE_CHECKING:
    from omarchy_monitor_arrange.core.manager import MonitorManager

PADDING = 60
MIN_MONITOR_PX = 80


class MonitorCanvas(Gtk.DrawingArea):
    """Cairo-based 2D canvas showing monitor arrangement."""

    def __init__(self, manager: MonitorManager, colors: dict):
        super().__init__()
        self._manager = manager
        self._colors = colors
        self._show_help = False
        self.set_vexpand(True)
        self.set_draw_func(self._draw)

    @property
    def show_help(self) -> bool:
        return self._show_help

    @show_help.setter
    def show_help(self, value: bool) -> None:
        self._show_help = value
        self.queue_draw()

    # -- coordinate transforms --

    def _compute_transform(self, canvas_w: float, canvas_h: float):
        monitors = self._manager.monitors
        if not monitors:
            return 0.0, 0.0, 1.0

        min_x = min(m.x for m in monitors)
        min_y = min(m.y for m in monitors)
        max_x = max(m.right for m in monitors)
        max_y = max(m.bottom for m in monitors)

        layout_w = max(max_x - min_x, 1)
        layout_h = max(max_y - min_y, 1)

        usable_w = canvas_w - 2 * PADDING
        usable_h = canvas_h - 2 * PADDING
        scale = min(usable_w / layout_w, usable_h / layout_h)
        scale = max(scale, MIN_MONITOR_PX / max(layout_w, layout_h))

        off_x = PADDING + (usable_w - layout_w * scale) / 2 - min_x * scale
        off_y = PADDING + (usable_h - layout_h * scale) / 2 - min_y * scale
        return off_x, off_y, scale

    def _hypr_to_canvas(self, hx: float, hy: float, off_x: float, off_y: float, scale: float):
        return off_x + hx * scale, off_y + hy * scale

    # -- drawing --

    def _draw(self, area, cr, width, height):
        bg = self._colors["bg"]
        cr.set_source_rgba(*bg)
        cr.paint()

        monitors = self._manager.monitors
        if not monitors:
            cr.set_source_rgba(*self._colors["text_dim"])
            cr.select_font_face("sans-serif")
            cr.set_font_size(16)
            cr.move_to(width / 2 - 80, height / 2)
            cr.show_text("No monitors detected")
            return

        off_x, off_y, scale = self._compute_transform(width, height)
        sel_idx = self._manager.selected_index

        self._draw_grid(cr, width, height)

        for i, mon in enumerate(monitors):
            self._draw_monitor(cr, mon, off_x, off_y, scale, selected=(i == sel_idx))

        overlaps = self._manager.overlaps
        if overlaps:
            self._draw_overlap_warnings(cr, monitors, overlaps, off_x, off_y, scale)

        if self._show_help:
            self._draw_help_overlay(cr, width, height)

    def _draw_grid(self, cr, width, height):
        cr.set_source_rgba(*self._colors["text_dim"][:3], 0.12)
        spacing = 30
        for x in range(0, int(width), spacing):
            for y in range(0, int(height), spacing):
                cr.arc(x, y, 1, 0, 2 * math.pi)
                cr.fill()

    def _draw_monitor(self, cr, mon, off_x, off_y, scale, selected: bool):
        cx, cy = self._hypr_to_canvas(mon.x, mon.y, off_x, off_y, scale)
        cw = mon.scaled_width * scale
        ch = mon.scaled_height * scale
        radius = 8

        self._rounded_rect(cr, cx, cy, cw, ch, radius)
        cr.set_source_rgba(*self._colors["monitor_fill"])
        cr.fill_preserve()

        border = self._colors["selected_border"] if selected else self._colors["monitor_border"]
        cr.set_source_rgba(*border)
        cr.set_line_width(3 if selected else 1.5)
        cr.stroke()

        cr.set_source_rgba(*self._colors["text"])
        cr.select_font_face("sans-serif")
        font_size = max(10, min(15, cw / 12))
        cr.set_font_size(font_size)

        label_name = mon.name
        label_res = f"{mon.width}x{mon.height}"
        label_detail = f"@{mon.refresh_rate:.0f} {mon.scale}x"

        for j, text in enumerate([label_name, label_res, label_detail]):
            ext = cr.text_extents(text)
            tx = cx + (cw - ext.width) / 2
            ty = cy + ch / 2 + (j - 1) * (font_size + 3)
            if tx > cx and tx + ext.width < cx + cw:
                cr.move_to(tx, ty)
                cr.show_text(text)

        if mon.name == self._manager.primary_name:
            cr.set_source_rgba(*self._colors["selected_border"][:3], 0.7)
            cr.set_font_size(max(8, font_size * 0.75))
            star = "★ primary"
            ext = cr.text_extents(star)
            cr.move_to(cx + (cw - ext.width) / 2, cy + ch - 8)
            cr.show_text(star)

    def _draw_overlap_warnings(self, cr, monitors, overlaps, off_x, off_y, scale):
        by_name = {m.name: m for m in monitors}
        cr.set_source_rgba(*self._colors["overlap_warn"])
        for ov in overlaps:
            a, b = by_name.get(ov.monitor_a), by_name.get(ov.monitor_b)
            if not a or not b:
                continue
            ix = max(a.x, b.x)
            iy = max(a.y, b.y)
            ix2 = min(a.right, b.right)
            iy2 = min(a.bottom, b.bottom)
            if ix < ix2 and iy < iy2:
                rx, ry = self._hypr_to_canvas(ix, iy, off_x, off_y, scale)
                rw = (ix2 - ix) * scale
                rh = (iy2 - iy) * scale
                cr.rectangle(rx, ry, rw, rh)
                cr.fill()

    def _draw_help_overlay(self, cr, width, height):
        cr.set_source_rgba(0, 0, 0, 0.75)
        cr.rectangle(0, 0, width, height)
        cr.fill()

        lines = [
            "Keyboard Shortcuts",
            "",
            "Tab / Shift+Tab    Select monitor",
            "Arrow keys         Move (coarse)",
            "Shift + Arrows     Move (fine)",
            "r                  Cycle resolution",
            "s                  Cycle scale",
            "f                  Cycle refresh rate",
            "t                  Cycle transform",
            "p                  Set primary",
            "i                  Identify monitors",
            "u                  Undo",
            "Ctrl+r             Reset to saved state",
            "Ctrl+Shift+r       Hard reset (reload from system)",
            "Enter              Apply & reload",
            "Escape             Close",
            "h / ?              Toggle this help",
        ]

        cr.select_font_face("monospace")
        cr.set_font_size(15)
        start_y = height / 2 - len(lines) * 10
        for j, line in enumerate(lines):
            cr.set_source_rgba(*self._colors["text"] if j == 0 else self._colors["text_dim"])
            if j == 0:
                cr.set_font_size(18)
            else:
                cr.set_font_size(14)
            ext = cr.text_extents(line)
            cr.move_to((width - ext.width) / 2, start_y + j * 22)
            cr.show_text(line)

    @staticmethod
    def _rounded_rect(cr, x, y, w, h, r):
        cr.new_sub_path()
        cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
        cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
        cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
        cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
        cr.close_path()
