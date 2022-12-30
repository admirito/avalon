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

    __title__ = "syslog"

    def __init__(self, max_writers, **options):
        super().__init__(max_writers, **options)

        if not os.path.exists(self.address):
            host, port, *_ = self.address.split(":") + [514]
            port = int(port)
            self.address = (host, port)

        self.level = logging.getLevelName(self.level.upper())

        tag_formatter = logging.Formatter(f"{self.tag}: %(message)s")
        handler = logging.handlers.SysLogHandler(self.address)
        handler.setLevel(self.level)
        handler.setFormatter(tag_formatter)

        self.logger = logging.getLogger("avalon-syslog-media")
        self.logger.addHandler(handler)
        self.logger.setLevel(self.level)

    @classmethod
    def add_arguments(cls, group):
        """
        Add class arguemtns to the argparse group
        """
        group.add_argument(
            "--syslog-address", metavar="<address>", default="/dev/log",
            help="Send data to the syslog server at <address>. It could be \
            host:port or path to syslog socket")
        group.add_argument(
            "--syslog-level", metavar="<level>", default="info",
            choices=["debug", "info", "warn", "error", "fatal"],
            help="Set the syslog level to <level>.")
        group.add_argument(
            "--syslog-tag", metavar="<name>", default="avalon",
            help="Set the syslog tag to <name>.")

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
