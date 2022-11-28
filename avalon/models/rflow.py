import base64
import datetime
import random
import re
import socket
import struct

from copy import deepcopy

from . import BaseModel

from .rflowdata import params as RFlow_params
from .rand import choose_in_normal_distribution, decision, random_epsilon


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
        Creates metadata dictionary using metadata name in
        self.__class__.metadata_list and RFlow_params.metadata_values
        (or RFlow_params.default_metadata_values)

        @return metadata as a dictionary
        """
        metadata_count = choose_in_normal_distribution(
            max=RFlow_params.metadata_count_max,
            mean=RFlow_params.metadata_count_mean,
            stddev=RFlow_params.metadata_stddev)
        sample_metadata = random.sample(
            list(range(len(self.__class__.metadata_list))), metadata_count)
        flow_metadata = {}
        for i in sample_metadata:
            if RFlow_params.metadata_values.get(
                    self.__class__.metadata_list[i]):
                vals = RFlow_params.metadata_values[
                    self.__class__.metadata_list[i]
                ]
            else:
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
            curr_rflow["last_byte_ts"] + random_epsilon(),
            datetime.datetime.now() - datetime.timedelta(
                milliseconds=random.randint(0, 90000)))  # 1.5 minutes
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

        # just add metadata to copy of existing rflow (or terminated
        # rflow which will be removed at the end of this function
        copy_curr_rflow = curr_rflow \
            if curr_rflow["is_terminated"] else deepcopy(curr_rflow)
        copy_curr_rflow["metadata"] = self._metadata_creator()

        return copy_curr_rflow

    def _new_rflow(self):
        """
        Creates a new flow and add it to the self._pendding_rflows
        if it is not terminated.

        @return a flow
        """
        # Identifications
        flow_id = self.curr_flow_id
        self.curr_flow_id = \
            (self.curr_flow_id + 1) if self.curr_flow_id < 0xffffffff else 0
        sensor_id = self._id
        session_id = random.randint(0, self._session_count - 1)
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
                stddev=RFlow_params.ip_norm_stddev)))
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
        now = datetime.datetime.now()
        first_byte_ts = now - datetime.timedelta(
            milliseconds=random.randint(0, 120000))  # two minutes
        last_byte_ts = min(
            now,
            first_byte_ts + datetime.timedelta(
                milliseconds=random.randint(0, 120000))
        )

        # packet stats
        packet_no_send = random.randint(0, 0xffffff)  # 3 byte
        packet_no_recv = random.randint(0, 0xffffff)  # 3 byte

        # total transmitted volume
        # packet count * random avg packet size
        volume_send = packet_no_send * random.randint(1400, 1550)
        volume_recv = packet_no_recv * random.randint(1400, 1550)

        # protocol specific data
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
        return self._new_rflow()
