import datetime

from . import BaseMapping


class DtToIsoMapping(BaseMapping):
    """
    Convert columns from datetime to string iso format with time
    zone.
    """

    __title__ = "dttoiso"

    def map(self, item):
        for key, value in item.items():
            if isinstance(value, datetime.datetime):
                item[key] = value.astimezone().isoformat()

        return item


class DtToTimestampMapping(BaseMapping):
    """
    Convert columns from datetime to unix timestamp.
    """

    __title__ = "dttots"

    def map(self, item):
        for key, value in item.items():
            if isinstance(value, datetime.datetime):
                item[key] = value.timestamp()

        return item
