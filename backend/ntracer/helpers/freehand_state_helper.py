from dataclasses import dataclass, field


@dataclass
class FreehandState:
    traversed_points_pixel: list[tuple[int, int, int]] = field(default_factory=list)
    traversed_points_physical: list[tuple[int, int, int]] = field(default_factory=list)
    now_at: tuple[int, int, int] | None = None
    is_dashboard_point_selected: bool = False
