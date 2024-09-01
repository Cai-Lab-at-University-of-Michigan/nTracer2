from time import time

# neuroglancer libraries
import neuroglancer
import neuroglancer.webdriver

# internal libraries
from ngauge import TracingPoint as TP

from neuroglancer.viewer_state import ViewerState
from ntracer.constants import Constants
from ntracer.helpers.ngauge_helper import NeuronHelper
from ntracer.ntracer_state import NtracerState
from ntracer.state_injector import inject_state
from ntracer.visualization.indicator import IndicatorFunctions


class ImageFunctions:
    @staticmethod
    @inject_state
    def image_init(
        state: NtracerState,
    ):  # initializes image layer, only called once at beginning
        viewer = state.viewer
        coords = state.coords

        dashboard_state = state.dashboard_state

        s: ViewerState
        with viewer.txn() as s:
            s.dimensions = neuroglancer.CoordinateSpace(
                names=["x", "y", "z"],
                units=["nm", "nm", "nm"],
                scales=state.coords.scale,
            )
            s.prefetch = False
            s.concurrent_downloads = 5

            s.layers["image"] = neuroglancer.viewer_state.ImageLayer(
                # source=coords.layer, #need to make this nicer?
                source=state.precomputed_base.geturl(),
                shader=Constants.DEFAULT_SHADER,
            )

            s.layers["annotate_pre"] = neuroglancer.viewer_state.SegmentationLayer(
                source=f"{state.precomputed_base.geturl()}/skeleton",
                skeleton_rendering=neuroglancer.viewer_state.SkeletonRenderingOptions(
                    mode2d="lines", line_width2d=1
                ),
            )

            # s.layers["soma"] = neuroglancer.AnnotationLayer(
            #     source=f"precomputed://http://localhost:{NtracerState.file_server_port}/annotations/soma",
            #     shader="""
            #     void setEndpointMarkerBorderColor(vec4 rgba);
            #     void setLineWidth(float widthInScreenPixels);
            #     void setEndpointMarkerSize(float diameter);
            #     void main() {
            #     setColor(prop_color());
            #     setEndpointMarkerSize(0.5);
            #     setLineWidth(0.5);
            #     setPointMarkerBorderWidth(0.0);
            #     setEndpointMarkerBorderColor(vec4(0,0,0,0));
            #     }
            #     """,
            # )

            # s.layers["z-projection"] = neuroglancer.ImageLayer(
            #     source=f"precomputed://http://localhost:{NtracerState.neuroglancer_port}/projection/",
            #     shader=Constants.PROJECTION_SHADER
            # )

            s.layout = neuroglancer.viewer_state.row_layout(
                [
                    neuroglancer.viewer_state.LayerGroupViewer(
                        layers=["image", "annotate_pre"]  # , "soma"]
                    ),
                    # neuroglancer.LayerGroupViewer(
                    #     layers=["z-projection", "indicators", "Selection Boxes"]
                    # ),
                ]
            )

            z_slices = coords.layer_data[0].shape[0] // 10

            dashboard_state.min_projection_slice = min(1, z_slices)
            dashboard_state.max_projection_slice = z_slices // 4

    @staticmethod
    @inject_state
    def image_write(var: NtracerState):  # displays the annotation layer
        s: ViewerState
        with var.viewer.txn() as s:
            # s.display_dimensions = ['z', 'y', 'x']
            # s.dimensions = neuroglancer.CoordinateSpace(
            #     names=["x", "y", "z"], units=["nm", "nm", "µm"], scales=[350, 350, 1],
            # )
            lines = []

            if var.dashboard_state.highlight_all:
                s.layers["annotate_pre"].layer.segments = set(
                    list(var.coords.roots.keys())
                )
            elif var.dashboard_state.highlight_selected:
                s.layers["annotate_pre"].layer.segments = set(
                    [i[0] for i in var.dashboard_state.selected_indexes]
                )
            else:
                s.layers["annotate_pre"].layer.segments.clear()

            # if var.dashboard_state.highlight_all:
            #     t1 = time()
            #     k = 0
            #     for neuron_id, neuron in var.coords.roots.items():
            #         for pt in neuron.iter_all_points(neuron_id):
            #             if pt.children is None or not pt.children:
            #                 continue
            #             else:
            #                 for child in pt.children:
            #                     line = neuroglancer.LineAnnotation()
            #                     line.point_a = list([pt.x, pt.y, pt.z])
            #                     line.point_b = list([child.x, child.y, child.z])
            #                     line.id = "annotate" + str(k)
            #                     lines.append(line)
            #                     k += 1

            #         lines += IndicatorFunctions.get_soma_annotation(var.coords, neuron_id)
            #     t2 = time()
            #     print("highlight all ", t2 - t1)

            # if len(var.coords.roots) > 0:  # creates annoataion color
            # neuron_id = list(var.coords.roots.keys())[0]
            # branch = var.coords.roots[neuron_id].get_main_branch()
            # C = "red"
            # if branch is None:
            #     C = "red"
            # else:
            #     C = image[int(branch.x),:,int(branch.y), int(branch.z)]
            #     C=C/max(C)
            #     C = colors.to_hex([C[0],C[1],C[2]])
            # else:
            # C = "red"

            #     s.layers["annotate"] = neuroglancer.AnnotationLayer(
            #         annotations=lines,
            #         annotation_color=C,
            #         shader="""
            # void setEndpointMarkerBorderColor(vec4 rgba);
            # void setLineWidth(float widthInScreenPixels);
            # void setEndpointMarkerSize(float diameter);
            # void main() {
            # setColor(defaultColor());
            # setEndpointMarkerSize(3.0);
            # setLineWidth(3.0);
            # setEndpointMarkerBorderColor(vec4(0,0,0,0));
            # }
            # """,
            #     )
            #     if not "indicators" in s.layers:
            #         s.layers["indicators"] = neuroglancer.AnnotationLayer(
            #             annotations=lines,
            #             annotation_color=C,
            #             shader="""
            # void setEndpointMarkerBorderColor(vec4 rgba);
            # void setLineWidth(float widthInScreenPixels);
            # void setEndpointMarkerSize(float diameter);
            # void main() {
            # setColor(defaultColor());
            # setEndpointMarkerSize(3.0);
            # setLineWidth(3.0);
            # setEndpointMarkerBorderColor(vec4(0,0,0,0));
            # }
            # """,
            #         )

            if "Selection Boxes" not in s.layers:
                s.layers["Selection Boxes"] = neuroglancer.viewer_state.AnnotationLayer(
                    annotations=lines,
                    annotation_color="red",
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

            if var.dashboard_state.selected_point is not None:
                new_point = NeuronHelper.physical_to_pixels(
                    var.dashboard_state.selected_point, var.coords.scale
                )
                var.startingPoint = (new_point[0], new_point[1], new_point[2])

                lines = IndicatorFunctions.box_indicator(new_point, "first")

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
                # s.position[2] = new_point[2]  # Adjust z-coordinate so selection box is visible
            else:
                IndicatorFunctions.clear_red_box(s)
