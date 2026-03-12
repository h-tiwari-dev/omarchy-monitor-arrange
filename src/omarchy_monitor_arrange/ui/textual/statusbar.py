from __future__ import annotations

from textual.widgets import Static

from omarchy_monitor_arrange.core.models import TRANSFORM_LABELS


class StatusBarWidget(Static):
    """Shows selected monitor info and warnings."""

    def __init__(self, manager):
        super().__init__()
        self._manager = manager

    def update_status(self) -> None:
        mon = self._manager.selected
        if mon is None:
            self.update("No monitors")
            return

        primary_tag = " *" if mon.name == self._manager.primary_name else ""
        transform_str = TRANSFORM_LABELS.get(mon.transform, str(mon.transform))
        info = (
            f"Selected: {mon.name}{primary_tag}  "
            f"Resolution: {mon.width}x{mon.height}  "
            f"Refresh: {mon.refresh_rate:.0f}Hz  "
            f"Scale: {mon.scale}x  "
            f"Position: {mon.x}x{mon.y}  "
            f"Transform: {transform_str}"
        )

        warnings: list[str] = []
        if self._manager.overlaps:
            names = ", ".join(
                f"{o.monitor_a}<->{o.monitor_b}" for o in self._manager.overlaps
            )
            warnings.append(f"Overlap: {names}")
        if self._manager.has_unsaved_changes:
            warnings.append("Unsaved changes")

        if warnings:
            warning_line = " | ".join(warnings)
            self.update(f"{info}\n{warning_line}")
        else:
            self.update(info)
