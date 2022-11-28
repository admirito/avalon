#!/usr/bin/env python3

import inspect
import pkgutil
import time

from ..auxiliary import importall


# Extend __path__ to enable avlaon namespace package extensions
__path__ = pkgutil.extend_path(__path__, __name__)


class Models:
    """
    An abstraction for keeping a list of available models.
    """
    def __init__(self):
        # key: model name
        # value: model class
        self._models = {}

        self._total = None

    def register(self, model_name, model_class):
        """
        Register a new model class.
        """
        self._models[model_name] = model_class

    def models_list(self):
        """
        Returns the list of available models.
        """
        return list(self._models.keys())

    def model(self, model_name, **options):
        """
        Returns an instance of a model that can generate model
        data by calling its next() method.
        """
        return self._models[model_name](**options)


class BaseModel:
    """
    A generic parent for the Models. Each Model is responsible for
    generating data that could be serialized by a Format.
    """
    def __init__(self, **options):
        pass

    def next(self):
        """
        Return the next generated item of the data model.
        """
        raise NotImplementedError


class TestModel(BaseModel):
    """
    A sample model, just for testing.
    """
    _id_counter = 0

    def __init__(self, **options):
        super().__init__(**options)

        self.__class__._id_counter += 1
        self._id = self._id_counter

    def next(self):
        """
        Reutrns data for test
        """
        _ts, _ms = divmod(time.time(), 1)
        return {"_id": f"test{self._id}",
                "_ts": int(_ts),
                "_ms": int(_ms * 1000000)}


class LogModel(BaseModel):
    """
    Log generator
    """
    _id_counter = 0

    def __init__(self):
        super().__init__()

        self.__class__._id_counter += 1
        self._id = self._id_counter

    def next(self):
        pass


def _get_model_tuples(package):
    """
    Given a python package, all the modules inside it will be
    iterated (the modules must be already imported) and every class
    inside each module which is based on BaseModel and has the
    attribute __model_name__ will be selected.

    The result will be a generator of tuples: The __model_name__
    attribute and the class itself.
    """
    for module_name, module in package.__dict__.items():
        for cls_name, cls in getattr(module, "__dict__", {}).items():
            if (inspect.isclass(cls) and issubclass(cls, BaseModel) and
                    hasattr(cls, "__model_name__")):
                yield cls.__model_name__, cls


def get_models():
    """
    Returns a singleton instance of Models class in which all the
    available models are registered.
    """
    global _models

    try:
        return _models
    except NameError:
        _models = Models()

    _models.register("test", TestModel)

    from .rflow import RFlowModel
    _models.register("rflow", RFlowModel)

    from . import log
    from . import ext

    for discovering_package in [log, ext]:
        importall(discovering_package)
        for name, cls in _get_model_tuples(discovering_package):
            _models.register(name, cls)

    return _models


def models_list():
    """
    Syntactic suger to get the list of models from the models
    singleton from get_models() method.
    """
    return get_models().models_list()


def model(model_name, **options):
    """
    Syntactic suger to get a new model instance of the model name
    from the models singleton from get_models() method.
    """
    return get_models().model(model_name, **options)
