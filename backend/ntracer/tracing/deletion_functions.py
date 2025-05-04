from flask_socketio import SocketIO

from ntracer.helpers.ngauge_helper import NeuronHelper, TracingPointHelper
from ntracer.helpers.tracing_data_helper import Action, ActionType
from ntracer.ntracer_functions import NtracerFunctions
from ntracer.ntracer_state import NtracerState
from ntracer.state_injector import inject_state, inject_state_and_socketio
from ntracer.tracing.update_functions import UpdateFunctions
from ntracer.visualization.image import ImageFunctions


class DeletionFunctions:
    @staticmethod
    @inject_state
    def delete_neuron(state: NtracerState, neuron_id: int):
        coords = state.coords
        if hasattr(coords, 'roots'):
            coords.roots.dashboard_state.set_state_dict(state.dashboard_state)
        coords.new_state()
        coords.roots.actions.append(Action(ActionType.DELETE_NEURON, neuron_id))
        coords.remove_root(neuron_id)
        state.dashboard_state.selected_indexes = []
        state.dashboard_state.selected_soma_z_slice = -1
        state.dashboard_state.selected_point = None
        state.coords.cdn_helper.delete_neuron(neuron_id)
        ImageFunctions.image_write()
        NtracerFunctions.request_fileserver_update()
        NtracerFunctions.set_selected_points()

    @staticmethod
    @inject_state
    def delete_branch(
        state: NtracerState,
        neuron_id: int,
        branch_indexes: list[int],
    ):
        coords = state.coords
        if hasattr(coords, 'roots'):
            coords.roots.dashboard_state.set_state_dict(state.dashboard_state)
        coords.new_state()
        neuron = coords.roots[neuron_id]
        if len(branch_indexes) == 1:  # Delete root branch
            NeuronHelper.delete_child_branch(neuron, branch_indexes[0])
        else:
            node = NeuronHelper.move_to_branches(neuron, branch_indexes[:-1])
            TracingPointHelper.delete_child_branch(node, branch_indexes[-1])

        if (
            len(neuron.branches) == 0 and len(neuron.soma_layers) == 0
        ):  # Remove neuron since it has no branches and soma
            coords.remove_root(neuron_id)
            coords.roots.actions.append(Action(ActionType.DELETE_NEURON, neuron_id))
            state.dashboard_state.selected_indexes = (
                state.dashboard_state.selected_indexes[:-1]
            )
            state.coords.cdn_helper.delete_neuron(neuron_id)
        else:
            coords.roots.actions.append(Action(ActionType.MODIFY_NEURON, neuron_id))
            state.dashboard_state.selected_indexes = []
            state.coords.cdn_helper.replace_neuron(neuron_id, neuron)

        state.dashboard_state.selected_point = None

        ImageFunctions.image_write()
        NtracerFunctions.set_selected_points()
        NtracerFunctions.request_fileserver_update()
        

    @staticmethod
    @inject_state
    def delete_point(
        state: NtracerState,
        neuron_id: int,
        branch_indexes: list[int],
        selected_point: tuple[int, int, int],
    ):
        coords = state.coords
        if hasattr(coords, 'roots'):
            coords.roots.dashboard_state.set_state_dict(state.dashboard_state)
        coords.new_state()
        coords.roots.actions.append(Action(ActionType.MODIFY_NEURON, neuron_id))
        if len(branch_indexes) == 0:  # Soma
            coords.delete_soma_point(
                neuron_id, state.dashboard_state.selected_soma_z_slice, selected_point
            )
            if (
                len(coords.roots[neuron_id].soma_layers) == 0
                and len(coords.roots[neuron_id].branches) == 0
            ):
                DeletionFunctions.delete_neuron(neuron_id)
            else:
                UpdateFunctions.replace_neuron(state.coords, neuron_id)
        else:
            branch = NeuronHelper.get_child_branch(
                coords.roots[neuron_id], branch_indexes[0]
            )
            branch = TracingPointHelper.move_to_branches(branch, branch_indexes[1:])
            if branch.total_child_nodes() == 1:
                DeletionFunctions.delete_branch(neuron_id, branch_indexes)
                return
            else:
                parent = coords.delete_point(neuron_id, branch_indexes, selected_point)
                UpdateFunctions.replace_neuron(state.coords, neuron_id)
                if parent is not None:
                    state.dashboard_state.selected_point = (
                        parent.x,
                        parent.y,
                        parent.z,
                    )

        NtracerFunctions.request_fileserver_update()
        ImageFunctions.image_write()
        NtracerFunctions.set_selected_points()

    @staticmethod
    @inject_state
    def delete_soma(
        state: NtracerState,
        neuron_id: int,
        selected_soma_z_slice: int,
    ):
        coords = state.coords
        if hasattr(coords, 'roots'):
            coords.roots.dashboard_state.set_state_dict(state.dashboard_state)
        coords.new_state()
        neuron = coords.roots[neuron_id]
        z_slices = None
        if selected_soma_z_slice != -1:
            z_slices = [selected_soma_z_slice]
        NeuronHelper.delete_soma(neuron, z_slices)
        if len(neuron.branches) == 0 and len(neuron.soma_layers) == 0:
            coords.remove_root(neuron_id)
            state.coords.cdn_helper.delete_neuron(neuron_id)
            coords.roots.actions.append(Action(ActionType.DELETE_NEURON, neuron_id))
        else:
            state.coords.cdn_helper.replace_neuron(neuron_id, neuron)
            coords.roots.actions.append(Action(ActionType.MODIFY_NEURON, neuron_id))

        state.dashboard_state.selected_indexes = []
        state.dashboard_state.selected_point = None
        state.dashboard_state.selected_soma_z_slice = -1
        ImageFunctions.image_write()
        NtracerFunctions.set_selected_points()
