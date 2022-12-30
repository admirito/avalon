#!/usr/bin/env python3

from ..registry import Registry, BaseRepository
from ..auxiliary import classproperty


class BaseFormat(BaseRepository):
    """
    A generic parent for the Formats. Each Fromat is responsible
    for serializing the output of a Model instance.

    Options could be passed to the init constructor by keyword
    arguments. The BaseFormat will store the "filters" option as an
    attribute of the created object.
    """

    # disable accepting arguments started with __title__
    args_prefix = None

    class NOTSET:
        pass

    @classproperty
    def args_group_description(cls):
        """
        `args_group_description` class attribute defaults to a
        generic description but it can be overridden in sub-classes.
        """
        return (
            f"Arguments for {cls.args_group_title!r} format"
            if cls.args_group_title and cls.default_kwargs() else None)

    def __init__(self, filters=None, **kwargs):
        self.filters = filters or []
        self.filters_nonexistent_default = self.NOTSET

        super().__init__(**kwargs)

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
        _formats = Registry()

    from .linebase import (
        JsonLinesFormat, CSVFormat, HeaderedCSVFormat, BatchHeaderedCSVFormat)
    from .listbase import SQLFormat, GRPCFormat
    from .idmef import IDMEFFormat, CorrelatedIDMEFFormat, PickledIDMEFFormat

    for fmt in [
            JsonLinesFormat, CSVFormat, HeaderedCSVFormat,
            BatchHeaderedCSVFormat, SQLFormat, GRPCFormat, IDMEFFormat,
            CorrelatedIDMEFFormat, PickledIDMEFFormat]:
        _formats.register(fmt.__title__, fmt)

    return _formats


def formats_list():
    """
    Syntactic suger to get the list of foramts from the formats
    singleton from get_formats() method.
    """
    return get_formats().classes_list()


def format(format_name):
    """
    Syntactic suger to get the format class from the formats singleton
    from get_formats() method.
    """
    return get_formats().get_class(format_name)
