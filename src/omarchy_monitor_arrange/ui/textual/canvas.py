from __future__ import annotations

from typing import TYPE_CHECKING

from rich.text import Text
from textual.widget import Widget

from omarchy_monitor_arrange.ui.textual.geometry import compute_transform, map_point

if TYPE_CHECKING:
    from omarchy_monitor_arrange.core.manager import MonitorManager
    from omarchy_monitor_arrange.core.models import Monitor

PADDING = 2
MIN_BOX_W = 6
MIN_BOX_H = 4


class MonitorCanvasWidget(Widget, can_focus=True):
    """Character-based canvas that renders monitor arrangement."""

    def __init__(self, manager: MonitorManager, colors: dict):
        super().__init__()
        self._manager = manager
        self._colors = colors
        self._show_help = False

    @property
    def show_help(self) -> bool:
        return self._show_help

    @show_help.setter
    def show_help(self, value: bool) -> None:
        self._show_help = value
        self.refresh()

    def render(self) -> Text:
        width = max(self.size.width, 1)
        height = max(self.size.height, 1)

        if self._show_help:
            return self._render_help(width, height)

        grid = [[" "] * width for _ in range(height)]
        monitors = self._manager.monitors
        if not monitors:
            return self._center_text(grid, "No monitors detected")

        off_x, off_y, scale = compute_transform(
            monitors,
            canvas_w=width,
            canvas_h=height,
            padding=PADDING,
            min_cells=MIN_BOX_W,
        )

        for idx, mon in enumerate(monitors):
            selected = idx == self._manager.selected_index
            self._draw_monitor(grid, mon, off_x, off_y, scale, selected)

        if self._manager.overlaps:
            self._draw_overlaps(grid, monitors, off_x, off_y, scale)

        return Text("\n".join("".join(row) for row in grid))

    def _draw_monitor(
        self,
        grid: list[list[str]],
        mon: Monitor,
        off_x: float,
        off_y: float,
        scale: float,
        selected: bool,
    ) -> None:
        left, top = map_point(mon.x, mon.y, off_x, off_y, scale)
        right, bottom = map_point(mon.right, mon.bottom, off_x, off_y, scale)

        if right <= left:
            right = left + MIN_BOX_W - 1
        if bottom <= top:
            bottom = top + MIN_BOX_H - 1

        width = right - left + 1
        height = bottom - top + 1

        if width < MIN_BOX_W:
            right = left + MIN_BOX_W - 1
        if height < MIN_BOX_H:
            bottom = top + MIN_BOX_H - 1

        border = "#" if selected else "+"
        horiz = "#" if selected else "-"
        vert = "#" if selected else "|"

        self._draw_box(grid, left, top, right, bottom, border, horiz, vert)

        label_lines = [mon.name, f"{mon.width}x{mon.height}", f"@{mon.refresh_rate:.0f} {mon.scale}x"]
        if mon.name == self._manager.primary_name:
            label_lines[0] = f"* {label_lines[0]}"

        self._draw_labels(grid, left, top, right, bottom, label_lines)

    def _draw_overlaps(
        self,
        grid: list[list[str]],
        monitors: list[Monitor],
        off_x: float,
        off_y: float,
        scale: float,
    ) -> None:
        by_name = {m.name: m for m in monitors}
        for overlap in self._manager.overlaps:
            a = by_name.get(overlap.monitor_a)
            b = by_name.get(overlap.monitor_b)
            if not a or not b:
                continue
            ix = max(a.x, b.x)
            iy = max(a.y, b.y)
            ix2 = min(a.right, b.right)
            iy2 = min(a.bottom, b.bottom)
            if ix >= ix2 or iy >= iy2:
                continue
            left, top = map_point(ix, iy, off_x, off_y, scale)
            right, bottom = map_point(ix2, iy2, off_x, off_y, scale)
            for y in range(max(top, 0), min(bottom + 1, len(grid))):
                row = grid[y]
                for x in range(max(left, 0), min(right + 1, len(row))):
                    if row[x] == " ":
                        row[x] = "!"

    def _draw_box(
        self,
        grid: list[list[str]],
        left: int,
        top: int,
        right: int,
        bottom: int,
        corner: str,
        horiz: str,
        vert: str,
    ) -> None:
        max_y = len(grid) - 1
        max_x = len(grid[0]) - 1

        left = max(left, 0)
        top = max(top, 0)
        right = min(right, max_x)
        bottom = min(bottom, max_y)

        if right <= left or bottom <= top:
            return

        for x in range(left + 1, right):
            grid[top][x] = horiz
            grid[bottom][x] = horiz
        for y in range(top + 1, bottom):
            grid[y][left] = vert
            grid[y][right] = vert

        grid[top][left] = corner
        grid[top][right] = corner
        grid[bottom][left] = corner
        grid[bottom][right] = corner

    def _draw_labels(
        self,
        grid: list[list[str]],
        left: int,
        top: int,
        right: int,
        bottom: int,
        lines: list[str],
    ) -> None:
        inner_width = right - left - 1
        inner_height = bottom - top - 1
        if inner_width <= 0 or inner_height <= 0:
            return

        start_y = top + 1 + max((inner_height - len(lines)) // 2, 0)
        for i, line in enumerate(lines[:inner_height]):
            if not line:
                continue
            trimmed = line[:inner_width]
            start_x = left + 1 + max((inner_width - len(trimmed)) // 2, 0)
            y = start_y + i
            if 0 <= y < len(grid):
                row = grid[y]
                for j, ch in enumerate(trimmed):
                    x = start_x + j
                    if 0 <= x < len(row):
                        row[x] = ch

    def _render_help(self, width: int, height: int) -> Text:
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
            "Ctrl+Shift+r       Hard reset",
            "Enter              Apply & reload",
            "Escape             Close",
            "h / ?              Toggle this help",
        ]
        grid = [[" "] * width for _ in range(height)]
        start_y = max((height - len(lines)) // 2, 0)
        for i, line in enumerate(lines):
            if start_y + i >= height:
                break
            trimmed = line[:width]
            start_x = max((width - len(trimmed)) // 2, 0)
            row = grid[start_y + i]
            for j, ch in enumerate(trimmed):
                if start_x + j < width:
                    row[start_x + j] = ch
        return Text("\n".join("".join(row) for row in grid))

    @staticmethod
    def _center_text(grid: list[list[str]], text: str) -> Text:
        height = len(grid)
        width = len(grid[0]) if height else 0
        if height == 0 or width == 0:
            return Text("")
        text = text[:width]
        y = height // 2
        x = max((width - len(text)) // 2, 0)
        for i, ch in enumerate(text):
            grid[y][x + i] = ch
        return Text("\n".join("".join(row) for row in grid))
