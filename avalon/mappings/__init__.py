#!/usr/bin/env python3

import inspect
import pathlib
import types
import urllib

from .. import models
from ..registry import Registry, BaseRepository


class Mappings(Registry):
    """
    An abstraction for keeping a list of available mappings.

    Just like the parnet class Registry but the `get_class` has been
    overridden so that URLs are also supported.
    """
    def get_class(self, class_name):
        """
        Returns the class object of a class name

        `class_name` could also be a URL in which case the URL will be
        fetched and executed as Python code and its mapping will be
        extracted.
        """
        if class_name in self._registry:
            return self._registry[class_name]

        # If the class_name is not already registered let's assume
        # it is a URL.
        with urllib.request.urlopen(class_name) as response:
            module_src = response.read()

        # Create a python module according to the URL fetched content.
        module_name = pathlib.Path(
            urllib.parse.urlparse(class_name).path).stem
        module = types.ModuleType(module_name)
        module.__file__ = class_name
        # By setting the __package__ on the module, the avalon
        # internals could be relatively imported in the module source
        # code (e.g. from . import mappings)
        module.__package__ = __package__
        exec(module_src, module.__dict__)

        # Find the first class in the module with a "map" method
        for cls_name, cls in inspect.getmembers(module, inspect.isclass):
            if callable(getattr(cls, "map", None)):
                # If cls is not a subclass of BaseMapping we will
                # create a new class and use multiple inheritance to
                # subclass both cls and BaseMapping.
                if not issubclass(cls, BaseMapping):
                    cls = type(f"{cls.__name__}BasedOnBaseMapping",
                               (cls, BaseMapping), {})

                return cls

        raise ValueError(f"No class with a map method found in {class_name}")


class BaseMapping(BaseRepository):
    """
    A generic parent for the Mappings. Each Mapping is responsible
    for map the output of a Model instance to a new one.
    """

    # disable accepting arguments started with __title__
    args_prefix = None

    def map_model(self, model_instance):
        """
        Given a model instance, returns a new instance (besed on a
        new model class) with a "next" method which will call map on
        the generated items.
        """
        def _next(self):
            return self._map(self._original_model.next())

        class_dict = {
            "_original_model": model_instance,
            "_map": self.map,
            "next": _next}

        # create a new model class
        mapped_model_class = type(
            f"Mapped{model_instance.__class__.__name__}",
            (models.BaseModel,), class_dict)

        return mapped_model_class()

    def map(self, item):
        """
        Returns the mapped item. This method should be overridden
        in the subclasses.
        """
        return item


def get_mappings():
    """
    Returns a singleton instance of Mappings class in which all the
    available mappings are registered.
    """
    global _mappings

    try:
        return _mappings
    except NameError:
        _mappings = Mappings()

    from .jsoncolumn import JsonColumnMapping, Int32IxMapping
    from .cast import DtToIsoMapping, DtToTimestampMapping
    from .grpc import (
        RFlowProtoMapping, RFlowHelloGRPCSensorIDMapping, LogProtoMapping)

    for mapping in [JsonColumnMapping, Int32IxMapping, DtToIsoMapping,
                    DtToTimestampMapping, RFlowProtoMapping,
                    RFlowHelloGRPCSensorIDMapping, LogProtoMapping]:
        _mappings.register(mapping.__title__, mapping)

    return _mappings


def mappings_list():
    """
    Syntactic suger to get the list of mappings from the mappings
    singleton from get_mappings() method.
    """
    return get_mappings().classes_list()


def mapping(mapping_name):
    """
    Syntactic suger to get the mapping class from the mappings singleton
    from get_mappings() method.
    """
    return get_mappings().get_class(mapping_name)
