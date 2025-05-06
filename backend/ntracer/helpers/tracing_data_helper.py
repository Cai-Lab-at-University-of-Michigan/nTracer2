import sys
from collections import namedtuple
from copy import Error, deepcopy
from dataclasses import dataclass, field
from enum import Enum
from typing import ItemsView, KeysView

import numpy as np
from ngauge import Neuron
from ngauge.TracingPoint import TracingPoint

from cdn.cdn_array import CdnArray
from cdn.cdn_helper import CdnHelper
from ntracer.helpers.neuron_dict import NeuronDict
from ntracer.helpers.ngauge_helper import NeuronHelper, TracingPointHelper
from ntracer.helpers.dashboard_state_helper import DashboardState

MAX_HISTORY_SIZE = 50
sys.setrecursionlimit(10000)

Action = namedtuple("Action", ["type", "neuron_id"])


class ActionType(Enum):
    DATABASE_RETRIEVE = 1
    ADD_NEURON = 2
    DELETE_NEURON = 3
    MODIFY_NEURON = 4


@dataclass
class NeuronState:
    neuron_dict: NeuronDict = field(default_factory=NeuronDict)
    branched_dict: dict = field(default_factory=dict)
    actions: list = field(default_factory=list)
    dashboard_state: DashboardState = field(default_factory=DashboardState)

    def __getitem__(self, key: int) -> Neuron:
        return self.neuron_dict[key]

    def __setitem__(self, key: int, value: Neuron):
        if not (key in self.neuron_dict):
            self.branched_dict[key] = False
        self.neuron_dict[key] = value

    def __iter__(self):
        return self.neuron_dict.__iter__()

    def __len__(self) -> int:
        return len(self.neuron_dict)

    def set_branched(self, key: str, value: bool):
        if key in self.neuron_dict:
            self.branched_dict[key] = value
        else:
            raise Exception("Cannot set branch values for undefined neurons")

    def has_branch(self, key: int) -> bool:
        return self.branched_dict[key]

    def items(self) -> ItemsView[int, Neuron]:
        return self.neuron_dict.items()

    def keys(self) -> KeysView[int]:
        return self.neuron_dict.keys()

    def pop(self, key: int) -> Neuron:
        self.branched_dict.pop(key)
        return self.neuron_dict.pop(key)


@dataclass()
class Coords:
    """Tracing data properties and functions"""

    cdn_helper: CdnHelper
    cdn_array: CdnArray
    layer_data: list[CdnArray.CdnResolutionItem]
    # layer_projection: ScalePyramid

    radius: int = 5
    timed_out: bool = False
    area: int = 3
    shiftWindow: int = 5
    roots_history: list[NeuronState] = field(default_factory=lambda: [NeuronState()])
    roots_pointer: int = 0
    downloaded_neurons: list[int] = field(default_factory=list)
    scale: tuple[float, float, float] = 10, 10, 1

    @property
    def im_path(self) -> CdnArray.CdnResolutionItem:
        return self.layer_data[0]

    @property
    def shape(self) -> tuple:
        return self.im_path.shape

    @property
    def im_type(self) -> str:
        return str(self.im_path.dtype)

    @property
    def dtype(self) -> str:
        return self.im_type

    @property
    def roots(self) -> NeuronState:
        return self.roots_history[self.roots_pointer]

    @roots.setter
    def roots(self, new_roots: NeuronState):
        if self.roots_pointer >= MAX_HISTORY_SIZE - 1:  # History full, prune
            self.roots_history.pop(0)
            self.roots_history.append(new_roots)
        else:
            if len(self.roots_history) <= self.roots_pointer + 1:
                self.roots_history.append(new_roots)
            else:
                self.roots_history[self.roots_pointer + 1] = new_roots
                del self.roots_history[self.roots_pointer + 2 :]
            self.roots_pointer += 1

    def new_state(self):
        new_coord = NeuronState()
        new_coord.neuron_dict = deepcopy(self.roots.neuron_dict)
        new_coord.branched_dict = deepcopy(self.roots.branched_dict)
        new_coord.dashboard_state = deepcopy(self.roots.dashboard_state)
        self.roots = new_coord

    def undo(self):
        if self.roots_pointer == 0:
            raise Error("No previous state available")
        self.roots_pointer -= 1

    def get_previous_state(self) -> NeuronState:
        if self.roots_pointer == 0:
            raise Error("No previous state available")
        return self.roots_history[self.roots_pointer - 1]

    def redo(self):
        if self.roots_pointer + 1 > len(self.roots_history) - 1:
            raise Error("No next state available")
        self.roots_pointer += 1

    def get_next_state(self) -> NeuronState:
        if self.roots_pointer + 1 > len(self.roots_history) - 1:
            raise Error("No next state available")
        return self.roots_history[self.roots_pointer + 1]

    def remove_root(self, neuron_index: int):
        """Remove a neuron from roots"""
        self.roots.pop(neuron_index)

    def get_newest_neuron(self) -> Neuron:
        """Get newest neuron from roots"""
        return self.roots[-1]

    def delete_soma_point(
        self, neuron_index: int, z_slice: int, target: tuple[int, int, int]
    ):
        neuron = self.roots[neuron_index]
        node = neuron.soma_layers[z_slice]
        del_node_index = next(
            i
            for i, p in enumerate(node)
            if p.x == target[0] and p.y == target[1] and p.z == target[2]
        )
        del node[del_node_index]

    def delete_point(
        self, neuron_index: int, branch_indexes: list[int], target: tuple[int, int, int]
    ) -> TracingPoint:
        """Delete point from neuron"""
        if len(branch_indexes) > 1:
            prev_node = NeuronHelper.move_to_branches(
                self.roots[neuron_index], branch_indexes[:-1]
            )
            prev_node = TracingPointHelper.move_to_last_branch_point(prev_node)
        else:
            prev_node = self.roots[neuron_index]

        node = NeuronHelper.move_to_branches(self.roots[neuron_index], branch_indexes)
        new_node = TracingPointHelper.delete_point(node, target)

        if type(new_node) is list:
            if len(branch_indexes) == 1:
                prev_node.branches = (
                    prev_node.branches[: branch_indexes[-1]]
                    + new_node
                    + prev_node.branches[branch_indexes[-1] + 1 :]
                )
            else:
                prev_node.children = (
                    prev_node.children[: branch_indexes[-1]]
                    + new_node
                    + prev_node.children[branch_indexes[-1] + 1 :]
                )
        else:
            if len(branch_indexes) == 1:
                prev_node.branches[branch_indexes[-1]] = new_node
            else:
                prev_node.children[branch_indexes[-1]] = new_node
        return new_node.parent

    def get_close_pt(
        self, pos, max_dist: int = 30
    ) -> tuple[TracingPoint, int] | tuple[None, None]:
        dist = np.inf
        id: int | None = None
        min_pos: TracingPoint | None = None
        for neuron_id, neuron in self.roots.items():
            for pt in neuron.iter_all_points(False):
                d = (pt.x - pos[0]) ** 2 + (pt.y - pos[1]) ** 2 + (pt.z - pos[2]) ** 2
                if d < dist:
                    dist = d
                    min_pos = pt
                    id = neuron_id
                    if dist < 0.01:
                        return min_pos, id

        if min_pos is None or id is None or dist > max_dist:
            return None, None

        return min_pos, id

    def get_pt(self, pos: tuple[int, int, int], neuron_id: int):
        for pt in self.roots[neuron_id].iter_all_points(False):
            if pos[0] == pt.x and pos[1] == pt.y and pos[2] == pt.z:
                return pt
