from __future__ import annotations

from typing import Iterable

from omarchy_monitor_arrange.core.models import Monitor


def compute_transform(
    monitors: Iterable[Monitor],
    canvas_w: int,
    canvas_h: int,
    padding: int,
    min_cells: int = 8,
) -> tuple[float, float, float]:
    monitors = list(monitors)
    if not monitors:
        return 0.0, 0.0, 1.0

    min_x = min(m.x for m in monitors)
    min_y = min(m.y for m in monitors)
    max_x = max(m.right for m in monitors)
    max_y = max(m.bottom for m in monitors)

    layout_w = max(max_x - min_x, 1)
    layout_h = max(max_y - min_y, 1)

    usable_w = max(canvas_w - 2 * padding, 1)
    usable_h = max(canvas_h - 2 * padding, 1)
    scale = min(usable_w / layout_w, usable_h / layout_h)
    scale = max(scale, min_cells / max(layout_w, layout_h))

    off_x = padding + (usable_w - layout_w * scale) / 2 - min_x * scale
    off_y = padding + (usable_h - layout_h * scale) / 2 - min_y * scale
    return off_x, off_y, scale


def map_point(x: float, y: float, off_x: float, off_y: float, scale: float) -> tuple[int, int]:
    return int(round(off_x + x * scale)), int(round(off_y + y * scale))
