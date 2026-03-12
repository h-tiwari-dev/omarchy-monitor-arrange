from __future__ import annotations

import re
from pathlib import Path

import pytest

from omarchy_monitor_arrange.core.config import HyprlandConfigWriter
from omarchy_monitor_arrange.core.models import Monitor


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mon(name: str, w: int = 1920, h: int = 1080, x: int = 0, y: int = 0,
         scale: float = 1.0, transform: int = 0, refresh_rate: float = 60.0) -> Monitor:
    return Monitor(
        name=name, description=name, width=w, height=h,
        x=x, y=y, scale=scale, transform=transform, refresh_rate=refresh_rate,
    )


@pytest.fixture
def config_path(tmp_path: Path) -> Path:
    return tmp_path / "hypr" / "monitors.conf"


@pytest.fixture
def writer(config_path: Path) -> HyprlandConfigWriter:
    return HyprlandConfigWriter(path=config_path)


# ---------------------------------------------------------------------------
# write() – monitor line format
# ---------------------------------------------------------------------------

class TestWriteFormat:
    def test_correct_monitor_line(self, writer: HyprlandConfigWriter, config_path: Path):
        monitors = [_mon("DP-1")]
        writer.write(monitors)
        text = config_path.read_text()
        assert "monitor = DP-1, 1920x1080@60, 0x0, 1.0" in text

    def test_custom_resolution_and_position(self, writer: HyprlandConfigWriter, config_path: Path):
        monitors = [_mon("HDMI-A-1", w=2560, h=1440, x=1920, y=100, refresh_rate=144.0, scale=1.5)]
        writer.write(monitors)
        text = config_path.read_text()
        assert "monitor = HDMI-A-1, 2560x1440@144, 1920x100, 1.5" in text

    def test_transform_appended_when_nonzero(self, writer: HyprlandConfigWriter, config_path: Path):
        monitors = [_mon("DP-1", transform=1)]
        writer.write(monitors)
        text = config_path.read_text()
        assert "transform, 1" in text

    def test_transform_absent_when_zero(self, writer: HyprlandConfigWriter, config_path: Path):
        monitors = [_mon("DP-1", transform=0)]
        writer.write(monitors)
        text = config_path.read_text()
        assert "transform" not in text

    def test_multiple_monitors(self, writer: HyprlandConfigWriter, config_path: Path):
        monitors = [_mon("DP-1"), _mon("DP-2", x=1920)]
        writer.write(monitors)
        text = config_path.read_text()
        assert "monitor = DP-1" in text
        assert "monitor = DP-2" in text


# ---------------------------------------------------------------------------
# write() – primary ordering
# ---------------------------------------------------------------------------

class TestWritePrimaryOrdering:
    def test_primary_monitor_listed_first(self, writer: HyprlandConfigWriter, config_path: Path):
        monitors = [_mon("DP-1"), _mon("DP-2", x=1920)]
        writer.write(monitors, primary_name="DP-2")
        text = config_path.read_text()
        lines = [l for l in text.splitlines() if l.startswith("monitor = ")]
        assert lines[0].startswith("monitor = DP-2")
        assert lines[1].startswith("monitor = DP-1")

    def test_primary_already_first(self, writer: HyprlandConfigWriter, config_path: Path):
        monitors = [_mon("DP-1"), _mon("DP-2", x=1920)]
        writer.write(monitors, primary_name="DP-1")
        text = config_path.read_text()
        lines = [l for l in text.splitlines() if l.startswith("monitor = ")]
        assert lines[0].startswith("monitor = DP-1")

    def test_no_primary_keeps_original_order(self, writer: HyprlandConfigWriter, config_path: Path):
        monitors = [_mon("DP-1"), _mon("DP-2", x=1920)]
        writer.write(monitors)
        text = config_path.read_text()
        lines = [l for l in text.splitlines() if l.startswith("monitor = ")]
        assert lines[0].startswith("monitor = DP-1")


# ---------------------------------------------------------------------------
# write() – GDK_SCALE
# ---------------------------------------------------------------------------

class TestWriteGdkScale:
    def test_gdk_scale_from_primary_scale_1(self, writer: HyprlandConfigWriter, config_path: Path):
        monitors = [_mon("DP-1", scale=1.0)]
        writer.write(monitors, primary_name="DP-1")
        text = config_path.read_text()
        assert "env = GDK_SCALE,1" in text

    def test_gdk_scale_from_primary_scale_1_5(self, writer: HyprlandConfigWriter, config_path: Path):
        monitors = [_mon("DP-1", scale=1.5)]
        writer.write(monitors, primary_name="DP-1")
        text = config_path.read_text()
        assert "env = GDK_SCALE,1" in text

    def test_gdk_scale_from_primary_scale_2(self, writer: HyprlandConfigWriter, config_path: Path):
        monitors = [_mon("DP-1", scale=2.0)]
        writer.write(monitors, primary_name="DP-1")
        text = config_path.read_text()
        assert "env = GDK_SCALE,2" in text

    def test_gdk_scale_from_primary_scale_3(self, writer: HyprlandConfigWriter, config_path: Path):
        """scale=3 -> int(3)=3 -> clamped to max 2."""
        monitors = [_mon("DP-1", scale=3.0)]
        writer.write(monitors, primary_name="DP-1")
        text = config_path.read_text()
        assert "env = GDK_SCALE,2" in text

    def test_gdk_scale_uses_primary_not_other(self, writer: HyprlandConfigWriter, config_path: Path):
        monitors = [_mon("DP-1", scale=1.0), _mon("DP-2", x=1920, scale=2.0)]
        writer.write(monitors, primary_name="DP-1")
        text = config_path.read_text()
        assert "env = GDK_SCALE,1" in text

    def test_gdk_scale_clamped_low(self, writer: HyprlandConfigWriter, config_path: Path):
        """Scale < 1 is unusual but GDK_SCALE should be at least 1."""
        monitors = [_mon("DP-1", scale=0.5)]
        writer.write(monitors, primary_name="DP-1")
        text = config_path.read_text()
        assert "env = GDK_SCALE,1" in text


# ---------------------------------------------------------------------------
# write() – header / directory creation
# ---------------------------------------------------------------------------

class TestWriteMisc:
    def test_timestamp_header(self, writer: HyprlandConfigWriter, config_path: Path):
        writer.write([_mon("DP-1")])
        text = config_path.read_text()
        assert text.startswith("# Generated by omarchy-monitor-arrange on ")
        assert re.search(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", text)

    def test_creates_parent_directory(self, writer: HyprlandConfigWriter, config_path: Path):
        assert not config_path.parent.exists()
        writer.write([_mon("DP-1")])
        assert config_path.exists()

    def test_parent_already_exists(self, writer: HyprlandConfigWriter, config_path: Path):
        config_path.parent.mkdir(parents=True, exist_ok=True)
        writer.write([_mon("DP-1")])
        assert config_path.exists()


# ---------------------------------------------------------------------------
# backup()
# ---------------------------------------------------------------------------

class TestBackup:
    def test_creates_bak_file(self, writer: HyprlandConfigWriter, config_path: Path):
        writer.write([_mon("DP-1")])
        result = writer.backup()
        assert result is not None
        backup_path = Path(result)
        assert backup_path.exists()
        assert ".conf.bak." in backup_path.name
        assert backup_path.read_text() == config_path.read_text()

    def test_backup_has_timestamp_in_name(self, writer: HyprlandConfigWriter, config_path: Path):
        writer.write([_mon("DP-1")])
        result = writer.backup()
        assert result is not None
        assert re.search(r"\d{8}_\d{6}", result)

    def test_returns_none_when_no_config(self, writer: HyprlandConfigWriter):
        assert writer.backup() is None

    def test_backup_preserves_content(self, writer: HyprlandConfigWriter, config_path: Path):
        monitors = [_mon("DP-1"), _mon("DP-2", x=1920, transform=1)]
        writer.write(monitors, primary_name="DP-1")
        original = config_path.read_text()
        backup_result = writer.backup()
        assert Path(backup_result).read_text() == original
