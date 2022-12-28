#!/usr/bin/env python3

class Formats:
    """
    An abstraction for keeping a list of available formats.
    """
    def __init__(self):
        self._formats = {}

    def register(self, format_name, format_class):
        """
        Register a new format class.
        """
        self._formats[format_name] = format_class

    def formats_list(self):
        """
        Returns the list of available formats.
        """
        return list(self._formats.keys())

    def format(self, format_name, **kwargs):
        return self._formats[format_name](**kwargs)


class BaseFormat:
    """
    A generic parent for the Formats. Each Fromat is responsible
    for serializing the output of a Model instance.

    Options could be passed to the init constructor by keyword
    arguments. The BaseFormat will only store the "filters" option as
    an attribute of the created object.
    """
    class NOTSET:
        pass

    def __init__(self, **kwargs):
        self.filters = kwargs.get("filters", [])
        self.filters_nonexistent_default = self.NOTSET

    def apply_filters(self, model_data):
        """
        """
        if not self.filters:
            return model_data

        return {key: model_data.get(key, self.filters_nonexistent_default)
                for key in self.filters
                if self.filters_nonexistent_default is not self.NOTSET or
                key in self.filters}

    def batch(self, model, size):
        """
        Return a batch with the given `size` by using the given
        model instance.
        """
        raise NotImplementedError


def get_formats():
    """
    Returns a singleton instance of Formats class in which all the
    available formats are registered.
    """
    global _formats

    try:
        return _formats
    except NameError:
        _formats = Formats()

    from .linebase import (
        JsonLinesFormat, CSVFormat, HeaderedCSVFormat, BatchHeaderedCSVFormat)
    from .listbase import SQLFormat, GRPCFormat
    from .idmef import IDMEFFormat, CorrelatedIDMEFFormat, PickledIDMEFFormat

    _formats.register("json-lines", JsonLinesFormat)
    _formats.register("csv", CSVFormat)
    _formats.register("headered-csv", HeaderedCSVFormat)
    _formats.register("batch-headered-csv", BatchHeaderedCSVFormat)
    _formats.register("sql", SQLFormat)
    _formats.register("grpc", GRPCFormat)
    _formats.register("idmef", IDMEFFormat)
    _formats.register("correlated-idmef", CorrelatedIDMEFFormat)
    _formats.register("pickled-idmef", PickledIDMEFFormat)

    return _formats


def formats_list():
    """
    Syntactic suger to get the list of foramts from the formats
    singleton from get_formats() method.
    """
    return get_formats().formats_list()


def format(format_name, **kwargs):
    """
    Syntactic suger to get a format from the formats singleton
    from get_formats() method.
    """
    return get_formats().format(format_name, **kwargs)
