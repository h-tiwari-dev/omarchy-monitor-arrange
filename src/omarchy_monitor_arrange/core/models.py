from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Monitor:
    name: str
    description: str
    width: int
    height: int
    x: int
    y: int
    scale: float
    transform: int
    refresh_rate: float
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
    0: "Normal",
    1: "90°",
    2: "180°",
    3: "270°",
    4: "Flipped",
    5: "Flipped 90°",
    6: "Flipped 180°",
    7: "Flipped 270°",
}

SCALE_CYCLE = [1.0, 1.25, 1.5, 1.75, 2.0, 3.0]
TRANSFORM_CYCLE = [0, 1, 2, 3]


@dataclass
class SnapResult:
    dx: int = 0
    dy: int = 0
    snapped_x: bool = False
    snapped_y: bool = False


@dataclass
class Overlap:
    monitor_a: str
    monitor_b: str
