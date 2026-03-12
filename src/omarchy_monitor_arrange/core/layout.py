from __future__ import annotations

from omarchy_monitor_arrange.core.models import Monitor, Overlap, SnapResult

SNAP_THRESHOLD = 50


class DefaultLayoutEngine:
    """Pure-logic layout engine: snapping, normalization, overlap detection."""

    def __init__(self, snap_threshold: int = SNAP_THRESHOLD):
        self._threshold = snap_threshold

    def compute_snaps(
        self, moving: Monitor, others: list[Monitor],
        move_dx: int = 0, move_dy: int = 0,
    ) -> SnapResult:
        best_dx: int | None = None
        best_dy: int | None = None

        for other in others:
            if other.name == moving.name:
                continue

            # --- horizontal snaps ---
            h_candidates = [
                other.right - moving.x,        # snap left edge to other's right
                other.x - moving.right,         # snap right edge to other's left
                other.x - moving.x,             # align left edges
                other.right - moving.right,     # align right edges
                other.center_x - moving.center_x,  # align centres
            ]
            for dx in h_candidates:
                if abs(dx) > self._threshold:
                    continue
                if self._opposes(dx, move_dx):
                    continue
                if best_dx is None or abs(dx) < abs(best_dx):
                    best_dx = dx

            # --- vertical snaps ---
            v_candidates = [
                other.bottom - moving.y,        # snap top edge to other's bottom
                other.y - moving.bottom,         # snap bottom edge to other's top
                other.y - moving.y,              # align top edges
                other.bottom - moving.bottom,    # align bottom edges
                other.center_y - moving.center_y,  # align centres
            ]
            for dy in v_candidates:
                if abs(dy) > self._threshold:
                    continue
                if self._opposes(dy, move_dy):
                    continue
                if best_dy is None or abs(dy) < abs(best_dy):
                    best_dy = dy

        return SnapResult(
            dx=best_dx or 0,
            dy=best_dy or 0,
            snapped_x=best_dx is not None,
            snapped_y=best_dy is not None,
        )

    @staticmethod
    def _opposes(snap_delta: int, move_delta: int) -> bool:
        """True if the snap would erase all forward progress from the movement."""
        if move_delta == 0:
            return False
        net = move_delta + snap_delta
        if move_delta > 0:
            return net <= 0
        return net >= 0

    def normalize_positions(self, monitors: list[Monitor]) -> None:
        if not monitors:
            return
        min_x = min(m.x for m in monitors)
        min_y = min(m.y for m in monitors)
        for m in monitors:
            m.x -= min_x
            m.y -= min_y

    def detect_overlaps(self, monitors: list[Monitor]) -> list[Overlap]:
        overlaps: list[Overlap] = []
        for i, a in enumerate(monitors):
            for b in monitors[i + 1 :]:
                if (
                    a.x < b.right
                    and a.right > b.x
                    and a.y < b.bottom
                    and a.bottom > b.y
                ):
                    overlaps.append(Overlap(monitor_a=a.name, monitor_b=b.name))
        return overlaps
