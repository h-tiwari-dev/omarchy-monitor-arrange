from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import App, ComposeResult
from textual.containers import Vertical

from omarchy_monitor_arrange.ui.textual.canvas import MonitorCanvasWidget
from omarchy_monitor_arrange.ui.textual.shortcuts import ShortcutBarWidget
from omarchy_monitor_arrange.ui.textual.statusbar import StatusBarWidget

if TYPE_CHECKING:
    from omarchy_monitor_arrange.core.manager import MonitorManager


class MonitorArrangeTextualUI:
    """Textual TUI implementation of MonitorArrangeUI protocol."""

    def __init__(self, colors: dict):
        self._colors = colors

    def run(self, manager: MonitorManager) -> None:
        app = MonitorArrangeApp(manager, self._colors)
        app.run()


class MonitorArrangeApp(App):
    BINDINGS = [
        ("tab", "select_next", "Next monitor"),
        ("shift+tab", "select_prev", "Previous monitor"),
        ("left", "move_left", "Move left"),
        ("right", "move_right", "Move right"),
        ("up", "move_up", "Move up"),
        ("down", "move_down", "Move down"),
        ("shift+left", "move_left_fine", "Move left (fine)"),
        ("shift+right", "move_right_fine", "Move right (fine)"),
        ("shift+up", "move_up_fine", "Move up (fine)"),
        ("shift+down", "move_down_fine", "Move down (fine)"),
        ("r", "cycle_resolution", "Cycle resolution"),
        ("s", "cycle_scale", "Cycle scale"),
        ("f", "cycle_refresh", "Cycle refresh"),
        ("t", "cycle_transform", "Cycle transform"),
        ("p", "set_primary", "Set primary"),
        ("i", "identify", "Identify monitors"),
        ("u", "undo", "Undo"),
        ("ctrl+r", "reset", "Reset"),
        ("ctrl+shift+r", "hard_reset", "Hard reset"),
        ("enter", "apply", "Apply"),
        ("escape", "quit", "Quit"),
        ("h", "toggle_help", "Help"),
        ("?", "toggle_help", "Help"),
    ]

    def __init__(self, manager: MonitorManager, colors: dict):
        super().__init__()
        self._manager = manager
        self._colors = colors
        self._canvas: MonitorCanvasWidget | None = None
        self._status: StatusBarWidget | None = None

    def compose(self) -> ComposeResult:
        self._canvas = MonitorCanvasWidget(self._manager, self._colors)
        self._status = StatusBarWidget(self._manager)
        shortcuts = ShortcutBarWidget()
        with Vertical():
            yield self._canvas
            yield self._status
            yield shortcuts

    def on_mount(self) -> None:
        self._manager.on_change(self._on_manager_change)
        self._manager.highlight_selected()
        self._on_manager_change()

    def _on_manager_change(self) -> None:
        if self._canvas:
            self._canvas.refresh()
        if self._status:
            self._status.update_status()

    def _move(self, dx: int, dy: int, fine: bool) -> None:
        step = self._manager.FINE_STEP if fine else self._manager.COARSE_STEP
        snap = not fine
        self._manager.move_selected(dx * step, dy * step, snap=snap)

    def action_select_next(self) -> None:
        self._manager.select_next()
        self._manager.highlight_selected()

    def action_select_prev(self) -> None:
        self._manager.select_prev()
        self._manager.highlight_selected()

    def action_move_left(self) -> None:
        self._move(-1, 0, fine=False)

    def action_move_right(self) -> None:
        self._move(1, 0, fine=False)

    def action_move_up(self) -> None:
        self._move(0, -1, fine=False)

    def action_move_down(self) -> None:
        self._move(0, 1, fine=False)

    def action_move_left_fine(self) -> None:
        self._move(-1, 0, fine=True)

    def action_move_right_fine(self) -> None:
        self._move(1, 0, fine=True)

    def action_move_up_fine(self) -> None:
        self._move(0, -1, fine=True)

    def action_move_down_fine(self) -> None:
        self._move(0, 1, fine=True)

    def action_cycle_resolution(self) -> None:
        self._manager.cycle_resolution()

    def action_cycle_scale(self) -> None:
        self._manager.cycle_scale()

    def action_cycle_refresh(self) -> None:
        self._manager.cycle_refresh_rate()

    def action_cycle_transform(self) -> None:
        self._manager.cycle_transform()

    def action_set_primary(self) -> None:
        self._manager.set_primary()

    def action_identify(self) -> None:
        self._manager.identify()

    def action_undo(self) -> None:
        self._manager.undo()

    def action_reset(self) -> None:
        self._manager.reset()

    def action_hard_reset(self) -> None:
        self._manager.hard_reset()

    def action_toggle_help(self) -> None:
        if self._canvas:
            self._canvas.show_help = not self._canvas.show_help

    def action_apply(self) -> None:
        self._manager.apply()
        self.exit()

    def action_quit(self) -> None:
        self._manager.clear_highlight()
        self.exit()
