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