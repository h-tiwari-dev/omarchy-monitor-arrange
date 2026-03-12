from __future__ import annotations

import pytest

from omarchy_monitor_arrange.core.models import (
    Monitor,
    Overlap,
    SnapResult,
    SCALE_CYCLE,
    TRANSFORM_CYCLE,
    TRANSFORM_LABELS,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def basic_monitor() -> Monitor:
    return Monitor(
        name="DP-1",
        description="Test Monitor",
        width=1920,
        height=1080,
        x=0,
        y=0,
        scale=1.0,
        transform=0,
        refresh_rate=60.0,
    )


@pytest.fixture
def offset_monitor() -> Monitor:
    return Monitor(
        name="DP-2",
        description="Second Monitor",
        width=2560,
        height=1440,
        x=1920,
        y=0,
        scale=1.0,
        transform=0,
        refresh_rate=144.0,
    )


# ---------------------------------------------------------------------------
# scaled_width / scaled_height – varying scale
# ---------------------------------------------------------------------------

class TestScaledDimensionsWithScale:
    def test_scale_1(self, basic_monitor: Monitor):
        assert basic_monitor.scaled_width == 1920
        assert basic_monitor.scaled_height == 1080

    def test_scale_1_5(self, basic_monitor: Monitor):
        basic_monitor.scale = 1.5
        assert basic_monitor.scaled_width == int(1920 / 1.5)
        assert basic_monitor.scaled_height == int(1080 / 1.5)

    def test_scale_2(self, basic_monitor: Monitor):
        basic_monitor.scale = 2.0
        assert basic_monitor.scaled_width == 960
        assert basic_monitor.scaled_height == 540

    def test_scale_3(self, basic_monitor: Monitor):
        basic_monitor.scale = 3.0
        assert basic_monitor.scaled_width == 640
        assert basic_monitor.scaled_height == 360


# ---------------------------------------------------------------------------
# scaled_width / scaled_height – varying transform
# ---------------------------------------------------------------------------

class TestScaledDimensionsWithTransform:
    """Transforms 1,3,5,7 swap width/height; 0,2,4,6 do not."""

    @pytest.mark.parametrize("transform", [0, 2, 4, 6])
    def test_non_rotating_transforms(self, basic_monitor: Monitor, transform: int):
        basic_monitor.transform = transform
        assert basic_monitor.scaled_width == 1920
        assert basic_monitor.scaled_height == 1080

    @pytest.mark.parametrize("transform", [1, 3, 5, 7])
    def test_rotating_transforms(self, basic_monitor: Monitor, transform: int):
        basic_monitor.transform = transform
        assert basic_monitor.scaled_width == 1080
        assert basic_monitor.scaled_height == 1920


# ---------------------------------------------------------------------------
# All combinations of transform + scale
# ---------------------------------------------------------------------------

class TestTransformAndScaleCombinations:
    @pytest.mark.parametrize("scale", [1.0, 1.5, 2.0, 3.0])
    @pytest.mark.parametrize("transform", range(8))
    def test_combined(self, basic_monitor: Monitor, scale: float, transform: int):
        basic_monitor.scale = scale
        basic_monitor.transform = transform

        w, h = 1920, 1080
        if transform in (1, 3, 5, 7):
            w, h = h, w

        assert basic_monitor.scaled_width == int(w / scale)
        assert basic_monitor.scaled_height == int(h / scale)


# ---------------------------------------------------------------------------
# right / bottom / center_x / center_y
# ---------------------------------------------------------------------------

class TestDerivedPositions:
    def test_right(self, basic_monitor: Monitor):
        assert basic_monitor.right == 1920

    def test_bottom(self, basic_monitor: Monitor):
        assert basic_monitor.bottom == 1080

    def test_center_x(self, basic_monitor: Monitor):
        assert basic_monitor.center_x == 960

    def test_center_y(self, basic_monitor: Monitor):
        assert basic_monitor.center_y == 540

    def test_right_with_offset(self, offset_monitor: Monitor):
        assert offset_monitor.right == 1920 + 2560

    def test_bottom_with_offset(self, offset_monitor: Monitor):
        assert offset_monitor.bottom == 1440

    def test_center_x_with_offset(self, offset_monitor: Monitor):
        assert offset_monitor.center_x == 1920 + 2560 // 2

    def test_center_y_with_offset(self, offset_monitor: Monitor):
        assert offset_monitor.center_y == 1440 // 2

    def test_right_with_scale(self, basic_monitor: Monitor):
        basic_monitor.scale = 2.0
        assert basic_monitor.right == 960

    def test_bottom_with_scale(self, basic_monitor: Monitor):
        basic_monitor.scale = 2.0
        assert basic_monitor.bottom == 540

    def test_center_with_transform_rotation(self, basic_monitor: Monitor):
        basic_monitor.transform = 1
        assert basic_monitor.center_x == 1080 // 2
        assert basic_monitor.center_y == 1920 // 2


# ---------------------------------------------------------------------------
# SnapResult defaults
# ---------------------------------------------------------------------------

class TestSnapResult:
    def test_defaults(self):
        sr = SnapResult()
        assert sr.dx == 0
        assert sr.dy == 0
        assert sr.snapped_x is False
        assert sr.snapped_y is False

    def test_custom_values(self):
        sr = SnapResult(dx=5, dy=-3, snapped_x=True, snapped_y=True)
        assert sr.dx == 5
        assert sr.dy == -3
        assert sr.snapped_x is True
        assert sr.snapped_y is True


# ---------------------------------------------------------------------------
# Overlap dataclass
# ---------------------------------------------------------------------------

class TestOverlap:
    def test_creation(self):
        o = Overlap(monitor_a="DP-1", monitor_b="DP-2")
        assert o.monitor_a == "DP-1"
        assert o.monitor_b == "DP-2"

    def test_equality(self):
        a = Overlap(monitor_a="DP-1", monitor_b="DP-2")
        b = Overlap(monitor_a="DP-1", monitor_b="DP-2")
        assert a == b

    def test_inequality(self):
        a = Overlap(monitor_a="DP-1", monitor_b="DP-2")
        b = Overlap(monitor_a="DP-2", monitor_b="DP-1")
        assert a != b


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

class TestConstants:
    def test_scale_cycle_values(self):
        assert SCALE_CYCLE == [1.0, 1.25, 1.5, 1.75, 2.0, 3.0]

    def test_transform_cycle_values(self):
        assert TRANSFORM_CYCLE == [0, 1, 2, 3]

    def test_transform_labels_keys(self):
        assert set(TRANSFORM_LABELS.keys()) == set(range(8))

    def test_transform_labels_normal(self):
        assert TRANSFORM_LABELS[0] == "Normal"

    def test_transform_labels_all_strings(self):
        for label in TRANSFORM_LABELS.values():
            assert isinstance(label, str)
            assert len(label) > 0
