#!/usr/bin/env python3

import multiprocessing
from multiprocessing.sharedctypes import Value
from multiprocessing.util import is_exiting
import socket
from socket import socket
import sys
import os
import zlib
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
    """
    Initialize keyword options:
     - `directory`: a path to the target directory
     - `suffix`: files suffix
     - `max_file_count`: maximum allowed file count

    Create a new file with specified suffix in directory
    with each call to _write()
    """
    def __init__(self,  max_writers, **options):
        super().__init__(max_writers, **options)

        self._index = multiprocessing.Value("l")
        self._oldest_index = multiprocessing.Value("l")
    
    def _write(self, batch):
        """
        Creates a new file with specified suffix and write the batch to it, if 
        count of directory's files exceed from the specified value 
        this function removes the oldest file and the create it 
        
        @param batch is data should be written to the file
        """
        with self._index, self._oldest_index:
            curr_file = os.path.join(
                self._options["directory"],
                str(self._index.value) + self._options["suffix"])
            self._index.value += 1

            if self._options["max_file_count"]:
                if (self._index.value - self._oldest_index.value > \
                        abs(self._options["max_file_count"])):
                    oldest_file = os.path.join(
                        self._options["directory"],
                        str(self._oldest_index.value) 
                            + self._options["suffix"])
                    if self._options["max_file_count"] > 0:
                        with open(oldest_file, "w") as f:
                            f.truncate(0)
                    else:
                        os.remove(oldest_file)
                    self._oldest_index.value += 1 
                               
        with open(curr_file, "w") as f:
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
