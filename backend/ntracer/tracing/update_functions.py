from ngauge import Neuron

from ntracer.helpers.ngauge_helper import NeuronHelper, TracingPointHelper
from ntracer.helpers.tracing_data_helper import Action, ActionType, Coords
from ntracer.ntracer_functions import NtracerFunctions
from ntracer.ntracer_state import NtracerState
from ntracer.state_injector import inject_state
from ntracer.visualization.image import ImageFunctions


class UpdateFunctions:
    @staticmethod
    def auto_update(
        coords: Coords,
    ) -> None:  # keeps all changes saved to sqlite database
        # conn = sqlite3.connect('trace.db')
        for neuron_id, neuron in coords.roots.items():
            neuron.fix_parents()
            coords.cdn_helper.replace_neuron(neuron_id, neuron)

    @staticmethod
    def update_neuron(coords: Coords, neuron_id: int, count: int) -> None:
        """Update specific neuron in database"""
        neuron = coords.roots[neuron_id]
        coords.cdn_helper.update_neuron(neuron_id, neuron)

    @staticmethod
    def replace_neuron(coords: Coords, neuron_id: int) -> None:
        neuron = coords.roots[neuron_id]
        coords.cdn_helper.replace_neuron(neuron_id, neuron)

    @staticmethod
    @inject_state
    def combine_neurons(state: NtracerState, neuron_ids: list[int]):
        coords = state.coords

        if len(neuron_ids) < 2:
            return
        if hasattr(coords, 'roots'):
            coords.roots.dashboard_state.set_state_dict(state.dashboard_state)
        coords.new_state()
        for neuron_id in neuron_ids:
            coords.roots.actions.append(Action(ActionType.MODIFY_NEURON, neuron_id))
        primary_neuron = coords.roots[neuron_ids[0]]
        for neuron_id in neuron_ids[1:]:
            neuron = coords.roots[neuron_id]
            for branch in neuron:
                primary_neuron.add_branch(branch)
            for z_slice, soma_nodes in neuron.soma_layers.items():
                soma_points = [
                    tuple([node.x, node.y, node.z, node.r]) for node in soma_nodes
                ]
                primary_neuron.add_soma_points(soma_points)
            coords.roots.pop(neuron_id)
            state.coords.cdn_helper.delete_neuron(neuron_id)

        state.coords.cdn_helper.replace_neuron(neuron_ids[0], primary_neuron)
        ImageFunctions.image_write()
        NtracerFunctions.set_selected_points()

    @staticmethod
    @inject_state
    def branch_break(
        state: NtracerState,
        neuron_id: int,
        branch_indexes: list[int],
        selected_point: tuple[int, int, int]
    ):
        coords = state.coords
        if hasattr(coords, 'roots'):
            coords.roots.dashboard_state.set_state_dict(state.dashboard_state)
        coords.new_state()
        neuron = coords.roots[neuron_id]
        branch = NeuronHelper.move_to_branches(neuron, branch_indexes)
        selected_node = TracingPointHelper.move_to_point(branch, selected_point)

        if selected_node is None:
            print("Cannot find specified point")
            return

        if len(selected_node.children) != 1:
            return

        new_neuron = Neuron()
        new_neuron.add_branch(selected_node.children[0])
        selected_node.children.pop(0)
        state.coords.cdn_helper.replace_neuron(neuron_id, neuron)
        new_neuron_id = NtracerFunctions.add_new_neuron(new_neuron)
        coords.roots.actions += [
            Action(ActionType.MODIFY_NEURON, neuron_id),
            Action(ActionType.ADD_NEURON, new_neuron_id),
        ]
        ImageFunctions.image_write()
        NtracerFunctions.set_selected_points()

    @staticmethod
    @inject_state
    def set_primary_branch(
        state: NtracerState, neuron_id: int, branch_indexes: list[int]
    ):
        coords = state.coords
        if hasattr(coords, 'roots'):
            coords.roots.dashboard_state.set_state_dict(state.dashboard_state)
        coords.new_state()
        neuron = coords.roots[neuron_id]
        NeuronHelper.set_primary_branch(neuron, branch_indexes)
        coords.roots.actions.append(Action(ActionType.MODIFY_NEURON, neuron_id))
        state.dashboard_state.selected_indexes = []
        state.dashboard_state.selected_point = None
        state.coords.cdn_helper.replace_neuron(neuron_id, neuron)
        NtracerFunctions.set_selected_points()
        ImageFunctions.image_write()

    @staticmethod
    @inject_state
    def join_branches(
        state: NtracerState,
        neuron_id1: int,
        neuron_id2: int,
        branch_indexes1: list[int],
        branch_indexes2: list[int],
    ):
        coords = state.coords
        if hasattr(coords, 'roots'):
            coords.roots.dashboard_state.set_state_dict(state.dashboard_state)
        coords.new_state()

        neuron1 = coords.roots[neuron_id1]
        neuron2 = coords.roots[neuron_id2]

        NeuronHelper.join_branches(neuron1, neuron2, branch_indexes1, branch_indexes2)
        coords.roots.pop(neuron_id2)

        state.coords.cdn_helper.replace_neuron(neuron_id1, neuron1)
        state.coords.cdn_helper.delete_neuron(neuron_id2)

        coords.roots.actions += [
            Action(ActionType.MODIFY_NEURON, neuron_id1),
            Action(ActionType.DELETE_NEURON, neuron_id2),
        ]

        state.dashboard_state.selected_indexes = []
        state.dashboard_state.selected_point = None
        NtracerFunctions.request_fileserver_update()
        NtracerFunctions.set_selected_points()
        ImageFunctions.image_write()
