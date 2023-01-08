import argparse
import importlib
import os
import pathlib
import shutil
import tempfile

from . import BaseMedia
from ..registry import RequiredValue


def _import_third_party_libs():
    global grpc_requests, protoc

    import grpc_requests
    from grpc_tools import protoc


class GRPCMedia(BaseMedia):
    """
    GRPC Media to send batches over GRPC methods which accept streams.

    Initialize keyword options:
     - `endpoint`: GRPC endpoint
     - `method`: GRPC method fullname (with package and servcie)
    """

    __title__ = "grpc"

    default_format = "grpc"

    def __init__(self, max_writers=None, **options):
        super().__init__(max_writers, **options)

        _import_third_party_libs()

        self.client = None
        self.service, self.method, *_ = \
            self.method_name.rsplit(".", 1) + [""]

        # remove package name from service name
        service_name = self.service.split(".", 1)[1]

        self.proto_file = getattr(self.proto_file, "name", None)
        self.service_descriptor = self._proto_to_service_descriptor(
            self.proto_file, service_name) if self.proto_file else None

    @classmethod
    def add_arguments(cls, group):
        """
        Add class arguemtns to the argparse group
        """
        group.add_argument(
            "--grpc-endpoint", metavar="<endpoint>",
            default=RequiredValue("--grpc-endpoint"),
            help="Send GRPC requests to <endpoint>.")
        group.add_argument(
            "--grpc-method-name", metavar="<fullname>",
            default=RequiredValue("--grpc-method-name"),
            help="Use <fullname> as the name of the method to call.")
        group.add_argument(
            "--grpc-proto", metavar="<file>", type=argparse.FileType("rb"),
            dest="grpc_proto_file",
            help="Use proto <file> to create grpc stubs instead of \
            using reflection.")

    def _proto_to_service_descriptor(self, proto_file, service_name):
        """
        Given a .proto file and a service name, the protoc module
        will be called to generate python bindins and the releated
        service descriptor will be returned.
        """
        input_proto_path = os.path.dirname(proto_file)
        output_proto_path = tempfile.mkdtemp()
        protoc.main(["protoc",
                     "--proto_path", input_proto_path,
                     "--python_out", output_proto_path,
                     proto_file])

        files_list = os.listdir(output_proto_path)
        if not files_list:
            raise Exception("protoc did not generate any file")

        # import the protoc output file
        module_path = files_list[0]
        module_name = pathlib.Path(module_path).stem
        spec = importlib.util.spec_from_file_location(
            module_name, module_path)
        proto_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(proto_module)
        shutil.rmtree(output_proto_path)

        return proto_module.DESCRIPTOR.services_by_name[service_name]

    def _write(self, batch):
        if not self.client:
            if self.service_descriptor:
                # If the service_descriptor is available, we can use
                # the releated StubClient
                self.client = grpc_requests.StubClient.get_by_endpoint(
                    self.endpoint,
                    service_descriptors=[self.service_descriptor])
            else:
                # No stub client is availabe, so we have to use GRPC
                # server reflection.
                self.client = grpc_requests.Client.get_by_endpoint(
                    self.endpoint)

        self.client.request(self.service, self.method, batch)
