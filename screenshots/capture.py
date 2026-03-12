"""Render the monitor-arrange TUI at various states and write ANSI text files.

Each output file can be piped to shellfie-cli to produce SVGs.
Usage: python screenshots/capture.py
"""
from __future__ import annotations

import os
import sys
from io import StringIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from rich.console import Console
from rich.style import Style
from rich.text import Text

from omarchy_monitor_arrange.core.models import Monitor, Overlap
from omarchy_monitor_arrange.theme import DEFAULT_COLORS
from omarchy_monitor_arrange.ui.textual.geometry import compute_transform, map_point

CANVAS_W = 72
CANVAS_H = 22
STATUS_LINES = 2
SHORTCUT_LINES = 2
TOTAL_H = CANVAS_H + STATUS_LINES + SHORTCUT_LINES

PADDING = 2
MIN_BOX_W = 20
MIN_BOX_H = 5

_LIGHT = {"tl": "┌", "tr": "┐", "bl": "└", "br": "┘", "h": "─", "v": "│"}
_HEAVY = {"tl": "┏", "tr": "┓", "bl": "┗", "br": "┛", "h": "━", "v": "┃"}


def _hex(rgba):
    return f"#{int(rgba[0]*255):02x}{int(rgba[1]*255):02x}{int(rgba[2]*255):02x}"


SAMPLE_MONITORS = [
    Monitor("HDMI-A-1", "LG 27UK850", 2560, 1440, 0, 0, 1.0, 0, 60.0,
            ["2560x1440@60Hz", "1920x1080@60Hz"], focused=True),
    Monitor("DP-2", "Dell U2723QE", 2560, 1440, 2560, 0, 1.0, 0, 60.0,
            ["2560x1440@144Hz", "2560x1440@60Hz"]),
    Monitor("eDP-1", "Built-in", 1920, 1200, 640, 1440, 1.5, 0, 60.0,
            ["1920x1200@60Hz"]),
]

OUT_DIR = Path(__file__).resolve().parent


class Styles:
    def __init__(self, c: dict):
        bg = _hex(c.get("bg", (0.12, 0.12, 0.14, 1.0)))
        fill = _hex(c.get("monitor_fill", (0.22, 0.22, 0.26, 1.0)))
        border = _hex(c.get("monitor_border", (0.4, 0.4, 0.45, 1.0)))
        sel = _hex(c.get("selected_border", (0.4, 0.6, 1.0, 1.0)))
        txt = _hex(c.get("text", (0.9, 0.9, 0.92, 1.0)))
        dim = _hex(c.get("text_dim", (0.6, 0.6, 0.65, 1.0)))
        warn = _hex(c.get("overlap_warn", (1.0, 0.4, 0.3, 0.6)))
        status_bg = _hex(c.get("status_bg", (0.15, 0.15, 0.18, 1.0)))

        self.bg = Style(color=dim, bgcolor=bg)
        self.border = Style(color=border, bgcolor=bg)
        self.sel_border = Style(color=sel, bgcolor=bg, bold=True)
        self.fill = Style(bgcolor=fill)
        self.sel_fill = Style(bgcolor=fill)
        self.name = Style(color=txt, bgcolor=fill, bold=True)
        self.sel_name = Style(color=sel, bgcolor=fill, bold=True)
        self.detail = Style(color=dim, bgcolor=fill)
        self.overlap = Style(color=warn, bgcolor=bg, bold=True)
        self.status_bg = Style(color=txt, bgcolor=status_bg)
        self.shortcut_bg = Style(color=dim, bgcolor=status_bg)
        self.help_title = Style(color=sel, bold=True)
        self.help_key = Style(color=sel)
        self.help_desc = Style(color=txt)
        self.help_bg = Style(color=dim, bgcolor=bg)


# ---------------------------------------------------------------------------
# Drawing primitives (mirrors canvas.py logic)
# ---------------------------------------------------------------------------

def draw_box(chars, styles, left, top, right, bottom, box, s):
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
    for cy, cx, oy, ox, key in [
        (t, l, top, left, "tl"), (t, r, top, right, "tr"),
        (b, l, bottom, left, "bl"), (b, r, bottom, right, "br"),
    ]:
        if cy == oy and cx == ox:
            chars[cy][cx], styles[cy][cx] = box[key], s


def fill_rect(chars, styles, left, top, right, bottom, s):
    max_y, max_x = len(chars) - 1, len(chars[0]) - 1
    for y in range(max(top, 0), min(bottom + 1, max_y + 1)):
        for x in range(max(left, 0), min(right + 1, max_x + 1)):
            chars[y][x], styles[y][x] = " ", s


def draw_labels(chars, styles, left, top, right, bottom, lines, name_s, detail_s):
    iw, ih = right - left - 1, bottom - top - 1
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
        s = name_s if i == 0 else detail_s
        for j, ch in enumerate(trimmed):
            x = sx + j
            if 0 <= x < len(chars[y]):
                chars[y][x], styles[y][x] = ch, s


def draw_monitor(chars, styles, mon, off_x, off_y, scale, selected, primary_name, st):
    left, top = map_point(mon.x, mon.y, off_x, off_y, scale)
    right, bottom = map_point(mon.right, mon.bottom, off_x, off_y, scale)
    if right - left + 1 < MIN_BOX_W:
        right = left + MIN_BOX_W - 1
    if bottom - top + 1 < MIN_BOX_H:
        bottom = top + MIN_BOX_H - 1

    box = _HEAVY if selected else _LIGHT
    border_s = st.sel_border if selected else st.border
    fill_s = st.sel_fill if selected else st.fill
    name_s = st.sel_name if selected else st.name

    fill_rect(chars, styles, left + 1, top + 1, right - 1, bottom - 1, fill_s)
    draw_box(chars, styles, left, top, right, bottom, box, border_s)

    name = mon.name
    if mon.name == primary_name:
        name = f"★ {name}"
    labels = [name, f"{mon.width}×{mon.height}", f"@{mon.refresh_rate:.0f}Hz {mon.scale}x"]
    draw_labels(chars, styles, left, top, right, bottom, labels, name_s, st.detail)


# ---------------------------------------------------------------------------
# Screen assembly
# ---------------------------------------------------------------------------

def assemble_text(chars, styles, w, h):
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


def render_canvas(monitors, selected_idx, primary_name, st, w=CANVAS_W, h=CANVAS_H):
    chars = [[" "] * w for _ in range(h)]
    styles_grid = [[st.bg] * w for _ in range(h)]

    off_x, off_y, scale = compute_transform(
        monitors, canvas_w=w, canvas_h=h, padding=PADDING, min_cells=MIN_BOX_W,
    )

    for idx, mon in enumerate(monitors):
        if idx != selected_idx:
            draw_monitor(chars, styles_grid, mon, off_x, off_y, scale, False, primary_name, st)
    if 0 <= selected_idx < len(monitors):
        draw_monitor(chars, styles_grid, monitors[selected_idx], off_x, off_y, scale, True, primary_name, st)

    return assemble_text(chars, styles_grid, w, h)


def render_status(monitors, selected_idx, primary_name, st, w=CANVAS_W):
    from omarchy_monitor_arrange.core.models import TRANSFORM_LABELS
    mon = monitors[selected_idx] if 0 <= selected_idx < len(monitors) else None
    if mon is None:
        return Text("No monitors", style=st.status_bg)

    primary_tag = " ★" if mon.name == primary_name else ""
    tf = TRANSFORM_LABELS.get(mon.transform, str(mon.transform))
    line1 = f" Selected: {mon.name}{primary_tag}  Res: {mon.width}x{mon.height}  Refresh: {mon.refresh_rate:.0f}Hz  Scale: {mon.scale}x"
    line2 = f" Position: {mon.x},{mon.y}  Transform: {tf}"

    text = Text()
    text.append(line1.ljust(w), style=st.status_bg)
    text.append("\n")
    text.append(line2.ljust(w), style=st.status_bg)
    return text


def render_shortcuts(st, w=CANVAS_W):
    keys = [
        ("Tab", "Select"), ("←↑↓→", "Move"), ("r", "Res"), ("s", "Scale"),
        ("f", "Hz"), ("t", "Rotate"), ("p", "Primary"), ("i", "Identify"),
        ("u", "Undo"), ("Ctrl+r", "Reset"), ("Enter", "Apply"),
        ("Esc", "Close"), ("h", "Help"),
    ]
    text = Text()
    line = Text()
    for i, (key, desc) in enumerate(keys):
        if i > 0:
            line.append("  ", style="dim")
        line.append(f" {key} ", style="reverse")
        line.append(f" {desc}", style="")

    row1_parts = []
    row2_parts = []
    split_at = 8
    for i, (key, desc) in enumerate(keys):
        part = Text()
        if row1_parts or row2_parts:
            part.append("  ", style=st.shortcut_bg)
        part.append(f" {key} ", style="reverse")
        part.append(f" {desc}", style=st.shortcut_bg)
        if i < split_at:
            row1_parts.append(part)
        else:
            row2_parts.append(part)

    text = Text()
    text.append(" ", style=st.shortcut_bg)
    for p in row1_parts:
        text.append_text(p)
    pad1 = max(w - sum(len(p.plain) for p in row1_parts) - 1, 0)
    text.append(" " * pad1, style=st.shortcut_bg)
    text.append("\n")
    text.append(" ", style=st.shortcut_bg)
    for p in row2_parts:
        text.append_text(p)
    pad2 = max(w - sum(len(p.plain) for p in row2_parts) - 1, 0)
    text.append(" " * pad2, style=st.shortcut_bg)
    return text


def render_help(st, w=CANVAS_W, h=CANVAS_H):
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

    def pad_center(s, width):
        pad = max((width - len(s)) // 2, 0)
        return " " * pad + s + " " * max(width - pad - len(s), 0)

    text = Text()
    for y in range(h):
        if y == start_y:
            text.append(pad_center(title, w), style=st.help_title)
        elif y == start_y + 1:
            bar = "─" * min(len(title) + 4, w)
            text.append(pad_center(bar, w), style=st.help_key)
        elif y == start_y + 2:
            text.append(" " * w, style=st.help_bg)
        elif start_y + 3 <= y < start_y + 3 + len(entries):
            idx = y - start_y - 3
            key, desc = entries[idx]
            padded_key = key.rjust(key_col)
            line_content = f"{padded_key}   {desc}"
            left_pad = max((w - len(line_content)) // 2, 0)
            text.append(" " * left_pad, style=st.help_bg)
            text.append(padded_key, style=st.help_key)
            text.append("   ", style=st.help_bg)
            text.append(desc, style=st.help_desc)
            remaining = w - left_pad - len(line_content)
            if remaining > 0:
                text.append(" " * remaining, style=st.help_bg)
        else:
            text.append(" " * w, style=st.help_bg)
        if y < h - 1:
            text.append("\n")
    return text


def render_full_screen(monitors, selected_idx, primary_name, st, help_mode=False):
    if help_mode:
        canvas = render_help(st)
    else:
        canvas = render_canvas(monitors, selected_idx, primary_name, st)
    status = render_status(monitors, selected_idx, primary_name, st)
    shortcuts = render_shortcuts(st)

    full = Text()
    full.append_text(canvas)
    full.append("\n")
    full.append_text(status)
    full.append("\n")
    full.append_text(shortcuts)
    return full


def text_to_ansi(rich_text: Text, width: int = CANVAS_W) -> str:
    buf = StringIO()
    console = Console(
        file=buf, width=width, force_terminal=True,
        color_system="truecolor", no_color=False,
    )
    console.print(rich_text, end="", overflow="crop", no_wrap=True)
    return buf.getvalue()


def main():
    st = Styles(DEFAULT_COLORS)
    monitors = SAMPLE_MONITORS
    primary = "eDP-1"

    screens = {
        "main": render_full_screen(monitors, 0, primary, st),
        "select-dp2": render_full_screen(monitors, 1, primary, st),
        "select-edp1": render_full_screen(monitors, 2, primary, st),
        "help": render_full_screen(monitors, 0, primary, st, help_mode=True),
    }

    for name, content in screens.items():
        ansi = text_to_ansi(content)
        path = OUT_DIR / f"{name}.ansi"
        path.write_text(ansi)
        print(f"  Wrote {path}")


if __name__ == "__main__":
    main()
