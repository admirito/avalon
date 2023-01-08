#!/usr/bin/env python3

import contextlib
import multiprocessing
import pkgutil

from .. import registry
from ..auxiliary import classproperty

# Extend __path__ to enable avlaon namespace package extensions
__path__ = pkgutil.extend_path(__path__, __name__)


class BaseMedia(registry.BaseRepository):
    """
    A generic parent for Media classes. Each Media is responsible
    for transferring serialized batch data through a specific media.
    """
    _semaphores = {}

    default_format = None

    @classproperty
    def args_group_description(cls):
        """
        `args_group_description` class attribute defaults to a
        generic description but it can be overridden in sub-classes.
        """
        return (
            f"Arguments for {cls.args_group_title!r} media"
            if cls.args_group_title and cls.args_list() and
            not cls.disable_args_group else None)

    def __init__(self, max_writers=None, *,
                 ignore_errors=False, **kwargs):
        self._semaphore = (
            contextlib.nullcontext()
            if max_writers is None
            else multiprocessing.Semaphore(max_writers))

        self.ignore_errors = ignore_errors

        super().__init__(**kwargs)

    def write(self, batch):
        """
        Call _write to stream the batch through the meida.
        """
        with self._semaphore:
            try:
                self._write(batch)
            except Exception:
                if not self.ignore_errors:
                    raise

    def _write(self, batch):
        raise NotImplementedError


def get_mediums():
    """
    Returns a singleton instance of Mediums class in which all the
    available mediums are registered.
    """
    global _mediums

    try:
        return _mediums
    except NameError:
        _mediums = registry.Registry()

    from .file import FileMedia, DirectoryMedia
    from .grpc import GRPCMedia
    from .httpbase import SingleHTTPRequestMedia
    from .kafka import KafkaMedia
    from .soap import SOAPMedia
    from .sql import SqlMedia, PsycopgMedia, ClickHouseMedia
    from .syslogbase import SyslogMedia

    for media in [
            FileMedia, DirectoryMedia, GRPCMedia, SingleHTTPRequestMedia,
            KafkaMedia, SOAPMedia, SqlMedia, PsycopgMedia, ClickHouseMedia,
            SyslogMedia]:
        _mediums.register(media.__title__, media)

    from . import ext
    _mediums.discover_and_register(ext, BaseMedia)

    return _mediums


def mediums_list():
    """
    Syntactic suger to get the list of mediums from the mediums
    singleton from get_mediums() method.
    """
    return get_mediums().classes_list()


def media(medium_name):
    """
    Syntactic suger to get a media class from the mediums
    singleton with get_mediums() method.
    """
    return get_mediums().get_class(medium_name)


def compatible_mediums(args=None, namespace=None):
    """
    Given an arguments list and an argparse namespace (after
    parsing the args), a list of compatible media names will be
    returned (sorted by compatibility weight).
    """
    return [repo.__title__ for repo in
            registry.compatible_repos(
                (media(media_name) for media_name in mediums_list()),
                args=args, namespace=namespace)]
