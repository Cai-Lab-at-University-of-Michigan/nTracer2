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
from ntracer.state_injector import inject_state, get_state, current_user_id
from ntracer.tracing.deletion_functions import DeletionFunctions
from ntracer.tracing.tracing_functions import TracingFunctions
from ntracer.tracing.update_functions import UpdateFunctions
from ntracer.versioning import Versioning
from ntracer.visualization.image import ImageFunctions
from ntracer.visualization.indicator import IndicatorFunctions
from ntracer.visualization.freehand import FreehandFunctions
import os

from authlib.integrations.starlette_client import OAuth
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import JSONResponse as StarletteJSONResponse
from jose import JWTError, jwt
from datetime import datetime, timedelta
import httpx
import secrets

from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from fastapi import FastAPI, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware

os.environ['HTTPS'] = 'on'

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add session middleware for OAuth state management
app.add_middleware(
    SessionMiddleware, 
    secret_key=os.getenv('SESSION_SECRET_KEY', secrets.token_urlsafe(32))
    )

oauth = OAuth()

# Configure Google OAuth
google = oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    access_token_url='https://oauth2.googleapis.com/token',
    userinfo_endpoint='https://openidconnect.googleapis.com/v1/userinfo',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

# Configure ORCID OAuth
orcid = oauth.register(
    name='orcid',
    client_id=os.getenv('ORCID_CLIENT_ID'),
    client_secret=os.getenv('ORCID_CLIENT_SECRET'),
    authorize_url='https://orcid.org/oauth/authorize',
    access_token_url='https://orcid.org/oauth/token',
    client_kwargs={
        'scope': '/authenticate'
    }
)
# JWT configuration
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', secrets.token_urlsafe(32))
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

app.mount("/dashboard", StaticFiles(directory="dashboard", html=True), name="static")

# User storage (in production, use a proper database)
authenticated_users = {}

def create_access_token(user_data: dict):
    """Create JWT access token for authenticated user"""
    to_encode = user_data.copy()
    expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt

def verify_token(token: str):
    """Verify JWT token and return user data"""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        return None

async def get_current_user_id(request) -> str:
    user_id = request.session.get('user_id')
    if user_id:
        return user_id
    
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        token = auth_header.split(' ')[1]
        user_data = verify_token(token)  # Use your existing function
        if user_data:
            return user_data.get('id')
    
    return "anonymous"

@app.middleware("http") 
async def set_user_context(request, call_next):
    user_id = await get_current_user_id(request)
    token = current_user_id.set(user_id)
    try:
        response = await call_next(request)
        return response
    finally:
        current_user_id.reset(token)

@app.get("/auth/google")
async def google_login(request: Request):
    try:
        state = secrets.token_urlsafe(32)
        request.session['oauth_state'] = state
        
        redirect_uri = str(request.url_for('google_callback')).replace('http://', 'https://')
        print(f"Google redirect URI: {redirect_uri}")
        
        return await google.authorize_redirect(request, redirect_uri, state=state)
    except Exception as e:
        print(f"Google auth error: {e}")
        return RedirectResponse("/?error=google_auth_failed")
    
@app.get("/auth/google/callback")
async def google_callback(request: Request):
    try:
        received_state = request.query_params.get('state')
        stored_state = request.session.get('oauth_state')
        if not received_state or received_state != stored_state:
            return RedirectResponse("/?error=csrf_protection")
            
        token = await google.authorize_access_token(request)
        print(f"Google token received: {token}")
        
        async with httpx.AsyncClient() as client:
            headers = {'Authorization': f'Bearer {token["access_token"]}'}
            response = await client.get(
                'https://openidconnect.googleapis.com/v1/userinfo',
                headers=headers
            )
            
            if response.status_code == 200:
                user_info = response.json()
                print(f"Google user info: {user_info}")
                
                user_data = {
                    'id': user_info.get('sub'),
                    'email': user_info.get('email'),
                    'name': user_info.get('name'),
                    'picture': user_info.get('picture'),
                    'provider': 'google'
                }
                
                authenticated_users[user_data['id']] = user_data
                access_token = create_access_token(user_data)

                request.session['access_token'] = access_token
                request.session['user_id'] = user_data['id']
                
                # FIX: Don't hardcode viewer URL, redirect to index to create user-specific viewer
                return RedirectResponse("/")  # Let index() create user-specific viewer
            else:
                print(f"Failed to get user info: {response.status_code}")
                return RedirectResponse("/?error=failed_to_get_user_info")
        
    except Exception as e:
        print(f"Google callback error: {e}")
        return RedirectResponse("/?error=authentication_failed")
    
@app.get("/auth/orcid")
async def orcid_login(request: Request):
    try:
        state = secrets.token_urlsafe(32)
        request.session['oauth_state'] = state
        
        redirect_uri = str(request.url_for('orcid_callback')).replace('http://', 'https://')
        print(f"ORCID redirect URI: {redirect_uri}")
        
        return await orcid.authorize_redirect(request, redirect_uri, state=state)
    except Exception as e:
        print(f"ORCID auth error: {e}")
        return RedirectResponse("/?error=orcid_auth_failed")

@app.get("/auth/orcid/callback")
async def orcid_callback(request: Request):
    try:
        received_state = request.query_params.get('state')
        stored_state = request.session.get('oauth_state')
        if not received_state or received_state != stored_state:
            return RedirectResponse("/?error=csrf_protection")
            
        token = await orcid.authorize_access_token(request)
        print(f"ORCID token received: {token}")
        
        orcid_id = token.get('orcid')
        access_token_value = token.get('access_token')
        
        if orcid_id and access_token_value:
            async with httpx.AsyncClient() as client:
                headers = {
                    'Authorization': f'Bearer {access_token_value}',
                    'Accept': 'application/json'
                }
                response = await client.get(
                    f'https://pub.orcid.org/v3.0/{orcid_id}/person',
                    headers=headers
                )
                
                if response.status_code == 200:
                    orcid_data = response.json()
                    name_data = orcid_data.get('name', {})
                    
                    user_data = {
                        'id': orcid_id,
                        'email': orcid_id + '@orcid.org',
                        'name': f"{name_data.get('given-names', {}).get('value', '')} {name_data.get('family-name', {}).get('value', '')}".strip() or orcid_id,
                        'orcid_id': orcid_id,
                        'provider': 'orcid'
                    }
                else:
                    user_data = {
                        'id': orcid_id,
                        'email': orcid_id + '@orcid.org',
                        'name': orcid_id,
                        'orcid_id': orcid_id,
                        'provider': 'orcid'
                    }
                
                authenticated_users[user_data['id']] = user_data
                access_token = create_access_token(user_data)
                
                request.session['access_token'] = access_token
                request.session['user_id'] = user_data['id']
                
                # FIX: Don't hardcode viewer URL, redirect to index to create user-specific viewer
                return RedirectResponse("/")  # Let index() create user-specific viewer
        
        return RedirectResponse("/?error=authentication_failed")
        
    except Exception as e:
        print(f"ORCID callback error: {e}")
        return RedirectResponse("/?error=authentication_failed")
    
@app.get("/auth/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/")

@app.get("/api/validate-token")
async def validate_token(request: Request):
    """Validate JWT token"""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return StarletteJSONResponse({'error': 'No token provided'}, status_code=401)
    
    token = auth_header.split(' ')[1]
    user_data = verify_token(token)
    
    if user_data:
        return StarletteJSONResponse({'valid': True, 'user': user_data})
    else:
        return StarletteJSONResponse({'error': 'Invalid token'}, status_code=401)

@app.get("/auth/status")
async def auth_status_simple(request: Request):
    access_token = request.session.get('access_token')
    user_id = request.session.get('user_id')
    
    if access_token and user_id and user_id in authenticated_users:
        return JSONResponse({
            'authenticated': True, 
            'user': authenticated_users[user_id]
        })
    return JSONResponse({'authenticated': False})

def clear_points():
    FreehandFunctions.clear_points()
    IndicatorFunctions.clear_points()
    ImageFunctions.image_write()
    NtracerFunctions.set_selected_points()

app.mount("/viewer", StaticFiles(directory="landing", html=True), name="viewer")
@app.get("/", response_model=None)
async def index(request: Request) -> RedirectResponse:
    state = get_state()
    coords = state.coords
    dashboard_state = state.dashboard_state

    if state.viewer is None:
        if not hasattr(neuroglancer.AnnotationLayer, "annotation_color"):
            from neuroglancer.viewer_state import optional, text_type, wrapped_property

            neuroglancer.AnnotationLayer.annotation_color = wrapped_property(
                "annotationColor", optional(text_type)
            )

        neuroglancer.set_server_bind_address(
            bind_address="0.0.0.0",
            bind_port=state.neuroglancer_port,
        )

        user_id = await get_current_user_id(request)
        user_token = f"ntracer_{user_id}_{secrets.token_urlsafe(8)}"
        viewer = neuroglancer.Viewer(token=user_token)
        state.viewer = viewer
        ImageFunctions.image_init()
        await NtracerFunctions.download_from_database(state.coords)
        if len(coords.shape) < 4:
            dashboard_state.channels = 1
        else:
            dashboard_state.channels = coords.shape[1]
        ImageFunctions.image_write()
        
        dashboard_state.selected_display_channels = list(range(dashboard_state.channels))
        dashboard_state.selected_analysis_channels = list(range(dashboard_state.channels))

        viewer.actions.add("undo", lambda s: Versioning.undo())
        viewer.actions.add("redo", lambda s: Versioning.redo())
        viewer.actions.add("freehand draw", lambda s: NtracerFunctions.hold_keyf(s))
        viewer.actions.add("add point", lambda s: NtracerFunctions.ctrl_left_click(s))
        viewer.actions.add("add point no shift", lambda s: NtracerFunctions.ctrl_left_click(s, no_mean_shift=True))
        viewer.actions.add("connect/commit points", lambda s: TracingFunctions.connect_or_commit_points())
        viewer.actions.add("connect/commit soma", lambda s: TracingFunctions.connect_or_commit_points(is_soma=True))
        viewer.actions.add("clear selections", lambda s: clear_points())
        viewer.actions.add("select branch", lambda s: NtracerFunctions.auto_select_branch(s))
        viewer.actions.add("select branch endpoint", lambda s: NtracerFunctions.auto_select_branch(s, get_endpoint=True))
        viewer.actions.add("complete soma", lambda s: complete_soma())

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
            s.input_event_bindings.data_view["shift+mousedown0"] = "select branch"
            s.input_event_bindings.data_view["keyo"] = "complete soma"

    viewer_url = quote_plus(
        urlparse(posixpath.join(os.environ["PUBLIC_URL"], f"ng/v/{state.viewer.token}/"))
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
            if await request.is_disconnected():
                break

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
                    "id": str(id)
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
        NtracerFunctions.change_coordinate_on_select(data["selected_point"], state.coords.scale)

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
        return JSONResponse(
            content={"success": False, "message": "No neuron selected"}
        )

    try:
        DeletionFunctions.delete_neuron(neuron_index)
        return JSONResponse(
            content={"success": True, "message": "Neuron deleted successfully"}
        )
    except Exception as e:
        return JSONResponse(
            content={"success": False, "message": f"Error: {str(e)}"}
        )

@app.get("/branch/delete")
def delete_branch():
    state = get_state()
    dashboard_state = state.dashboard_state
    branch_indexes = dashboard_state.selected_branch_indexes
    neuron_id = dashboard_state.selected_neuron_id

    if (
        not dashboard_state.is_neuron_selected
        or branch_indexes is None
        or len(branch_indexes) < 1
    ):
        return JSONResponse(
            content={"success": False, "message": "No branch selected"}
        )

    try:
        DeletionFunctions.delete_branch(neuron_id, branch_indexes)
        return JSONResponse(
            content={"success": True, "message": "Branch deleted successfully"}
        )
    except Exception as e:
        return JSONResponse(
            content={"success": False, "message": f"Error: {str(e)}"}
        )

@app.get("/point/delete")
def delete_point():
    state = get_state()
    dashboard_state = state.dashboard_state
    neuron_id = dashboard_state.selected_neuron_id
    branch_indexes = dashboard_state.selected_branch_indexes
    
    if dashboard_state.selected_point is None:
        return JSONResponse(
            content={"success": False, "message": "No point selected"}
        )

    try:
        DeletionFunctions.delete_point(
            neuron_id, branch_indexes, dashboard_state.selected_point
        )
        return JSONResponse(
            content={"success": True, "message": "Point deleted successfully"}
        )
    except Exception as e:
        return JSONResponse(
            content={"success": False, "message": f"Error: {str(e)}"}
        )

@app.get("/soma/delete")
def delete_soma():
    state = get_state()
    dashboard_state = state.dashboard_state
    neuron_id = dashboard_state.selected_neuron_id
    selected_soma_z_slice = dashboard_state.selected_soma_z_slice
    
    if selected_soma_z_slice == -1:
        return JSONResponse(
            content={"success": False, "message": "No soma selected"}
        )
    
    try:
        DeletionFunctions.delete_soma(neuron_id, selected_soma_z_slice)
        return JSONResponse(
            content={"success": True, "message": "Soma deleted successfully"}
        )
    except Exception as e:
        return JSONResponse(
            content={"success": False, "message": f"Error: {str(e)}"}
        )

@app.get("/neuron/combine")
def combine_neurons():
    state = get_state()
    dashboard_state = state.dashboard_state
    neuron_ids = set([s[0] for s in dashboard_state.selected_indexes])
    
    if len(neuron_ids) < 2:
        return JSONResponse(
            content={"success": False, "message": "Must select at least 2 neurons"}
        )
    
    try:
        UpdateFunctions.combine_neurons(list(neuron_ids))
        dashboard_state.selected_indexes = []
        dashboard_state.selected_point = None
        return JSONResponse(
            content={"success": True, "message": "Neurons combined successfully"}
        )
    except Exception as e:
        return JSONResponse(
            content={"success": False, "message": f"Error: {str(e)}"}
        )

@app.get("/branch/break")
def break_branch():
    state = get_state()
    dashboard_state = state.dashboard_state

    if not dashboard_state.is_branch_selected:
        return JSONResponse(
            content={"success": False, "message": "No branch selected"}
        )

    neuron_id = dashboard_state.selected_neuron_id
    selected_branch_indexes = dashboard_state.selected_branch_indexes
    selected_point = dashboard_state.selected_point

    if selected_point is None:
        return JSONResponse(
            content={"success": False, "message": "No point selected"}
        )

    try:
        UpdateFunctions.branch_break(
            neuron_id, selected_branch_indexes, selected_point
        )
        return JSONResponse(
            content={"success": True, "message": "Branch broken successfully"}
        )
    except Exception as e:
        return JSONResponse(
            content={"success": False, "message": f"Error: {str(e)}"}
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
        return JSONResponse(
            content={"success": False, "message": "No soma selected"}
        )

    try:
        selected_soma_z_slice = dashboard_state.selected_soma_z_slice
        TracingFunctions.complete_soma(neuron_id, selected_soma_z_slice)
        return JSONResponse(
            content={"success": True, "message": "Soma completed successfully"}
        )
    except Exception as e:
        return JSONResponse(
            content={"success": False, "message": f"Error: {str(e)}"}
        )

@app.get("/branch/set_primary")
def set_primary_branch():
    state = get_state()
    dashboard_state = state.dashboard_state
    neuron_id = dashboard_state.selected_neuron_id
    selected_branch_indexes = dashboard_state.selected_branch_indexes
    
    if (
        not dashboard_state.is_branch_selected
        or selected_branch_indexes is None
        or len(selected_branch_indexes) < 1
    ):
        return JSONResponse(
            content={"success": False, "message": "No branch selected"}
        )
    
    try:
        UpdateFunctions.set_primary_branch(neuron_id, selected_branch_indexes)
        return JSONResponse(
            content={"success": True, "message": "Primary branch set successfully"}
        )
    except Exception as e:
        return JSONResponse(
            content={"success": False, "message": f"Error: {str(e)}"}
        )

@app.get("/branch/join")
def join_branches():
    state = get_state()
    dashboard_state = state.dashboard_state
    
    if len(dashboard_state.selected_indexes) != 2:
        return JSONResponse(
            content={"success": False, "message": "Must select exactly 2 branches"}
        )

    try:
        indexes1 = dashboard_state.selected_indexes[0][1:]
        indexes2 = dashboard_state.selected_indexes[1][1:]
        neuron_id1 = dashboard_state.selected_indexes[0][0]
        neuron_id2 = dashboard_state.selected_indexes[1][0]
        
        UpdateFunctions.join_branches(neuron_id1, neuron_id2, indexes1, indexes2)
        return JSONResponse(
            content={"success": True, "message": "Branches joined successfully"}
        )
    except Exception as e:
        return JSONResponse(
            content={"success": False, "message": f"Error: {str(e)}"}
        )

@app.get("/swc/export")
async def export_swc(selected: bool):
    state = get_state()
    if selected:
        neuron_ids = [s[0] for s in state.dashboard_state.selected_indexes]
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
    try:
        TracingFunctions.connect_selected_points()
        return JSONResponse(
            content={"success": True, "message": "Neurite traced successfully"}
        )
    except Exception as e:
        return JSONResponse(
            content={"success": False, "message": f"Error: {str(e)}"}
        )

@app.get("/trace/soma")
def trace_soma():
    try:
        TracingFunctions.connect_selected_points(is_soma=True)
        return JSONResponse(
            content={"success": True, "message": "Soma traced successfully"}
        )
    except Exception as e:
        return JSONResponse(
            content={"success": False, "message": f"Error: {str(e)}"}
        )

@app.post("/swc/import")
async def import_swc(request: Request):
    try:
        data = await request.body()
        swc_helper.import_swc(data)
        return JSONResponse(
            content={"success": True, "message": "SWC imported successfully"}
        )
    except Exception as e:
        return JSONResponse(
            content={"success": False, "message": f"Error importing SWC: {str(e)}"}
        )

@app.get("/dashboard/")
def dashboard():
    return send_file("dashboard/build/index.html")

@app.get("/static/js/<path:filename>")
def static_js_files(filename):
    return send_from_directory("dashboard/build/static/js", filename)

@app.get("/static/css/<path:filename>")
def static_css_files(filename):
    return send_from_directory("dashboard/build/static/css", filename)