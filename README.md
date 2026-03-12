# Omarchy Monitor Arrange

![Default Image](./screenshots/svg/main.svg)
A macOS-like, keyboard-first visual monitor arrangement tool for [Omarchy](https://omarchy.com) (Hyprland).  
Drag monitors as rectangles on a 2D canvas, reposition with arrow keys, and write directly to `~/.config/hypr/monitors.conf`.

## Requirements

- **Hyprland** (running — uses `hyprctl`)
- **Python 3.11+**
- **Textual** (terminal UI library)

Install Textual with pip.

## Quick Start (development)

Run directly from the source tree:

```bash
cd ~/Documents/omarchy-monitor-arrange
python3 -m pip install -r requirements.txt
PYTHONPATH=src python3 -m omarchy_monitor_arrange
```

## Install (local)

Copy the package and launcher into your local paths:

```bash
# Install library
mkdir -p ~/.local/lib/omarchy-monitor-arrange
cp -r src/omarchy_monitor_arrange ~/.local/lib/omarchy-monitor-arrange/

# Install launcher
cp bin/omarchy-monitor-arrange ~/.local/bin/
chmod +x ~/.local/bin/omarchy-monitor-arrange

# Add Hyprland window rule (float the app window)
echo 'windowrule = tag +floating-window, match:class org.omarchy.monitor-arrange' \
  >> ~/.config/hypr/hyprland.conf
```

Then run from anywhere:

```bash
omarchy-monitor-arrange
```

## Omarchy Menu Integration

To add a "Monitors" entry to the Omarchy setup menu, create or edit `~/.config/omarchy/extensions/menu.sh` and override `show_setup_menu()` so the Monitors case launches `omarchy-monitor-arrange` instead of opening the config in an editor. See `PLAN.md` for the full menu override snippet.

## Keyboard Controls

| Key | Action |
|-----|--------|
| Tab / Shift+Tab | Select next / previous monitor |
| Arrow keys | Move selected monitor (coarse) |
| Shift + Arrows | Move selected monitor (fine, 1px) |
| r | Cycle resolution |
| s | Cycle scale (1 → 1.25 → 1.5 → 1.75 → 2 → 3) |
| f | Cycle refresh rate |
| t | Cycle transform (Normal → 90° → 180° → 270°) |
| p | Set selected as primary |
| i | Identify — flash name on each physical display |
| u | Undo last move |
| Enter | Apply — write config and reload Hyprland |
| Escape | Close without saving |
| h / ? | Toggle help overlay |

## Running Tests

```bash
cd ~/Documents/omarchy-monitor-arrange
PYTHONPATH=src python3 -m pytest tests/ -v
```

## Project Structure

```
src/omarchy_monitor_arrange/
├── core/           # Pure logic — models, layout engine, config writer, manager
├── backends/       # Compositor abstraction (Hyprland today, others later)
├── ui/             # Presentation layer (Textual TUI)
└── theme.py        # Omarchy theme color loading
```

The architecture is interface-driven: core knows nothing about UI, UI knows nothing about Hyprland. All layer boundaries use Python Protocols (PEP 544). See `PLAN.md` for the full design.

## License

Part of the Omarchy project.
