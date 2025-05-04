from flask_socketio import SocketIO

from ntracer.helpers.tracing_data_helper import ActionType
from ntracer.ntracer_functions import NtracerFunctions
from ntracer.ntracer_state import NtracerState
from ntracer.state_injector import inject_state, inject_state_and_socketio
from ntracer.visualization.image import ImageFunctions
from ntracer.visualization.indicator import IndicatorFunctions


class Versioning:
    @staticmethod
    @inject_state
    def undo(state: NtracerState):
        coords = state.coords
        if hasattr(state.coords, 'roots'):
            state.coords.roots.dashboard_state.set_state_dict(state.dashboard_state)
        coords.undo()

        for action in coords.roots.actions:
            print(action)
            if action.type == ActionType.ADD_NEURON:
                coords.cdn_helper.delete_neuron(action.neuron_id)
            elif action.type == ActionType.DELETE_NEURON:
                neuron_swc = coords.roots[action.neuron_id].to_swc()
                if neuron_swc is None:
                    raise Warning("Cannot load swc from neuron")
                
                neuron_swc = [line.strip().split() for line in neuron_swc.splitlines()]
                coords.cdn_helper.add_neuron(neuron_swc, action.neuron_id)
            elif action.type == ActionType.MODIFY_NEURON:
                coords.cdn_helper.replace_neuron(
                    action.neuron_id, coords.roots[action.neuron_id]
                )

        IndicatorFunctions.clear_points()
        state.dashboard_state.set_state_dict(coords.roots.dashboard_state)
        NtracerFunctions.set_selected_points()
        NtracerFunctions.request_fileserver_update()
        ImageFunctions.image_write()

        NtracerFunctions.change_coordinate_on_select(state.dashboard_state.selected_point, state.coords.scale)

    @staticmethod
    @inject_state
    def redo(state: NtracerState):
        coords = state.coords
        coords.redo()

        # Redo database changes
        for action in coords.roots.actions:
            if action.type == ActionType.ADD_NEURON:
                neuron_swc = coords.roots[action.neuron_id].to_swc()
                if neuron_swc is None:
                    raise Warning("Cannot load swc from neuron")

                neuron_swc = [line.strip().split() for line in neuron_swc.splitlines()]
                coords.cdn_helper.add_neuron(neuron_swc, action.neuron_id)
            elif action.type == ActionType.DELETE_NEURON:
                coords.cdn_helper.delete_neuron(action.neuron_id)
            elif action.type == ActionType.MODIFY_NEURON:
                coords.cdn_helper.replace_neuron(
                    action.neuron_id, coords.roots[action.neuron_id]
                )

        IndicatorFunctions.clear_points()
        state.dashboard_state.set_state_dict(coords.roots.dashboard_state)
        NtracerFunctions.set_selected_points()
        NtracerFunctions.request_fileserver_update()
        ImageFunctions.image_write()

        NtracerFunctions.change_coordinate_on_select(state.dashboard_state.selected_point, state.coords.scale)