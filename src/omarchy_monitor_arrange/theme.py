from __future__ import annotations

from pathlib import Path

OMARCHY_THEME_DIR = Path.home() / ".config" / "omarchy" / "current" / "theme"

DEFAULT_COLORS: dict[str, tuple[float, float, float, float]] = {
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

_COLOR_MAP = {
    "background":      "bg",
    "color5":          "selected_border",
    "foreground":      "text",
}


def _hex_to_rgba(hex_str: str, alpha: float = 1.0) -> tuple[float, float, float, float]:
    h = hex_str.lstrip("#")
    if len(h) == 6:
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return r / 255.0, g / 255.0, b / 255.0, alpha
    return DEFAULT_COLORS["text"]


def load_colors() -> dict[str, tuple[float, float, float, float]]:
    colors = dict(DEFAULT_COLORS)

    colors_file = OMARCHY_THEME_DIR / "colors"
    if not colors_file.exists():
        return colors

    try:
        for line in colors_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key in _COLOR_MAP and value.startswith("#"):
                    colors[_COLOR_MAP[key]] = _hex_to_rgba(value)
    except OSError:
        pass

    return colors
