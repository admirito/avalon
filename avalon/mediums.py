#!/usr/bin/env python3

import multiprocessing
import os
import zlib
import requests
import sqlalchemy
import re
import kafka

from . import auxiliary


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

        if self._options["ordered_mode"]:
            self._index = multiprocessing.Value("l")
            self._oldest_index = multiprocessing.Value("l")
        else:
            self._index = 0
            self._oldest_index = 0
            self._max_file_allowed = int(
                abs(self._options["max_file_count"])
                    / self._options["instances"])\
                        + (1 if self._options["instances"] > 1 else 0)

    def _blocking_max_file(self):
        def _check_files_count():
            return sum(
                1 for i in os.scandir(self._options["directory"]) 
                if i.is_file()
            ) >= abs(self._options["max_file_count"])

        if _check_files_count():
            notifier = auxiliary.DirectoryNotifier(
                self._options["directory"])
            notifier.notify = _check_files_count
            notifier.wait()

    def _remove_or_truncate(self, raw_file_name):
        oldest_file_path = os.path.join(
            self._options["directory"], raw_file_name + self._options["suffix"])
        if self._options["max_file_count"] > 0:
            with open(oldest_file_path, "w") as f:
                f.truncate(0)
        else:
            os.remove(oldest_file_path)
        
    def _ordered_get_name_and_remove_truncate_oldest(self):
        with self._index, self._oldest_index:
            curr_file_name = str(self._index.value) + self._options["suffix"]
            self._index.value += 1

            if self._options["max_file_count"]:
                if not self._options["dir_blocking_enable"]:
                    if (self._index.value - self._oldest_index.value > \
                        abs(self._options["max_file_count"])):
                        self._remove_or_truncate(str(self._oldest_index.value))
                        self._oldest_index.value += 1
                else:
                    self._blocking_max_file()

        return curr_file_name

    def _unorderd_get_name_and_remove_truncate_oldest(self):
        curr_file_name = str(self._index) \
            + "_" + str(os.getpid()) + self._options["suffix"]
        self._index += 1
        
        if self._options["max_file_count"]:
            if not self._options["dir_blocking_enable"]:
                if self._index - self._oldest_index > self._max_file_allowed:
                    self._remove_or_truncate(
                        str(self._oldest_index) + "_" + str(os.getpid()))    
                    self._oldest_index += 1    
            else:
                self._blocking_max_file()

        return curr_file_name

    def _write(self, batch):
        """
        Creates a new file with specified suffix and write the batch to it, if 
        count of directory's files exceed from the specified value 
        this function removes the oldest file and the create it 
        
        @param batch is data should be written to the file
        """
        if self._options["ordered_mode"]:
            curr_file_name = self._ordered_get_name_and_remove_truncate_oldest()
        else:
            curr_file_name = \
                self._unorderd_get_name_and_remove_truncate_oldest()

        # TODO: if we want to be ensure that count of directory files never
        # exceed from 'max-files' in 'ordered mode', we should open the file
        # in 'ordered_get_name_and_remove_oldest' under it's lock 
        # and write in and close it here, but do we really need this?
        if self._options["tmp_dir_path"]:
            curr_file_path = os.path.join(
                    self._options["tmp_dir_path"], curr_file_name) 
            with open(curr_file_path, "w") as f:
                f.write(batch)
                os.rename(
                    curr_file_path,
                    os.path.join(
                        self._options["directory"], curr_file_name))  
        else:
            with open(
                os.path.join(self._options["directory"], curr_file_name), 
                "w") as f:
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


class SqlMedia(BaseMedia):
    """
    General SQL Media
    """
    def __init__(self, max_writers, **options):
        super().__init__(max_writers, **options)

        self._options = options

        # table_name should contain fields order like 'tb (a, b, c)'
        self.table_params = re.findall(
            r"[^\s\(\),]+", self._options["table_name"])
        self.table = sqlalchemy.table(
            self.table_params[0], 
            *[sqlalchemy.column(x) for x in self.table_params[1:]])
        self.con = None

    def _connect(self):
        self.engine = sqlalchemy.create_engine(self._options['dsn'])
        self.con = self.engine.connect()
        self.con.execution_options(autocommit=self._options["autocommit"])
        
    
    def _write(self, batch):
        # lazy connect to avoid multi-processing problems on connection
        if not self.con:
            self._connect()
        self.con.execute(self.table.insert(), batch)
    
    def __del__(self):
        if self.con:
            self.con.close()


class KafkaMedia(BaseMedia):
    def __init__(self, max_writers, **options):
       super().__init__(max_writers, **options)
       self.topic = options["topic"]
       self.producer = kafka.KafkaProducer(
           bootstrap_servers=options["bootstrap_servers"])

    def _write(self, batch: str):
        if not isinstance(batch, str):
            raise ValueError("kafka media only accepts string value.")
        self.producer.send(topic=self.topic, value=batch.encode('utf-8'))
