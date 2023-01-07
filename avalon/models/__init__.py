#!/usr/bin/env python3

import pkgutil
import time

from .. import registry
from ..auxiliary import classproperty

# Extend __path__ to enable avlaon namespace package extensions
__path__ = pkgutil.extend_path(__path__, __name__)


class BaseModel(registry.BaseRepository):
    """
    A generic parent for the Models. Each Model is responsible for
    generating data that could be serialized by a Format.
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
            f"Arguments for {cls.args_group_title!r} model"
            if cls.args_group_title and cls.args_list() and
            not cls.disable_args_group else None)

    def next(self):
        """
        Return the next generated item of the data model.
        """
        raise NotImplementedError


class TestModel(BaseModel):
    """
    A sample model, just for testing.
    """

    __title__ = "test"

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


def get_models():
    """
    Returns a singleton instance of Models class in which all the
    available models are registered.
    """
    global _models

    try:
        return _models
    except NameError:
        _models = registry.Registry()

    _models.register(TestModel.__title__, TestModel)

    from .rflow import RFlowModel
    _models.register(RFlowModel.__title__, RFlowModel)

    from . import log
    from . import ext

    _models.discover_and_register(log, BaseModel)
    _models.unregister("_template_model_")

    _models.discover_and_register(ext, BaseModel)

    return _models


def models_list():
    """
    Syntactic suger to get the list of models from the models
    singleton from get_models() method.
    """
    return get_models().classes_list()


def model(model_name):
    """
    Syntactic suger to get the model class for the model name
    from the models singleton from get_models() method.
    """
    return get_models().get_class(model_name)
