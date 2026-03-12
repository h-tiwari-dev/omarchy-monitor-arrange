from __future__ import annotations

import pytest

from omarchy_monitor_arrange.core.layout import DefaultLayoutEngine, SNAP_THRESHOLD
from omarchy_monitor_arrange.core.models import Monitor, Overlap


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mon(name: str, x: int, y: int, w: int = 1920, h: int = 1080,
         scale: float = 1.0, transform: int = 0) -> Monitor:
    return Monitor(
        name=name, description=name, width=w, height=h,
        x=x, y=y, scale=scale, transform=transform, refresh_rate=60.0,
    )


@pytest.fixture
def engine() -> DefaultLayoutEngine:
    return DefaultLayoutEngine()


# ---------------------------------------------------------------------------
# compute_snaps – edge snapping
# ---------------------------------------------------------------------------

class TestComputeSnapsEdge:
    def test_left_to_right_snap(self, engine: DefaultLayoutEngine):
        """Moving monitor's left edge near other's right edge -> snaps."""
        other = _mon("A", x=0, y=0)
        moving = _mon("B", x=1920 + 5, y=0)  # 5px gap
        result = engine.compute_snaps(moving, [other])
        assert result.snapped_x
        assert result.dx == -5  # pull left to close the gap

    def test_right_to_left_snap(self, engine: DefaultLayoutEngine):
        """Moving monitor's right edge near other's left edge -> snaps."""
        other = _mon("A", x=1920, y=0)
        moving = _mon("B", x=-5, y=0)  # right edge at 1915, other left at 1920
        result = engine.compute_snaps(moving, [other])
        assert result.snapped_x
        assert result.dx == 5

    def test_top_to_bottom_snap(self, engine: DefaultLayoutEngine):
        """Moving monitor's top near other's bottom."""
        other = _mon("A", x=0, y=0)
        moving = _mon("B", x=0, y=1080 + 10)
        result = engine.compute_snaps(moving, [other])
        assert result.snapped_y
        assert result.dy == -10

    def test_bottom_to_top_snap(self, engine: DefaultLayoutEngine):
        """Moving monitor's bottom near other's top."""
        other = _mon("A", x=0, y=1080)
        moving = _mon("B", x=0, y=-8)  # bottom at 1072, other top at 1080
        result = engine.compute_snaps(moving, [other])
        assert result.snapped_y
        assert result.dy == 8


# ---------------------------------------------------------------------------
# compute_snaps – alignment snapping
# ---------------------------------------------------------------------------

class TestComputeSnapsAlign:
    def test_left_to_left_align(self, engine: DefaultLayoutEngine):
        other = _mon("A", x=100, y=0)
        moving = _mon("B", x=105, y=1080)
        result = engine.compute_snaps(moving, [other])
        assert result.snapped_x
        assert result.dx == -5

    def test_right_to_right_align(self, engine: DefaultLayoutEngine):
        other = _mon("A", x=0, y=0)  # right = 1920
        moving = _mon("B", x=10, y=1080)  # right = 1930
        result = engine.compute_snaps(moving, [other])
        assert result.snapped_x
        assert result.dx == -10

    def test_center_x_align(self, engine: DefaultLayoutEngine):
        other = _mon("A", x=0, y=0, w=1920)  # center_x = 960
        moving = _mon("B", x=5, y=1080, w=1920)  # center_x = 965
        result = engine.compute_snaps(moving, [other])
        assert result.snapped_x
        assert result.dx == -5

    def test_center_y_align(self, engine: DefaultLayoutEngine):
        other = _mon("A", x=0, y=0, h=1080)  # center_y = 540
        moving = _mon("B", x=1920, y=10, h=1080)  # center_y = 550
        result = engine.compute_snaps(moving, [other])
        assert result.snapped_y
        assert result.dy == -10

    def test_top_to_top_align(self, engine: DefaultLayoutEngine):
        other = _mon("A", x=0, y=50)
        moving = _mon("B", x=1920, y=55)
        result = engine.compute_snaps(moving, [other])
        assert result.snapped_y
        assert result.dy == -5

    def test_bottom_to_bottom_align(self, engine: DefaultLayoutEngine):
        other = _mon("A", x=0, y=0, h=1080)  # bottom=1080
        moving = _mon("B", x=1920, y=15, h=1080)  # bottom=1095
        result = engine.compute_snaps(moving, [other])
        assert result.snapped_y
        assert result.dy == -15


# ---------------------------------------------------------------------------
# compute_snaps – no snap / closest
# ---------------------------------------------------------------------------

class TestComputeSnapsEdgeCases:
    def test_no_snap_when_far_apart(self, engine: DefaultLayoutEngine):
        other = _mon("A", x=0, y=0)
        moving = _mon("B", x=5000, y=5000)
        result = engine.compute_snaps(moving, [other])
        assert not result.snapped_x
        assert not result.snapped_y
        assert result.dx == 0
        assert result.dy == 0

    def test_picks_closest_snap(self, engine: DefaultLayoutEngine):
        """Two candidates within threshold: pick the one with smallest |delta|."""
        other1 = _mon("A", x=0, y=0)       # right = 1920
        other2 = _mon("C", x=1917, y=0)    # left = 1917
        moving = _mon("B", x=1918, y=0)    # left at 1918, right at 3838
        result = engine.compute_snaps(moving, [other1, other2])
        assert result.snapped_x
        assert abs(result.dx) <= SNAP_THRESHOLD

    def test_skips_self_in_others(self, engine: DefaultLayoutEngine):
        moving = _mon("A", x=100, y=100)
        same = _mon("A", x=0, y=0)
        result = engine.compute_snaps(moving, [same])
        assert not result.snapped_x
        assert not result.snapped_y

    def test_empty_others(self, engine: DefaultLayoutEngine):
        moving = _mon("A", x=100, y=100)
        result = engine.compute_snaps(moving, [])
        assert result.dx == 0
        assert result.dy == 0

    def test_snap_with_different_scales(self, engine: DefaultLayoutEngine):
        other = _mon("A", x=0, y=0, w=3840, h=2160, scale=2.0)  # scaled: 1920x1080
        moving = _mon("B", x=1925, y=0, w=2560, h=1440, scale=1.5)
        result = engine.compute_snaps(moving, [other])
        assert result.snapped_x
        assert result.dx == (other.right - moving.x)

    def test_snap_with_transform(self, engine: DefaultLayoutEngine):
        other = _mon("A", x=0, y=0, w=1920, h=1080, transform=1)  # scaled: 1080x1920
        moving = _mon("B", x=1085, y=0)
        result = engine.compute_snaps(moving, [other])
        assert result.snapped_x
        assert result.dx == (other.right - moving.x)


# ---------------------------------------------------------------------------
# normalize_positions
# ---------------------------------------------------------------------------

class TestNormalizePositions:
    def test_shifts_to_zero(self, engine: DefaultLayoutEngine):
        monitors = [_mon("A", x=100, y=200), _mon("B", x=300, y=400)]
        engine.normalize_positions(monitors)
        assert monitors[0].x == 0
        assert monitors[0].y == 0
        assert monitors[1].x == 200
        assert monitors[1].y == 200

    def test_already_normalized(self, engine: DefaultLayoutEngine):
        monitors = [_mon("A", x=0, y=0), _mon("B", x=1920, y=0)]
        engine.normalize_positions(monitors)
        assert monitors[0].x == 0
        assert monitors[0].y == 0
        assert monitors[1].x == 1920
        assert monitors[1].y == 0

    def test_negative_positions(self, engine: DefaultLayoutEngine):
        monitors = [_mon("A", x=-500, y=-300), _mon("B", x=100, y=50)]
        engine.normalize_positions(monitors)
        assert monitors[0].x == 0
        assert monitors[0].y == 0
        assert monitors[1].x == 600
        assert monitors[1].y == 350

    def test_empty_list(self, engine: DefaultLayoutEngine):
        engine.normalize_positions([])  # should not raise

    def test_single_monitor(self, engine: DefaultLayoutEngine):
        monitors = [_mon("A", x=500, y=300)]
        engine.normalize_positions(monitors)
        assert monitors[0].x == 0
        assert monitors[0].y == 0


# ---------------------------------------------------------------------------
# detect_overlaps
# ---------------------------------------------------------------------------

class TestDetectOverlaps:
    def test_no_overlap_side_by_side(self, engine: DefaultLayoutEngine):
        monitors = [_mon("A", x=0, y=0), _mon("B", x=1920, y=0)]
        assert engine.detect_overlaps(monitors) == []

    def test_partial_overlap(self, engine: DefaultLayoutEngine):
        monitors = [_mon("A", x=0, y=0), _mon("B", x=1000, y=500)]
        overlaps = engine.detect_overlaps(monitors)
        assert len(overlaps) == 1
        assert overlaps[0] == Overlap(monitor_a="A", monitor_b="B")

    def test_complete_overlap_same_position(self, engine: DefaultLayoutEngine):
        monitors = [_mon("A", x=0, y=0), _mon("B", x=0, y=0)]
        overlaps = engine.detect_overlaps(monitors)
        assert len(overlaps) == 1

    def test_touching_edges_not_overlapping(self, engine: DefaultLayoutEngine):
        monitors = [_mon("A", x=0, y=0), _mon("B", x=1920, y=0)]
        assert engine.detect_overlaps(monitors) == []

    def test_touching_top_bottom_not_overlapping(self, engine: DefaultLayoutEngine):
        monitors = [_mon("A", x=0, y=0), _mon("B", x=0, y=1080)]
        assert engine.detect_overlaps(monitors) == []

    def test_one_pixel_overlap(self, engine: DefaultLayoutEngine):
        monitors = [_mon("A", x=0, y=0), _mon("B", x=1919, y=0)]
        overlaps = engine.detect_overlaps(monitors)
        assert len(overlaps) == 1

    def test_multiple_overlapping_pairs(self, engine: DefaultLayoutEngine):
        monitors = [
            _mon("A", x=0, y=0),
            _mon("B", x=100, y=100),
            _mon("C", x=200, y=200),
        ]
        overlaps = engine.detect_overlaps(monitors)
        assert len(overlaps) == 3  # A-B, A-C, B-C
        names = {(o.monitor_a, o.monitor_b) for o in overlaps}
        assert ("A", "B") in names
        assert ("A", "C") in names
        assert ("B", "C") in names

    def test_empty_list(self, engine: DefaultLayoutEngine):
        assert engine.detect_overlaps([]) == []

    def test_single_monitor(self, engine: DefaultLayoutEngine):
        assert engine.detect_overlaps([_mon("A", x=0, y=0)]) == []

    def test_overlap_with_scaled_monitors(self, engine: DefaultLayoutEngine):
        a = _mon("A", x=0, y=0, w=3840, h=2160, scale=2.0)  # scaled 1920x1080
        b = _mon("B", x=1919, y=0)  # overlaps by 1 scaled pixel
        overlaps = engine.detect_overlaps([a, b])
        assert len(overlaps) == 1

    def test_no_overlap_with_scaled_monitors(self, engine: DefaultLayoutEngine):
        a = _mon("A", x=0, y=0, w=3840, h=2160, scale=2.0)  # scaled 1920x1080
        b = _mon("B", x=1920, y=0)
        assert engine.detect_overlaps([a, b]) == []
