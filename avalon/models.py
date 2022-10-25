#!/usr/bin/env python3

import base64
from copy import deepcopy
import time
import datetime
import random
import socket
import struct
import re

from avalon.data import RFlow_params


def choose_in_normal_distribution(min=0, max=0, exclude=[],
                                  mean=None, stddev=None) -> int:
    """
    Get a range by minimum and maximum values and choose an integer from it 
    using normal distribution which not exist in exclude list.

    @param min is minimum selectable value of range
    @param max is maximum selectable value of range
    @param exclude is list of forbidden valuse
    @param mean is mean in normal distribution
    @param stddev is standard deviation in normal distribution
    @return an integer chosen from the range using normal distribution 
    """
    if mean is None:
        # set mean to center of the list
        mean = (max - min) / 2

    if stddev is None:
        stddev = (max - min + 1) / 6

    while True:
        val = int(random.normalvariate(mean, stddev) + 0.5)
        if min <= val < max and val not in exclude:
            return val


def decision(prob: float):
    """
    Get a probability and return a boolean with respect it
    @param prob is probability
    @return a boolean w.r.t input probability
    """
    return random.random() < prob


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
    Initialize keyword options:
     - `metadata_file_name`: path to the metadata file bash script

    Rflow generator
    """
    _id_counter = 0
    metadata_list = None
    max_allowed_pendding = 100

    def __init__(self, **options):
        super().__init__(**options)

        self._id = self.__class__._id_counter
        self.__class__._id_counter += 1

        self._session_count = random.randint(1, 0xf)

        self.curr_flow_id = 0

        self._pendding_rflows = []

        if self.__class__.metadata_list is None:
            with open(options["metadata_file_name"], "r") as f:
                tmp_str = f.read()
                self.__class__.metadata_list = re.findall(
                    r"\"(\S+)\"", tmp_str)
               

    def _metadata_creator(self):
        """
        Creates metadata dictionary using metadata name 
        in self.__class__.metadata_list and 
        RFlow_params.metadata_values (or RFlow_params.default_metadata_values)
        
        @return metadata as a dictionary
        """
        metadata_count = random.randint(0, len(self.__class__.metadata_list))
        sample_metadata = random.sample(
            list(range(len(self.__class__.metadata_list))), metadata_count)
        flow_metadata = {}
        for i in sample_metadata:
            if RFlow_params.metadata_values.get(
                self.__class__.metadata_list[i]):
                    vals = RFlow_params.metadata_values[
                        self.__class__.metadata_list[i]
                        ]
            else :
                vals = RFlow_params.default_metadata_values
            flow_metadata[self.__class__.metadata_list[i]] = \
                base64.b64encode(vals[choose_in_normal_distribution(
                    max=len(vals)-1,
                    stddev=RFlow_params.metadata_values_stddev)
                ].encode()).decode()
        return flow_metadata


    def _update_pending(self, flow_index):
        """
        Generate a flow by updating a pending flow
        
        @param flow_index is index of a pending flow in self._pendding_rflows
        @return a flow
        """
        curr_rflow: dict = self._pendding_rflows[flow_index]
        curr_rflow["last_byte_ts"] = max(
            curr_rflow["last_byte_ts"],
            datetime.datetime.now() 
                - datetime.timedelta(
                    microseconds=random.randint(0, 90000))) # 1.5 minutes
        new_no_packet_send = random.randint(0, 0xffffff)  # 3 byte
        new_no_packet_recv = random.randint(0, 0xffffff)  # 3 byte
        curr_rflow["packet_no_send"] += new_no_packet_send
        curr_rflow["packet_no_recv"] += new_no_packet_recv
        curr_rflow["volume_send"] += (
            new_no_packet_send * random.randint(1400, 1550))
        curr_rflow["volume_recv"] += (
            new_no_packet_recv * random.randint(1400, 1550))

        if not decision(RFlow_params.continuous_flow_prob):
            curr_rflow["is_terminated"] = True
            self._pendding_rflows.pop(flow_index)

        # just add metadata to copy of existing rflow (or terminated rflow
        #  which will be removed at the end of this function 
        copy_curr_rflow = curr_rflow \
            if curr_rflow["is_terminated"] else deepcopy(curr_rflow)
        copy_curr_rflow["metadata"] = self._metadata_creator()

        return copy_curr_rflow

    def _new_rflow(self):
        """
        Creates a new flow and add it to the self._pendding_rflows if
        it is not terminated.
        @return a flow
        """
        # Identifications
        flow_id = self.curr_flow_id
        self.curr_flow_id = \
            (self.curr_flow_id + 1) if self.curr_flow_id < 0xffffffff else 0
        sensor_id = self._id
        session_id = random.randint(0, self._session_count -1)
        user_id = random.randint(0, 500)

        # Flow Key
        int_ip = choose_in_normal_distribution(
            *RFlow_params.ip_range, stddev=RFlow_params.ip_norm_stddev)
        src_ip = socket.inet_ntoa(struct.pack(">I", int_ip))
        src_port = choose_in_normal_distribution(
            *RFlow_params.port_range, stddev=RFlow_params.port_norm_stddev)
        dst_ip = socket.inet_ntoa(struct.pack(
            ">I", choose_in_normal_distribution(
                *RFlow_params.ip_range, exclude=[int_ip],
                    stddev= RFlow_params.ip_norm_stddev)))
        dst_port = choose_in_normal_distribution(
            *RFlow_params.port_range, stddev=RFlow_params.port_norm_stddev)

        # Protocols
        l4_protocol = choose_in_normal_distribution(
            *RFlow_params.l4_range, stddev=RFlow_params.l4_norm_stddev)
        l7_protocol = choose_in_normal_distribution(
            *RFlow_params.l7_range, stddev=RFlow_params.l7_norm_stddev)

        # interfaces
        input_if_id = random.randint(-1, 0xffff)   # 2 byte
        output_if_id = random.randint(-1, 0xffff)  # 2 byte

        # timestamps
        first_byte_ts = datetime.datetime.now() - datetime.timedelta(
            milliseconds=random.randint(0, 120000)) # two minutes
        last_byte_ts = first_byte_ts \
            + datetime.timedelta(
                0, random.randint(0, 0x1fff), random.randint(0, 0x1fff))

        # packet stats
        packet_no_send = random.randint(0, 0xffffff)  # 3 byte
        packet_no_recv = random.randint(0, 0xffffff)  # 3 byte

        # total transmitted volume
        # packet count * random avg packet size
        volume_send = packet_no_send * random.randint(1400, 1550)
        volume_recv = packet_no_recv * random.randint(1400, 1550)

        #protocol specific data
        protocol_data_send = random.randint(0, 1)
        protocol_data_recv = random.randint(0, 1)

        # flow termination
        flow_terminated = \
            (not decision(RFlow_params.continuous_flow_prob)) or \
            (len(self._pendding_rflows) >= self.__class__.max_allowed_pendding)
        
        rflow_dict = {
            "flow_id": flow_id, "id_session": session_id, "user_id": user_id,
            "srcip": src_ip, "srcport": src_port,
            "destip": dst_ip, "destport": dst_port, 
            "protocol_l4": l4_protocol, "protocol_l7": l7_protocol,
            "input_if": input_if_id, "output_if": output_if_id,
            "first_byte_ts": first_byte_ts,
            "last_byte_ts": last_byte_ts,
            "packet_no_send": packet_no_send, "packet_no_recv": packet_no_recv,
            "volume_send": volume_send, "volume_recv": volume_recv,
            "sensor_id": sensor_id, "is_terminated": flow_terminated,
            "proto_flags_send": protocol_data_send,
            "proto_flags_recv": protocol_data_recv,
            "metadata": {}}
        
        if not flow_terminated:
            self._pendding_rflows.append(deepcopy(rflow_dict))

        # flow meta data
        rflow_dict["metadata"] = self._metadata_creator()

        return rflow_dict

    def next(self):
        """
        Creates or updates a flow
        @return a flow
        """
        if self._pendding_rflows:
            if decision(RFlow_params.update_flow_prob):
                return self._update_pending(
                    random.randint(0, len(self._pendding_rflows)-1))
        return  self._new_rflow()


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
    _models.register("rflow", RFlowModel)

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
