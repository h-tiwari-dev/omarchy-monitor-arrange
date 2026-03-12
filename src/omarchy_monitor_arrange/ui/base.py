from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from omarchy_monitor_arrange.core.manager import MonitorManager


class MonitorArrangeUI(Protocol):
    """Interface for any UI implementation."""

    def run(self, manager: MonitorManager) -> None:
        """Start the UI event loop. Blocks until the user closes the app."""
        ...
