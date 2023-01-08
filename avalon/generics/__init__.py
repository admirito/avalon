"""
Generics are abstractions for Avalon extensions that are
responsible for doing any general task. They differ from other
abstractions in that they define hooks that are all called regardless
of the user provided arguments.
"""

import pkgutil

from .. import registry

# Extend __path__ to enable avlaon namespace package extensions
__path__ = pkgutil.extend_path(__path__, __name__)

# A list of instances of generic extensions
generic_instances = []


class BaseGenericExtension(registry.BaseRepository):
    """
    A Base class for all the generic extensions.
    """
    def pre_add_args(self, parser):
        pass

    def post_add_args(self, parser):
        pass

    def post_parse_args(self, args):
        pass


def get_generics():
    """
    Returns a singleton instance of Registry class in which all the
    available generics are registered.
    """
    global _generics

    try:
        return _generics
    except NameError:
        _generics = registry.Registry()

    from .shortcuts import ShortcutExtension
    from .modelsargs import GeneralModelsArgumentsExtension

    for gen in [ShortcutExtension, GeneralModelsArgumentsExtension]:
        _generics.register(gen.__title__, gen)

    from . import ext
    _generics.discover_and_register(ext, BaseGenericExtension)

    return _generics


def generics_list():
    """
    Syntactic suger to get the list of generics from the generics
    singleton from get_generics() method.
    """
    return get_generics().classes_list()


def generic(generic_name):
    """
    Syntactic suger to get the generic class from the generics singleton
    from get_generics() method.
    """
    return get_generics().get_class(generic_name)


def instantiate_generics(*args, **kwargs):
    """
    Instantiate all the generics classes retrieved from generics
    singleton and store them in `generic_instances` list in the module
    """
    for generic_name in generics_list():
        generic_class = generic(generic_name)
        generic_instance = generic_class(*args, **kwargs)
        generic_instances.append(generic_instance)


def hook(hook_name, **kwargs):
    """
    Call the specified hook on all the generic instances in the
    `generic_instances` list in the module
    """
    for generic_instance in generic_instances:
        hook = getattr(generic_instance, hook_name)
        hook(**kwargs)
