import datetime
import ipaddress
import re
import time

try:
    import grpc_requests
except ModuleNotFoundError:
    pass

from . import BaseMapping
from .. import auxiliary


class RFlowProtoMapping(BaseMapping):
    """
    Transfrom RFlow model data to be compatible with RFlow proto.
    """

    __title__ = "rflowproto"

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

    __title__ = "rflowhello"

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

    __title__ = "logproto"

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
