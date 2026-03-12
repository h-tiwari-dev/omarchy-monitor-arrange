"""Entry point: wires backend + core + UI, then runs the app."""

from __future__ import annotations

import subprocess
import sys


def _hyprland_available() -> bool:
    try:
        subprocess.check_output(["hyprctl", "version"], stderr=subprocess.DEVNULL)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


def main() -> None:
    if not _hyprland_available():
        print("Error: Hyprland is not running (hyprctl not found).", file=sys.stderr)
        sys.exit(1)

    from omarchy_monitor_arrange.backends.hyprland import HyprlandBackend
    from omarchy_monitor_arrange.core.config import HyprlandConfigWriter
    from omarchy_monitor_arrange.core.layout import DefaultLayoutEngine
    from omarchy_monitor_arrange.core.manager import MonitorManager
    from omarchy_monitor_arrange.theme import load_colors
    from omarchy_monitor_arrange.ui.gtk4.app import MonitorArrangeGtkUI

    backend = HyprlandBackend()
    layout = DefaultLayoutEngine()
    config = HyprlandConfigWriter()
    manager = MonitorManager(backend, layout, config)

    try:
        manager.load_monitors()
    except Exception as exc:
        print(f"Error loading monitors: {exc}", file=sys.stderr)
        sys.exit(1)

    if not manager.monitors:
        print("No monitors detected.", file=sys.stderr)
        sys.exit(1)

    colors = load_colors()
    ui = MonitorArrangeGtkUI(colors)
    ui.run(manager)


if __name__ == "__main__":
    main()
