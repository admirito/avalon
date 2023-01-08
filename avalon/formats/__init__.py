#!/usr/bin/env python3

import pkgutil

from .. import registry
from ..auxiliary import classproperty

# Extend __path__ to enable avlaon namespace package extensions
__path__ = pkgutil.extend_path(__path__, __name__)


class BaseFormat(registry.BaseRepository):
    """
    A generic parent for the Formats. Each Fromat is responsible
    for serializing the output of a Model instance.

    Options could be passed to the init constructor by keyword
    arguments. The BaseFormat will store the "filters" option as an
    attribute of the created object.
    """

    # disable accepting arguments started with __title__
    args_prefix = None

    @classproperty
    def args_group_description(cls):
        """
        `args_group_description` class attribute defaults to a
        generic description but it can be overridden in sub-classes.
        """
        return (
            f"Arguments for {cls.args_group_title!r} format"
            if cls.args_group_title and cls.args_list() and
            not cls.disable_args_group else None)

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
        _formats = registry.Registry()

    from .linebase import (
        JsonLinesFormat, CSVFormat, HeaderedCSVFormat, BatchHeaderedCSVFormat)
    from .listbase import SQLFormat, GRPCFormat
    from .idmef import IDMEFFormat, CorrelatedIDMEFFormat, PickledIDMEFFormat

    for fmt in [
            JsonLinesFormat, CSVFormat, HeaderedCSVFormat,
            BatchHeaderedCSVFormat, SQLFormat, GRPCFormat, IDMEFFormat,
            CorrelatedIDMEFFormat, PickledIDMEFFormat]:
        _formats.register(fmt.__title__, fmt)

    from . import ext
    _formats.discover_and_register(ext, BaseFormat)

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


def compatible_formats(args=None, namespace=None):
    """
    Given an arguments list and an argparse namespace (after
    parsing the args), a list of compatible format names will be
    returned (sorted by compatibility weight).
    """
    return [repo.__title__ for repo in
            registry.compatible_repos(
                (format(format_name) for format_name in formats_list()),
                args=args, namespace=namespace)]
