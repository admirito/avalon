import ctypes
import datetime
import json
import os

from . import BaseMapping


class JsonColumnMapping(BaseMapping):
    """
    Transfrom the model data to three columns:
     - dt  : current date time as unix timestamp
     - _ix : counter
    - json : all the data as a json
    """

    __title__ = "jsoncolumn"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self._prefix = None
        self._counter = 0

    def map(self, item):
        if self._prefix is None:
            self._prefix = (os.getpid() % 0xFFFF << 16)

        new_item = {
            "dt": datetime.datetime.now(),
            "_ix": self._prefix + self._counter,
            "json": json.dumps(item),
        }

        self._counter = (self._counter + 1) % 0xFFFF

        return new_item


class Int32IxMapping(BaseMapping):
    """
    Transform the _ix column to a signed int32 (appropriate for
    postgresql)
    """

    __title__ = "int32ix"

    def map(self, item):
        try:
            item["_ix"] = ctypes.c_int32(item["_ix"]).value
        except Exception:
            pass
        return item
