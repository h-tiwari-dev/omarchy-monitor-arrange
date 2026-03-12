from __future__ import annotations

from unittest.mock import MagicMock, call

import pytest

from omarchy_monitor_arrange.core.manager import MonitorManager
from omarchy_monitor_arrange.core.models import (
    Monitor,
    Overlap,
    SnapResult,
    SCALE_CYCLE,
    TRANSFORM_CYCLE,
)


# ---------------------------------------------------------------------------
# Helpers / Fixtures
# ---------------------------------------------------------------------------

def _mon(name: str, x: int = 0, y: int = 0, w: int = 1920, h: int = 1080,
         scale: float = 1.0, transform: int = 0, refresh_rate: float = 60.0,
         focused: bool = False, modes: list[str] | None = None) -> Monitor:
    return Monitor(
        name=name, description=name, width=w, height=h,
        x=x, y=y, scale=scale, transform=transform, refresh_rate=refresh_rate,
        available_modes=modes or [], focused=focused,
    )


@pytest.fixture
def mock_backend():
    backend = MagicMock()
    backend.get_monitors.return_value = [
        _mon("DP-1", focused=True, modes=["1920x1080@60Hz", "1920x1080@144Hz", "2560x1440@60Hz"]),
        _mon("DP-2", x=1920, modes=["2560x1440@60Hz", "2560x1440@120Hz"]),
    ]
    return backend


@pytest.fixture
def mock_layout():
    layout = MagicMock()
    layout.compute_snaps.return_value = SnapResult()
    layout.detect_overlaps.return_value = []
    return layout


@pytest.fixture
def mock_config():
    return MagicMock()


@pytest.fixture
def manager(mock_backend, mock_layout, mock_config) -> MonitorManager:
    mgr = MonitorManager(mock_backend, mock_layout, mock_config)
    mgr.load_monitors()
    return mgr


# ---------------------------------------------------------------------------
# load_monitors
# ---------------------------------------------------------------------------

class TestLoadMonitors:
    def test_populates_monitors(self, manager: MonitorManager):
        assert len(manager.monitors) == 2
        assert manager.monitors[0].name == "DP-1"
        assert manager.monitors[1].name == "DP-2"

    def test_sets_primary_to_first(self, manager: MonitorManager):
        assert manager.primary_name == "DP-1"

    def test_selects_focused_monitor(self, manager: MonitorManager):
        assert manager.selected.name == "DP-1"
        assert manager.selected_index == 0

    def test_selects_focused_when_not_first(self, mock_backend, mock_layout, mock_config):
        mock_backend.get_monitors.return_value = [
            _mon("DP-1"),
            _mon("DP-2", x=1920, focused=True),
        ]
        mgr = MonitorManager(mock_backend, mock_layout, mock_config)
        mgr.load_monitors()
        assert mgr.selected.name == "DP-2"
        assert mgr.selected_index == 1

    def test_defaults_to_index_0_when_none_focused(self, mock_backend, mock_layout, mock_config):
        mock_backend.get_monitors.return_value = [_mon("DP-1"), _mon("DP-2", x=1920)]
        mgr = MonitorManager(mock_backend, mock_layout, mock_config)
        mgr.load_monitors()
        assert mgr.selected_index == 0

    def test_empty_monitors(self, mock_backend, mock_layout, mock_config):
        mock_backend.get_monitors.return_value = []
        mgr = MonitorManager(mock_backend, mock_layout, mock_config)
        mgr.load_monitors()
        assert mgr.monitors == []
        assert mgr.selected is None

    def test_clears_history_on_load(self, mock_backend, mock_layout, mock_config):
        mock_backend.get_monitors.return_value = [
            _mon("DP-1", focused=True, modes=["1920x1080@60Hz"]),
            _mon("DP-2", x=1920),
        ]
        mgr = MonitorManager(mock_backend, mock_layout, mock_config)
        mgr.load_monitors()
        mgr.move_selected(10, 0, snap=False)
        assert mgr.selected.x == 10

        mock_backend.get_monitors.return_value = [
            _mon("DP-1", focused=True, modes=["1920x1080@60Hz"]),
            _mon("DP-2", x=1920),
        ]
        mgr.load_monitors()
        assert mgr.selected.x == 0  # fresh objects from backend
        mgr.undo()  # history was cleared, so nothing happens
        assert mgr.selected.x == 0


# ---------------------------------------------------------------------------
# select_next / select_prev
# ---------------------------------------------------------------------------

class TestSelection:
    def test_select_next(self, manager: MonitorManager):
        manager.select_next()
        assert manager.selected.name == "DP-2"

    def test_select_next_wraps(self, manager: MonitorManager):
        manager.select_next()
        manager.select_next()
        assert manager.selected.name == "DP-1"

    def test_select_prev(self, manager: MonitorManager):
        manager.select_next()
        manager.select_prev()
        assert manager.selected.name == "DP-1"

    def test_select_prev_wraps(self, manager: MonitorManager):
        manager.select_prev()
        assert manager.selected.name == "DP-2"

    def test_select_next_single_monitor(self, mock_backend, mock_layout, mock_config):
        mock_backend.get_monitors.return_value = [_mon("DP-1")]
        mgr = MonitorManager(mock_backend, mock_layout, mock_config)
        mgr.load_monitors()
        mgr.select_next()
        assert mgr.selected.name == "DP-1"

    def test_select_prev_empty(self, mock_backend, mock_layout, mock_config):
        mock_backend.get_monitors.return_value = []
        mgr = MonitorManager(mock_backend, mock_layout, mock_config)
        mgr.load_monitors()
        mgr.select_prev()  # should not raise
        assert mgr.selected is None


# ---------------------------------------------------------------------------
# move_selected
# ---------------------------------------------------------------------------

class TestMoveSelected:
    def test_moves_by_dx_dy(self, manager: MonitorManager, mock_layout):
        manager.move_selected(100, 50, snap=False)
        assert manager.selected.x == 100
        assert manager.selected.y == 50

    def test_applies_snap(self, manager: MonitorManager, mock_layout):
        mock_layout.compute_snaps.return_value = SnapResult(dx=-5, dy=3, snapped_x=True, snapped_y=True)
        manager.move_selected(100, 50, snap=True)
        assert manager.selected.x == 100 - 5
        assert manager.selected.y == 50 + 3

    def test_snap_false_skips_snapping(self, manager: MonitorManager, mock_layout):
        manager.move_selected(100, 50, snap=False)
        mock_layout.compute_snaps.assert_not_called()

    def test_pushes_undo_state(self, manager: MonitorManager):
        orig_x = manager.selected.x
        manager.move_selected(100, 0, snap=False)
        manager.undo()
        assert manager.selected.x == orig_x

    def test_no_selected_does_nothing(self, mock_backend, mock_layout, mock_config):
        mock_backend.get_monitors.return_value = []
        mgr = MonitorManager(mock_backend, mock_layout, mock_config)
        mgr.load_monitors()
        mgr.move_selected(10, 10)  # should not raise

    def test_cumulative_moves(self, manager: MonitorManager):
        manager.move_selected(100, 0, snap=False)
        manager.move_selected(50, 0, snap=False)
        assert manager.selected.x == 150


# ---------------------------------------------------------------------------
# cycle_resolution
# ---------------------------------------------------------------------------

class TestCycleResolution:
    def test_cycles_to_next_resolution(self, manager: MonitorManager):
        assert manager.selected.width == 1920
        assert manager.selected.height == 1080
        manager.cycle_resolution()
        assert manager.selected.width == 2560
        assert manager.selected.height == 1440

    def test_wraps_around(self, manager: MonitorManager):
        manager.cycle_resolution()  # -> 2560x1440
        manager.cycle_resolution()  # -> wrap to 1920x1080
        assert manager.selected.width == 1920

    def test_no_modes_does_nothing(self, mock_backend, mock_layout, mock_config):
        mock_backend.get_monitors.return_value = [_mon("DP-1")]
        mgr = MonitorManager(mock_backend, mock_layout, mock_config)
        mgr.load_monitors()
        mgr.cycle_resolution()
        assert mgr.selected.width == 1920

    def test_pushes_undo(self, manager: MonitorManager):
        manager.cycle_resolution()
        manager.undo()
        assert manager.selected.width == 1920


# ---------------------------------------------------------------------------
# cycle_scale
# ---------------------------------------------------------------------------

class TestCycleScale:
    def test_cycles_through_scale(self, manager: MonitorManager):
        assert manager.selected.scale == 1.0
        manager.cycle_scale()
        assert manager.selected.scale == 1.25

    def test_wraps_around(self, manager: MonitorManager):
        for _ in range(len(SCALE_CYCLE)):
            manager.cycle_scale()
        assert manager.selected.scale == 1.0

    def test_unknown_scale_goes_to_first(self, manager: MonitorManager):
        manager.selected.scale = 99.0
        manager.cycle_scale()
        assert manager.selected.scale == SCALE_CYCLE[0]

    def test_pushes_undo(self, manager: MonitorManager):
        manager.cycle_scale()
        manager.undo()
        assert manager.selected.scale == 1.0


# ---------------------------------------------------------------------------
# cycle_refresh_rate
# ---------------------------------------------------------------------------

class TestCycleRefreshRate:
    def test_cycles_rates_for_current_resolution(self, manager: MonitorManager):
        assert manager.selected.refresh_rate == 60.0
        manager.cycle_refresh_rate()
        assert manager.selected.refresh_rate == 144.0

    def test_wraps_rates(self, manager: MonitorManager):
        manager.cycle_refresh_rate()  # 60 -> 144
        manager.cycle_refresh_rate()  # 144 -> 60
        assert manager.selected.refresh_rate == 60.0

    def test_no_modes_does_nothing(self, mock_backend, mock_layout, mock_config):
        mock_backend.get_monitors.return_value = [_mon("DP-1")]
        mgr = MonitorManager(mock_backend, mock_layout, mock_config)
        mgr.load_monitors()
        mgr.cycle_refresh_rate()
        assert mgr.selected.refresh_rate == 60.0

    def test_pushes_undo(self, manager: MonitorManager):
        manager.cycle_refresh_rate()
        manager.undo()
        assert manager.selected.refresh_rate == 60.0


# ---------------------------------------------------------------------------
# cycle_transform
# ---------------------------------------------------------------------------

class TestCycleTransform:
    def test_cycles_through_transforms(self, manager: MonitorManager):
        assert manager.selected.transform == 0
        manager.cycle_transform()
        assert manager.selected.transform == 1

    def test_wraps_around(self, manager: MonitorManager):
        for _ in range(len(TRANSFORM_CYCLE)):
            manager.cycle_transform()
        assert manager.selected.transform == 0

    def test_unknown_transform_goes_to_first(self, manager: MonitorManager):
        manager.selected.transform = 7
        manager.cycle_transform()
        assert manager.selected.transform == TRANSFORM_CYCLE[0]

    def test_pushes_undo(self, manager: MonitorManager):
        manager.cycle_transform()
        manager.undo()
        assert manager.selected.transform == 0


# ---------------------------------------------------------------------------
# set_primary
# ---------------------------------------------------------------------------

class TestSetPrimary:
    def test_changes_primary_name(self, manager: MonitorManager):
        manager.select_next()
        manager.set_primary()
        assert manager.primary_name == "DP-2"

    def test_primary_already_set(self, manager: MonitorManager):
        manager.set_primary()
        assert manager.primary_name == "DP-1"


# ---------------------------------------------------------------------------
# apply
# ---------------------------------------------------------------------------

class TestApply:
    def test_calls_normalize_backup_write_reload(self, manager: MonitorManager,
                                                  mock_layout, mock_config, mock_backend):
        mock_layout.reset_mock()
        mock_config.reset_mock()
        mock_backend.reset_mock()

        manager.apply()

        mock_layout.normalize_positions.assert_called_once()
        mock_config.backup.assert_called_once()
        mock_config.write.assert_called_once()
        mock_backend.reload_config.assert_called_once()

    def test_call_order(self, manager: MonitorManager, mock_layout, mock_config, mock_backend):
        call_order = []
        mock_layout.normalize_positions.side_effect = lambda m: call_order.append("normalize")
        mock_config.backup.side_effect = lambda: call_order.append("backup")
        mock_config.write.side_effect = lambda m, p: call_order.append("write")
        mock_backend.reload_config.side_effect = lambda: call_order.append("reload")

        manager.apply()
        assert call_order == ["normalize", "backup", "write", "reload"]

    def test_clears_history(self, manager: MonitorManager):
        manager.move_selected(10, 0, snap=False)
        manager.apply()
        manager.undo()  # should do nothing
        assert manager.selected.x == 10  # move persists

    def test_updates_saved_snapshot(self, manager: MonitorManager):
        manager.move_selected(10, 0, snap=False)
        assert manager.has_unsaved_changes
        manager.apply()
        assert not manager.has_unsaved_changes

    def test_write_receives_monitors_and_primary(self, manager: MonitorManager, mock_config):
        mock_config.reset_mock()
        manager.apply()
        args = mock_config.write.call_args
        assert len(args[0][0]) == 2  # monitors list
        assert args[0][1] == "DP-1"  # primary_name


# ---------------------------------------------------------------------------
# undo
# ---------------------------------------------------------------------------

class TestUndo:
    def test_restores_previous_state(self, manager: MonitorManager):
        manager.move_selected(100, 200, snap=False)
        manager.undo()
        assert manager.selected.x == 0
        assert manager.selected.y == 0

    def test_does_nothing_when_empty(self, manager: MonitorManager):
        x_before = manager.selected.x
        manager.undo()
        assert manager.selected.x == x_before

    def test_multiple_undos(self, manager: MonitorManager):
        manager.move_selected(10, 0, snap=False)
        manager.move_selected(20, 0, snap=False)
        manager.undo()
        assert manager.selected.x == 10
        manager.undo()
        assert manager.selected.x == 0

    def test_undo_scale_cycle(self, manager: MonitorManager):
        orig = manager.selected.scale
        manager.cycle_scale()
        manager.undo()
        assert manager.selected.scale == orig


# ---------------------------------------------------------------------------
# identify
# ---------------------------------------------------------------------------

class TestIdentify:
    def test_calls_backend_for_each_monitor(self, manager: MonitorManager, mock_backend):
        mock_backend.reset_mock()
        manager.identify()
        assert mock_backend.identify_monitor.call_count == 2
        mock_backend.identify_monitor.assert_any_call("DP-1")
        mock_backend.identify_monitor.assert_any_call("DP-2")

    def test_empty_monitors(self, mock_backend, mock_layout, mock_config):
        mock_backend.get_monitors.return_value = []
        mgr = MonitorManager(mock_backend, mock_layout, mock_config)
        mgr.load_monitors()
        mock_backend.reset_mock()
        mgr.identify()
        mock_backend.identify_monitor.assert_not_called()


# ---------------------------------------------------------------------------
# has_unsaved_changes
# ---------------------------------------------------------------------------

class TestHasUnsavedChanges:
    def test_false_initially(self, manager: MonitorManager):
        assert not manager.has_unsaved_changes

    def test_true_after_move(self, manager: MonitorManager):
        manager.move_selected(10, 0, snap=False)
        assert manager.has_unsaved_changes

    def test_true_after_scale_change(self, manager: MonitorManager):
        manager.cycle_scale()
        assert manager.has_unsaved_changes

    def test_false_after_apply(self, manager: MonitorManager):
        manager.move_selected(10, 0, snap=False)
        manager.apply()
        assert not manager.has_unsaved_changes

    def test_true_after_undo_past_save(self, manager: MonitorManager):
        manager.move_selected(10, 0, snap=False)
        manager.apply()
        manager.move_selected(5, 0, snap=False)
        manager.undo()
        assert not manager.has_unsaved_changes


# ---------------------------------------------------------------------------
# overlaps property
# ---------------------------------------------------------------------------

class TestOverlaps:
    def test_delegates_to_layout(self, manager: MonitorManager, mock_layout):
        expected = [Overlap(monitor_a="DP-1", monitor_b="DP-2")]
        mock_layout.detect_overlaps.return_value = expected
        assert manager.overlaps == expected

    def test_no_overlaps(self, manager: MonitorManager, mock_layout):
        mock_layout.detect_overlaps.return_value = []
        assert manager.overlaps == []


# ---------------------------------------------------------------------------
# on_change callbacks
# ---------------------------------------------------------------------------

class TestOnChangeCallbacks:
    def test_fired_on_load(self, mock_backend, mock_layout, mock_config):
        cb = MagicMock()
        mgr = MonitorManager(mock_backend, mock_layout, mock_config)
        mgr.on_change(cb)
        mgr.load_monitors()
        cb.assert_called()

    def test_fired_on_move(self, manager: MonitorManager):
        cb = MagicMock()
        manager.on_change(cb)
        manager.move_selected(10, 0, snap=False)
        cb.assert_called_once()

    def test_fired_on_select_next(self, manager: MonitorManager):
        cb = MagicMock()
        manager.on_change(cb)
        manager.select_next()
        cb.assert_called_once()

    def test_fired_on_select_prev(self, manager: MonitorManager):
        cb = MagicMock()
        manager.on_change(cb)
        manager.select_prev()
        cb.assert_called_once()

    def test_fired_on_cycle_scale(self, manager: MonitorManager):
        cb = MagicMock()
        manager.on_change(cb)
        manager.cycle_scale()
        cb.assert_called_once()

    def test_fired_on_cycle_transform(self, manager: MonitorManager):
        cb = MagicMock()
        manager.on_change(cb)
        manager.cycle_transform()
        cb.assert_called_once()

    def test_fired_on_cycle_resolution(self, manager: MonitorManager):
        cb = MagicMock()
        manager.on_change(cb)
        manager.cycle_resolution()
        cb.assert_called_once()

    def test_fired_on_cycle_refresh_rate(self, manager: MonitorManager):
        cb = MagicMock()
        manager.on_change(cb)
        manager.cycle_refresh_rate()
        cb.assert_called_once()

    def test_fired_on_set_primary(self, manager: MonitorManager):
        cb = MagicMock()
        manager.on_change(cb)
        manager.set_primary()
        cb.assert_called_once()

    def test_fired_on_apply(self, manager: MonitorManager):
        cb = MagicMock()
        manager.on_change(cb)
        manager.apply()
        cb.assert_called_once()

    def test_fired_on_undo(self, manager: MonitorManager):
        manager.move_selected(10, 0, snap=False)
        cb = MagicMock()
        manager.on_change(cb)
        manager.undo()
        cb.assert_called_once()

    def test_multiple_callbacks(self, manager: MonitorManager):
        cb1 = MagicMock()
        cb2 = MagicMock()
        manager.on_change(cb1)
        manager.on_change(cb2)
        manager.select_next()
        cb1.assert_called_once()
        cb2.assert_called_once()
