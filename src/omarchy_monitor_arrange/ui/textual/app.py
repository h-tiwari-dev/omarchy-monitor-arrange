from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import App, ComposeResult
from textual.binding import Binding

from omarchy_monitor_arrange.ui.textual.canvas import MonitorCanvasWidget
from omarchy_monitor_arrange.ui.textual.shortcuts import ShortcutBarWidget
from omarchy_monitor_arrange.ui.textual.statusbar import StatusBarWidget

if TYPE_CHECKING:
    from omarchy_monitor_arrange.core.manager import MonitorManager


def _rgba_to_hex(rgba: tuple[float, float, float, float]) -> str:
    r, g, b, _a = rgba
    return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"


class MonitorArrangeTextualUI:
    """Textual TUI implementation of MonitorArrangeUI protocol."""

    def __init__(self, colors: dict):
        self._colors = colors

    def run(self, manager: MonitorManager) -> None:
        app = MonitorArrangeApp(manager, self._colors)
        app.run()


class MonitorArrangeApp(App):
    CSS = """
    Screen {
        layout: vertical;
    }
    MonitorCanvasWidget {
        height: 1fr;
    }
    StatusBarWidget {
        height: auto;
        max-height: 3;
        padding: 0 1;
    }
    ShortcutBarWidget {
        height: auto;
        max-height: 2;
        padding: 0 1;
    }
    """

    BINDINGS = [
        Binding("tab", "select_next", "Next monitor", priority=True),
        Binding("shift+tab", "select_prev", "Previous monitor", priority=True),
        Binding("left", "move_left", "Move left"),
        Binding("right", "move_right", "Move right"),
        Binding("up", "move_up", "Move up"),
        Binding("down", "move_down", "Move down"),
        Binding("shift+left", "move_left_fine", "Move left (fine)"),
        Binding("shift+right", "move_right_fine", "Move right (fine)"),
        Binding("shift+up", "move_up_fine", "Move up (fine)"),
        Binding("shift+down", "move_down_fine", "Move down (fine)"),
        Binding("r", "cycle_resolution", "Cycle resolution"),
        Binding("s", "cycle_scale", "Cycle scale"),
        Binding("f", "cycle_refresh", "Cycle refresh"),
        Binding("t", "cycle_transform", "Cycle transform"),
        Binding("p", "set_primary", "Set primary"),
        Binding("i", "identify", "Identify monitors"),
        Binding("u", "undo", "Undo"),
        Binding("ctrl+r", "reset", "Reset"),
        Binding("ctrl+shift+r", "hard_reset", "Hard reset"),
        Binding("enter", "apply", "Apply", priority=True),
        Binding("escape", "quit", "Quit", priority=True),
        Binding("h", "toggle_help", "Help"),
        Binding("question_mark", "toggle_help", "Help"),
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
        yield self._canvas
        yield self._status
        yield ShortcutBarWidget()

    def on_mount(self) -> None:
        bg = _rgba_to_hex(self._colors.get("bg", (0.12, 0.12, 0.14, 1.0)))
        status_bg = _rgba_to_hex(self._colors.get("status_bg", (0.15, 0.15, 0.18, 1.0)))
        text_color = _rgba_to_hex(self._colors.get("text", (0.9, 0.9, 0.92, 1.0)))
        text_dim = _rgba_to_hex(self._colors.get("text_dim", (0.6, 0.6, 0.65, 1.0)))

        self.screen.styles.background = bg

        if self._canvas:
            self._canvas.styles.background = bg
            self._canvas.styles.color = text_color
            self._canvas.focus()

        if self._status:
            self._status.styles.background = status_bg
            self._status.styles.color = text_color

        shortcuts = self.query_one(ShortcutBarWidget)
        shortcuts.styles.background = status_bg
        shortcuts.styles.color = text_dim

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
