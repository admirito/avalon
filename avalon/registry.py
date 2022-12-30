import argparse
import sys
import unittest.mock

from .auxiliary import classproperty


class Registry:
    """
    An abstraction for keeping a list of available classes
    e.g. models, formats, etc.
    """
    def __init__(self):
        self._registry = {}

    def register(self, class_name, _class):
        """
        Register a new format class.
        """
        self._registry[class_name] = _class

    def classes_list(self):
        """
        Returns the list of names of available classes.
        """
        return list(self._registry.keys())

    def get_class(self, class_name):
        """
        Returns the class object of a class name
        """
        return self._registry[class_name]


class RequiredValue:
    """
    Defines a value that could be used for marking the argparse
    arguments as required (without really make them required by
    passing required=True). This strategy will let us handle the
    arguments requirement errors more flexibly.
    """
    name = None

    def __init__(self, name=""):
        """
        Arguments:
         - name: the name of the value as a string
        """
        self.name = name

    def __str__(self):
        return f"<RequiredValue: {self.name}>"

    __repr__ = __str__

    def __eq__(self, value):
        return isinstance(value, self.__class__) and self.name == value.name


class BaseRepository:
    """A generic parent for a component class which could define its
    own arguments.

    Class attributes that might be overridden in sub-classes:

    - __title__: The reference key to this repository

    - args_group_title: The title of argparse group

    - args_group_description: The description of argparse group

    - args_prefix: The class attribute `args_prefix`, if set as an
      string, specifies that all the argparse namespace keys with this
      prefix will be used by this class (see namespace_to_kwargs
      description for more details). The default value for
      `args_prefix` is __title__ value with an underscore at its end.

    - args_mapping: If set as a dictionary, specifies extra keys in
      argparse namespace keys that would be used bu this class. The
      values in the mapping will specify the alternative name of the
      key for this class.

    """
    __title__ = ""

    @classproperty
    def args_group_title(cls):
        """
        `args_group_title` class attribute defaults to __title__
        but it can overridden in sub-classes.
        """
        return f"{cls.__title__}" if cls.__title__ else None

    @classproperty
    def args_group_description(cls):
        """
        `args_group_description` class attribute defaults to a
        generic description but it can be overridden in sub-classes.
        """
        return (
            f"Arguments for {cls.args_group_title!r}"
            if cls.args_group_title and cls.default_kwargs() else None)

    args_mapping = None

    @classproperty
    def args_prefix(cls):
        """
        `args_prefix` class attribute defaults to __title__ value
        with an underscore at its end if __title__ is not empty.
        """
        return f"{cls.__title__}_" if cls.__title__ else None

    def __init__(self, **kwargs):
        """
        All the **kwargs compatible with the `default_kwargs`
        class method specification will be added as instance members
        and TypeError will be raised if there is a key not defined by
        the specification.

        The arguments with the value `RequiredValue` will cause an
        argparse.ArgumentError exception.
        """
        default_kwargs = self.default_kwargs()

        required_args = []

        for key, value in {**default_kwargs, **kwargs}.items():
            if key not in default_kwargs:
                raise TypeError(f"got an unexpected keyword argument {key!r}")

            if value is RequiredValue or isinstance(value, RequiredValue):
                required_args.append(value.name or key)
            else:
                setattr(self, key, value)

        if required_args:
            for_title = f" (for {self.__title__!r})" if self.__title__ else ""
            raise argparse.ArgumentError(
                None,
                f"the following arguments are required{for_title}: "
                f"{', '.join(required_args)}")

    @classmethod
    def add_arguments(cls, group):
        """
        This method should be overridden in sub-classes and given
        an argparse group, it has to add the required arguments for
        the repository to that group by calling `group.add_argument`
        method.
        """
        pass

    @classmethod
    def namespace_to_kwargs(cls, namespace):
        """
        Given an argparse namespace this method will extract the
        required key/values for instantiating this class and returns
        them as a dictionary that could be passed to the `__init__`
        method.

        This method first tries to determine the required keys by
        matching the namespace keys with the class attribute
        `args_mapping` i.e. a dictionary/mapping from the keys in the
        namespace to keys for instantiating.

        If a namespace key was not found in the `args_mapping`
        dictionary but it was prefixed with the string in the class
        attribute `args_prefix`, its prefix will be removed and the
        reuslt along side its value will also be added to the result.

        Arguments:
         - namespace: an argparse.Namespace object
        """
        prefix = cls.args_prefix or ""
        mapping = cls.args_mapping or {}

        result = {}

        for key, value in vars(namespace).items():
            if key in mapping:
                result[mapping[key]] = value
            elif key.startswith(prefix):
                # key = key.removeprefix(prefix) in Python 3.9+
                key = key[len(prefix):]

                result[key] = value

        return result

    @classmethod
    def default_kwargs(cls):
        """
        Returns a dictionary with the default kwargs dictionary for
        instantiating the class.

        This method passes a temporary argparse.ArgumentParser to
        `add_arguments` method and passes the output to
        `namespace_to_kwargs` method to determine the results.

        This method does not support arguments with required=True. So,
        it is advised to use `RequiredValue` as the default value for
        the arguments, which later will be catched in the `__init__`
        method, otherwise the sub-classes should override this method.
        """

        def error_handler(message):
            raise argparse.ArgumentError(None, message)

        # for compatibility with Python older versions (< 3.9) we call
        # ArgumentParser without exit_on_error=False argument
        temp_parser = argparse.ArgumentParser()
        temp_parser.error = error_handler

        cls.add_arguments(temp_parser)

        try:
            temp_namespace, _ = temp_parser.parse_known_args([])
        except argparse.ArgumentError:
            temp_namespace = argparse.Namespace()

        return cls.namespace_to_kwargs(temp_namespace)

    @classmethod
    def args_list(cls):
        """
        Returns a list of all the acceptable argparse
        arguments. The list will be determined by calling
        `add_arguments` class on a mock group and analyzing the
        changes on the mock object.
        """
        group = unittest.mock.Mock()
        cls.add_arguments(group)

        args = [call.args for call in group.add_argument.call_args_list]
        args = sum(args, ())  # flatten the list

        return list(args)

    @classmethod
    def check_args_namespace_relation(cls, args=None, namespace=None):
        """
        Given an argparse list of arguments and the result
        Namespace after parsing them, this method will return a
        number that determines if the namespace is related to this
        repository or not. This is useful for automatic selection of
        repository according to arguments.

        The reuslt number will be 0 if there is no relationship and
        higher and higher as the relationship is more strong!

        The default implementation of this method will return `1` if
        it can find at least one argument releated to the class and
        `0` otherwise, but the sub-classes may change this behaviour.
        """
        args = sys.argv[1:] if args is None else args
        namespace = namespace or argparse.Namespace()

        args_list = cls.args_list()

        for arg in args:
            if arg == "--":
                break  # skip positional arguments after --

            if arg.startswith("-"):
                for class_arg in args_list:
                    if arg.startswith(class_arg):
                        return 1  # we have found a matching argument

        kwargs = cls.namespace_to_kwargs(namespace)
        default_kwargs = cls.default_kwargs()

        # If the default arguments are different than the parsed
        # arguments then the namespace probably has provided an
        # argument to modify the default.
        return 1 if kwargs != default_kwargs else 0
