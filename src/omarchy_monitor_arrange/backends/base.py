from __future__ import annotations

from typing import Protocol

from omarchy_monitor_arrange.core.models import Monitor


class MonitorBackend(Protocol):
    def get_monitors(self) -> list[Monitor]:
        """Read all connected monitors from the compositor."""
        ...

    def get_available_modes(self, monitor_name: str) -> list[str]:
        """Get available modes for a monitor (e.g. '1920x1080@60.00Hz')."""
        ...

    def identify_monitor(self, monitor_name: str, duration_ms: int = 2000) -> None:
        """Flash the monitor name on the physical display."""
        ...

    def reload_config(self) -> None:
        """Tell the compositor to reload its monitor configuration."""
        ...
