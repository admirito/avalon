from . import BaseFormat


class ListFormat(BaseFormat):
    """
    Serialize data as a Python list
    """
    def batch(self, model, size):
        """
        Call model next method `size` times and return it as a
        list.
        """
        return [model.next() for _ in range(size)]


class SQLFormat(ListFormat):
    """
    Creates SQL insert query values from dictionaries
    """
    __title__ = "sql"


class GRPCFormat(ListFormat):
    """
    Creates GRPC batches i.e. a list of dictionaries
    """
    __title__ = "grpc"
