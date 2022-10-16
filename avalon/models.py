#!/usr/bin/env python3

import time
import datetime
import random
import socket
import struct
import re


class Models:
    """
    An abstraction for keeping a list of available models.
    """
    def __init__(self):
        # key: model name
        # value: model class
        self._models = {}

        self._total = None

    def register(self, model_name, model_class):
        """
        Register a new model class.
        """
        self._models[model_name] = model_class

    def models_list(self):
        """
        Returns the list of available models.
        """
        return list(self._models.keys())

    def model(self, model_name, **options):
        """
        Returns an instance of a model that can generate model
        data by calling its next() method.
        """
        return self._models[model_name](**options)


class BaseModel:
    """
    A generic parent for the Models. Each Model is responsible for
    generating data that could be serialized by a Format.
    """
    def __init__(self, **options):
        pass
    
    def next(self):
        """
        Return the next generated item of the data model.
        """
        raise NotImplementedError


class TestModel(BaseModel):
    """
    A sample model, just for testing.
    """
    _id_counter = 0

    def __init__(self, **options):
        super().__init__(**options)

        self.__class__._id_counter += 1
        self._id = self._id_counter

    def next(self):
        """
        Reutrns data for test
        """
        _ts, _ms = divmod(time.time(), 1)
        return {"_id": f"test{self._id}",
                "_ts": int(_ts),
                "_ms": int(_ms * 1000000)}


class RFlowModel(BaseModel):
    """
    Rflow generator
    """
    _id_counter = 0
    metadata_list = None

    def __init__(self, **options):
        super().__init__(**options)

        self.__class__._id_counter += 1
        self._id = self._id_counter

        self.curr_flow_id = 0

        if self.__class__.metadata_list is None:
            self.__class__.metadata_list = list()
            with open(options["metadata_file_name"], 'r') as f:
                tmp_str = f.read()
                re_groups = re.findall(r'"(\S+)"', tmp_str)
                for g in re_groups:
                    self.__class__.metadata_list.append(g)

    def next(self):
        # Identifications
        flow_id = self.curr_flow_id
        self.curr_flow_id += 1
        session_id = self._id
        sensor_id = 0

        # Flow Key
        src_ip = socket.inet_ntoa(
            struct.pack('>I', random.randint(1, 0xffffffff)))
        src_port = random.randint(0, 0xffff)
        dst_ip = socket.inet_ntoa(
            struct.pack('>I', random.randint(1, 0xffffffff)))
        dst_port = random.randint(0, 0xffff)

        # Protocols
        l4_protocol = random.randint(0, 142)
        l7_protocol = random.randint(0, 2988)

        # interfaces
        input_if_id = random.randint(-1, 0xffffffff)   # 4 byte
        output_if_id = random.randint(-1, 0xffffffff)  # 4 byte

        # timestamps
        first_byte_ts = datetime.datetime.now()
        last_byte_ts = first_byte_ts \
            + datetime.timedelta(
                0, random.randint(0, 0xfff), random.randint(0, 0xfff))

        # packet stats
        packet_no_send = random.randint(0, 0xffffffffffff)  # 6 byte
        packet_no_recv = random.randint(0, 0xffffffffffff)  # 6 byte

        # total transmitted volume
        # packet count * random avg packet size
        volume_send = packet_no_send * random.randint(1400, 1550)
        volume_recv = packet_no_recv * random.randint(1400, 1550)

        #protocol specific data
        protocol_data_send = random.randint(0, 1)
        protocol_data_recv = random.randint(0, 1)

        # flow termination
        flow_terminated = True

        # flow metadata
        metadata_count = random.randint(0, len(self.__class__.metadata_list))
        sample_metadata = random.sample(
            list(range(len(self.__class__.metadata_list))), metadata_count)
        flow_metadata = {}
        for i in sample_metadata:
            flow_metadata[self.__class__.metadata_list[i]] = "some dummy bytes"
        
        rflow_dict = {
            "flow_id":flow_id, "session_id":session_id,
            "src_ip":src_ip, "src_port":src_port,
            "dst_ip":dst_ip, "dst_port":dst_port, 
            "l4_protocol":l4_protocol, "l7_protocol":l7_protocol,
            "input_if_id":input_if_id, "output_if_id":output_if_id,
            "first_byte_ts":str(first_byte_ts),
            "last_byte_ts":str(last_byte_ts),
            "packet_no_send":packet_no_send, "packet_no_recv":packet_no_recv,
            "volume_send":volume_send, "volume_recv":volume_recv,
            "flow_terminated":flow_terminated,
            "protocol_data_send":protocol_data_send,
            "protocol_data_recv":protocol_data_recv,
            }
        rflow_dict.update(flow_metadata)
        return rflow_dict


class LogModel(BaseModel):
    """
    Log generator
    """
    _id_counter = 0
    
    def __init__(self):
        super().__init__()

        self.__class__._id_counter += 1
        self._id = self._id_counter

    def next(self):
        pass


def get_models():
    """
    Returns a singleton instance of Models class in which all the
    available models are registered.
    """
    global _models

    try:
        return _models
    except NameError:
        _models = Models()

    _models.register("test", TestModel)
    _models.register("RFlow", RFlowModel)

    return _models


def models_list():
    """
    Syntactic suger to get the list of models from the models
    singleton from get_models() method.
    """
    return get_models().models_list()


def model(model_name, **options):
    """
    Syntactic suger to get a new model instance of the model name
    from the models singleton from get_models() method.
    """
    return get_models().model(model_name, **options)
