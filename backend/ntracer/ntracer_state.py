import os
import posixpath
from dataclasses import dataclass
from urllib.parse import urlparse

import requests
from neuroglancer import Viewer
from neuroglancer.viewer_config_state import ActionState

from cdn.cdn_array import CdnArray
from cdn.cdn_helper import CdnHelper
from ntracer.helpers.dashboard_state_helper import DashboardState
from ntracer.helpers.freehand_state_helper import FreehandState
from ntracer.helpers.tracing_data_helper import Coords
from ntracer.utils.timing import print_time


@dataclass(init=True)
class NtracerState:
    coords: Coords
    viewer: Viewer | None = None

    dataset_id: str = os.environ["DATASET_ID"]

    cdn_url = urlparse(os.environ["CDN_URL"])
    cdn_url_dataset = urlparse(posixpath.join(cdn_url.geturl(), dataset_id))
    """Base URL for CDN server used by SERVER"""

    cdn_url_host = urlparse(os.environ["CDN_URL_HOST"])
    cdn_url_host_dataset = urlparse(posixpath.join(cdn_url_host.geturl(), dataset_id))
    """URL used to show CDN images to HOST"""

    cdn_url_local = urlparse(os.environ["CDN_URL_LOCAL"])
    cdn_url_local_dataset = urlparse(posixpath.join(cdn_url_local.geturl(), dataset_id))
    """URL used for tracing skeletons, default CDN_URL"""

    cdn_url_local_host = urlparse(os.environ["CDN_URL_LOCAL_HOST"])
    cdn_url_local_host_dataset = urlparse(posixpath.join(cdn_url_local_host.geturl(), dataset_id))
    """URL used for tracing skeleton host access, default CDN_URL"""
    
    database_url: str = posixpath.join(
        #cdn_url.geturl(), f"{dataset_id}/skeleton_api"
        cdn_url_local.geturl(), f"{dataset_id}/skeleton_api"
    )
    """URL for database (skeleton API)"""

    neuroglancer_port: int = int(os.environ.get("NEUROGLANCER_PORT", 8050))
    """Port for neuroglancer server"""

    neuroglancer_bind: str = os.environ.get("NEUROGLANCER_BIND", "localhost")

    file_server_port: int = 8082

    is_multi: bool = False  # set on image load
    """True if image has more than 3 channels"""

    dashboard_state: DashboardState = DashboardState()
    selected_tracing_points: list | None = None
    freehand_state: FreehandState = FreehandState()
    startingPoint: tuple[int, int, int] | None = None
    endingPoint: tuple[int, int, int] | None = None
    currentAction: str | None = None

    @print_time("NTRACER_STATE")
    def __init__(self):
        # Check if image is multi-channel
        self.is_multi = self.__is_multi()

        # Load Image
        cdn_helper = CdnHelper(self.database_url)
        cdn_array = CdnArray(
            drop_channel_dim=False if self.is_multi else True,
            url=self.cdn_url_dataset.geturl(),
        )
        scale = cdn_array.scales[0]["resolution"]
        layer_data = [cdn_array[i] for i in cdn_array.keys()]
        self.coords = Coords(
            cdn_array=cdn_array,
            cdn_helper=cdn_helper,
            scale=scale,
            layer_data=layer_data,
        )

        self.dashboard_state.scale = scale
        self.image: CdnArray.CdnResolutionItem = self.coords.layer_data[
            0
        ]  # highest resolution

    def __is_multi(self) -> bool:
        url = posixpath.join(
            self.cdn_url_dataset.geturl(),
            "info",
        )
        try:
            # 211124 Changing to call any multichannel image "multi"
            return requests.get(url).json()["num_channels"] > 1
        except Exception as e:
            print(
                "Error, checking if image is multi-channel, verify Neuroglancer info file for image exists at:",
                url,
            )
            raise e
