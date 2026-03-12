from omarchy_monitor_arrange.core.models import Monitor
from omarchy_monitor_arrange.ui.textual.geometry import compute_transform, map_point


def test_compute_transform_centers_layout():
    monitors = [
        Monitor("A", "", 1920, 1080, 0, 0, 1.0, 0, 60.0),
        Monitor("B", "", 1280, 1024, 1920, 0, 1.0, 0, 60.0),
    ]
    off_x, off_y, scale = compute_transform(monitors, canvas_w=80, canvas_h=24, padding=2)
    assert scale > 0
    x0, y0 = map_point(0, 0, off_x, off_y, scale)
    assert x0 >= 2
