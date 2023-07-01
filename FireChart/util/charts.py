import base64
import re
import numpy as np
import requests
from typing import Dict

BYTE_ORDER = "little"


class Charts:
    def __init__(self):
        self.Request = requests.Session()
        self.BokehSession = None

    def get_bokeh_token(self):
        url: str = "https://app.materialindicators.com/FireCharts"
        headers: Dict[str , str] = {
            "Host": "app.materialindicators.com" ,
            "Connection": "keep-alive" ,
            "Pragma": "no-cache" ,
            "Cache-Control": "no-cache" ,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36" ,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7" ,
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7" ,
            "Cookie": 'user="\"Min_Soo_Lee\""'
        }

        response: requests.models.Response = self.Request.get(url=url , headers=headers , timeout=30 , allow_redirects=True)

        if response.ok:
            encoding = response.encoding
            text: str = response.content.decode(encoding).strip()
            result: re.Match = re.search(pattern=r'"token":"(.*)",' , string=text)
            self.BokehSession: str = result.groups()[0]

        else:
            print(f"{response.status_code}, {response.reason}")

        return True if self.BokehSession is not None else False

    @property
    def getBokehSession(self) -> str:
        return self.BokehSession


def buffer_to_base64(buffer):
    bytes_array = np.frombuffer(buffer , dtype=np.uint8)
    characters = [chr(byte) for byte in bytes_array]
    byte_string = ''.join(characters)
    return base64.b64encode(byte_string.encode()).decode()


def base64_to_buffer(base64_string):
    decoded_string = base64.b64decode(base64_string)
    bytes_array = np.frombuffer(decoded_string , dtype=np.uint8)
    return bytes_array.tobytes()


def swap16(array):
    array.byteswap(True)


def swap32(array):
    array.byteswap(True)


def swap64(array):
    array.byteswap(True)


def is_NDArray_ref(obj):
    return isinstance(obj , dict) and ("__buffer__" in obj or "__ndarray__" in obj)


def decode_NDArray(obj , buffers=None):
    shape = obj["shape"]
    dtype = obj["dtype"]
    order = obj["order"]
    # print(f"{shape}, {dtype}, {order}")
    if "__buffer__" in obj:
        buffer_id = obj["__buffer__"]
        buffer_data = buffers.get(buffer_id)
        if buffer_data is None:
            raise ValueError(f"Buffer {buffer_id} not found")
        ndarray_data = base64_to_buffer(buffer_data)
    else:
        ndarray_data = base64_to_buffer(obj["__ndarray__"])

    if dtype == "uint8":
        ndarray = np.frombuffer(ndarray_data , dtype=np.uint8).reshape(shape)
    elif dtype == "int8":
        ndarray = np.frombuffer(ndarray_data , dtype=np.int8).reshape(shape)
    elif dtype == "uint16":
        ndarray = np.frombuffer(ndarray_data , dtype=np.uint16).reshape(shape)
    elif dtype == "int16":
        ndarray = np.frombuffer(ndarray_data , dtype=np.int16).reshape(shape)
    elif dtype == "uint32":
        ndarray = np.frombuffer(ndarray_data , dtype=np.uint32).reshape(shape)
    elif dtype == "int32":
        ndarray = np.frombuffer(ndarray_data , dtype=np.int32).reshape(shape)
    elif dtype == "float32":
        ndarray = np.frombuffer(ndarray_data , dtype=np.float32).reshape(shape)
    elif dtype == "float64":
        ndarray: np.ndarray = np.frombuffer(ndarray_data , dtype=np.float64).reshape(shape)

    if order != BYTE_ORDER:
        if ndarray.dtype.itemsize == 2:
            swap16(ndarray)
        elif ndarray.dtype.itemsize == 4:
            swap32(ndarray)
        elif ndarray.dtype.itemsize == 8:
            swap64(ndarray)

    return ndarray


def encode_NDArray(array , buffers=None):
    dtype = array.dtype.name
    shape = array.shape

    if buffers is not None:
        buffer_id = str(buffers.size)
        buffers[buffer_id] = buffer_to_base64(array.tobytes())
        return {
            "__buffer__": buffer_id ,
            "order": BYTE_ORDER ,
            "dtype": dtype ,
            "shape": shape
        }
    else:
        ndarray_data = buffer_to_base64(array.tobytes())
        return {
            "__ndarray__": ndarray_data ,
            "order": BYTE_ORDER ,
            "dtype": dtype ,
            "shape": shape
        }
