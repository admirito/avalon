#!/usr/bin/env python3

from copy import deepcopy
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
    max_allowed_pendding = 100

    def __init__(self, **options):
        super().__init__(**options)

        self.__class__._id_counter += 1
        self._id = self.__class__._id_counter

        self._sesstion_count = random.randint(0, 0xf)

        self.curr_flow_id = 0

        self._pendding_rflows = []

        if self.__class__.metadata_list is None:
            self.__class__.metadata_list = list()
            with open(options["metadata_file_name"], 'r') as f:
                tmp_str = f.read()
                re_groups = re.findall(r'"(\S+)"', tmp_str)
                for g in re_groups:
                    self.__class__.metadata_list.append(g)

    def _metadata_creator(self, bytes):
        metadata_count = random.randint(0, len(self.__class__.metadata_list))
        sample_metadata = random.sample(
            list(range(len(self.__class__.metadata_list))), metadata_count)
        flow_metadata = {}
        for i in sample_metadata:
            flow_metadata[self.__class__.metadata_list[i]] = bytes
        return flow_metadata


    def _updatePendding(self, flow_id):
        curr_rflow: dict = self._pendding_rflows[flow_id]
        curr_rflow["last_byte_ts"] += datetime.timedelta(
                0, random.randint(0, 0xfff), random.randint(0, 0xfff))
        new_no_packet_send = random.randint(0, 0xffffff)  # 3 byte
        new_no_packet_recv = random.randint(0, 0xffffff)  # 3 byte
        curr_rflow["packet_no_send"] += new_no_packet_send
        curr_rflow["packet_no_recv"] += new_no_packet_recv
        curr_rflow["volume_send"] += (
            new_no_packet_send * random.randint(1400, 1550))
        curr_rflow["volume_recv"] += (
            new_no_packet_recv * random.randint(1400, 1550))

        if random.randint(0, 3) == 3:
            curr_rflow["flow_terminated"] = True
            self._pendding_rflows.pop(flow_id)

        # just add metadata to copy of existing rflow (or terminated rflow
        #  which will be removed at the end of this function 
        copy_curr_rflow = curr_rflow \
            if curr_rflow["flow_terminated"] else deepcopy(curr_rflow)
        copy_curr_rflow.update(self._metadata_creator("some new dummy bytes"))

        return copy_curr_rflow

    def _newRflow(self):
        # Identifications
        flow_id = self.curr_flow_id
        self.curr_flow_id += 1 
        sensor_id = self._id
        session_id = random.randint(0, self._sesstion_count -1)

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
        flow_terminated = (random.randint(0, 3) != 3) or \
            (len(self._pendding_rflows) >= self.__class__.max_allowed_pendding)
        
        rflow_dict = {
            "flow_id":flow_id, "session_id":session_id,
            "src_ip":src_ip, "src_port":src_port,
            "dst_ip":dst_ip, "dst_port":dst_port, 
            "l4_protocol":l4_protocol, "l7_protocol":l7_protocol,
            "input_if_id":input_if_id, "output_if_id":output_if_id,
            "first_byte_ts":first_byte_ts,
            "last_byte_ts":last_byte_ts,
            "packet_no_send":packet_no_send, "packet_no_recv":packet_no_recv,
            "volume_send":volume_send, "volume_recv":volume_recv,
            "sensor_id":sensor_id, "flow_terminated":flow_terminated,
            "protocol_data_send":protocol_data_send,
            "protocol_data_recv":protocol_data_recv,
            }
        
        if not flow_terminated:
            self._pendding_rflows.append(deepcopy(rflow_dict))

        # flow meta data
        rflow_dict.update(self._metadata_creator("some dummy bytes"))

        return rflow_dict

    def next(self):
        if self._pendding_rflows:
            if random.randint(0, 1) == 1:
                return self._updatePendding(
                    random.randint(0, len(self._pendding_rflows)-1))
        return  self._newRflow()


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
