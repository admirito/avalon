#!/usr/bin/env python3

import ctypes
import datetime
import inspect
import ipaddress
import json
import os
import pathlib
import re
import time
import types
import urllib

try:
    import grpc_requests
except ModuleNotFoundError:
    pass

from . import auxiliary
from . import models


class Mappings:
    """
    An abstraction for keeping a list of available mappings.
    """
    def __init__(self):
        self._mappings = {}

    def register(self, mapping_name, mapping_class):
        """
        Register a new mapping class.
        """
        self._mappings[mapping_name] = mapping_class

    def mappings_list(self):
        """
        Returns the list of available mappings.
        """
        return list(self._mappings.keys())

    def mapping(self, mapping_name, **kwargs):
        if mapping_name in self._mappings:
            return self._mappings[mapping_name](**kwargs)

        # If the mapping_name is not already registered let's assume
        # it is a URL.
        with urllib.request.urlopen(mapping_name) as response:
            module_src = response.read()

        # Create a python module according to the URL fetched content.
        module_name = pathlib.Path(
            urllib.parse.urlparse(mapping_name).path).stem
        module = types.ModuleType(module_name)
        module.__file__ = mapping_name
        # By setting the __package__ on the module, the avalon
        # internals could be relatively imported in the module source
        # code (e.g. from . import mappings)
        module.__package__ = __package__
        exec(module_src, module.__dict__)

        # Find the first class in the module with a "map" method
        for cls_name, cls in inspect.getmembers(module, inspect.isclass):
            if callable(getattr(cls, "map", None)):
                # If cls is not a subclass of BaseMapping we will
                # create a new class and use multiple inheritance to
                # subclass both cls and BaseMapping.
                if not issubclass(cls, BaseMapping):
                    cls = type(f"{cls.__name__}BasedOnBaseMapping",
                               (cls, BaseMapping), {})

                return cls(**kwargs)

        raise ValueError(f"No class with a map method found in {mapping_name}")


class BaseMapping:
    """
    A generic parent for the Mappings. Each Mapping is responsible
    for map the output of a Model instance to a new one.
    """
    def __init__(self, **kwargs):
        pass

    def map_model(self, model_instance):
        """
        Given a model instance, returns a new instance (besed on a
        new model class) with a "next" method which will call map on
        the generated items.
        """
        def _next(self):
            return self._map(self._original_model.next())

        class_dict = {
            "_original_model": model_instance,
            "_map": self.map,
            "next": _next}

        # create a new model class
        mapped_model_class = type(
            f"Mapped{model_instance.__class__.__name__}",
            (models.BaseModel,), class_dict)

        return mapped_model_class()

    def map(self, item):
        """
        Returns the mapped item. This method should be overridden
        in the subclasses.
        """
        return item


class JsonColumnMapping(BaseMapping):
    """
    Transfrom the model data to three columns:
     - dt  : current date time as unix timestamp
     - _ix : counter
    - json : all the data as a json
    """
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
    def map(self, item):
        try:
            item["_ix"] = ctypes.c_int32(item["_ix"]).value
        except Exception:
            pass
        return item


class DtToIsoMapping(BaseMapping):
    """
    Convert columns from datetime to string iso format with time
    zone.
    """
    def map(self, item):
        for key, value in item.items():
            if isinstance(value, datetime.datetime):
                item[key] = value.astimezone().isoformat()

        return item


class DtToTimestampMapping(BaseMapping):
    """
    Convert columns from datetime to unix timestamp.
    """
    def map(self, item):
        for key, value in item.items():
            if isinstance(value, datetime.datetime):
                item[key] = value.timestamp()

        return item


class RFlowProtoMapping(BaseMapping):
    """
    Transfrom RFlow model data to be compatible with RFlow proto.
    """
    def map(self, item):
        item["id"] = item.pop("flow_id", 1)
        item.pop("user_id", None)

        item["l4_protocol"] = item.pop("protocol_l4", 0)
        item["l7_protocol"] = item.pop("protocol_l7", 0)

        item["packets_no_send"] = item.pop("packet_no_send", 0)
        item["packets_no_recv"] = item.pop("packet_no_recv", 0)

        item["flow_terminated"] = item.pop("is_terminated", 0)

        item["proto_data_send"] = {
            "tcp_flags": item.pop("proto_flags_send", 0)}
        item["proto_data_recv"] = {
            "tcp_flags": item.pop("proto_flags_recv", 0)}

        item["src_ip"] = int(ipaddress.IPv4Address(item.pop("srcip", 0)))
        item["src_port"] = item.pop("srcport", 0)
        item["dest_ip"] = int(ipaddress.IPv4Address(item.pop("destip", 0)))
        item["dest_port"] = item.pop("destport", 0)

        now = datetime.datetime.now().astimezone().isoformat()
        item["first_byte_ts"] = item.get(
            "first_byte_ts", now).astimezone().isoformat()
        item["last_byte_ts"] = item.get(
            "last_byte_ts", now).astimezone().isoformat()

        item["metadata"] = {key: {"values": {value: {"sequences": [1]}}}
                            for key, value in item.get("metadata", {}).items()}

        return item


class RFlowHelloGRPCSensorIDMapping(BaseMapping):
    """
    Add a sensor_id to the model data by calling "Hello" method of
    the GRPC endpoint provided by the avalon CLI.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.sensor_id = None

    def get_sensor_id(self):
        """
        This mehtod when called for the first time will call the
        "Hello" method of the GRPC endpoint and retrieve the
        "sensor_id" key from the returned value. On the consecutive
        calls the same sensor_id will be returned.
        """
        if self.sensor_id is not None:
            return self.sensor_id

        endpoint = self.avalon_args.grpc_endpoint
        service = self.avalon_args.grpc_method_name.rsplit(".", 1)[0]

        self.client = grpc_requests.Client.get_by_endpoint(endpoint)
        result = self.client.request(service, "Hello", {
            "version": 1,
            "info": {"name": "Avalon", "flow_type": 100, "id_session": 1}})

        self.sensor_id = result["sensor_id"]

        return self.sensor_id

    def map(self, item):
        item["sensor_id"] = self.get_sensor_id()
        return item


class LogProtoMapping(BaseMapping):
    """
    Transfrom log models data to be compatible with Log proto.
    """
    afterdash_regex = re.compile("-.*")

    def map(self, item):
        now = time.time()

        new_item = {
            "logid": auxiliary.new_oid(now),
            "timestamp": int(now * 1000000),
            "timestamp_rsyslog": int(item.get("ctime", 0) * 1000000),
            "hostname": "avalon",
            "fromhost_ip": "0.0.0.0",
            "programname": self.afterdash_regex.sub(
                "", item.get("aname", "avalon")).lower(),
            "log": item.get("msg", "avalon log"),
            "json": "{}",
            "pluginid": "",
        }

        return new_item


def get_mappings():
    """
    Returns a singleton instance of Mappings class in which all the
    available mappings are registered.
    """
    global _mappings

    try:
        return _mappings
    except NameError:
        _mappings = Mappings()

    _mappings.register("jsoncolumn", JsonColumnMapping)
    _mappings.register("int32ix", Int32IxMapping)
    _mappings.register("dttoiso", DtToIsoMapping)
    _mappings.register("dttots", DtToTimestampMapping)
    _mappings.register("rflowproto", RFlowProtoMapping)
    _mappings.register("rflowhello", RFlowHelloGRPCSensorIDMapping)
    _mappings.register("logproto", LogProtoMapping)

    return _mappings


def mappings_list():
    """
    Syntactic suger to get the list of foramts from the mappings
    singleton from get_mappings() method.
    """
    return get_mappings().mappings_list()


def mapping(mapping_name, **kwargs):
    """
    Syntactic suger to get a mapping from the mappings singleton
    from get_mappings() method.
    """
    return get_mappings().mapping(mapping_name, **kwargs)
