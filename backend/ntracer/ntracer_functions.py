import json
import os
import random

# neuroglancer libraries
import neuroglancer
import neuroglancer.webdriver

# numerical libraries
from flask_socketio import SocketIO
from neuroglancer import Viewer
from neuroglancer.viewer_config_state import ConfigState

# internal libraries
from neuroglancer.viewer_config_state import ActionState
from neuroglancer.viewer_state import ViewerState
from ngauge import Neuron
from ngauge import TracingPoint as TP

from ntracer.constants import Constants
from ntracer.helpers.ngauge_helper import NeuronHelper, TracingPointHelper
from ntracer.helpers.tracing_data_helper import Action, ActionType, Coords
from ntracer.ntracer_state import NtracerState
from ntracer.state_injector import inject_state, inject_state_and_socketio
from ntracer.tracing.mean_shift import mean_shift
from ntracer.visualization.image import ImageFunctions
from ntracer.visualization.indicator import IndicatorFunctions


class NtracerFunctions:
    @inject_state
    @staticmethod
    def first_point(
        state: NtracerState,
        action_state: ActionState,
        no_mean_shift: bool = False,
        extend: bool = False,
    ):  # selects first point for a given trace
        if Constants.IS_DEBUG_MODE:
            print("Running first_point with no_mean_shift", no_mean_shift)

        new_point = tuple(map(int, action_state.mouse_voxel_coordinates))
        if not no_mean_shift:
            x = mean_shift(
                action_state.mouse_voxel_coordinates,
                os.environ["PRECOMPUTED_URL_DOCKER"][14:],
                os.environ["DATASET_ID"],
            )
            print(x)
            new_point = x

        if extend and state.endingPoint is not None:
            new_point = state.endingPoint

        state.startingPoint = (
            (new_point[0], new_point[1], new_point[2]) if new_point else None
        )

        print("First mouse position:", new_point)

        config_state: ConfigState
        with state.viewer.config_state.txn() as config_state:
            msg = "First point: " + str(new_point)
            config_state.status_messages["first_point"] = msg
            # socketio.emit("status_message", msg)

        s: ViewerState
        with state.viewer.txn() as s:
            lines = IndicatorFunctions.box_indicator(new_point, "first")

            s.layers["Selection Boxes"] = neuroglancer.viewer_state.AnnotationLayer(
                annotations=lines,
                annotation_color="#ff2400 ",
                shader="""
            void setEndpointMarkerBorderColor(vec4 rgba);
            void setLineWidth(float widthInScreenPixels);
            void setEndpointMarkerSize(float diameter);
            void main() {
            setColor(defaultColor());
            setEndpointMarkerSize(3.0);
            setLineWidth(3.0);
            setEndpointMarkerBorderColor(vec4(0,0,0,0));
            }
            """,
            )
            s.position[2] = new_point[
                2
            ]  # Adjust z-coordinate so selection box is visible

    @inject_state
    @staticmethod
    def change_coordinate(state: NtracerState, xyz):
        viewer = state.viewer
        if viewer is None:
            return
        
        s: ViewerState
        with viewer.txn() as s:
            if s.position is None:
                return
            if xyz[0]:
                s.position[0] = xyz[0]
            if xyz[1]:
                s.position[1] = xyz[1]
            if xyz[2]:
                s.position[2] = xyz[2]
            string_pos = "("
            for i in s.position:
                string_pos += str(i) + ", "
            string_pos = string_pos[:-2]
            string_pos += ")"
            # socketio.emit("status_message", "New position at: " + string_pos)

    @staticmethod
    @inject_state
    def change_coordinate_on_select(state: NtracerState, xyz, scale):
        viewer = state.viewer
        if viewer is None:
            return
        if xyz is None:
            return
        
        s: ViewerState
        with viewer.txn() as s:
            if s.position is None:
                return

            xyz = NeuronHelper.physical_to_pixels(xyz, scale)
            dist = (
                abs(s.position[0] - xyz[0])
                + abs(s.position[1] - xyz[1])
                + abs(s.position[2] - xyz[2])
            )
            if dist < 50:  # only move z if we are already close to selected point
                s.position = [s.position[0], s.position[1], xyz[2]]
            else:
                s.position = xyz

    @staticmethod
    @inject_state
    def ctrl_left_click(state: NtracerState, action_state: ActionState):
        if state.startingPoint is None:
            NtracerFunctions.first_point(action_state)
        else:
            IndicatorFunctions.draw_cyan_box(action_state)

            cs: ConfigState
            with state.viewer.config_state.txn() as cs:
                cs.status_messages[
                    "second_point"
                ] = f"Second point: {state.endingPoint}"
                if "connect" in cs.status_messages:
                    del cs.status_messages["connect"]

    @staticmethod
    @inject_state
    def no_shift(state: NtracerState, s: ActionState):
        if state.startingPoint is None:
            NtracerFunctions.first_point(s, no_mean_shift=True)
        else:
            IndicatorFunctions.draw_cyan_box(s)

    @staticmethod
    async def download_from_database(
        coords: Coords,
    ) -> None:  # retrieves all saved annotations from database
        NUM_PREFETCH = 10

        res = coords.cdn_helper.get_all_neurons()
        coords.new_state()
        coords.roots.actions.append(Action(ActionType.DATABASE_RETRIEVE, -1))

        for neuron_id, _ in res[:-NUM_PREFETCH]:
            coords.roots[neuron_id] = Neuron()
            coords.roots[neuron_id].add_branch(TP(0, 0, 0, 0, 0))

        for neuron_id, _ in res[-NUM_PREFETCH:]:
            neuron = await coords.cdn_helper.get_swc(neuron_id, True)
            if not isinstance(neuron, Neuron):
                raise Warning("Cannot load neuron from swc")

            coords.roots[neuron_id] = neuron

    @staticmethod
    @inject_state
    def add_new_neuron(
        state: NtracerState, neuron: Neuron, neuron_id: int | None = None
    ):
        """Add new neuron to database and coords"""
        neuron_swc = neuron.to_swc()
        if neuron_swc is None:
            raise Warning("Cannot convert neuron to swc")

        neuron_id = state.coords.cdn_helper.add_neuron(neuron_swc, neuron_id)
        state.coords.new_state()
        state.coords.roots.actions.append(Action(ActionType.ADD_NEURON, neuron_id))
        state.coords.roots[neuron_id] = neuron
        NtracerFunctions.request_fileserver_update()
        return neuron_id
    
    @staticmethod
    @inject_state
    def get_selected_points(state: NtracerState) -> list:
        dashboard_state = state.dashboard_state
        coords = state.coords

        if dashboard_state.is_neuron_selected:
            neuron_id = dashboard_state.selected_neuron_id
            neuron = coords.roots[neuron_id]

            if dashboard_state.is_soma_selected:
                return NeuronHelper.get_simple_neuron_soma(
                    neuron, dashboard_state.selected_soma_z_slice
                )
            elif dashboard_state.is_branch_selected:
                node = NeuronHelper.move_to_branches(
                    neuron, dashboard_state.selected_branch_indexes
                )
                return TracingPointHelper.get_simple_branch_points(node)

        return []
    
    @staticmethod
    @inject_state
    def get_soma_list(state: NtracerState) -> list:
        dashboard_state = state.dashboard_state
        if dashboard_state.is_neuron_selected:
            neuron_id = dashboard_state.selected_neuron_id
            if len(dashboard_state.selected_indexes[0]) == 1:  # Return soma list
                return [
                    {"neuron": neuron_id + 1, "z_slice": z_slice}
                    for z_slice, _ in state.coords.roots[neuron_id].soma_layers.items()
                ]
        return []
    
    @staticmethod
    @inject_state
    def set_selected_points(state: NtracerState):
        points = NtracerFunctions.get_selected_points()
        state.selected_tracing_points = json.dumps(points)

    @staticmethod
    def set_display_channels():
        print("set_display_channels has been disabled")

    @staticmethod
    def set_analysis_channels():
        print("set_analysis_channels has been disabled")

    @staticmethod
    @inject_state
    def auto_select_branch(
        state: NtracerState, action_state: ActionState, search_radius: int = 5,
        get_endpoint: bool = False
    ):
        coords = state.coords
        dashboard_state = state.dashboard_state

        selected_coords = NeuronHelper.pixels_to_physical(
            action_state.mouse_voxel_coordinates, coords.scale
        )
        pt, selected_neuron_index = coords.get_close_pt(selected_coords, search_radius)

        if pt is None or selected_neuron_index is None:
            print("No point found")
            return

        if selected_neuron_index is not None:
            current_coords = (pt.x, pt.y, pt.z)
            neuron = coords.roots[selected_neuron_index]
            branch_indexes = NeuronHelper.get_branch_indexes_from_point(
                neuron, current_coords
            )

            if branch_indexes is not None:
                dashboard_state.selected_indexes = [
                    [selected_neuron_index] + branch_indexes
                ]
            else:
                dashboard_state.selected_indexes = [[selected_neuron_index]]
                dashboard_state.selected_soma_z_slice = pt.z

            if get_endpoint and branch_indexes is not None:
                endpoint0 = NeuronHelper.move_to_branches(neuron, branch_indexes)
                endpoint1 = TracingPointHelper.move_to_last_branch_point(endpoint0)

                selected_TP = TP(int(selected_coords[0]), int(selected_coords[1]), int(selected_coords[2]), 0, 0)
                d0 = endpoint0.euclidean_dist(selected_TP)
                d1 = endpoint1.euclidean_dist(selected_TP)

                if d0 < d1:
                    current_coords = (endpoint0.x, endpoint0.y, endpoint0.z)
                else:
                    current_coords = (endpoint1.x, endpoint1.y, endpoint1.z)
            
            dashboard_state.selected_point = current_coords

            ImageFunctions.image_write()
            NtracerFunctions.set_selected_points()
            translated_coords = NeuronHelper.physical_to_pixels(
                current_coords, coords.scale
            )

            s: ViewerState
            with state.viewer.txn() as s:
                s.position[2] = int(translated_coords[2])

            tree_key = ""
            tree_keys = []
            for idx in dashboard_state.selected_indexes[0]:
                if len(tree_keys) == 0:
                    tree_keys.append(str(idx))
                    tree_key = str(idx)
                else:
                    tree_keys.append(tree_key + "_" + str(idx))
                    tree_key = tree_key + "_" + str(idx)


    @staticmethod
    @inject_state
    def set_projection_range(state: NtracerState):
        pass
        # coords = var.coords
        # dashboard_state = var.dashboard_state
        # viewer = var.viewer
        #
        # coords.layer_projection = pyramid_data_format.scale_pyramid.ScalePyramid(
        # [
        #     neuroglancer.LocalVolume(
        #         data=self.ProjectionArray( layer_i, dashboard_state.projection_range ),
        #         dimensions=neuroglancer.CoordinateSpace(
        #             names=["z", "x", "y"],  # ['c^', 'x', 'y', 'z'],
        #             units=["nm", "nm", "nm"],  # ['', 'nm', 'nm', 'nm'],
        #             scales=[2 ** i] * 3,
        #             # coordinate_arrays=[neuroglancer.CoordinateArray(labels=['red','green','blue']), None, None, None]
        #             coordinate_arrays=[None, None, None],
        #         ),
        #         # voxel_offset=(0,0,0,0),
        #         voxel_offset=(0, 0, 0),
        #         volume_type="image",
        #         downsampling=None, # Important to disable downsampling
        #     )
        #     for i, layer_i in enumerate(coords.layer_data)
        # ])
        #
        # with viewer.txn() as s:
        #     s.layers["z-projection"] = neuroglancer.ImageLayer(
        #         source=coords.layer_projection,
        #         shader=self.DEFAULT_SHADER
        #     )

    @staticmethod
    @inject_state
    def request_fileserver_update(state: NtracerState):
        s: ViewerState
        with state.viewer.txn() as s:
            nonce = random.getrandbits(16)
            s.layers["annotate_pre"] = neuroglancer.viewer_state.SegmentationLayer(
                source=f"{state.precomputed_annotation_base}+{nonce}/skeleton/",
                skeleton_rendering=neuroglancer.viewer_state.SkeletonRenderingOptions(
                    mode2d="lines", line_width2d=1
                ),
            )

        # with viewer.txn() as s:
        #     s.layers["annotate_pre"] = neuroglancer.SegmentationLayer(
        #         source="precomputed://http://ntracer2_cdn_1.miserver.it.umich.edu/data/182725/skeleton",
        #         skeleton_rendering=neuroglancer.SkeletonRenderingOptions(mode2d='lines', line_width2d=1)
        #     )
