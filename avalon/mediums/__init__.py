#!/usr/bin/env python3

import multiprocessing


class BaseMedia:
    """
    A generic parent for Media classes. Each Media is responsible
    for transferring serialized batch data through a specific media.
    """
    _semaphores = {}

    def __init__(self, max_writers, **options):
        self._semaphore = multiprocessing.Semaphore(max_writers)

        self._options = options
        self.ignore_errors = options.get("ignore_errors", False)

    def write(self, batch):
        """
        Call _write to stream the batch through the meida.
        """
        with self._semaphore:
            try:
                self._write(batch)
            except Exception:
                if not self.ignore_errors:
                    raise

    def _write(self, batch):
        raise NotImplementedError


from .file import FileMedia, DirectoryMedia
from .grpc import GRPCMedia
from .httpbase import SingleHTTPRequestMedia
from .kafka import KafkaMedia
from .soap import SOAPMedia
from .sql import SqlMedia, PsycopgMedia, ClickHouseMedia
from .syslogbase import SyslogMedia
