#!/usr/bin/env python3

import binascii
import fcntl
import fnmatch
import importlib
import multiprocessing
import os
import re
import signal
import struct
import time
import urllib


class DirectoryNotifier:
    """
    blocking directory watcher
    only one instace of this class can exist at a time 
    because of system signal limitations
    """
    sig = signal.SIGUSR1

    def __init__(
        
        self, dirname, 
        events_mask=fcntl.DN_DELETE | fcntl.DN_MULTISHOT, timeout=0.3):
        """
        Create an object
        
        @param dirname is directory name should be watched
        @param event_mask determines which events should be listened
        """
        if not os.path.isdir(dirname):
            raise NotADirectoryError("you can only watch a directory.")

        self.timeout = timeout
        self.dirname = dirname
        self.fd = os.open(dirname, os.O_RDONLY)
        fcntl.fcntl(self.fd, fcntl.F_SETSIG, self.__class__.sig)
        fcntl.fcntl(self.fd, fcntl.F_NOTIFY, events_mask)
        signal.signal(self.__class__.sig, self)


    def __del__(self):
        os.close(self.fd)

    def __repr__(self):
        return "<%s watching %s>" % (self.__class__.__name__, self.dirname)   
    
    def __call__(self, sig_num, frame):
        if self.notify():
            self.wait()

    def notify(self):
        """
        handle signals and return true if more signals is needed.
        """
        return False

    def wait(self):
        """
        blocks the process until it receives a signal from specific signal list
        """
        if not signal.sigtimedwait(
            [self.__class__.sig, signal.SIGTERM, signal.SIGINT], self.timeout):
            self(-1, None)


def importall(package, pattern="*.py"):
    """
    Given a python package object and a filename pattern, all the
    modules inside the package will be imported and returned as a
    list.

    Namespace packages are supported by this mehtod but modules
    requiring import hooks
    (https://docs.python.org/3/reference/import.html#import-hooks) are
    not supported and only normal files with valid python module
    identifiers and ending with .py suffix will be imported.
    """
    VALID_MODULE_NAME = re.compile(r"[_a-z]\w*\.py$", re.IGNORECASE)

    result = []

    for top_dir in package.__path__:
        try:
            for path in sorted(os.listdir(top_dir)):
                full_path = os.path.join(top_dir, path)
                if (os.path.isfile(full_path) and
                        fnmatch.fnmatch(path, pattern) and
                        VALID_MODULE_NAME.match(path)):
                    import_name = f"{package.__name__}.{path[:-3]}"
                    try:
                        module = importlib.import_module(import_name)
                    except ImportError:
                        pass
                    else:
                        result.append(module)
        except OSError:
            pass

    return result


# a counter used by new_oid method
_time_id_counter = multiprocessing.Value("i")


def new_oid(ts=None):
    """
    Generate a unique 24 character string
    """
    ts = int(time.time()) if ts is None else int(ts)

    _id = struct.pack(">I", ts)
    _id += os.urandom(5)
    with _time_id_counter.get_lock():
        _id += struct.pack(">I", _time_id_counter.value)[1:4]
        _time_id_counter.value += 1
        if _time_id_counter.value < 0:
            _time_id_counter.value = 0

    return binascii.hexlify(_id).decode()


def parse_db_url(url):
    """
    Given a database url
    (e.g. postgresql://user:pass@host:5432/db) a dictionary will be
    returned accordingly. The "scheme" key in the dictionary will
    determine the database type and other parameters will be present
    based on the URL and the scheme.
    """
    _url = urllib.parse.urlparse(url)

    if not _url.scheme:
        return {}

    result = {"scheme": _url.scheme}

    _netloc = re.match(r"((?P<username>[^:@]*)(:(?P<password>[^:@]*))?@)?"
                       r"(?P<host>[^:@]*)(:(?P<port>\d+))?", _url.netloc)
    if _netloc:
        result.update({k: v for k, v in _netloc.groupdict().items()
                       if v is not None})
    else:
        result["host"] = _url.netloc

    if _url.path:
        result["database"] = _url.path.lstrip("/")

    if result["scheme"].startswith("postgre"):
        if "database" in result:
            result["dbname"] = result.pop("database")
        if "username" in result:
            result["user"] = result.pop("username")

    if _url.query:
        result.update(dict(tuple(i.split("=", 1) + [""])[:2]
                           for i in _url.query.split("&")))

    return result
