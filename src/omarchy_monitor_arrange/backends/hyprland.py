from __future__ import annotations

import json
import subprocess

from omarchy_monitor_arrange.core.models import Monitor


class HyprlandBackend:
    """MonitorBackend implementation for Hyprland via hyprctl."""

    def get_monitors(self) -> list[Monitor]:
        raw = subprocess.check_output(["hyprctl", "monitors", "-j"])
        data = json.loads(raw)
        return [self._parse_monitor(m) for m in data]

    def _parse_monitor(self, data: dict) -> Monitor:
        return Monitor(
            name=data["name"],
            description=data.get("description", ""),
            width=data["width"],
            height=data["height"],
            x=data["x"],
            y=data["y"],
            scale=data["scale"],
            transform=data["transform"],
            refresh_rate=data["refreshRate"],
            available_modes=data.get("availableModes", []),
            focused=data.get("focused", False),
        )

    def get_available_modes(self, monitor_name: str) -> list[str]:
        monitors = self.get_monitors()
        for m in monitors:
            if m.name == monitor_name:
                return m.available_modes
        return []

    def identify_monitor(self, monitor_name: str, duration_ms: int = 2000) -> None:
        subprocess.run([
            "hyprctl", "notify", "0", str(duration_ms),
            "rgb(ff9e64)", f"fontsize:40 {monitor_name}",
        ])

    def highlight_monitor(self, monitor_name: str) -> None:
        """Show a red notification on the target monitor, then return focus."""
        focused = self._get_focused_monitor()
        subprocess.run(["hyprctl", "dismissnotify", "-1"])
        if focused and focused != monitor_name:
            script = (
                f'hyprctl dispatch focusmonitor "{monitor_name}" && '
                f'sleep 0.15 && '
                f'hyprctl notify 6 3000 "rgb(ff3333)" "fontsize:36 ▶ {monitor_name}" && '
                f'sleep 0.5 && '
                f'hyprctl dispatch focusmonitor "{focused}"'
            )
            subprocess.Popen(["bash", "-c", script])
        else:
            subprocess.run([
                "hyprctl", "notify", "6", "3000",
                "rgb(ff3333)", f"fontsize:36 ▶ {monitor_name}",
            ])

    def clear_highlight(self) -> None:
        subprocess.run(["hyprctl", "dismissnotify", "-1"])

    def _get_focused_monitor(self) -> str | None:
        try:
            raw = subprocess.check_output(["hyprctl", "monitors", "-j"])
            for m in json.loads(raw):
                if m.get("focused"):
                    return m["name"]
        except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError):
            pass
        return None

    def reload_config(self) -> None:
        subprocess.run(["hyprctl", "reload"])
