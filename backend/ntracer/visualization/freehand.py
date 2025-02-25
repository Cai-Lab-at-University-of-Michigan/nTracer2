import neuroglancer
import numpy as np
from neuroglancer.viewer_config_state import ConfigState, ActionState

from ntracer.ntracer_state import NtracerState
from ntracer.state_injector import inject_state
from ntracer.helpers.ngauge_helper import NeuronHelper

class FreehandFunctions:
    @staticmethod
    @inject_state
    def select_point(state: NtracerState, new_point: tuple[int, int, int]):
        FreehandFunctions.update_freehand_location(new_point)
        FreehandFunctions.update_freehand_state()
        FreehandFunctions.update_canvas()

    @staticmethod
    @inject_state
    def update_freehand_location(state: NtracerState, new_point: tuple[int, int, int]):
        state.freehand_state.now_at = new_point

    @staticmethod
    @inject_state
    def clear_points(state: NtracerState):
        FreehandFunctions.clear_freehand_state()
        FreehandFunctions.update_canvas()
        FreehandFunctions.clear_status_messages()

    @staticmethod
    @inject_state
    def is_empty(state: NtracerState):
        if len(state.freehand_state.traversed_points_physical):
            return False
        else:
            return True    
        
    @staticmethod
    @inject_state
    def update_freehand_state(state: NtracerState):
        state.freehand_state.traversed_points_pixel.append(state.freehand_state.now_at)
        new_point_physical = NeuronHelper.pixels_to_physical(state.freehand_state.now_at, state.coords.scale)
        state.freehand_state.traversed_points_physical.append(new_point_physical)

    @staticmethod
    @inject_state
    def clear_freehand_state(state: NtracerState):
        state.freehand_state.now_at = None
        # state.freehand_state.dashboard_selected_point = None
        state.freehand_state.traversed_points_pixel = []
        state.freehand_state.traversed_points_physical = []

    @staticmethod
    @inject_state
    def smooth_current_path(state: NtracerState, 
                        simplify_tolerance: float = 2.0,
                        smooth_factor: float = 0.5,
                        iterations: int = 1):
        if len(state.freehand_state.traversed_points_pixel) < 3:
            return
        
        points_array = np.array(state.freehand_state.traversed_points_pixel)
        
        # Step 1: Simplify - remove redundant points
        simplified = []
        if len(points_array) >= 2:
            simplified = [points_array[0]]
            
            for i in range(1, len(points_array)):
                last_point = simplified[-1]
                current_point = points_array[i]
                
                dx = current_point[0] - last_point[0]
                dy = current_point[1] - last_point[1]
                dz = current_point[2] - last_point[2]
                distance = np.sqrt(dx*dx + dy*dy + dz*dz)
                
                if distance > simplify_tolerance:
                    simplified.append(current_point)
            
            if not np.array_equal(simplified[-1], points_array[-1]):
                simplified.append(points_array[-1])
        
        simplified = np.array(simplified)
        
        # Step 2: Smooth the path
        smoothed = simplified.copy()
        if len(simplified) >= 3:
            for _ in range(iterations):
                new_smoothed = smoothed.copy()
                
                for i in range(1, len(smoothed) - 1):
                    prev = smoothed[i - 1]
                    current = smoothed[i]
                    next_point = smoothed[i + 1]
                    
                    new_smoothed[i] = current * (1 - smooth_factor) + (prev + next_point) / 2 * smooth_factor
                
                smoothed = new_smoothed
        
        smoothed_points = [(int(round(x)), int(round(y)), int(round(z))) for x, y, z in smoothed]
        state.freehand_state.traversed_points_pixel = smoothed_points
        state.freehand_state.traversed_points_physical = [
            NeuronHelper.pixels_to_physical(point, state.coords.scale)
            for point in smoothed_points
        ]

    @staticmethod
    @inject_state
    def update_canvas(state: NtracerState) -> None:
        points = state.freehand_state.traversed_points_pixel
        lines = []
        i = 1
        if len(points) > 1:
            for tp0, tp1 in zip(points[:-1], points[1:]):
                line = neuroglancer.viewer_state.LineAnnotation()
                line.point_a = [tp0[0], tp0[1], tp0[2]]
                line.point_b = [tp1[0], tp1[1], tp1[2]]
                line.id = i
                i += 1
                lines.append(line)

        with state.viewer.txn() as s:
            s.dimensions = neuroglancer.CoordinateSpace(
                names=["x", "y", "z"],
                units=["nm", "nm", "nm"],
                scales=state.coords.scale,
            )

            s.layers['freehand_canvas'] = neuroglancer.viewer_state.AnnotationLayer(
                annotations=lines,
                annotation_color="#f5f5f5",
                shader="""
                void main() {
                setColor(defaultColor());
                }
                """,
            )
        
    @staticmethod
    @inject_state
    def update_box_indicator(
        state:NtracerState, lines: list[neuroglancer.viewer_state.LineAnnotation]
    ) -> None:
        with state.viewer.txn() as s:
            s.dimensions = neuroglancer.CoordinateSpace(
                names=["x", "y", "z"],
                units=["nm", "nm", "nm"],
                scales=state.coords.scale,
            )
            
            s.layers["Selection Boxes"] = neuroglancer.viewer_state.AnnotationLayer(
                annotations=lines,
                annotation_color="#ff2400",
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

            s.position[2] = state.freehand_state.now_at[2]

    @staticmethod
    @inject_state
    def clear_status_messages(state: NtracerState):
        cs: ConfigState
        with state.viewer.config_state.txn() as cs:
            if "start_point" in cs.status_messages:
                del cs.status_messages["start_point"]
            if "end_point" in cs.status_messages:
                del cs.status_messages["end_point"]
            if "commit" in cs.status_messages:
                del cs.status_messages["commit"]

    @staticmethod
    @inject_state
    def add_status_message(state: NtracerState, message: str, key: str, clear_previous: bool = False):
        cs: ConfigState
        with state.viewer.config_state.txn() as cs:
            cs.status_messages[key] = message