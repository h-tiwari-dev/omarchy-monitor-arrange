from __future__ import annotations

from rich.text import Text
from textual.widgets import Static


class ShortcutBarWidget(Static):
    """Shows keyboard shortcut hints."""

    def __init__(self):
        super().__init__()
        self.update(
            Text(
                "[Tab] Select  [Arrows] Move  [r] Res  [s] Scale  "
                "[f] Refresh  [t] Rotate  [p] Primary  "
                "[i] Identify  [u] Undo  [Ctrl+r] Reset  [Ctrl+Shift+r] Hard Reset  "
                "[Enter] Apply  [Esc] Close  [h] Help"
            )
        )
