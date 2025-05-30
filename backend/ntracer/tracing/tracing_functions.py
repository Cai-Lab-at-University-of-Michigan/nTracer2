# internal libraries
from time import time

import neuroglancer
import numpy as np
from neuroglancer.viewer_state import ViewerState
from neuroglancer.viewer_config_state import ConfigState
from flask_socketio import SocketIO
from ngauge import Neuron
from ngauge import TracingPoint as TP

from algorithm.astar.tracing import get_trace_cdn as astar
from ntracer.helpers.ngauge_helper import NeuronHelper, TracingPointHelper
from ntracer.helpers.tracing_data_helper import Action, ActionType
from ntracer.ntracer_functions import NtracerFunctions
from ntracer.ntracer_state import NtracerState
from ntracer.state_injector import inject_state
from ntracer.tracing.update_functions import UpdateFunctions
from ntracer.visualization.image import ImageFunctions
from ntracer.utils.timing import print_time
from ntracer.visualization.indicator import IndicatorFunctions
from ntracer.visualization.freehand import FreehandFunctions


class TracingFunctions:
    @staticmethod
    @inject_state
    def connect_or_commit_points(state: NtracerState, is_soma: bool = False):
        if state.endingPoint is not None: # use this to determine
            return TracingFunctions.connect_selected_points(is_soma=is_soma)
        else:
            return TracingFunctions.commit_selected_points(is_soma=is_soma)

    @staticmethod
    @inject_state
    def connect_selected_points(state: NtracerState, is_soma: bool = False):
        start = state.startingPoint
        end = state.endingPoint

        if start is None or end is None:
            IndicatorFunctions.add_status_message("Start and end points not selected", "connect")
            return

        return TracingFunctions._connect_points(start, end, is_soma)
    
    @staticmethod
    @inject_state
    def complete_soma(state: NtracerState, neuron_id: int, selected_soma_z_slice: int):
        coords = state.coords
        if hasattr(coords, 'roots'):
            coords.roots.dashboard_state.set_state_dict(state.dashboard_state)
        coords.new_state()
        coords.roots.actions.append(Action(ActionType.MODIFY_NEURON, neuron_id))
        neuron = coords.roots[neuron_id]
        soma_points = neuron.soma_layers[selected_soma_z_slice]
        start = NeuronHelper.physical_to_pixels(
            tuple(np.array([soma_points[-1].x, soma_points[-1].y, soma_points[-1].z])),
            coords.scale,
        )
        end = NeuronHelper.physical_to_pixels(
            tuple(np.array([soma_points[0].x, soma_points[0].y, soma_points[0].z])),
            coords.scale,
        )
        return TracingFunctions._connect_points(start, end, True)
    
    @staticmethod
    @print_time("ASTAR")
    @inject_state
    def _connect_points(state: NtracerState, start: tuple, end: tuple, is_soma: bool = False):
        if state.dashboard_state.is_soma_selected and not is_soma:
            state.dashboard_state.selected_soma_z_slice = -1
        
        print("Running Astar:", start, end)
        try:
            new_path = astar(
                state.cdn_url.geturl(),
                state.dataset_id,
                start,
                end,
                state.is_multi,
                is_soma,
                tracing_sensitivity=state.dashboard_state.tracing_sensitivity,
            )
        except Exception as e:
            IndicatorFunctions.add_status_message(f"Trace failed: {e}", "connect")
            return
        
        # Path drawn, need to connect path to each other AND root to existing node
        s: ViewerState
        with state.viewer.txn() as s:
            s.dimensions = neuroglancer.CoordinateSpace(
                names=["x", "y", "z"],
                units=["nm", "nm", "nm"],
                scales=state.coords.scale,
            )

        new_path = [
            NeuronHelper.pixels_to_physical(xs, state.coords.scale) for xs in new_path
        ]

        if is_soma:
            TracingFunctions._add_traced_soma(new_path)
        else:
            TracingFunctions._add_traced_neurites(new_path)

        IndicatorFunctions.clear_status_messages()

        config_state: ConfigState
        with state.viewer.config_state.txn() as config_state:
            config_state.status_messages["connect"] = "tracing generated"

        NtracerFunctions.select_point(end, no_mean_shift=is_soma, is_end_point=False)
        
        if state.dashboard_state.is_neuron_selected:
            neuron_id = state.dashboard_state.selected_neuron_id
            neuron = state.coords.roots[neuron_id]
            branch_indexes = NeuronHelper.get_branch_indexes_from_point(
                neuron, new_path[-1]
            )
            if branch_indexes is not None:
                state.dashboard_state.selected_indexes = [
                    [neuron_id] + branch_indexes
                ]

        state.dashboard_state.selected_point = new_path[-1]  # type: ignore
        NtracerFunctions.change_coordinate_on_select(state.dashboard_state.selected_point, state.coords.scale)

        NtracerFunctions.set_selected_points()
        ImageFunctions.image_write()


    @staticmethod
    @inject_state
    def _add_traced_neurites(state: NtracerState, new_path: list):
        if state.dashboard_state.is_neuron_selected:
            if hasattr(state.coords, 'roots'):
                state.coords.roots.dashboard_state.set_state_dict(state.dashboard_state)
            state.coords.new_state()
            state.coords.roots.actions.append(
                Action(
                    ActionType.MODIFY_NEURON, state.dashboard_state.selected_neuron_id
                )
            )
            neuron = state.coords.roots[state.dashboard_state.selected_neuron_id]

            if state.dashboard_state.is_branch_selected:
                branch_indexes = state.dashboard_state.selected_branch_indexes
                if branch_indexes is None:
                    raise Warning("Point specified but branch not specified")

                branch = NeuronHelper.move_to_branches(neuron, branch_indexes)

                if state.dashboard_state.selected_point is None:
                    raise Warning("Point not specified")

                found = TracingPointHelper.move_to_point(
                    branch, state.dashboard_state.selected_point
                )
                if found is None:
                    raise Warning("Branch end point not found")
                current = found

            else:  # Add new root branch
                neuron.add_branch(
                    TP(
                        new_path[0][0],
                        new_path[0][1],
                        new_path[0][2],
                        state.coords.radius,
                        2,
                    )
                )
                current = neuron.branches[-1]

            if current is None or not isinstance(current, TP):
                print("Selected point not found")
                return

            for pt in new_path[1:]:
                new_pt = TP(pt[0], pt[1], pt[2], state.coords.radius, 2)
                current.add_child(new_pt)
                current = new_pt

            neuron_id = state.dashboard_state.selected_neuron_id
            UpdateFunctions.replace_neuron(state.coords, neuron_id)
            NtracerFunctions.request_fileserver_update()
        else:
            neuron = Neuron()
            neuron.add_branch(
                TP(
                    new_path[0][0],
                    new_path[0][1],
                    new_path[0][2],
                    state.coords.radius,
                    2,
                )
            )
            current: TP = neuron.branches[0]
            for pt in new_path[1:]:
                new_pt = TP(pt[0], pt[1], pt[2], state.coords.radius, 2)
                current.add_child(new_pt)
                current = new_pt
            new_neuron_id = NtracerFunctions.add_new_neuron(neuron)
            state.dashboard_state.selected_indexes = [[new_neuron_id, 0]]

    @staticmethod
    @inject_state
    def _add_traced_soma(state: NtracerState, new_path: list):
        if state.dashboard_state.is_neuron_selected:
            if hasattr(state.coords, 'roots'):
                state.coords.roots.dashboard_state.set_state_dict(state.dashboard_state)
            state.coords.new_state()
            state.coords.roots.actions.append(
                Action(
                    ActionType.MODIFY_NEURON, state.dashboard_state.selected_neuron_id
                )
            )
            neuron_id = state.dashboard_state.selected_neuron_id
            neuron = state.coords.roots[neuron_id]
            neuron.add_soma_points(
                [(pt[0], pt[1], pt[2], state.coords.radius) for pt in new_path]
            )
            UpdateFunctions.replace_neuron(state.coords, neuron_id)
            NtracerFunctions.request_fileserver_update()
        else:
            neuron = Neuron()
            neuron.add_soma_points(
                [(pt[0], pt[1], pt[2], state.coords.radius) for pt in new_path]
            )

            new_neuron_id = NtracerFunctions.add_new_neuron(neuron)
            state.dashboard_state.selected_indexes = [[new_neuron_id]]
            state.dashboard_state.selected_soma_z_slice = new_path[0][2]  # type: ignore

    @staticmethod
    @print_time("DB")
    @inject_state
    def commit_selected_points(state: NtracerState, is_soma=False):
        def interpolate_soma_points(points_list):
            if len(points_list) < 2:
                return [NeuronHelper.pixels_to_physical(tuple(p), state.coords.scale) 
                        for p in points_list]
            
            points = np.array(points_list)
            pixel_pts = []
            
            for i in range(len(points) - 1):
                p1, p2 = points[i], points[i + 1]
                pixel_pts.append(tuple(p1))
                
                dist = np.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)
                steps = max(20, int(np.ceil(dist)))
                z = p1[2] if len(p1) > 2 else 0.0
                
                for j in range(1, steps):
                    t = float(j / steps)
                    x = p1[0] * (1 - t) + p2[0] * t
                    y = p1[1] * (1 - t) + p2[1] * t
                    pixel_pts.append((x, y, z))
            
            if len(points) > 0:
                pixel_pts.append(tuple(points[-1]))
            return [NeuronHelper.pixels_to_physical(tuple([float(p) for p in pt]), state.coords.scale) for pt in pixel_pts]

        if FreehandFunctions.is_empty():
            return
        
        if is_soma:
            TracingFunctions._add_traced_soma(interpolate_soma_points(state.freehand_state.traversed_points_pixel))
        else:
            TracingFunctions._add_traced_neurites(state.freehand_state.traversed_points_physical)

        if state.dashboard_state.is_neuron_selected:
            neuron_id = state.dashboard_state.selected_neuron_id
            neuron = state.coords.roots[neuron_id]
            branch_indexes = NeuronHelper.get_branch_indexes_from_point(
                neuron, state.freehand_state.traversed_points_physical[-1]
            )
            if branch_indexes is not None:
                state.dashboard_state.selected_indexes = [
                    [neuron_id] + branch_indexes
                ]

        NtracerFunctions.select_point(state.freehand_state.traversed_points_pixel[-1], no_mean_shift=is_soma, is_end_point=False)
        state.dashboard_state.selected_point = state.freehand_state.traversed_points_physical[-1]
        NtracerFunctions.set_selected_points()

        config_state: ConfigState
        with state.viewer.config_state.txn() as config_state:
            config_state.status_messages["commit"] = "drawing committed"

        FreehandFunctions.clear_freehand_state()
        FreehandFunctions.update_canvas()
        FreehandFunctions.clear_status_messages()
        IndicatorFunctions.clear_status_messages()
        ImageFunctions.image_write()