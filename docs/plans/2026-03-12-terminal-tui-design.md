# Terminal TUI UI (Textual) Design

Date: 2026-03-12

## Summary
Replace the GTK4 GUI with a keyboard-only terminal UI implemented using Textual.
The core, backend, and config layers remain unchanged. The UI layer is swapped to
Textual while preserving the current keyboard-first workflow and visual layout
semantics.

## Architecture
- Remove GTK4 UI implementation entirely.
- Add a Textual UI implementation under `src/omarchy_monitor_arrange/ui/textual/`.
- Keep `MonitorArrangeUI` protocol as the UI boundary.
- Update `__main__.py` to instantiate the Textual UI instead of GTK4.

## Components
1. MonitorCanvasWidget
   - Custom Textual widget that renders monitor rectangles on a character grid.
   - Handles layout-to-canvas transform, selected highlight, overlap rendering.
   - Optional help overlay.

2. StatusBarWidget
   - Shows selected monitor details (resolution, refresh, scale, position, transform).
   - Displays overlap warnings and unsaved changes.

3. ShortcutBarWidget
   - One-line keyboard shortcut hints.

4. MonitorArrangeApp
   - Wires widgets together.
   - Binds keys to manager actions.
   - Handles apply/exit flow and optional relaunch.

## Data Flow
- MonitorManager remains the single source of truth.
- UI listens to manager changes and triggers redraws.
- Keybindings map directly to manager actions.
- Apply writes config; the app exits and can optionally re-exec for recentering.

## Error Handling
- If Hyprland is not running or no monitors detected, exit with stderr messages.
- Exceptions during load/apply surface as a status message and exit non-zero.
- Overlap warnings are shown in the status bar.

## Testing
- Existing core tests remain unchanged.
- Add UI-level behavior tests only if feasible with Textual test harness; otherwise
  keep UI logic thin and covered by manager/core tests.

## Open Questions
- Whether to re-exec on apply for consistent “recenter” behavior in TUI.
- Final character-cell scaling for monitor rectangles (precision vs readability).
