#!/usr/bin/env python3

import multiprocessing
import socket
from socket import socket
import sys
import zlib
import asyncio

import requests


class BaseMedia:
    """
    A generic parent for Media classes. Each Media is responsible
    for transferring serialized batch data through a specific media.
    """
    _semaphores = {}

    def __init__(self, max_writers, **options):
        self._semaphore = multiprocessing.Semaphore(max_writers)

        self._options = options

    def write(self, batch):
        """
        Call _write to stream the batch through the meida.
        """
        with self._semaphore:
            self._write(batch)

    def _write(self, batch):
        raise NotImplementedError


class FileMedia(BaseMedia):
    """
    Initialize keyword options:
     - `file`:  an IO stream with a write method

    Write the data into an IO stream.
    """
    def _write(self, batch):
        fp = self._options["file"]
        fp.write(batch)


class SingleHTTPRequest(BaseMedia):
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
    def _write(self, batch):
        method = self._options.get("method", "POST")
        url = self._options["url"]
        headers = self._options.get("headers", {})
        gzip = self._options.get("gzip", False)

        if gzip:
            batch = zlib.compress(batch)
            headers["Content-Encoding"] = "gzip"

        requests.request(method, url, headers=headers, data=batch)


class MessageBroadcast(BaseMedia):
    """
    Sends a message as a buffer of bytes to a tcp socket
    first four byte is an integer shows buffer len
    """
    def __init__(self, ip:str, port:int):
        self.ch_mgr
        connection_list = list()
        self.socket = socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.socket.bind((ip, port))
            self.socket.listen()
            while True:
                temp_conn, addr = self.socket.accept()
                connection_list.append(temp_conn)
                print(f"new connection received {addr}",
                    addr.ip, addr.port)
        except Exception as e:
            sys.stderr.write(str(e))

    def _write(self, batch):
        try:
            for buffer in batch:
                pass
        except Exception as e:
            sys.stderr.write(str(e))
