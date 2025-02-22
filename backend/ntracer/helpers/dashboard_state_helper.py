from dataclasses import dataclass, field


@dataclass
class DashboardState:
    selected_indexes: list[list[int]] = field(default_factory=list)
    expanded_neuron: int = -1
    selected_soma_z_slice: int = -1
    selected_point: tuple[int, int, int] | None = None
    highlight_all: bool = False
    highlight_selected: bool = True
    channels: int = 0
    selected_analysis_channels: list[int] = field(default_factory=list)
    selected_display_channels: list[int] = field(default_factory=list)
    projection_range: int = 10
    min_projection_slice: int = 1
    max_projection_slice: int = 40
    scale: tuple[int, int, int] = (1, 1, 1)
    tracing_sensitivity: int = 5
    mean_shift_XY: int = 10
    mean_shift_Z: int = 5

    def get_state_dict(self) -> dict:
        return vars(self)

    @property
    def selected_neuron_id(self) -> int:
        if len(self.selected_indexes) != 1:
            raise Exception("No neuron selected")

        return self.selected_indexes[0][0]

    @property
    def selected_branch_indexes(self) -> list[int]:
        if len(self.selected_indexes) != 1:
            raise Exception("No branch selected")

        return self.selected_indexes[0][1:]

    @property
    def is_neuron_selected(self) -> bool:
        return len(self.selected_indexes) == 1

    @property
    def is_branch_selected(self) -> bool:
        return self.is_neuron_selected and len(self.selected_indexes[0]) > 1

    @property
    def is_point_selected(self) -> bool:
        return (
            self.is_neuron_selected
            and self.selected_point is not None
            and self.selected_point != (-1, -1, -1)
        )

    @property
    def is_soma_selected(self) -> bool:
        return (
            self.is_neuron_selected
            and len(self.selected_indexes[0]) == 1
            and self.selected_soma_z_slice != -1
        )
