import argparse

from . import BaseMapping


class ClassifiedAppendAction(argparse.Action):
    """
    An argparse Action that will append argument values into a list,
    but each item will be appended as a dictionary of the form:
    {"class": "<const_value>", "values": [...]} and all the adjacent
    values of the same <const_value> will be aggregated in the same
    values list.

    Here is an example:

      action = ClassifiedAppendAction
      parser.add_argument(
          "--foo", dest="foobar", const="foo", action=action)
      parser.add_argument(
          "--bar", dest="foobar", const="bar", action=action)
      args = parser.parse_args(
          "--foo a --foo b --bar c --bar d --foo e".split())

      assert args.foobar == [
          {"class": "foo", "values": ["a", "b"]},
          {"class": "bar", "values": ["c", "e"]},
          {"class": "foo", "values": ["e"]},
      ]

    This is useful for consuming arguments in different classes while
    their input order matters.
    """
    def __init__(self, option_strings, dest, **kwargs):
        super().__init__(option_strings, dest, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        dest = getattr(namespace, self.dest)
        if not getattr(dest, "append", None):
            dest = []
            setattr(namespace, self.dest, dest)

        cls = self.const or option_string.lstrip(
            parser.prefix_chars).replace("-", "_")

        last = dest[-1] if dest and isinstance(dest[-1], dict) \
            and isinstance(dest[-1].get("values"), list) else None

        if last and last.get("class") == cls:
            last["values"].append(values)
        else:
            dest.append({"class": cls, "values": [values]})


class SimpleMapping(BaseMapping):
    """
    Uses user provided filters to filter the input
    """

    __title__ = "simple"

    args_mapping = {"simple_mappings": "mappings"}

    # include, exclude, rename

    @classmethod
    def add_arguments(cls, group):
        """
        Add class arguemtns to the argparse group
        """
        group.add_argument(
            "--include", metavar="<keys>", dest="simple_mappings",
            action=ClassifiedAppendAction,
            help="Only the specified <keys> will be included. This option \
            could be repeated or a list of comma separated <keys> could \
            be provieded. The output will use the same order as it is \
            provided here in the command-line so it could be used to set \
            the csv columns order.")
        group.add_argument(
            "--exclude", metavar="<keys>", dest="simple_mappings",
            action=ClassifiedAppendAction,
            help="The specified <keys> will be excluded. This option \
            could be repeated or a list of comma separated <keys> could \
            be provieded.")
        group.add_argument(
            "--rename", metavar="<old_name=new_name>", dest="simple_mappings",
            action=ClassifiedAppendAction,
            help="Rename the specified keys with old_name to new_name. This \
            option could be repeated or a list of comma separated \
            <old_name=new_nam> could be provieded.")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.mappings = self.mappings or []

        for mapping in self.mappings:
            values = [i.split(",") for i in mapping["values"]]
            values = sum(values, [])  # flatten the list

            if mapping["class"] == "rename":
                mapping["values"] = dict((key_val.split("=", 1) * 2)[:2]
                                         for key_val in values)
            else:
                mapping["values"] = set(values)

    def map(self, item):
        for mapping in self.mappings:
            values = mapping["values"]
            if mapping["class"] == "include":
                # We want to keep the order in values, so we have to
                # iterate on it.
                item = {k: item[k] for k in values if k in item}
            elif mapping["class"] == "exclude":
                item = {k: v for k, v in item.items() if k not in values}
            else:  # mapping["class"] == "rename"
                item = {values.get(k, k): v for k, v in item.items()}

        return item
