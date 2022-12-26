"""
Base class and utilities for template-based modles to generate
logs are defined in this module.
"""

import collections
import os
import random
import socket
import struct
import time

from . import BaseModel
from .rand import choose_in_normal_distribution


class LogTemplateModel(BaseModel):
    """
    Base model class that facilitates sub-classes to generate logs
    according to a set of templates. Each log produced by `next`
    method is a `dict`.

    The sub-class must override the `templates` attribute with a list
    of dictionaries (templates). The `next` method will randomly
    select a template and uses a seed (i.e. a `dict`) to convert the
    template to the concrete value.

    The seed for each template will be created by first calling the
    __seed__ method. The default __seed__ (which could be overridden
    by the sub-classes) will randomly generate common log requirements
    like srcip, srcport, etc.

    The seed object can be later completed by `__seed__` and
    `__instance_seed__` items of the template. First `__seed__` (if
    exists) will be called with old seed as the only argument and then
    `__instance_seed__` (if exists) will be called by passing two
    arguments `self` and the old seed. The result of these calls must
    be a dictionary that will be merged into the old seed.

    The value of each item in the template dictionary will be rendered
    to the concrete value according to its data type:

      - callable: It will be called (with one argument: the seed
        dictionary) and the result will be used as the concrete value.

      - str (or any object with `format` method): The `.format`
        attribute will be called (with **seed as the keyword
        arguments).

      - other types: It will be used as-is.
    """

    templates = []
    enable_default_log_seeds = True

    def _random_ip(self, stddev=100):
        ip_int = choose_in_normal_distribution(
            -2 ** 31, 2 ** 31 - 1, stddev=stddev)
        ip_string = socket.inet_ntoa(struct.pack("!l", ip_int))
        return ip_int, ip_string

    def _random_valid_port(self):
        return random.choices(
            [21, 22, 23, 25, 80, 110, 220, 443],
            weights=[10, 5, 5, 5, 100, 5, 5, 20])[0]

    def _random_port(self, stddev=2, valid_port_probability=0.4):
        return self._random_valid_port() \
            if random.random() < valid_port_probability else \
            choose_in_normal_distribution(1, 32768, stddev=stddev)

    def __seed__(self, seed):
        default = {}

        if self.enable_default_log_seeds:
            # TODO: preserve "aid" value in consecutive executions
            default["ctime"] = time.time()
            default["aid"] = os.getpid()
            default["srcip_int"], default["srcip"] = self._random_ip()
            default["dstip_int"], default["dstip"] = self._random_ip()
            default["srcport"] = self._random_port()
            default["dstport"] = self._random_port()

        return {**seed, **default}

    def next(self):
        """
        Returns a dictionary by randomly selecting a template and
        using the seed value to convert it to a concrete value.
        """
        seed = self.__seed__({})

        # Select an item from templates according to their weights
        template = {**random.choices(self.templates,
                                     weights=self.templates_weights)[0]}

        template_seed = template.pop("__seed__", {})
        if callable(template_seed):
            seed.update(template_seed(seed))
        else:
            seed.update(template_seed)

        template_instance_seed = template.pop("__instance_seed__", {})
        if callable(template_instance_seed):
            seed.update(template_instance_seed(self, seed))
        else:
            seed.update(template_instance_seed)

        result = {key: (value(seed) if callable(value) else
                        value.format(**seed)
                        if callable(getattr(value, "format", None))
                        else value)
                  for key, value in template.items()}

        return result


def log_templates(obj=None, *,
                  # keyword-only arugmets for the decorator
                  default_keys=False, enable_default_log_seeds=None):
    """
    A decorator for LogTemplateModel sub-classed which will update
    the class `templates` attribute.

    A set of default templates useful for logs (srcip, srcport, ...)
    will be added to each template if `default_keys` is True.

    Also all the class attributes started with the prefix "all_" will
    be added to each template (without "all_" prefix).

    A "templates_weights" attribute i.e. a list of weights according
    to "__ratio__" key of each template in templates list will also be
    added to the decorated object and "__ratio__" keys will be removed
    from the template dictionaries.

    The decorator will always preserve a specific order for the items
    of the dictionary (CPython 3.6+).

    The decorator could be called with or without arguments. It will
    call `LogTemplateDecorator` accordingly.

    Optional Keyword Arguments:
     - default_keys:
         if it is a dictionary: it will be used as-is to define the
         default keys and their values.
         if it is a list: the default keys defined in the list will
         be enabled.
         if it is boolean: it contorls whether default keys are
         enabled or not.
     - enable_default_log_seeds: boolean that contorls whether default
       seeds are enabled or not.
    """
    if obj is None:  # decorator is used with arguments
        return LogTemplateDecorator(default_keys, enable_default_log_seeds)
    else:  # decorator is used without arguments
        return LogTemplateDecorator()(obj)


class LogTemplateDecorator:
    """
    This class is used by `log_templates` decorator for
    implementing the decoration. It is usually enough to call
    `log_templates` directly without instantiating this class.
    """

    defaults_base = {
        "ctime": lambda seed: seed["ctime"],
        "aname": None, "aclass": None, "amodel": None, "aid": "{aid}",
        "severity": "low",
        "srcip": lambda seed: seed["srcip_int"],
        "srcport": lambda seed: seed["srcport"],
        "dstip": lambda seed: seed["dstip_int"],
        "dstport": lambda seed: seed["dstport"],
        "ident": None, "msg": None,
    }

    def __init__(self, default_keys=False, enable_default_log_seeds=None):
        self.default_keys = (
            default_keys if isinstance(default_keys, collections.abc.Mapping)
            else {k: v for k, v in self.defaults_base if k in default_keys}
            if isinstance(default_keys, collections.abc.Iterable) else
            self.defaults_base if default_keys else {})

        self.enable_default_log_seeds = enable_default_log_seeds

    def __call__(self, obj):
        for template in obj.templates:
            defaults = {}

            # Add dunder magic attirbutes in the beginning of the
            # dictionary
            for attr in ["__ratio__", "__seed__"]:
                if attr in template:
                    defaults[attr] = None

            defaults.update(self.default_keys)

            for attr, value in obj.__dict__.items():
                if attr.startswith("all_"):
                    defaults[attr[4:]] = value

            defaults.update(template)

            # To change order in Python 3.6+ dictionaries
            template.clear()
            template.update(defaults)

        obj.templates_weights = [template.pop("__ratio__", 1)
                                 for template in obj.templates]

        if self.enable_default_log_seeds is not None:
            obj.enable_default_log_seeds = self.enable_default_log_seeds

        return obj
