## May need to be run: export LIBMYSQL_ENABLE_CLEARTEXT_PLUGIN=1

import ngauge
import numpy as np
from time import time
import httpx
from typing import Union
from ngauge import Neuron
import requests
from ntracer.utils.timing import print_time

key_location = "./"
LOGGER_TAG = "CDN"

class CdnHelper:
    def __init__(self, base_url) -> None:
         self.session = requests.Session()
         self.async_session = httpx.AsyncClient()
         self.base_url = base_url
         self.initiate_database()

    @print_time(LOGGER_TAG)
    def initiate_database(self):
        res = self.session.get(f"{self.base_url}")
        if res.status_code != 200:
            raise Exception(f"initiate_database failed: http status code: {res.status_code}")

    @print_time(LOGGER_TAG)
    def get_all_neurons(self, imageid: str | None = None):
        res = self.session.get(f"{self.base_url}/ls")
        if res.status_code != 200:
            raise Exception(f"get_all_neurons failed: http status code: {res.status_code}")

        return [(int(neuronid), []) for neuronid in res.json()["neuronids"]]


    @print_time(LOGGER_TAG)
    async def get_swc(self, neuronid: int, as_neuron=False) -> Union[str, Neuron]:
        res = await self.async_session.get(f"{self.base_url}/get/{neuronid}")
        if res.status_code != 200:
            raise Exception(
                f"get_swc for `{neuronid}` failed: http status code: {res.status_code}"
            )

        swc = res.text
        if as_neuron:
            swc = swc.split("\n")
            neuron = ngauge.Neuron.from_swc_text(swc)
            return neuron
        return swc

    @print_time(LOGGER_TAG)
    def delete_neuron(self, neuronid: int):
        res = self.session.get(f"{self.base_url}/delete/{neuronid}")
        if res.status_code != 200:
            raise Exception(
                f"delete neuron '{neuronid}' failed: http status code: {res.status_code}"
            )

    @print_time(LOGGER_TAG)
    def add_neuron(self, toinsert: str, neuronid: Union[int, None] = None) -> int:
        # np.savetxt("new_neuron.swc", toinsert, delimiter=",", fmt="%d")
        res = self.session.post(
            f"{self.base_url}/upload",
            files={"data": ("new_neuron.swc", bytes(toinsert, encoding="utf8"))},
        )
        if res.status_code != 200:
            print(res.text)
            raise Exception(
                f"add neuron '{neuronid}' failed: http status code: {res.status_code}"
            )

        neuronid = (res.json())["neuronid"]
        return neuronid # type: ignore

    @print_time(LOGGER_TAG)
    def replace_neuron(self, neuronid: int, neuron: Neuron):
        toadd = neuron.to_swc()
        res = self.session.post(
            f"{self.base_url}/replace/{neuronid}", files={"data": ("new_neuron.swc", toadd)} # type: ignore
        )
        if res.status_code != 200:
            raise Exception(
                f"replace neuron '${neuronid}' failed: http status code: {res.status_code}"
            )

    @print_time(LOGGER_TAG)
    def update_neuron(self, neuronid: int, neuron: Neuron):
        self.replace_neuron(neuronid, neuron)


    def get_point_from_coordinates(self, x, y, z):
        # cmd = exe("SELECT neuronid FROM swc WHERE x=%s AND y=%s AND z=%s", [x, y, z],)
        # res = cmd.fetchone()
        # if len(res) > 0:
        #     return res[0]
        return None
