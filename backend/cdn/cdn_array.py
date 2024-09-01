import collections
from io import UnsupportedOperation
import numpy
import urllib
import json
import requests
import time
import posixpath
from ntracer.utils.timing import print_time

LOGGER_TAG = "CDN"

@print_time(LOGGER_TAG)
def download_raw(session: requests.Session, res: int, params: list, url: str):
    (x1, x2), (y1, y2), (z1, z2) = params

    s_time = time.time()
    response = requests.get(f"{url}{res}/{x1}-{x2}_{y1}-{y2}_{z1}-{z2}")
    content = response.content
    dt = time.time() - s_time
    return params, content, dt

class CdnArray:
    class CdnResolutionItem:
        def __init__(self, parent, res_key, session, drop_channel_dim=False):
            self.parent = parent
            self.res_key = int(res_key)
            self.parent_i = self.parent.resolution_keys.index(self.res_key)
            self._resolution = self.parent.resolutions[self.parent_i]
            self._size = self.parent.sizes[self.parent_i]
            self._shape = tuple([*self._size, self.parent.channel_count])
            self.drop_channel_dim = drop_channel_dim
            self.session = session
            self.dtype=numpy.uint16

        def __getitem__(self, key) -> numpy.ndarray:
            key = list(key)
            if (len(self._size) != len(key)) and (len(self._shape) != len(key)):
                raise NotImplementedError(
                    "All axes must be specified other than channel"
                )

            for i in range(len(key)):
                if type(key[i]) == int:
                    key[i] = slice(key[i], key[i] + 1)
                start = 0 if (key[i].start is None) else key[i].start
                end = self._shape[i] if (key[i].stop is None) else key[i].stop
                key[i] = range(start, end)

            channel_selector = range(0, self._shape[-1])
            if len(key) == len(self._shape):  # channel specified
                channel_selector = key.pop(-1)

            params = [[k.start, k.stop] for k in key[:3]]
            ((x1, x2), (y1, y2), (z1, z2)) = params
            _, dl_result, t = download_raw(self.session, self.res_key, params, self.parent.url)

            # load buffer into numpy uint16 type
            dl_result = numpy.frombuffer(dl_result, dtype=numpy.uint16)

            # The subvolume data for the chunk is stored directly in little-endian binary format in [x, y, z, channel];
            # Fortran order (i.e. consecutive x values are contiguous)
            #                          Z              Y              X             CH
            # uint16_t out_buffer[channel_count][chunk_sizes[2]][chunk_sizes[1]][chunk_sizes[0]];

            # define buffer using server code definitions
            if (self.drop_channel_dim):
                shape = (
                    z2 - z1,
                    y2 - y1,
                    x2 - x1,
                )
            else:
                shape = (
                    channel_selector.stop - channel_selector.start,
                    z2 - z1,
                    y2 - y1,
                    x2 - x1,
                )

            dl_result = dl_result.reshape(shape)

            return dl_result.T

        def __repr__(self) -> str:
            return "<cdn_array.cdn_resolution_item parent={} resolution_key={} resolution={} size={} {}>".format(
                self.parent, self.res_key, self.resolution, self._size, hex(id(self))
            )

        def get_resolution(self) -> tuple:
            return tuple(self._resolution)

        def get_shape(self) -> tuple:
            if self.drop_channel_dim:
                return self._size
            return self._shape

        shape = property(get_shape)
        resolution = property(get_resolution)

    # def __init__(self, url="http://vm020.bil.psc.edu:8000/data/mouseID_405429-182725/"):
    def __init__(
        self,
        url,
        drop_channel_dim=False,
    ):

        self.url = url
        self.res_cache = dict()
        self.session = requests.Session()

        info_url = posixpath.join(self.url, "info")
        try:
            response = urllib.request.urlopen(info_url)
            self.metadata = json.loads(response.read())
        except Exception as e:
            raise ConnectionError(f"Failed to load metadata from URL: {info_url}")

        try:
            self.channel_count = int(self.metadata["num_channels"])
            self.dtype_raw = self.metadata["data_type"]
            self.scales = self.metadata["scales"]
            self.scales.sort(key=lambda x: int(x["key"]))
            self.resolution_keys = [int(i["key"]) for i in self.scales]
            self.resolutions = [tuple(map(int, i["resolution"])) for i in self.scales]
            self.sizes = [tuple(map(int, i["size"])) for i in self.scales]
        except:
            raise KeyError("Failed to parse metadata")

        if self.channel_count > 1 and drop_channel_dim:
            raise UnsupportedOperation("Cannot drop channel dimension when channel count is more than 1")
        self.drop_channel_dim = drop_channel_dim

        if self.metadata["type"].strip() != "image":
            raise ValueError("Not an image!")

    def __getitem__(self, key) -> CdnResolutionItem:
        if type(key) is not int:
            # default to highest resolution if none provided
            default_res_key = self.keys()[0]
            if default_res_key not in self.res_cache:
                self.res_cache[default_res_key] = self.CdnResolutionItem(
                    parent=self, res_key=default_res_key, session=self.session
                )
            return self.res_cache[default_res_key][key]
        if key not in self.keys():
            raise IndexError("Resolution key not available")

        if key not in self.res_cache:
            self.res_cache[key] = self.CdnResolutionItem(parent=self, res_key=key, session=self.session, drop_channel_dim=self.drop_channel_dim)
        return self.res_cache[key]

    def __repr__(self) -> str:
        return "<cdn_array url='{}' resolutions={} at {}>".format(
            self.url, self.keys(), hex(id(self))
        )

    def keys(self) -> list:
        return self.resolution_keys
