# neuroglancer libraries
import os

import neuroglancer
import neuroglancer.webdriver
from flask_socketio import SocketIO
from neuroglancer import LineAnnotation  # type: ignore
from neuroglancer.viewer_config_state import ActionState
from neuroglancer.viewer_state import ViewerState
from neuroglancer.viewer_config_state import ConfigState

from ntracer.helpers.tracing_data_helper import Coords
from ntracer.ntracer_state import NtracerState
from ntracer.state_injector import inject_state, inject_state_and_socketio
from ntracer.tracing.mean_shift import mean_shift


class IndicatorFunctions:
    @staticmethod
    @inject_state
    def select_end_point(state: NtracerState, action_state: ActionState, no_mean_shift: bool):
        state.endingPointS = action_state

        if no_mean_shift is False:
            new_point = mean_shift(
                action_state.mouse_voxel_coordinates,
            state.cdn_url.geturl(),
            state.dataset_id,
            )
        else:
            new_point = action_state.mouse_voxel_coordinates
        
        state.endingPoint = new_point
        print("Second mouse position:", state.endingPoint)

        s: ViewerState
        with state.viewer.txn() as s:
            s.dimensions = neuroglancer.CoordinateSpace(
                names=["x", "y", "z"],
                units=["nm", "nm", "nm"],
                scales=state.coords.scale,
            )
            if state.startingPoint is None:
                raise Warning("Starting point is not set")
            
            lines = IndicatorFunctions.box_indicator(state.startingPoint, "first")
            lines.extend(IndicatorFunctions.box_indicator(new_point, "second"))
            s.layers["Selection Boxes"] = neuroglancer.viewer_state.AnnotationLayer(
                annotations=lines,
                annotation_color="#00FFFF",
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

    @staticmethod
    @inject_state
    def clear_points(state: NtracerState):
        from ntracer.ntracer_functions import (
            NtracerFunctions,
        )  # moved due to circular import error

        state.startingPoint = None
        state.endingPoint = None

        s: ViewerState
        with state.viewer.txn() as s:
            # s.display_dimensions = ['z', 'y', 'x']
            s.dimensions = neuroglancer.CoordinateSpace(
                names=["x", "y", "z"],
                units=["nm", "nm", "nm"],
                scales=state.coords.scale,
            )
            s.layers["Selection Boxes"] = neuroglancer.viewer_state.AnnotationLayer(
                annotations=[],
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

            s.layers["Indicators"] = neuroglancer.viewer_state.AnnotationLayer(
                annotations=[],
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

        IndicatorFunctions.clear_status_messages()
        state.dashboard_state.selected_indexes = []
        state.dashboard_state.selected_soma_z_slice = -1
        state.dashboard_state.selected_point = None
        state.dashboard_state.expanded_neuron = -1

    @staticmethod
    def get_soma_annotation(coords: Coords, neuron_id: int, z_slices=None):
        lines = []
        soma_nodes = coords.roots[neuron_id].soma_layers

        if z_slices is None:
            z_slices = soma_nodes.keys()
        for z_slice in z_slices:
            nodes = soma_nodes[z_slice]
            for n in range(len(nodes) - 1):
                pt1, pt2 = nodes[n], nodes[n + 1]
                line = neuroglancer.viewer_state.LineAnnotation()
                line.point_a = list([pt1.x, pt1.y, pt1.z])
                line.point_b = list([pt2.x, pt2.y, pt2.z])
                line.id = "annotate" + str(n)
                lines.append(line)

        return lines

    @staticmethod
    def box_indicator(
        new_point: tuple[int, int, int], name: str
    ) -> list[LineAnnotation]:
        lines = []
        i = 0
        line = neuroglancer.viewer_state.LineAnnotation()
        line.point_a = [new_point[0] - 1, new_point[1] - 1, new_point[2]]
        line.point_b = [new_point[0] + 1, new_point[1] - 1, new_point[2]]
        line.id = name + str(i)
        lines.append(line)
        i += 1
        line = neuroglancer.viewer_state.LineAnnotation()
        line.point_a = [new_point[0] + 1, new_point[1] - 1, new_point[2]]
        line.point_b = [new_point[0] + 1, new_point[1] + 1, new_point[2]]
        line.id = name + str(i)
        lines.append(line)
        i += 1
        line = neuroglancer.viewer_state.LineAnnotation()
        line.point_a = [new_point[0] + 1, new_point[1] + 1, new_point[2]]
        line.point_b = [new_point[0] - 1, new_point[1] + 1, new_point[2]]
        line.id = name + str(i)
        lines.append(line)
        i += 1
        line = neuroglancer.viewer_state.LineAnnotation()
        line.point_a = [new_point[0] - 1, new_point[1] + 1, new_point[2]]
        line.point_b = [new_point[0] - 1, new_point[1] - 1, new_point[2]]
        line.id = name + str(i)
        lines.append(line)

        return lines

    @staticmethod
    @inject_state
    def clear_red_box(state: NtracerState, s):
        state.startingPoint = None
        s.layers["Selection Boxes"] = neuroglancer.viewer_state.AnnotationLayer(
            annotations=[],
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

    @staticmethod
    @inject_state
    def right_click_indicator(state: NtracerState, s: ActionState):
        new_point = tuple(map(int, s.mouse_voxel_coordinates))

        with state.viewer.txn() as s:
            lines = IndicatorFunctions.box_indicator(new_point, "ind")

            s.viewer_state.layers["Selection Boxes"] = neuroglancer.viewer_state.AnnotationLayer(
                annotations=lines,
                annotation_color="#8510d8",
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

    @staticmethod
    @inject_state
    def clear_status_messages(state: NtracerState):
        cs: ConfigState
        with state.viewer.config_state.txn() as cs:
            if "start_point" in cs.status_messages:
                del cs.status_messages["start_point"]
            if "end_point" in cs.status_messages:
                del cs.status_messages["end_point"]
            if "connect" in cs.status_messages:
                del cs.status_messages["connect"]

    @staticmethod
    @inject_state
    def add_status_message(state: NtracerState, message: str, key: str, clear_previous: bool = False):
        cs: ConfigState
        with state.viewer.config_state.txn() as cs:
            cs.status_messages[key] = message
 