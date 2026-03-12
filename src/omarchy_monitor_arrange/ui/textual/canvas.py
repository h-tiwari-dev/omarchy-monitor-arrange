from __future__ import annotations

from typing import TYPE_CHECKING

from rich.style import Style
from rich.text import Text
from textual.widget import Widget

from omarchy_monitor_arrange.ui.textual.geometry import compute_transform, map_point

if TYPE_CHECKING:
    from omarchy_monitor_arrange.core.manager import MonitorManager
    from omarchy_monitor_arrange.core.models import Monitor

PADDING = 2
MIN_BOX_W = 10
MIN_BOX_H = 5

_LIGHT = {"tl": "┌", "tr": "┐", "bl": "└", "br": "┘", "h": "─", "v": "│"}
_HEAVY = {"tl": "┏", "tr": "┓", "bl": "┗", "br": "┛", "h": "━", "v": "┃"}


def _hex(rgba: tuple[float, ...]) -> str:
    return f"#{int(rgba[0]*255):02x}{int(rgba[1]*255):02x}{int(rgba[2]*255):02x}"


class MonitorCanvasWidget(Widget, can_focus=True):
    """Styled character-canvas that renders the monitor arrangement."""

    def __init__(self, manager: MonitorManager, colors: dict):
        super().__init__()
        self._manager = manager
        self._colors = colors
        self._show_help = False
        self._init_styles(colors)

    def _init_styles(self, c: dict) -> None:
        bg = _hex(c.get("bg", (0.12, 0.12, 0.14, 1.0)))
        fill = _hex(c.get("monitor_fill", (0.22, 0.22, 0.26, 1.0)))
        border = _hex(c.get("monitor_border", (0.4, 0.4, 0.45, 1.0)))
        sel = _hex(c.get("selected_border", (0.4, 0.6, 1.0, 1.0)))
        txt = _hex(c.get("text", (0.9, 0.9, 0.92, 1.0)))
        dim = _hex(c.get("text_dim", (0.6, 0.6, 0.65, 1.0)))
        warn = _hex(c.get("overlap_warn", (1.0, 0.4, 0.3, 0.6)))

        self._s_bg = Style(color=dim, bgcolor=bg)
        self._s_border = Style(color=border, bgcolor=bg)
        self._s_sel_border = Style(color=sel, bgcolor=bg, bold=True)
        self._s_fill = Style(bgcolor=fill)
        self._s_sel_fill = Style(bgcolor=fill)
        self._s_name = Style(color=txt, bgcolor=fill, bold=True)
        self._s_sel_name = Style(color=sel, bgcolor=fill, bold=True)
        self._s_detail = Style(color=dim, bgcolor=fill)
        self._s_overlap = Style(color=warn, bgcolor=bg, bold=True)
        self._s_help_title = Style(color=sel, bold=True)
        self._s_help_key = Style(color=sel)
        self._s_help_desc = Style(color=txt)
        self._s_help_bg = Style(color=dim, bgcolor=bg)

    # -- public property --

    @property
    def show_help(self) -> bool:
        return self._show_help

    @show_help.setter
    def show_help(self, value: bool) -> None:
        self._show_help = value
        self.refresh()

    # -- rendering --

    def render(self) -> Text:
        w = max(self.size.width, 1)
        h = max(self.size.height, 1)

        if self._show_help:
            return self._render_help(w, h)

        chars = [[" "] * w for _ in range(h)]
        styles: list[list[Style]] = [[self._s_bg] * w for _ in range(h)]

        monitors = self._manager.monitors
        if not monitors:
            return self._centered_message(w, h, "No monitors detected")

        off_x, off_y, scale = compute_transform(
            monitors, canvas_w=w, canvas_h=h,
            padding=PADDING, min_cells=MIN_BOX_W,
        )

        sel_idx = self._manager.selected_index
        for idx, mon in enumerate(monitors):
            if idx != sel_idx:
                self._draw_monitor(chars, styles, mon, off_x, off_y, scale, False)
        if 0 <= sel_idx < len(monitors):
            self._draw_monitor(chars, styles, monitors[sel_idx], off_x, off_y, scale, True)

        if self._manager.overlaps:
            self._draw_overlaps(chars, styles, monitors, off_x, off_y, scale)

        return self._assemble(chars, styles, w, h)

    # -- monitor drawing --

    def _draw_monitor(
        self,
        chars: list[list[str]],
        styles: list[list[Style]],
        mon: Monitor,
        off_x: float, off_y: float, scale: float,
        selected: bool,
    ) -> None:
        left, top = map_point(mon.x, mon.y, off_x, off_y, scale)
        right, bottom = map_point(mon.right, mon.bottom, off_x, off_y, scale)

        if right - left + 1 < MIN_BOX_W:
            right = left + MIN_BOX_W - 1
        if bottom - top + 1 < MIN_BOX_H:
            bottom = top + MIN_BOX_H - 1

        box = _HEAVY if selected else _LIGHT
        border_s = self._s_sel_border if selected else self._s_border
        fill_s = self._s_sel_fill if selected else self._s_fill
        name_s = self._s_sel_name if selected else self._s_name

        self._fill_rect(chars, styles, left + 1, top + 1, right - 1, bottom - 1, fill_s)
        self._draw_box(chars, styles, left, top, right, bottom, box, border_s)

        labels = self._monitor_labels(mon)
        self._draw_labels(chars, styles, left, top, right, bottom, labels, name_s)

    def _monitor_labels(self, mon: Monitor) -> list[str]:
        name = mon.name
        if mon.name == self._manager.primary_name:
            name = f"★ {name}"
        return [name, f"{mon.width}×{mon.height}", f"@{mon.refresh_rate:.0f}Hz {mon.scale}x"]

    # -- box primitives --

    def _draw_box(
        self,
        chars: list[list[str]], styles: list[list[Style]],
        left: int, top: int, right: int, bottom: int,
        box: dict[str, str], s: Style,
    ) -> None:
        max_y, max_x = len(chars) - 1, len(chars[0]) - 1
        l, t = max(left, 0), max(top, 0)
        r, b = min(right, max_x), min(bottom, max_y)
        if r <= l or b <= t:
            return

        for x in range(l + 1, r):
            chars[t][x], styles[t][x] = box["h"], s
            chars[b][x], styles[b][x] = box["h"], s
        for y in range(t + 1, b):
            chars[y][l], styles[y][l] = box["v"], s
            chars[y][r], styles[y][r] = box["v"], s

        corners = [
            (t, l, top, left, "tl"), (t, r, top, right, "tr"),
            (b, l, bottom, left, "bl"), (b, r, bottom, right, "br"),
        ]
        for cy, cx, orig_y, orig_x, key in corners:
            if cy == orig_y and cx == orig_x:
                chars[cy][cx], styles[cy][cx] = box[key], s

    def _fill_rect(
        self,
        chars: list[list[str]], styles: list[list[Style]],
        left: int, top: int, right: int, bottom: int,
        s: Style,
    ) -> None:
        max_y, max_x = len(chars) - 1, len(chars[0]) - 1
        for y in range(max(top, 0), min(bottom + 1, max_y + 1)):
            for x in range(max(left, 0), min(right + 1, max_x + 1)):
                chars[y][x], styles[y][x] = " ", s

    def _draw_labels(
        self,
        chars: list[list[str]], styles: list[list[Style]],
        left: int, top: int, right: int, bottom: int,
        lines: list[str], name_style: Style,
    ) -> None:
        iw = right - left - 1
        ih = bottom - top - 1
        if iw <= 0 or ih <= 0:
            return

        start_y = top + 1 + max((ih - len(lines)) // 2, 0)
        for i, line in enumerate(lines[:ih]):
            if not line:
                continue
            trimmed = line[:iw]
            sx = left + 1 + max((iw - len(trimmed)) // 2, 0)
            y = start_y + i
            if not (0 <= y < len(chars)):
                continue
            s = name_style if i == 0 else self._s_detail
            for j, ch in enumerate(trimmed):
                x = sx + j
                if 0 <= x < len(chars[y]):
                    chars[y][x], styles[y][x] = ch, s

    # -- overlap rendering --

    def _draw_overlaps(
        self,
        chars: list[list[str]], styles: list[list[Style]],
        monitors: list[Monitor],
        off_x: float, off_y: float, scale: float,
    ) -> None:
        by_name = {m.name: m for m in monitors}
        for ov in self._manager.overlaps:
            a, b = by_name.get(ov.monitor_a), by_name.get(ov.monitor_b)
            if not a or not b:
                continue
            ix, iy = max(a.x, b.x), max(a.y, b.y)
            ix2, iy2 = min(a.right, b.right), min(a.bottom, b.bottom)
            if ix >= ix2 or iy >= iy2:
                continue
            l, t = map_point(ix, iy, off_x, off_y, scale)
            r, bt = map_point(ix2, iy2, off_x, off_y, scale)
            for y in range(max(t, 0), min(bt + 1, len(chars))):
                for x in range(max(l, 0), min(r + 1, len(chars[y]))):
                    chars[y][x], styles[y][x] = "░", self._s_overlap

    # -- help overlay --

    def _render_help(self, w: int, h: int) -> Text:
        entries = [
            ("Tab / Shift+Tab", "Select monitor"),
            ("Arrow keys", "Move (coarse)"),
            ("Shift + Arrows", "Move (fine)"),
            ("r", "Cycle resolution"),
            ("s", "Cycle scale"),
            ("f", "Cycle refresh rate"),
            ("t", "Cycle transform"),
            ("p", "Set primary"),
            ("i", "Identify monitors"),
            ("u", "Undo"),
            ("Ctrl+r", "Reset to saved state"),
            ("Ctrl+Shift+r", "Hard reset"),
            ("Enter", "Apply & reload"),
            ("Escape", "Close"),
            ("h / ?", "Toggle this help"),
        ]
        title = "Keyboard Shortcuts"
        key_col = max(len(k) for k, _ in entries)
        total_lines = len(entries) + 3
        start_y = max((h - total_lines) // 2, 0)

        text = Text()
        for y in range(h):
            if y == start_y:
                text.append(self._pad_center(title, w), style=self._s_help_title)
            elif y == start_y + 1:
                bar = "─" * min(len(title) + 4, w)
                text.append(self._pad_center(bar, w), style=self._s_help_key)
            elif y == start_y + 2:
                text.append(" " * w, style=self._s_help_bg)
            elif start_y + 3 <= y < start_y + 3 + len(entries):
                idx = y - start_y - 3
                key, desc = entries[idx]
                padded_key = key.rjust(key_col)
                line_content = f"{padded_key}   {desc}"
                left_pad = max((w - len(line_content)) // 2, 0)
                text.append(" " * left_pad, style=self._s_help_bg)
                text.append(padded_key, style=self._s_help_key)
                text.append("   ", style=self._s_help_bg)
                text.append(desc, style=self._s_help_desc)
                remaining = w - left_pad - len(line_content)
                if remaining > 0:
                    text.append(" " * remaining, style=self._s_help_bg)
            else:
                text.append(" " * w, style=self._s_help_bg)
            if y < h - 1:
                text.append("\n")
        return text

    # -- helpers --

    def _centered_message(self, w: int, h: int, msg: str) -> Text:
        text = Text()
        mid = h // 2
        for y in range(h):
            if y == mid:
                text.append(self._pad_center(msg[:w], w), style=self._s_name)
            else:
                text.append(" " * w, style=self._s_bg)
            if y < h - 1:
                text.append("\n")
        return text

    def _assemble(
        self, chars: list[list[str]], styles: list[list[Style]], w: int, h: int,
    ) -> Text:
        text = Text()
        for y in range(h):
            row_c, row_s = chars[y], styles[y]
            x = 0
            while x < w:
                cur_s = row_s[x]
                end = x + 1
                while end < w and row_s[end] is cur_s:
                    end += 1
                text.append("".join(row_c[x:end]), style=cur_s)
                x = end
            if y < h - 1:
                text.append("\n")
        return text

    @staticmethod
    def _pad_center(s: str, width: int) -> str:
        pad = max((width - len(s)) // 2, 0)
        return " " * pad + s + " " * max(width - pad - len(s), 0)
