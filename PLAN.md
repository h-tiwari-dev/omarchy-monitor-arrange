# Omarchy Monitor Arrangement GUI

A macOS-like, keyboard-first visual monitor arrangement tool for Omarchy.
Lets users see their monitors as rectangles on a 2D canvas and reposition them
with arrow keys, including diagonal/offset placements. Writes directly to
`~/.config/hypr/monitors.conf` and Hyprland auto-reloads.

**Key architectural goal**: The UI layer is replaceable. Core logic, backend
communication, and config writing are fully decoupled from the presentation
layer via Python Protocols (structural interfaces).

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Project Structure](#project-structure)
4. [Interface Definitions](#interface-definitions)
5. [Core Layer](#core-layer)
6. [Backend Layer](#backend-layer)
7. [UI Layer](#ui-layer)
8. [Keyboard Controls](#keyboard-controls)
9. [GUI Layout](#gui-layout)
10. [Hyprland Integration](#hyprland-integration)
11. [Theming](#theming)
12. [Deployment and File Locations](#deployment-and-file-locations)
13. [Omarchy Menu Integration](#omarchy-menu-integration)
14. [Edge Cases and Error Handling](#edge-cases-and-error-handling)
15. [Implementation Checklist](#implementation-checklist)

---

## Overview

### Problem

Configuring multi-monitor layouts in Omarchy requires manually editing
`~/.config/hypr/monitors.conf` with pixel position values. Users must calculate
offsets themselves, accounting for resolution and scale.

### Solution

A modular Python application with:
- A **core** layer managing monitor state, snap logic, and config I/O
- A **backend** layer abstracting compositor communication (Hyprland today, others later)
- A **UI** layer that can be swapped (GTK4 today, TUI/Qt/web tomorrow)

### Design Principles

- **Separation of concerns**: Core knows nothing about UI. UI knows nothing about Hyprland.
- **Interface-driven**: All layer boundaries use Python Protocols (PEP 544).
- **Keyboard-first**: Every action has a keyboard shortcut.
- **Omarchy-native**: Floats as a standard Omarchy floating window. Matches theme.
- **Zero extra deps**: Uses only python-gobject, gtk4, pycairo (all pre-installed).

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Entry Point                          │
│               omarchy-monitor-arrange                    │
│         (wires backend + core + UI together)             │
└──────────────────────┬──────────────────────────────────┘
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
┌──────────────┐ ┌───────────┐ ┌──────────────────┐
│   Backend    │ │   Core    │ │       UI         │
│  (Protocol)  │ │           │ │    (Protocol)    │
│              │ │           │ │                  │
│ - Hyprland   │ │ - Manager │ │ - GTK4 (current) │
│ - (future:   │ │ - Layout  │ │ - (future: TUI,  │
│   wlroots,   │ │ - Config  │ │   Qt, web, etc.) │
│   KDE, etc.) │ │ - Models  │ │                  │
└──────┬───────┘ └─────┬─────┘ └────────┬─────────┘
       │               │                │
       │         ┌─────▼─────┐          │
       └────────►│  Monitor  │◄─────────┘
                 │  Manager  │
                 │  (state)  │
                 └───────────┘
```

### Data Flow

```
1. Startup:
   Backend.get_monitors() ──► MonitorManager (state) ──► UI.render()

2. User moves a monitor:
   UI ──► MonitorManager.move_monitor() ──► LayoutEngine.snap() ──► UI.render()

3. User hits Enter (apply):
   UI ──► MonitorManager.apply() ──► ConfigWriter.write() ──► Backend.reload()

4. User changes resolution:
   UI ──► MonitorManager.set_resolution() ──► UI.render()
```

---

## Project Structure

```
~/Documents/omarchy-monitor-arrange/
├── PLAN.md                              # This file
├── src/
│   └── omarchy_monitor_arrange/
│       ├── __init__.py                  # Package init, version
│       ├── __main__.py                  # Entry point: wires layers, runs app
│       │
│       ├── core/                        # Pure logic, no I/O, no UI
│       │   ├── __init__.py
│       │   ├── models.py               # Monitor dataclass, SnapResult, Overlap
│       │   ├── manager.py              # MonitorManager: central state + operations
│       │   ├── layout.py               # LayoutEngine: snap, overlap, normalize
│       │   └── config.py               # ConfigWriter: read/write monitors.conf
│       │
│       ├── backends/                    # Compositor communication
│       │   ├── __init__.py
│       │   ├── base.py                 # MonitorBackend Protocol definition
│       │   └── hyprland.py             # Hyprland implementation (hyprctl)
│       │
│       ├── ui/                          # Presentation layer
│       │   ├── __init__.py
│       │   ├── base.py                 # MonitorArrangeUI Protocol definition
│       │   └── gtk4/                   # GTK4 implementation
│       │       ├── __init__.py
│       │       ├── app.py              # Gtk.Application setup, window, key handling
│       │       ├── canvas.py           # Gtk.DrawingArea + Cairo rendering
│       │       └── statusbar.py        # Bottom status bar widget
│       │
│       └── theme.py                    # Theme color loading (Omarchy-aware)
│
├── bin/
│   └── omarchy-monitor-arrange          # Shell launcher script
│
└── tests/                               # Unit tests (optional, future)
    ├── test_models.py
    ├── test_layout.py
    └── test_config.py
```

---

## Interface Definitions

All interfaces use `typing.Protocol` (PEP 544) for structural subtyping.
Implementations don't need to explicitly inherit -- they just need to match
the method signatures.

### MonitorBackend Protocol (`backends/base.py`)

Abstracts compositor communication. Swap this to support a different compositor.

```python
from typing import Protocol
from core.models import Monitor

class MonitorBackend(Protocol):
    def get_monitors(self) -> list[Monitor]:
        """Read all connected monitors from the compositor."""
        ...

    def get_available_modes(self, monitor_name: str) -> list[str]:
        """Get available modes for a monitor (e.g., '1920x1080@60.00Hz')."""
        ...

    def identify_monitor(self, monitor_name: str, duration_ms: int = 2000) -> None:
        """Flash the monitor name on the physical display."""
        ...

    def reload_config(self) -> None:
        """Tell the compositor to reload its monitor configuration."""
        ...
```

### MonitorArrangeUI Protocol (`ui/base.py`)

Abstracts the presentation layer. Swap this to change the entire UI.

```python
from typing import Protocol, Callable
from core.manager import MonitorManager

class MonitorArrangeUI(Protocol):
    def run(self, manager: MonitorManager) -> None:
        """Start the UI event loop. Blocks until the user closes the app."""
        ...
```

The UI interacts with `MonitorManager` for all state changes. The manager
fires change callbacks that the UI listens to for re-rendering.

### LayoutEngine Protocol (`core/layout.py`)

Abstracts position calculations. Could be swapped for different snap behaviors.

```python
from typing import Protocol
from core.models import Monitor, SnapResult, Overlap

class LayoutEngine(Protocol):
    def compute_snaps(
        self, moving: Monitor, others: list[Monitor]
    ) -> SnapResult:
        """Calculate snap adjustments for a moving monitor."""
        ...

    def normalize_positions(self, monitors: list[Monitor]) -> None:
        """Shift all monitors so min x=0, min y=0. Mutates in place."""
        ...

    def detect_overlaps(self, monitors: list[Monitor]) -> list[Overlap]:
        """Find any overlapping monitor pairs."""
        ...
```

### ConfigWriter Protocol (`core/config.py`)

Abstracts config file I/O. Could be swapped for a different config format.

```python
from typing import Protocol
from core.models import Monitor

class ConfigWriter(Protocol):
    def write(self, monitors: list[Monitor], primary_name: str | None = None) -> None:
        """Write monitor config to disk."""
        ...

    def backup(self) -> str | None:
        """Backup current config. Returns backup path or None."""
        ...
```

---

## Core Layer

### models.py -- Data Structures

```python
from dataclasses import dataclass, field

@dataclass
class Monitor:
    name: str
    description: str
    width: int                    # Native pixel width
    height: int                   # Native pixel height
    x: int                        # Hyprland position x
    y: int                        # Hyprland position y
    scale: float                  # Display scale
    transform: int                # Rotation (0-7)
    refresh_rate: float           # Current refresh rate
    available_modes: list[str] = field(default_factory=list)
    focused: bool = False

    @property
    def scaled_width(self) -> int:
        w, h = self.width, self.height
        if self.transform in (1, 3, 5, 7):
            w, h = h, w
        return int(w / self.scale)

    @property
    def scaled_height(self) -> int:
        w, h = self.width, self.height
        if self.transform in (1, 3, 5, 7):
            w, h = h, w
        return int(h / self.scale)

    @property
    def right(self) -> int:
        return self.x + self.scaled_width

    @property
    def bottom(self) -> int:
        return self.y + self.scaled_height

    @property
    def center_x(self) -> int:
        return self.x + self.scaled_width // 2

    @property
    def center_y(self) -> int:
        return self.y + self.scaled_height // 2


TRANSFORM_LABELS = {
    0: "Normal", 1: "90°", 2: "180°", 3: "270°",
    4: "Flipped", 5: "Flipped 90°", 6: "Flipped 180°", 7: "Flipped 270°",
}

SCALE_CYCLE = [1.0, 1.25, 1.5, 1.75, 2.0, 3.0]
TRANSFORM_CYCLE = [0, 1, 2, 3]


@dataclass
class SnapResult:
    dx: int = 0                   # Horizontal snap adjustment
    dy: int = 0                   # Vertical snap adjustment
    snapped_x: bool = False       # Whether horizontal snap activated
    snapped_y: bool = False       # Whether vertical snap activated


@dataclass
class Overlap:
    monitor_a: str                # Name of first monitor
    monitor_b: str                # Name of second monitor
```

### manager.py -- Central State

```python
from typing import Callable

class MonitorManager:
    def __init__(self, backend, layout_engine, config_writer):
        self._backend = backend
        self._layout = layout_engine
        self._config = config_writer
        self._monitors: list[Monitor] = []
        self._selected_index: int = 0
        self._primary_name: str | None = None
        self._history: list[dict] = []     # Undo stack
        self._on_change: list[Callable] = []

    # -- Observer pattern --
    def on_change(self, callback: Callable) -> None:
        self._on_change.append(callback)

    def _notify(self) -> None:
        for cb in self._on_change:
            cb()

    # -- Initialization --
    def load_monitors(self) -> None:
        self._monitors = self._backend.get_monitors()
        if self._monitors:
            self._primary_name = self._monitors[0].name
        self._notify()

    # -- Selection --
    @property
    def selected(self) -> Monitor | None: ...
    def select_next(self) -> None: ...
    def select_prev(self) -> None: ...

    # -- Movement --
    def move_selected(self, dx: int, dy: int, snap: bool = True) -> None:
        """Move selected monitor by (dx, dy) in Hyprland coords."""
        # Save to undo stack
        # Apply movement
        # Apply snap if enabled
        # Notify UI
        ...

    # -- Settings --
    def cycle_resolution(self) -> None: ...
    def cycle_scale(self) -> None: ...
    def cycle_refresh_rate(self) -> None: ...
    def cycle_transform(self) -> None: ...
    def set_primary(self) -> None: ...

    # -- Actions --
    def apply(self) -> None:
        """Normalize positions, write config, trigger reload."""
        self._layout.normalize_positions(self._monitors)
        self._config.backup()
        self._config.write(self._monitors, self._primary_name)
        self._backend.reload_config()
        self._notify()

    def undo(self) -> None: ...

    def identify(self) -> None:
        for m in self._monitors:
            self._backend.identify_monitor(m.name)

    # -- Queries --
    @property
    def monitors(self) -> list[Monitor]: ...
    @property
    def overlaps(self) -> list[Overlap]: ...
    @property
    def has_unsaved_changes(self) -> bool: ...
```

### layout.py -- Snap and Position Logic

Contains `DefaultLayoutEngine` implementing the `LayoutEngine` protocol.
Pure math, no I/O. See snap algorithm in the detailed design section below.

### config.py -- Config File I/O

Contains `HyprlandConfigWriter` implementing the `ConfigWriter` protocol.
Reads/writes `~/.config/hypr/monitors.conf`.

---

## Backend Layer

### hyprland.py -- Hyprland Implementation

```python
import subprocess
import json
from core.models import Monitor

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
            "rgb(ff9e64)", f"fontsize:40 {monitor_name}"
        ])

    def reload_config(self) -> None:
        subprocess.run(["hyprctl", "reload"])
```

---

## UI Layer

### base.py -- UI Protocol

```python
from typing import Protocol
from core.manager import MonitorManager

class MonitorArrangeUI(Protocol):
    """Interface for any UI implementation."""

    def run(self, manager: MonitorManager) -> None:
        """Start the UI. Blocks until closed."""
        ...
```

Any future UI (TUI, Qt, web) just needs to implement this single method.
Inside `run()`, the UI:
1. Registers a change callback with `manager.on_change(self.redraw)`
2. Renders the initial state
3. Translates user input into `manager` method calls
4. Blocks in its event loop until the user closes

### GTK4 Implementation

#### app.py -- Application Shell

```python
class MonitorArrangeApp(Gtk.Application):
    """GTK4 application. Sets up window, layout, key handling."""

    APP_ID = "org.omarchy.monitor-arrange"

    def __init__(self, manager: MonitorManager):
        super().__init__(application_id=self.APP_ID)
        self._manager = manager

    def do_activate(self):
        window = Gtk.ApplicationWindow(application=self)
        window.set_title("Monitor Arrangement")
        window.set_default_size(875, 600)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self._canvas = MonitorCanvas(self._manager)
        self._statusbar = StatusBar(self._manager)

        box.append(self._canvas)
        box.append(self._statusbar)
        window.set_child(box)

        # Key controller
        key_ctrl = Gtk.EventControllerKey()
        key_ctrl.connect("key-pressed", self._on_key_pressed)
        window.add_controller(key_ctrl)

        # Register for manager changes
        self._manager.on_change(self._on_manager_change)

        window.present()

    def _on_key_pressed(self, ctrl, keyval, keycode, state):
        """Route all keyboard input to manager actions."""
        ...

    def _on_manager_change(self):
        self._canvas.queue_draw()
        self._statusbar.update()
```

#### canvas.py -- 2D Drawing Surface

```python
class MonitorCanvas(Gtk.DrawingArea):
    """Cairo-based 2D canvas showing monitor arrangement."""

    def __init__(self, manager: MonitorManager):
        super().__init__()
        self._manager = manager
        self.set_vexpand(True)
        self.set_draw_func(self._draw)

    def _draw(self, area, cr, width, height):
        """Cairo draw callback. Renders all monitors."""
        # 1. Fill background
        # 2. Compute view transform (Hyprland coords → canvas pixels)
        # 3. Draw grid/reference dots
        # 4. Draw each monitor rectangle
        # 5. Highlight selected monitor
        ...

    def _hypr_to_canvas(self, hx, hy):
        """Convert Hyprland coords to canvas pixel coords."""
        ...

    def _canvas_to_hypr(self, cx, cy):
        """Convert canvas pixel coords to Hyprland coords."""
        ...
```

#### statusbar.py -- Info and Shortcut Legend

```python
class StatusBar(Gtk.Box):
    """Bottom bar showing selected monitor info and keyboard shortcuts."""

    def __init__(self, manager: MonitorManager):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self._manager = manager
        # Labels for monitor info, shortcut legend
        ...

    def update(self):
        """Refresh displayed info from manager state."""
        ...
```

---

## Keyboard Controls

### Navigation

| Key              | Action                                          |
|------------------|-------------------------------------------------|
| Tab              | Select next monitor                             |
| Shift+Tab        | Select previous monitor                         |

### Movement

| Key              | Action                                          |
|------------------|-------------------------------------------------|
| Arrow keys       | Move selected monitor (coarse: ~10px in layout)  |
| Shift+Arrows     | Fine move (1px in layout)                        |

Snap-to-edge activates automatically when edges are close.

### Monitor Settings

| Key | Action                                                    |
|-----|-----------------------------------------------------------|
| r   | Cycle available resolutions for selected monitor          |
| s   | Cycle scale: 1 → 1.25 → 1.5 → 1.75 → 2 → 3 → 1         |
| f   | Cycle available refresh rates                             |
| t   | Cycle transform: Normal → 90° → 180° → 270° → Normal     |
| m   | Toggle mirror mode                                        |

### Actions

| Key     | Action                                                  |
|---------|---------------------------------------------------------|
| Enter   | Apply: write config, Hyprland reloads                   |
| Escape  | Cancel and close without saving                         |
| i       | Identify: flash monitor name on each physical display   |
| p       | Mark selected as primary (first in config)              |
| h / ?   | Toggle help overlay                                     |
| u       | Undo last move                                          |

---

## GUI Layout

```
┌──────────────────────────────────────────────────────┐
│                                                      │
│            2D Canvas (~70% of window)                │
│                                                      │
│     ┌──────────────┐  ┌────────────────────┐         │
│     │              │  │                    │         │
│     │   eDP-1      │  │    HDMI-A-1        │         │
│     │  1920x1200   │  │   2560x1440        │         │
│     │   @60 1.5x   │  │    @144 1x         │         │
│     │              │  │                    │         │
│     └──────────────┘  │                    │         │
│                       └────────────────────┘         │
│                                                      │
├──────────────────────────────────────────────────────┤
│ Status Bar                                           │
│                                                      │
│ Selected: HDMI-A-1                                   │
│ Resolution: 2560x1440  Refresh: 144Hz  Scale: 1x    │
│ Position: 1280x0  Transform: Normal                  │
│                                                      │
│ [Tab] Select  [←→↑↓] Move  [r] Res  [s] Scale      │
│ [f] Refresh  [t] Rotate  [Enter] Apply  [Esc] Close │
└──────────────────────────────────────────────────────┘
```

---

## Hyprland Integration

### Monitor Config Syntax

```
monitor = name, resolution, position, scale[, transform, N]
```

Examples:
```
monitor = DP-1, 1920x1080@144, 0x0, 1
monitor = DP-2, 1920x1080, 1920x0, 1
monitor = eDP-1, 2880x1800@90, 0x0, 2, transform, 1
```

### Position Math with Scale

From the Hyprland wiki: "The position is calculated with the scaled (and
transformed) resolution."

- A 4K monitor (3840x2160) at scale 2 occupies 1920x1080 in logical space
- To place a monitor to its right, use position `1920x0` (not `3840x0`)
- If also rotated 90°, logical size becomes 1080x1920

This is handled by `Monitor.scaled_width` / `scaled_height`.

### Transform Values

```
0 → Normal          4 → Flipped
1 → 90°             5 → Flipped + 90°
2 → 180°            6 → Flipped + 180°
3 → 270°            7 → Flipped + 270°
```

### Identify via hyprctl

```bash
hyprctl notify 0 2000 "rgb(ff9e64)" "fontsize:40 Monitor: eDP-1"
```

---

## Theming

Read Omarchy theme colors from `~/.config/omarchy/current/theme/` to match
the app to the active system theme. Fallback to a dark palette.

```python
DEFAULT_COLORS = {
    "bg":              (0.12, 0.12, 0.14, 1.0),
    "monitor_fill":    (0.22, 0.22, 0.26, 1.0),
    "monitor_border":  (0.4,  0.4,  0.45, 1.0),
    "selected_border": (0.4,  0.6,  1.0,  1.0),
    "text":            (0.9,  0.9,  0.92, 1.0),
    "text_dim":        (0.6,  0.6,  0.65, 1.0),
    "status_bg":       (0.15, 0.15, 0.18, 1.0),
    "snap_line":       (0.4,  0.6,  1.0,  0.4),
    "overlap_warn":    (1.0,  0.4,  0.3,  0.6),
}
```

Theme loading is in `theme.py`, used by the UI layer. Core and backend
layers do not reference theme colors.

---

## Deployment and File Locations

### Development (in Documents)

All source lives in `~/Documents/omarchy-monitor-arrange/src/`.

### Local Install

| File | Purpose |
|------|---------|
| `~/.local/lib/omarchy-monitor-arrange/` | Python package (copy of `src/omarchy_monitor_arrange/`) |
| `~/.local/bin/omarchy-monitor-arrange` | Shell launcher |
| `~/.config/omarchy/extensions/menu.sh` | Menu override |
| `~/.config/hypr/hyprland.conf` | Window rule |

The shell launcher (`bin/omarchy-monitor-arrange`):
```bash
#!/bin/bash
LIB_DIR="$HOME/.local/lib/omarchy-monitor-arrange"
exec /usr/bin/python3 -c "
import sys; sys.path.insert(0, '$LIB_DIR')
from omarchy_monitor_arrange.__main__ import main; main()
"
```

### Omarchy Feature (contribution)

| File | Destination |
|------|-------------|
| `src/omarchy_monitor_arrange/` | `~/.local/share/omarchy/lib/monitor-arrange/omarchy_monitor_arrange/` |
| `bin/omarchy-monitor-arrange` | `~/.local/share/omarchy/bin/omarchy-monitor-arrange` |
| Window rule | `~/.local/share/omarchy/default/hypr/apps/monitor-arrange.conf` |
| Menu change | `omarchy-menu` line ~233: `open_in_editor` → `omarchy-monitor-arrange` |

---

## Omarchy Menu Integration

### Window Rule

```
windowrule = tag +floating-window, match:class org.omarchy.monitor-arrange
```

This reuses the existing `floating-window` tag which provides float, center,
and size (875x600).

### Menu Override (local, via extensions)

In `~/.config/omarchy/extensions/menu.sh`:

```bash
show_setup_menu() {
  local options="  Audio\n  Wifi\n󰂯  Bluetooth\n󱐋  Power Profile\n  System Sleep\n󰍹  Monitors"
  [[ -f ~/.config/hypr/bindings.conf ]] && options="$options\n  Keybindings"
  [[ -f ~/.config/hypr/input.conf ]] && options="$options\n  Input"
  options="$options\n󰱔  DNS\n  Security\n  Config"

  case $(menu "Setup" "$options") in
  *Audio*) omarchy-launch-audio ;;
  *Wifi*) omarchy-launch-wifi ;;
  *Bluetooth*) omarchy-launch-bluetooth ;;
  *Power*) show_setup_power_menu ;;
  *System*) show_setup_system_menu ;;
  *Monitors*) omarchy-monitor-arrange ;;
  *Keybindings*) open_in_editor ~/.config/hypr/bindings.conf ;;
  *Input*) open_in_editor ~/.config/hypr/input.conf ;;
  *DNS*) present_terminal omarchy-setup-dns ;;
  *Security*) show_setup_security_menu ;;
  *Config*) show_setup_config_menu ;;
  *) show_main_menu ;;
  esac
}
```

---

## Edge Cases and Error Handling

| Scenario | Handling |
|----------|----------|
| Single monitor | App opens normally; useful for res/scale/refresh changes |
| No monitors (headless) | Show error notification, exit gracefully |
| Monitor hotplug | Not live-tracked; close and reopen to refresh |
| Overlapping monitors | Detect and show warning in status bar |
| Invalid scale | Only offer scales that divide resolution cleanly |
| Config backup failure | Warn user but don't block |
| hyprctl not found | Show error: "Hyprland not running" |
| Write permission denied | Show error notification |
| Available modes empty | Default to current resolution only |
| GDK_SCALE | Set to `int(primary_scale)` clamped to 1 or 2 |

---

## Implementation Checklist

### Phase 1: Project Scaffolding
- [ ] Create directory structure under `~/Documents/omarchy-monitor-arrange/src/`
- [ ] Create all `__init__.py` files
- [ ] Create `__main__.py` entry point with argument parsing
- [ ] Create shell launcher `bin/omarchy-monitor-arrange`

### Phase 2: Data Models (`core/models.py`)
- [ ] `Monitor` dataclass with all fields
- [ ] `scaled_width` / `scaled_height` properties (accounting for transform)
- [ ] `right`, `bottom`, `center_x`, `center_y` helpers
- [ ] `SnapResult` dataclass
- [ ] `Overlap` dataclass
- [ ] `TRANSFORM_LABELS`, `SCALE_CYCLE`, `TRANSFORM_CYCLE` constants

### Phase 3: Backend Protocol + Hyprland Implementation
- [ ] `MonitorBackend` Protocol in `backends/base.py`
- [ ] `HyprlandBackend` in `backends/hyprland.py`
- [ ] `get_monitors()`: parse `hyprctl monitors -j`
- [ ] `get_available_modes()`: extract from monitor data
- [ ] `identify_monitor()`: via `hyprctl notify`
- [ ] `reload_config()`: via `hyprctl reload`

### Phase 4: Layout Engine (`core/layout.py`)
- [ ] `LayoutEngine` Protocol
- [ ] `DefaultLayoutEngine` implementation
- [ ] `compute_snaps()`: all edge-pair snap calculations
- [ ] Horizontal snaps: left↔right, left↔left, right↔right, center↔center
- [ ] Vertical snaps: top↔bottom, top↔top, bottom↔bottom, center↔center
- [ ] Configurable snap threshold
- [ ] `normalize_positions()`: shift all to min x=0, y=0
- [ ] `detect_overlaps()`: find overlapping monitor pairs

### Phase 5: Config Writer (`core/config.py`)
- [ ] `ConfigWriter` Protocol
- [ ] `HyprlandConfigWriter` implementation
- [ ] `write()`: generate `monitor = ...` lines with all params
- [ ] Handle transform syntax appending
- [ ] Set `GDK_SCALE` based on primary monitor
- [ ] Timestamp comment header
- [ ] `backup()`: copy to `.bak.<timestamp>`

### Phase 6: Monitor Manager (`core/manager.py`)
- [ ] Observer pattern: `on_change()` / `_notify()`
- [ ] `load_monitors()`: fetch from backend, initialize state
- [ ] Selection: `select_next()`, `select_prev()`, `selected` property
- [ ] Movement: `move_selected(dx, dy, snap=True)`
- [ ] Settings: `cycle_resolution()`, `cycle_scale()`, `cycle_refresh_rate()`, `cycle_transform()`
- [ ] `set_primary()`: mark selected as primary
- [ ] `apply()`: normalize + backup + write + reload
- [ ] `undo()`: pop from history stack
- [ ] `identify()`: call backend for all monitors
- [ ] Overlap detection: `overlaps` property
- [ ] Unsaved changes tracking: `has_unsaved_changes` property

### Phase 7: UI Protocol (`ui/base.py`)
- [ ] `MonitorArrangeUI` Protocol with `run(manager)` method

### Phase 8: GTK4 Canvas (`ui/gtk4/canvas.py`)
- [ ] `MonitorCanvas(Gtk.DrawingArea)` class
- [ ] Bounding box calculation for all monitors
- [ ] View transform: Hyprland coords ↔ canvas coords
- [ ] `_draw()`: Cairo rendering of all monitors
- [ ] Rounded rectangle drawing for each monitor
- [ ] Monitor labels: name, resolution, scale, refresh
- [ ] Selected monitor highlight (accent border)
- [ ] Subtle grid dots on canvas background
- [ ] Snap indicator lines (when snap is active)
- [ ] Overlap warning overlay (red tint on overlapping area)
- [ ] Handle canvas resize (recalculate view transform)

### Phase 9: GTK4 Status Bar (`ui/gtk4/statusbar.py`)
- [ ] `StatusBar(Gtk.Box)` class
- [ ] Display: monitor name, resolution, refresh, scale, transform, position
- [ ] Keyboard shortcut legend (compact, always visible)
- [ ] Overlap warning indicator
- [ ] Unsaved changes indicator
- [ ] `update()` method called on manager change

### Phase 10: GTK4 App Shell (`ui/gtk4/app.py`)
- [ ] `MonitorArrangeApp(Gtk.Application)` with app-id
- [ ] Window setup: title, default size, layout (canvas + statusbar)
- [ ] Key controller: `Gtk.EventControllerKey`
- [ ] Route all keys to manager actions (see keyboard controls table)
- [ ] Tab / Shift+Tab: selection
- [ ] Arrows / Shift+Arrows: movement (coarse / fine)
- [ ] r / s / f / t / m: settings cycling
- [ ] Enter: apply
- [ ] Escape: close
- [ ] i: identify
- [ ] p: primary
- [ ] h / ?: help overlay
- [ ] u: undo
- [ ] Help overlay toggle (draw on canvas or separate widget)
- [ ] Register `manager.on_change()` to trigger redraws

### Phase 11: Theme Loading (`theme.py`)
- [ ] Read Omarchy theme directory for color values
- [ ] Parse Hyprland/CSS color values into RGBA tuples
- [ ] Fallback to dark defaults
- [ ] Provide colors dict to UI layer

### Phase 12: Entry Point (`__main__.py`)
- [ ] Wire backend (HyprlandBackend)
- [ ] Wire layout engine (DefaultLayoutEngine)
- [ ] Wire config writer (HyprlandConfigWriter)
- [ ] Create MonitorManager with all dependencies
- [ ] Load monitors
- [ ] Create GTK4 UI and call `run(manager)`
- [ ] `--ui` flag to select UI implementation (default: gtk4, future: tui)
- [ ] `--identify` flag for quick identify-only mode

### Phase 13: Local Deployment
- [ ] Copy package to `~/.local/lib/omarchy-monitor-arrange/`
- [ ] Install launcher to `~/.local/bin/omarchy-monitor-arrange`
- [ ] `chmod +x` the launcher
- [ ] Add window rule to `~/.config/hypr/hyprland.conf`
- [ ] Update `~/.config/omarchy/extensions/menu.sh`

### Phase 14: Testing
- [ ] Test with single monitor (eDP-1)
- [ ] Test selection cycling (Tab / Shift+Tab)
- [ ] Test arrow key movement (coarse and fine)
- [ ] Test snap-to-edge behavior
- [ ] Test resolution cycling
- [ ] Test scale cycling
- [ ] Test refresh rate cycling
- [ ] Test transform cycling
- [ ] Test config writing (correct syntax, normalized positions)
- [ ] Test backup creation
- [ ] Test Hyprland reload after apply
- [ ] Test identify (hyprctl notify)
- [ ] Test undo
- [ ] Test help overlay
- [ ] Test with mock multi-monitor data (if only one physical monitor)

### Phase 15: Omarchy Contribution Prep
- [ ] Document contribution path in this plan
- [ ] Prepare script for `~/.local/share/omarchy/bin/`
- [ ] Prepare window rule for `~/.local/share/omarchy/default/hypr/apps/`
- [ ] Prepare menu change for `omarchy-menu`
- [ ] Write PR description

---

## Omarchy Contribution Workflow

Step-by-step guide to submit this tool as a PR to `basecamp/omarchy`.

### Prerequisites

- GitHub CLI (`gh`) authenticated
- Upstream repo: `https://github.com/basecamp/omarchy.git`
- Default branch: `dev`
- Omarchy is entirely bash scripts today — no `lib/` directory exists yet
- Python deps (python-gobject, gtk4, pycairo) are already pre-installed on Omarchy

### Step 1: Fork and Clone

```bash
cd ~/Documents
gh repo fork basecamp/omarchy --clone
cd omarchy
git checkout -b monitor-arrange origin/dev
```

### Step 2: Add the Python Package

Create a new `lib/` directory (first of its kind in Omarchy):

```
lib/monitor-arrange/omarchy_monitor_arrange/
├── __init__.py
├── __main__.py
├── theme.py
├── core/
│   ├── __init__.py
│   ├── models.py
│   ├── layout.py
│   ├── config.py
│   └── manager.py
├── backends/
│   ├── __init__.py
│   ├── base.py
│   └── hyprland.py
└── ui/
    ├── __init__.py
    ├── base.py
    └── gtk4/
        ├── __init__.py
        ├── app.py
        ├── canvas.py
        └── statusbar.py
```

Copy from the development project:

```bash
mkdir -p lib/monitor-arrange
cp -r ~/Documents/omarchy-monitor-arrange/src/omarchy_monitor_arrange lib/monitor-arrange/
```

Do NOT include `tests/`, `PLAN.md`, `README.md`, `install.sh`, or `bin/` from the
dev project — those are for local development only.

### Step 3: Add the Launcher Script

Create `bin/omarchy-monitor-arrange` following Omarchy conventions (`AGENTS.md`):

```bash
#!/bin/bash
LIB_DIR="${OMARCHY_PATH:-$HOME/.local/share/omarchy}/lib/monitor-arrange"
exec /usr/bin/python3 -c "
import sys; sys.path.insert(0, '$LIB_DIR')
from omarchy_monitor_arrange.__main__ import main; main()
"
```

Note: uses `$OMARCHY_PATH` (set by Omarchy's boot process) with a sensible fallback.

### Step 4: Add the Hyprland Window Rule

Create `default/hypr/apps/monitor-arrange.conf`:

```
windowrule = tag +floating-window, match:class org.omarchy.monitor-arrange
```

This reuses the existing `floating-window` tag from `default/hypr/apps/system.conf`
which provides `float`, `center`, and `size 875 600`.

### Step 5: Modify the Menu

In `bin/omarchy-menu`, change line 233 from:

```bash
  *Monitors*) open_in_editor ~/.config/hypr/monitors.conf ;;
```

to:

```bash
  *Monitors*) omarchy-monitor-arrange ;;
```

### Step 6: Add a Migration

Create a migration file in `migrations/` so existing installs pick up the new
window rule. Use the Omarchy convention (`omarchy-dev-add-migration --no-edit`)
or manually create a file named after the unix timestamp of the last commit:

```bash
echo "Add monitor-arrange window rule"

omarchy-refresh-config hypr/apps/monitor-arrange.conf
```

### Step 7: Add Keybinding

Add a default keybinding for quick access. In the Omarchy PR, suggest this as a
default binding or include it in the migration. The binding uses `SUPER ALT, M`
which is currently unbound (`SUPER SHIFT, M` is Music/Spotify):

```
bindd = SUPER ALT, M, Monitor Arrangement, exec, omarchy-monitor-arrange
```

For the PR, this would go in `config/hypr/bindings.conf` (the default bindings
file). For local use, add it to `~/.config/hypr/bindings.conf`.

### Step 8: Review boot.sh / install.sh

Check that `boot.sh` and `install.sh` handle the new `lib/` directory during
installation (symlinks or copies to `~/.local/share/omarchy/`). If they only
handle `bin/`, `config/`, `default/`, and `themes/`, they may need a one-line
addition to also sync `lib/`.

### Step 9: Commit and Open PR

```bash
git add lib/monitor-arrange/ bin/omarchy-monitor-arrange \
        default/hypr/apps/monitor-arrange.conf bin/omarchy-menu \
        migrations/
git commit -m "Add visual monitor arrangement tool"
git push -u origin monitor-arrange
gh pr create --base dev --title "Add visual monitor arrangement tool" --body "..."
```

### PR Description Template

```
## Summary

- Adds `omarchy-monitor-arrange`, a macOS-like visual monitor layout tool
- Replaces manual `monitors.conf` editing with a keyboard-first 2D canvas GUI
- Writes directly to `~/.config/hypr/monitors.conf`; Hyprland auto-reloads

## Architecture

3-layer design (core / backend / UI) connected via Python Protocols:
- **Core**: Monitor state, snap-to-edge engine, config I/O (pure logic, no deps)
- **Backend**: Hyprland communication via hyprctl (swappable for other compositors)
- **UI**: GTK4 + Cairo canvas (swappable for TUI/Qt/web)

## Dependencies

Zero new packages — uses python-gobject, gtk4, and pycairo which are already
pre-installed on Omarchy.

## Changes

- `lib/monitor-arrange/` — Python package (new `lib/` directory)
- `bin/omarchy-monitor-arrange` — Launcher script
- `default/hypr/apps/monitor-arrange.conf` — Window rule (floating)
- `bin/omarchy-menu` — Monitors entry now launches the GUI
- `config/hypr/bindings.conf` — Default keybinding (SUPER ALT + M)
- `migrations/` — Refresh window rule for existing installs

## Keyboard Controls

Tab/Shift+Tab: select monitor | Arrows: move | Shift+Arrows: fine move
r: resolution | s: scale | f: refresh | t: rotate | p: primary
Enter: apply | Escape: close | i: identify | u: undo | h: help
```

### Contribution Checklist

- [ ] Fork `basecamp/omarchy` and create `monitor-arrange` branch off `dev`
- [ ] Copy Python package to `lib/monitor-arrange/`
- [ ] Create `bin/omarchy-monitor-arrange` launcher with `$OMARCHY_PATH`
- [ ] Create `default/hypr/apps/monitor-arrange.conf` window rule
- [ ] Update `bin/omarchy-menu` line 233 to launch `omarchy-monitor-arrange`
- [ ] Add keybinding `SUPER ALT + M` to default bindings and locally
- [ ] Add migration for existing installs
- [ ] Verify `boot.sh` / `install.sh` handle `lib/` directory
- [ ] Commit, push, open PR against `dev`
