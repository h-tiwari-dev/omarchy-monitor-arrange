from __future__ import annotations

from rich.text import Text
from textual.widgets import Static

_SHORTCUTS = [
    ("Tab", "Select"),
    ("←↑↓→", "Move"),
    ("r", "Res"),
    ("s", "Scale"),
    ("f", "Hz"),
    ("t", "Rotate"),
    ("p", "Primary"),
    ("i", "Identify"),
    ("u", "Undo"),
    ("Ctrl+r", "Reset"),
    ("Enter", "Apply"),
    ("Esc", "Close"),
    ("h", "Help"),
]


class ShortcutBarWidget(Static):
    """Shows keyboard shortcut hints with styled keys."""

    def __init__(self):
        super().__init__()
        text = Text()
        for i, (key, desc) in enumerate(_SHORTCUTS):
            if i > 0:
                text.append("  ", style="dim")
            text.append(f" {key} ", style="reverse")
            text.append(f" {desc}", style="")
        self.update(text)
