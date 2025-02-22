import dotenv
from sse_starlette import EventSourceResponse

from ntracer.helpers.dashboard_state_helper import DashboardState
from ntracer.helpers.ngauge_helper import NeuronHelper
dotenv.load_dotenv()

import json
import logging
import os
import webbrowser
import asyncio
from urllib.parse import quote_plus, urlparse
import posixpath

import neuroglancer.webdriver
from neuroglancer.viewer_config_state import ConfigState
from flask import Flask, redirect, request, send_file, send_from_directory
from flask_socketio import SocketIO
from ngauge import Neuron
from ntracer.helpers import swc_helper

from ntracer.ntracer_functions import NtracerFunctions
from ntracer.ntracer_state import NtracerState
from ntracer.state_injector import inject_state, get_state
from ntracer.tracing.deletion_functions import DeletionFunctions
from ntracer.tracing.tracing_functions import TracingFunctions
from ntracer.tracing.update_functions import UpdateFunctions
from ntracer.versioning import Versioning
from ntracer.visualization.image import ImageFunctions
from ntracer.visualization.indicator import IndicatorFunctions
from ntracer.visualization.freehand import FreehandFunctions
import os
from fastapi.staticfiles import StaticFiles


from fastapi import FastAPI, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/dashboard", StaticFiles(directory="dashboard", html=True), name="static")
user_id = 0
TOKEN = "ntracer2"

def clear_points():
    FreehandFunctions.clear_points()
    IndicatorFunctions.clear_points()
    ImageFunctions.image_write()
    NtracerFunctions.set_selected_points()


app.mount("/viewer", StaticFiles(directory="landing", html=True), name="viewer")
@app.get("/", response_model=None)
async def index() -> RedirectResponse:
    global user_id
    state = get_state()
    coords = state.coords
    dashboard_state = state.dashboard_state

    if state.viewer is None:
        if not hasattr(neuroglancer.AnnotationLayer, "annotation_color"):  # type: ignore
            from neuroglancer.viewer_state import optional, text_type, wrapped_property

            neuroglancer.AnnotationLayer.annotation_color = wrapped_property(  # type: ignore
                "annotationColor", optional(text_type)
            )

        neuroglancer.set_server_bind_address(
            bind_address="0.0.0.0",  # Allow access from outside Docker container
            bind_port=state.neuroglancer_port,
        )

        # runs image layer functions
        viewer = neuroglancer.Viewer(token=TOKEN)
        user_id+=1
        state.viewer = viewer
        ImageFunctions.image_init()
        await NtracerFunctions.download_from_database(state.coords)
        ImageFunctions.image_write()
        dashboard_state.channels = coords.shape[1]
        dashboard_state.selected_display_channels = list(
            range(dashboard_state.channels)
        )
        dashboard_state.selected_analysis_channels = list(
            range(dashboard_state.channels)
        )

        # Add these to html, hover for tip on how to use
        # defines all of the hot key commands
        viewer.actions.add("undo", lambda s: Versioning.undo())
        viewer.actions.add("redo", lambda s: Versioning.redo())
        viewer.actions.add("freehand draw", lambda s: NtracerFunctions.ctrl_keyf_left_click(s))
        viewer.actions.add("add point", lambda s: NtracerFunctions.ctrl_left_click(s))
        viewer.actions.add("add point no shift", lambda s: NtracerFunctions.ctrl_left_click(s, no_mean_shift=True))
        viewer.actions.add(
            "connect/commit points", lambda s: TracingFunctions.connect_or_commit_points()
        )
        viewer.actions.add(
            "connect/commit soma", lambda s: TracingFunctions.connect_or_commit_points(is_soma=True)
        )
        viewer.actions.add(
            "clear selections", lambda s: clear_points()
        )
        viewer.actions.add(
            "select branch", lambda s: NtracerFunctions.auto_select_branch(s)
        )
        viewer.actions.add(
            "select branch endpoint", lambda s: NtracerFunctions.auto_select_branch(s, get_endpoint=True)
        )
        viewer.actions.add(
            "complete soma", lambda s: complete_soma()
        )

        s: ConfigState
        with viewer.config_state.txn() as s:
            s.input_event_bindings.viewer["control+keyz"] = "undo"
            s.input_event_bindings.viewer["control+keyy"] = "redo"
            s.input_event_bindings.viewer["keyf"] = "freehand draw"
            s.input_event_bindings.data_view["control+mousedown0"] = "add point"
            s.input_event_bindings.data_view["alt+mousedown0"] = "add point no shift"
            s.input_event_bindings.data_view["keya"] = "connect/commit points"
            s.input_event_bindings.data_view["keys"] = "connect/commit soma"
            s.input_event_bindings.data_view["mousedown2"] = "clear selections"
            s.input_event_bindings.data_view["control+mousedown2"] = "clear selections"
            s.input_event_bindings.data_view["alt+mousedown2"] = "clear selections"
            s.input_event_bindings.data_view["alt+dblclick0"] = "select branch endpoint"
            s.input_event_bindings.data_view["keyo"] = "complete soma"

    viewer_url = quote_plus(
        urlparse(posixpath.join(os.environ["PUBLIC_URL"], f"v/{TOKEN}/"))
        ._replace(netloc=f"{urlparse(os.environ['PUBLIC_URL']).hostname}:{state.neuroglancer_port}")
        .geturl()
    )
    dashboard_url = quote_plus("/dashboard")
    return RedirectResponse(
        f"/viewer?viewer={viewer_url}&dashboard={dashboard_url}"
    )

def get_dashboard_state():
    return get_state().dashboard_state.get_state_dict()

def get_tracing_state():
    simple_object = {"children": []}
    state = get_state()
    for neuron_number, neuron in state.coords.roots.items():
        simple_object["children"].append(
            NeuronHelper.get_simple_neuron_object(neuron, neuron_number)
        )

    return simple_object

def get_points_state():
    res = get_state().selected_tracing_points
    if res is None:
        return []
    return res

def get_soma_state():
    return NtracerFunctions.get_soma_list()


@app.get("/stream/dashboard")
async def dashboard_stream(request: Request):
    async def event_generator():
        prev_state: str | None = None

        id = 0
        while True:
            # If client closes connection, stop sending events
            if await request.is_disconnected():
                break

            # Checks for new messages and return them to client if any
            dashboard_state = get_dashboard_state()
            tracing_state = get_tracing_state()
            points_state = get_points_state()
            soma_state = get_soma_state()

            res = json.dumps({
                "dashboard_state": dashboard_state,
                "tracing_state": tracing_state,
                "points_state": points_state,
                "soma_state": soma_state
            })

            if prev_state is None or res != prev_state:
                prev_state = res
                yield  {
                    "event": "state",
                    "retry": 15000,
                    "data": res,
                    "id": id
                }

            id += 1
            await asyncio.sleep(0.5)

    return EventSourceResponse(event_generator(), send_timeout=5)

@app.post("/dashboard_state/update")
async def dashboard_state_update(request: Request):
    data = await request.json()
    state = get_state()
    dashboard_state = state.dashboard_state
    (
        channels_have_changed,
        projection_range_has_changed,
        expanded_neuron_has_changed,
    ) = (False, False, False)
    if (
        data["selected_display_channels"]
        != dashboard_state.selected_display_channels
    ):
        channels_have_changed = True
    if data["projection_range"] != dashboard_state.projection_range:
        projection_range_has_changed = True
    if data["expanded_neuron"] != dashboard_state.expanded_neuron:
        expanded_neuron_has_changed = True
    if (
        "selected_point" in data
        and data["selected_point"] != (-1, -1, -1)
        and (
            not dashboard_state.is_point_selected
            or data["selected_point"] != dashboard_state.selected_point
        )
    ):
        NtracerFunctions.change_coordinate_on_select(
            data["selected_point"], state.coords.scale
        )

    for key in data:
        if hasattr(dashboard_state, key):
            setattr(dashboard_state, key, data[key])

    ImageFunctions.image_write()
    NtracerFunctions.set_selected_points()
    if channels_have_changed:
        NtracerFunctions.set_display_channels()

    if projection_range_has_changed:
        NtracerFunctions.set_projection_range()

    if expanded_neuron_has_changed and dashboard_state.expanded_neuron != -1:
        neuron = await state.coords.cdn_helper.get_swc(dashboard_state.expanded_neuron, True)
        if not isinstance(neuron, Neuron):
            raise TypeError("Cannot retrieve swc as Neuron object")

        state.coords.roots[dashboard_state.expanded_neuron] = neuron
        state.coords.downloaded_neurons.append(dashboard_state.expanded_neuron)
        # NtracerFunctions.set_selected_points()


@app.get("/neuron/delete")
def delete_neuron():
    state = get_state()
    dashboard_state = state.dashboard_state
    neuron_index = dashboard_state.selected_neuron_id

    if len(dashboard_state.selected_indexes) == 0:
        print("No neuron selected")
        return

    DeletionFunctions.delete_neuron(neuron_index)


@app.get("/branch/delete")
def delete_branch():
    state = get_state()
    dashboard_state = state.dashboard_state
    branch_indexes = dashboard_state.selected_branch_indexes
    neuron_id = dashboard_state.selected_neuron_id

    # Only neuron specified, return
    if (
        not dashboard_state.is_neuron_selected
        or branch_indexes is None
        or len(branch_indexes) < 1
    ):
        print("No branch selected")
        return

    DeletionFunctions.delete_branch(neuron_id, branch_indexes)


@app.get("/point/delete")
def delete_point():
    state = get_state()
    dashboard_state = state.dashboard_state
    neuron_id = dashboard_state.selected_neuron_id
    branch_indexes = dashboard_state.selected_branch_indexes
    if dashboard_state.selected_point is None:
        raise Warning("No point selected")

    DeletionFunctions.delete_point(
        neuron_id, branch_indexes, dashboard_state.selected_point
    )

@app.get("/soma/delete")
def delete_soma():
    state = get_state()
    dashboard_state = state.dashboard_state
    neuron_id = dashboard_state.selected_neuron_id
    selected_soma_z_slice = dashboard_state.selected_soma_z_slice
    DeletionFunctions.delete_soma(neuron_id, selected_soma_z_slice)

@app.get("/neuron/combine")
def combine_neurons():
    state = get_state()
    dashboard_state = state.dashboard_state
    neuron_ids = [s[0] for s in dashboard_state.selected_indexes]
    if len(neuron_ids) != len(set(neuron_ids)):
        return
    UpdateFunctions.combine_neurons(neuron_ids)
    dashboard_state.selected_indexes = []
    dashboard_state.selected_point = None

@app.get("/branch/break")
def break_branch():
    state = get_state()
    dashboard_state = state.dashboard_state

    if not dashboard_state.is_branch_selected:
        return

    neuron_id = dashboard_state.selected_neuron_id
    selected_branch_indexes = dashboard_state.selected_branch_indexes
    selected_point = dashboard_state.selected_point

    if selected_point is None:
        raise Warning("No point selected")

    UpdateFunctions.branch_break(
        neuron_id, selected_branch_indexes, selected_point
    )


@app.get("/soma/complete")
def complete_soma():
    state = get_state()
    dashboard_state = state.dashboard_state
    neuron_id = dashboard_state.selected_neuron_id

    if (
        dashboard_state.selected_soma_z_slice == -1
        or len(dashboard_state.selected_indexes) == 0
    ):
        print("No soma selected")
        return

    selected_soma_z_slice = dashboard_state.selected_soma_z_slice
    TracingFunctions.complete_soma(neuron_id, selected_soma_z_slice)


@app.get("/branch/set_primary")
def set_primary_branch():
    state = get_state()
    dashboard_state = state.dashboard_state
    neuron_id = dashboard_state.selected_neuron_id
    selected_branch_indexes = dashboard_state.selected_branch_indexes
    UpdateFunctions.set_primary_branch(neuron_id, selected_branch_indexes)

@app.get("/branch/join")
def join_branches():
    state = get_state()
    dashboard_state = state.dashboard_state
    if len(dashboard_state.selected_indexes) != 2:  # Must have 2 branch selected
        return

    indexes1 = dashboard_state.selected_indexes[0][1:]
    indexes2 = dashboard_state.selected_indexes[1][1:]
    neuron_id1 = dashboard_state.selected_indexes[0][0]
    neuron_id2 = dashboard_state.selected_indexes[1][0]
    UpdateFunctions.join_branches(neuron_id1, neuron_id2, indexes1, indexes2)


@app.get("/swc/export")
async def export_swc(selected: bool):
    state = get_state()
    if selected:
        neuron_ids = [s[0] for s in state.dashboard_state.selected_indexes]
        print("exporting selected", neuron_ids)
    else:
        neuron_ids = list(state.coords.roots.keys())

    awaits = []

    for neuron_id in neuron_ids:
        if neuron_id not in state.coords.downloaded_neurons:
            awaits.append((state.coords.cdn_helper.get_swc(neuron_id, True), neuron_id))

    for (awaitable, neuron_id) in awaits:
        new_neuron = await awaitable
        if type(new_neuron) is Neuron:
            state.coords.roots[neuron_id] = new_neuron
            state.coords.downloaded_neurons.append(neuron_id)
    
    out_bin = swc_helper.export_swc(neuron_ids)
    filename = f"{state.dataset_id}_swc.zip"
    return Response(content=out_bin.getvalue(), media_type=
                    'application/zip', headers={'Content-Disposition': f'attachment; filename="{filename}"'})


@app.get("/trace/neurite")
def trace_neurite():
    TracingFunctions.connect_selected_points()


@app.get("/trace/soma")
def trace_soma():
    TracingFunctions.connect_selected_points(is_soma=True)


@app.post("/swc/import")
async def import_swc(request: Request):
    data = await request.body()
    swc_helper.import_swc(data)

@app.get("/dashboard/")
def dashboard():
    return send_file("dashboard/build/index.html")

@app.get("/static/js/<path:filename>")
def static_js_files(filename):
    return send_from_directory("dashboard/build/static/js", filename)

@app.get("/static/css/<path:filename>")
def static_css_files(filename):
    return send_from_directory("dashboard/build/static/css", filename)
