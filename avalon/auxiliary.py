#!/usr/bin/env python3

import fcntl
import os
import signal

class DirectoryNotifier:
    """
    blocking directory watcher
    only one instace of this class can exist at a time 
    because of system signal limitations
    """
    sig = signal.SIGUSR1

    def __init__(
        self, dirname, func, 
        events_mask=fcntl.DN_DELETE | fcntl.DN_MULTISHOT, timeout=5):
        if not os.path.isdir(dirname):
            raise NotADirectoryError("you can only watch a directory.")

        self.timeout = timeout
        self.timed_out = False
        self.func = func
        self.dirname = dirname
        self.fd = os.open(dirname, os.O_RDONLY)
        fcntl.fcntl(self.fd, fcntl.F_SETSIG, self.__class__.sig)
        fcntl.fcntl(self.fd, fcntl.F_NOTIFY, events_mask)
        signal.signal(self.__class__.sig, self)


    def __del__(self):
        os.close(self.fd)

    def __str__(self):
        return "%s watching %s" % (self.__class__.__name__, self.dirname)   
    
    def __call__(self, sig_num, frame):
        if self.func(self.timed_out):
            self.wait()

    def wait(self):
        """
        blocks the process until receives a signal
        """
        self.timed_out = not signal.sigtimedwait(
            [self.__class__.sig, signal.SIGABRT, signal.SIGKILL], self.timeout)
        if self.timed_out:
            self()