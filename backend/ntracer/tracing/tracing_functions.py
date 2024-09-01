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


class TracingFunctions:
    @staticmethod
    @print_time("ASTAR")
    @inject_state
    def connect_points(state: NtracerState):
        if state.startingPoint is None or state.endingPoint is None:
            raise Warning("End points not selected")

        if state.startingPoint is None or state.endingPoint is None:
            return

        is_soma = False

        print("Running Astar:", state.startingPoint, state.endingPoint)
        new_path = astar(
            state.cdn_url.geturl(),
            state.dataset_id,
            state.startingPoint,
            state.endingPoint,
            state.is_multi,
            is_soma,
            tracing_sensitivity=state.dashboard_state.tracing_sensitivity,
        )
        # Path drawn, need to connect path to each other AND root to existing node

        s: ViewerState
        with state.viewer.txn() as s:
            s.dimensions = neuroglancer.CoordinateSpace(
                names=["x", "y", "z"],
                units=["nm", "nm", "nm"],
                scales=state.coords.scale,
            )

        if len(new_path) == 0:  # timed out
            config_state: ConfigState
            with state.viewer.config_state.txn() as config_state:
                if state.coords.timed_out:
                    config_state.status_messages["connect"] = "time out"
                    socketio.emit("status_message", "time out")
            return

        new_path = [
            NeuronHelper.pixels_to_physical(xs, state.coords.scale) for xs in new_path
        ]

        if state.dashboard_state.is_neuron_selected:
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
            # socketio.emit(
            #     "expand_tree", {"ids": [str(new_neuron_id), f"{new_neuron_id}-1"]}
            # )
            # NtracerFunctions.send_to_html(state, socketio)

        config_state: ConfigState
        with state.viewer.config_state.txn() as config_state:
            ImageFunctions.image_write()
            if "first_point" in config_state.status_messages:
                del config_state.status_messages["first_point"]
            if "second_point" in config_state.status_messages:
                del config_state.status_messages["second_point"]
            config_state.status_messages["connect"] = "path generated"
            # socketio.emit("status_message", "path generated")

        if state.endingPointS is None:
            return

        NtracerFunctions.first_point(state.endingPointS, True, True)

        state.dashboard_state.selected_point = new_path[-1]  # type: ignore

        NtracerFunctions.set_selected_points()


    @staticmethod
    @print_time("ASTAR")
    @inject_state
    def connect_soma_points(state: NtracerState):
        if state.startingPoint is None or state.endingPoint is None:
            print("End points not selected")
            return

        t1 = time()
        viewer = state.viewer
        dashboard_state = state.dashboard_state
        coords = state.coords

        if state.startingPoint is None or state.endingPoint is None:
            print("points not selected")
            return

        print("STARTING SOMA CONNECTION")

        print("Second mouse position:", state.endingPoint)

        print("Running Astar:", state.startingPoint, state.endingPoint)
        state.endingPoint = (
            state.endingPoint[0],
            state.endingPoint[1],
            state.startingPoint[2],
        )

        t2 = time()
        new_path = astar(
            state.cdn_url.geturl(),
            state.dataset_id,
            state.startingPoint,
            state.endingPoint,
            state.is_multi,
            True,
            tracing_sensitivity=state.dashboard_state.tracing_sensitivity,
        )
        t3 = time()
        # print("New path:", new_path)

        # Path drawn, need to connect path to each other AND root to existing node

        # with viewer.txn() as s:
        #     s.dimensions = neuroglancer.CoordinateSpace(
        #         names=["x", "y", "z"], units=["nm", "nm", "µm"], scales=[350, 350, 1],
        #     )

        if len(new_path) == 0:
            s: ConfigState
            with state.viewer.config_state.txn() as s:
                if state.coords.timed_out:
                    s.status_messages["connect"] = "time out"
                    # socketio.emit("status_message", "time out")
            return

        new_path = [
            NeuronHelper.pixels_to_physical(xs, state.coords.scale) for xs in new_path
        ]

        t4, t5, tt1, tt2 = time(), time(), time(), time()

        if dashboard_state.is_neuron_selected:
            neuron_id = dashboard_state.selected_neuron_id
            neuron = coords.roots[neuron_id]
            neuron.add_soma_points(
                [(pt[0], pt[1], pt[2], coords.radius) for pt in new_path]
            )
            UpdateFunctions.replace_neuron(coords, neuron_id)
        else:
            neuron = Neuron()
            neuron.add_soma_points(
                [(pt[0], pt[1], pt[2], coords.radius) for pt in new_path]
            )

            new_neuron_id = NtracerFunctions.add_new_neuron(neuron)
            dashboard_state.selected_indexes = [[new_neuron_id]]
            dashboard_state.selected_soma_z_slice = new_path[0][2]  # type: ignore
            # socketio.emit("expand_tree", {"ids": [str(new_neuron_id)]})
        NtracerFunctions.request_fileserver_update()

        t9 = time()

        s: ConfigState
        with state.viewer.config_state.txn() as s:
            ImageFunctions.image_write()
            del s.status_messages["first_point"]
            del s.status_messages["second_point"]
            s.status_messages["connect"] = "path generated"
            # socketio.emit("status_message", "path generated")

        t7 = time()

        if state.endingPointS is not None:
            NtracerFunctions.first_point(state.endingPointS, True, True)

        t8 = time()
        dashboard_state.selected_point = new_path[-1]  # type: ignore
        NtracerFunctions.set_selected_points()
        t6 = time()
        print("Total time: ", t6 - t1)
        print("astar: ", t3 - t2)
        print("database: ", t5 - t4)
        print("mean shift", t8 - t7)
        print("send to html", t6 - t8)
        print("image_write", t7 - t9)
        print(
            "others: ",
            (t6 - t1) - (t3 - t2) - (t5 - t4) - (t8 - t7) - (t6 - t8) - (t7 - t9),
        )

    @staticmethod
    @inject_state
    def complete_soma(
        state: NtracerState,
        neuron_id: int,
        selected_soma_z_slice: int,
    ):
        coords = state.coords
        coords.new_state()
        coords.roots.actions.append(Action(ActionType.MODIFY_NEURON, neuron_id))
        neuron = coords.roots[neuron_id]
        soma_points = neuron.soma_layers[selected_soma_z_slice]
        st = NeuronHelper.physical_to_pixels(
            tuple(np.array([soma_points[-1].x, soma_points[-1].y, soma_points[-1].z])),
            coords.scale,
        )
        end = NeuronHelper.physical_to_pixels(
            tuple(np.array([soma_points[0].x, soma_points[0].y, soma_points[0].z])),
            coords.scale,
        )
        new_path = astar(
            state.cdn_url.geturl(),
            state.dataset_id,
            st,
            end,
            state.is_multi,
            is_soma=True,
            tracing_sensitivity=state.dashboard_state.tracing_sensitivity,
        )
        new_path = [
            NeuronHelper.pixels_to_physical(xs, coords.scale) for xs in new_path
        ]
        neuron.add_soma_points([list(point) + [coords.radius] for point in new_path])
        UpdateFunctions.update_neuron(state.coords, neuron_id, len(new_path))
        ImageFunctions.image_write()
        NtracerFunctions.request_fileserver_update()
        NtracerFunctions.set_selected_points()
