#!/usr/bin/env python3

import time


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

    def model(self, model_name):
        """
        Returns an instance of a model that can generate model
        data by calling its next() method.
        """
        return self._models[model_name]()


class BaseModel:
    """
    A generic parent for the Models. Each Model is responsible for
    generating data that could be serialized by a Format.
    """
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

    def __init__(self):
        super().__init__()

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

    return _models


def models_list():
    """
    Syntactic suger to get the list of models from the models
    singleton from get_models() method.
    """
    return get_models().models_list()


def model(model_name):
    """
    Syntactic suger to get a new model instance of the model name
    from the models singleton from get_models() method.
    """
    return get_models().model(model_name)
