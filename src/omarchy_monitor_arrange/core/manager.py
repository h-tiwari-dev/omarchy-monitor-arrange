from __future__ import annotations

import copy
from typing import Callable

from omarchy_monitor_arrange.core.models import (
    Monitor,
    Overlap,
    SCALE_CYCLE,
    TRANSFORM_CYCLE,
)


class MonitorManager:
    """Central state holder: mediates between backend, layout engine, config writer, and UI."""

    COARSE_STEP = 50
    FINE_STEP = 5

    def __init__(self, backend, layout_engine, config_writer):
        self._backend = backend
        self._layout = layout_engine
        self._config = config_writer
        self._monitors: list[Monitor] = []
        self._selected_index: int = 0
        self._primary_name: str | None = None
        self._history: list[list[dict]] = []
        self._on_change: list[Callable] = []
        self._saved_snapshot: list[dict] | None = None

    # -- Observer pattern --

    def on_change(self, callback: Callable) -> None:
        self._on_change.append(callback)

    def _notify(self) -> None:
        for cb in self._on_change:
            cb()

    # -- Snapshots for undo / dirty tracking --

    def _snapshot(self) -> list[dict]:
        return [
            {"name": m.name, "x": m.x, "y": m.y, "width": m.width,
             "height": m.height, "scale": m.scale, "transform": m.transform,
             "refresh_rate": m.refresh_rate}
            for m in self._monitors
        ]

    def _restore_snapshot(self, snap: list[dict]) -> None:
        by_name = {s["name"]: s for s in snap}
        for m in self._monitors:
            if m.name in by_name:
                s = by_name[m.name]
                m.x, m.y = s["x"], s["y"]
                m.width, m.height = s["width"], s["height"]
                m.scale = s["scale"]
                m.transform = s["transform"]
                m.refresh_rate = s["refresh_rate"]

    # -- Initialization --

    def load_monitors(self) -> None:
        self._monitors = self._backend.get_monitors()
        if self._monitors:
            self._primary_name = self._monitors[0].name
            self._selected_index = next(
                (i for i, m in enumerate(self._monitors) if m.focused), 0
            )
        self._saved_snapshot = self._snapshot()
        self._history.clear()
        self._notify()

    # -- Selection --

    @property
    def selected(self) -> Monitor | None:
        if not self._monitors:
            return None
        return self._monitors[self._selected_index]

    @property
    def selected_index(self) -> int:
        return self._selected_index

    def select_next(self) -> None:
        if self._monitors:
            self._selected_index = (self._selected_index + 1) % len(self._monitors)
            self._notify()

    def select_prev(self) -> None:
        if self._monitors:
            self._selected_index = (self._selected_index - 1) % len(self._monitors)
            self._notify()

    # -- Movement --

    def move_selected(self, dx: int, dy: int, snap: bool = True) -> None:
        mon = self.selected
        if mon is None:
            return
        self._push_undo()
        mon.x += dx
        mon.y += dy
        if snap:
            others = [m for m in self._monitors if m.name != mon.name]
            result = self._layout.compute_snaps(mon, others, move_dx=dx, move_dy=dy)
            mon.x += result.dx
            mon.y += result.dy
        self._notify()

    # -- Settings cycling --

    def cycle_resolution(self) -> None:
        mon = self.selected
        if mon is None or not mon.available_modes:
            return
        self._push_undo()
        resolutions = self._unique_resolutions(mon)
        current = f"{mon.width}x{mon.height}"
        try:
            idx = resolutions.index(current)
        except ValueError:
            idx = -1
        next_res = resolutions[(idx + 1) % len(resolutions)]
        w, h = next_res.split("x")
        mon.width, mon.height = int(w), int(h)
        self._notify()

    def cycle_scale(self) -> None:
        mon = self.selected
        if mon is None:
            return
        self._push_undo()
        try:
            idx = SCALE_CYCLE.index(mon.scale)
        except ValueError:
            idx = -1
        mon.scale = SCALE_CYCLE[(idx + 1) % len(SCALE_CYCLE)]
        self._notify()

    def cycle_refresh_rate(self) -> None:
        mon = self.selected
        if mon is None or not mon.available_modes:
            return
        self._push_undo()
        rates = self._available_refresh_rates(mon)
        if not rates:
            return
        try:
            closest = min(rates, key=lambda r: abs(r - mon.refresh_rate))
            idx = rates.index(closest)
        except ValueError:
            idx = -1
        mon.refresh_rate = rates[(idx + 1) % len(rates)]
        self._notify()

    def cycle_transform(self) -> None:
        mon = self.selected
        if mon is None:
            return
        self._push_undo()
        try:
            idx = TRANSFORM_CYCLE.index(mon.transform)
        except ValueError:
            idx = -1
        mon.transform = TRANSFORM_CYCLE[(idx + 1) % len(TRANSFORM_CYCLE)]
        self._notify()

    def set_primary(self) -> None:
        mon = self.selected
        if mon is None:
            return
        self._primary_name = mon.name
        self._notify()

    # -- Actions --

    def apply(self) -> None:
        self._layout.normalize_positions(self._monitors)
        self._config.backup()
        self._config.write(self._monitors, self._primary_name)
        self._backend.reload_config()
        self._saved_snapshot = self._snapshot()
        self._history.clear()
        self._notify()

    def undo(self) -> None:
        if not self._history:
            return
        snap = self._history.pop()
        self._restore_snapshot(snap)
        self._notify()

    def reset(self) -> None:
        """Soft reset: restore to the last applied/saved state."""
        if self._saved_snapshot is None:
            return
        self._restore_snapshot(self._saved_snapshot)
        self._history.clear()
        self._notify()

    def hard_reset(self) -> None:
        """Hard reset: restore Hyprland defaults (auto-detect all monitors), reload, and re-read."""
        self._config.backup()
        self._config.write_defaults()
        self._backend.reload_config()
        self.load_monitors()

    def identify(self) -> None:
        for m in self._monitors:
            self._backend.identify_monitor(m.name)

    def highlight_selected(self) -> None:
        mon = self.selected
        if mon is None:
            return
        self._backend.highlight_monitor(mon.name)

    def clear_highlight(self) -> None:
        self._backend.clear_highlight()

    # -- Queries --

    @property
    def monitors(self) -> list[Monitor]:
        return list(self._monitors)

    @property
    def primary_name(self) -> str | None:
        return self._primary_name

    @property
    def overlaps(self) -> list[Overlap]:
        return self._layout.detect_overlaps(self._monitors)

    @property
    def has_unsaved_changes(self) -> bool:
        return self._snapshot() != self._saved_snapshot

    # -- Helpers --

    def _push_undo(self) -> None:
        self._history.append(self._snapshot())

    @staticmethod
    def _unique_resolutions(mon: Monitor) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for mode in mon.available_modes:
            res = mode.split("@")[0]
            if res not in seen:
                seen.add(res)
                result.append(res)
        return result

    @staticmethod
    def _available_refresh_rates(mon: Monitor) -> list[float]:
        current_res = f"{mon.width}x{mon.height}"
        rates: list[float] = []
        for mode in mon.available_modes:
            parts = mode.split("@")
            if parts[0] == current_res and len(parts) == 2:
                rate_str = parts[1].rstrip("Hz")
                try:
                    rates.append(float(rate_str))
                except ValueError:
                    continue
        return sorted(set(rates))
