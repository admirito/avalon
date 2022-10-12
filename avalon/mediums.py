#!/usr/bin/env python3

import ctypes
import multiprocessing
from multiprocessing.util import is_exiting
import socket
from socket import socket
import sys, os
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


class DirectoryMedia(BaseMedia):
    def __init__(self,  max_writers, **options):
        super().__init__(max_writers, **options)

        self._index = multiprocessing.Value(ctypes.c_long, 0)
        self.lock = multiprocessing.Lock()
        if not os.path.isdir(options["directory"]):
            os.mkdir(options["directory"])
    
    def _write(self, batch):
        with self.lock:
            curr_file = os.path.join(self._options["directory"],
                str(self._index.value) + '.' + self._options["suffix"])
            self._index.value += 1
       
        with open(curr_file, 'w') as f:
            f.write(batch)
        


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