#!/usr/bin/env python3

import fcntl
import fnmatch
import importlib
import os
import re
import signal


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
