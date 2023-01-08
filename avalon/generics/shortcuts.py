import sys

from . import BaseGenericExtension


class ShortcutExtension(BaseGenericExtension):
    __title__ = "shortcuts"

    def post_add_args(self, parser):
        group = parser.add_argument_group(
            title=self.__title__,
            description="Argument shortcuts")
        group.add_argument(
            "--textlog", action="store_true",
            help="Equivalent to --include=msg --format=csv.")

    def post_parse_args(self, args):
        if args.textlog:
            if args.simple_mappings:
                sys.stderr.write(
                    "WARNING: 'simple' mapping arguments will be ignored when "
                    "output format is rawlog.\n")
            if args.output_format and args.output_format != "csv":
                sys.stderr.write(
                    f"WARNING: {args.output_format} output format will be "
                    f"ignored when textlog is specified.\n")

            args.output_format = "csv"
            args.simple_mappings = [{"class": "include", "values": ["msg"]}]
