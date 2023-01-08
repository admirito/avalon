import zlib

import requests

from . import BaseMedia
from ..auxiliary import key_values_str_to_dict


class SingleHTTPRequestMedia(BaseMedia):
    """
    Initialize keyword options:
     - `method`:  the HTTP method
     - `url`: the HTTP URL
     - `headers`: a mapping of HTTP headers
     - `gizp`: a boolean indicating weather zlib compression is
       enabled or not.

    Transfer data to an HTTP server with a single HTTP request for
    each batch.
    """

    __title__ = "http"

    def __init__(self, **kwargs):
        """
        A callback method to update members after avalon_args
        updated
        """
        super().__init__(**kwargs)

        self.headers = \
            key_values_str_to_dict(self.headers) if self.headers else {}

    @classmethod
    def add_arguments(cls, group):
        """
        Add class arguemtns to the argparse group
        """
        group.add_argument(
            "--http-url", metavar="<url>",
            default="http://localhost",
            help="Use <url> to send output.")
        group.add_argument(
            "--http-method", metavar="<method>", choices=[
                "options", "get", "head", "post", "put", "delete", "trace",
                "connect", "patch"], default="post", type=str.lower,
            help="For http media, use <method> to send the request.")
        group.add_argument(
            "--http-headers", default="",
            help="A list of space separated key=value of http headers.")
        group.add_argument(
            "---http-gzip", action="store_true",
            help="Enable gzip compression.")

    def _write(self, batch):
        if self.gzip:
            batch = zlib.compress(batch)
            self.headers["Content-Encoding"] = "gzip"

        requests.request(self.method, self.url, headers=self.headers,
                         data=batch)
