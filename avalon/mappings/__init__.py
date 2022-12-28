#!/usr/bin/env python3

import inspect
import pathlib
import types
import urllib

from .. import models


class Mappings:
    """
    An abstraction for keeping a list of available mappings.
    """
    def __init__(self):
        self._mappings = {}

    def register(self, mapping_name, mapping_class):
        """
        Register a new mapping class.
        """
        self._mappings[mapping_name] = mapping_class

    def mappings_list(self):
        """
        Returns the list of available mappings.
        """
        return list(self._mappings.keys())

    def mapping(self, mapping_name, **kwargs):
        if mapping_name in self._mappings:
            return self._mappings[mapping_name](**kwargs)

        # If the mapping_name is not already registered let's assume
        # it is a URL.
        with urllib.request.urlopen(mapping_name) as response:
            module_src = response.read()

        # Create a python module according to the URL fetched content.
        module_name = pathlib.Path(
            urllib.parse.urlparse(mapping_name).path).stem
        module = types.ModuleType(module_name)
        module.__file__ = mapping_name
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

                return cls(**kwargs)

        raise ValueError(f"No class with a map method found in {mapping_name}")


class BaseMapping:
    """
    A generic parent for the Mappings. Each Mapping is responsible
    for map the output of a Model instance to a new one.
    """
    def __init__(self, **kwargs):
        pass

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

    _mappings.register("jsoncolumn", JsonColumnMapping)
    _mappings.register("int32ix", Int32IxMapping)
    _mappings.register("dttoiso", DtToIsoMapping)
    _mappings.register("dttots", DtToTimestampMapping)
    _mappings.register("rflowproto", RFlowProtoMapping)
    _mappings.register("rflowhello", RFlowHelloGRPCSensorIDMapping)
    _mappings.register("logproto", LogProtoMapping)

    return _mappings


def mappings_list():
    """
    Syntactic suger to get the list of foramts from the mappings
    singleton from get_mappings() method.
    """
    return get_mappings().mappings_list()


def mapping(mapping_name, **kwargs):
    """
    Syntactic suger to get a mapping from the mappings singleton
    from get_mappings() method.
    """
    return get_mappings().mapping(mapping_name, **kwargs)
