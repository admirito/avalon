import logging.handlers
import os

from . import BaseMedia


class SyslogMedia(BaseMedia):
    """
    Send data via syslog.

    Initialize keyword options:
     - `address`: syslog address
     - `level`: syslog level name
     - `tag`: syslog tag
    """
    def __init__(self, max_writers, **options):
        super().__init__(max_writers, **options)

        self.address = options.get("address", "/dev/log")
        if not os.path.exists(self.address):
            host, port, *_ = self.address.split(":") + [514]
            port = int(port)
            self.address = (host, port)

        self.level = logging.getLevelName(options.get("level", "INFO").upper())
        self.tag = options.get("tag", "avalon")

        tag_formatter = logging.Formatter(f"{self.tag}: %(message)s")
        handler = logging.handlers.SysLogHandler(self.address)
        handler.setLevel(self.level)
        handler.setFormatter(tag_formatter)

        self.logger = logging.getLogger("avalon-syslog-media")
        self.logger.addHandler(handler)
        self.logger.setLevel(self.level)

    def _write(self, batch):
        if isinstance(batch, bytes):
            batch = batch.decode("utf8")
        if isinstance(batch, str):
            for line in batch.split("\n"):
                line = line.rstrip()
                if line:
                    self.logger.log(self.level, line)
        else:
            for item in batch:
                self.logger.log(self.level, str(item))
