#!/usr/bin/env python3

import argparse
import re
import os
import sys

from . import __version__
from . import formats
from . import generics
from . import mediums
from . import mappings
from . import models
from . import processors


def models_completer(prefix="", action=None, parser=None, parsed_args=None,
                     **kwargs):
    """
    argcomplete's completer for model names according to
    [I]model[R][bB][{mapping,...}] syntax for the postional arguments
    of avalon cli.
    """
    models_list = models.models_list()

    match = re.match(
        r"(?:(\d+))?([A-Za-z_]+)?(?:(\d+))?(?:b(\d+))?(?:{([^}]+))?",
        prefix)

    if not match:
        return models_list

    instances, model_name, ratio, batch_size, mapping_names = match.groups()

    new_prefix = [instances] if instances else []

    if not model_name:
        return [f"{instances or ''}{model}" for model in models_list]
    elif model_name in models_list:
        new_prefix += [model_name]
    elif not ratio and not batch_size and not mapping_names and any(
            i.startswith(model_name) for i in models_list):
        return [f"{instances or ''}{model}" for model in models_list]
    else:
        return []

    new_prefix += [ratio] if ratio else []

    suggestions = ["b"] if ratio and not batch_size and not mapping_names \
        else []

    new_prefix += [f"b{batch_size}"] if batch_size else []

    mappings_list = mappings.mappings_list()

    if mapping_names:
        mapping_tuple = mapping_names.rsplit(",", 1)
        mapping_prefix, new_mapping = \
            (f"{mapping_tuple[0]},", mapping_tuple[1]) \
            if len(mapping_tuple) == 2 else [""] + mapping_tuple

        suggestions += [f"{{{mapping_prefix}{suggestion}}}"
                        for suggestion in mappings_list
                        if suggestion.startswith(new_mapping)]
    else:
        suggestions += [f"{{{mapping}}}" for mapping in mappings_list]

    new_prefix_str = "".join(new_prefix)
    return [f"{new_prefix_str}{suggestion}" for suggestion in suggestions]


def get_mapping_names(model_names):
    """
    Given a list of model name strings in format
    "...{mapping1,mapping2,...} the list of all the mapping names will
    be returned.
    """
    result = []

    for model in model_names:
        match = re.match(r"[^{]*\{(.*)\}", model)
        if match:
            result.extend(match.group(1).split(","))

    return result


def main():
    """
    The main entrypoint for the application
    """
    # Instantiate generic extensions
    # `**generic_class.namespace_to_kwargs(args)` cannot be passed to
    # generic constructor as `args` doesn't exist at this porint!
    generics.instantiate_generics()

    parser = argparse.ArgumentParser(
        description="real-time streaming data generator")

    generics.hook("pre_add_args", parser=parser)

    parser.add_argument(
        "model", nargs="*", metavar="[I]model[R][bB][{mapping,...}]",
        default=["test"],
        help="create 'I' instances from the 'model' data model which should "
        "generate the 'R' ratio from the total output with the 'B' batch size "
        "e.g. '10snort1000b100' which means 10 instances of snort model with "
        "1000 ratio (compared to other instances of models) with batch size "
        "of 100. The data will be generated based on the specified "
        "composition. An optional comma seperated list of mappings inside "
        "braces could also be defined at the end of each expression."
    ).completer = models_completer
    parser.add_argument(
        "--rate", metavar="<N>", type=int, default=sys.maxsize,
        help="Set avarage transfer rate to to <N> items per seconds.")
    parser.add_argument(
        "--duration", metavar="<N>", type=int, default=None,
        help="Set the maximum transfering time to <N> seconds.")
    parser.add_argument(
        "--number", metavar="<N>", type=int, default=100,
        help="Set the maximum number of generated items to <N>.")
    parser.add_argument(
        "--batch-size", metavar="<N>", type=int, default=None,
        help="Set the default batch size to <N>.")
    parser.add_argument(
        "--progress", metavar="<N>", type=int, default=5,
        help="Show the progress every <N> seconds.")
    parser.add_argument(
        "--output-format", choices=formats.formats_list(), default=None,
        help="Set the output format for serialization.")
    parser.add_argument(
        "--output-media", default=None, choices=mediums.mediums_list(),
        help="Set the output media for transferring data.")
    parser.add_argument(
        "--output-writers", metavar="<N>", type=int, default=None,
        help="Limit the maximum number of simultaneous output writers to <N>.")
    parser.add_argument(
        "--media-ignore-errors", action="store_true",
        help="Ignore errors while sending data over media.")
    parser.add_argument(
        "--map", type=str, action="append", dest="mappings", default=[],
        metavar=f"{{{','.join(mappings.mappings_list())},[custom url]}}",
        help="Map the model output with the specified map. This argument "
        "could be used multiple times."
    ).completer = lambda **kwargs: mappings.mappings_list() + ["file:///"]
    parser.add_argument(
        "--list-models", action="store_true",
        help="Print the list of available data models and exit.")
    parser.add_argument(
        "--list-formats", action="store_true",
        help="Print the list of available formats and exit.")
    parser.add_argument(
        "--list-mediums", action="store_true",
        help="Print the list of available mediums and exit.")
    parser.add_argument(
        "--list-mappings", action="store_true",
        help="Print the list of available mappings and exit.")
    parser.add_argument(
        "--list-generics", action="store_true",
        help="Print the list of available generic extensions and exit.")
    parser.add_argument(
        "--completion-script", default=None, metavar="<shell>",
        nargs="?", const="bash", choices=["bash", "tsh", "fish"],
        help="Generate autocompletion script for <shell> and exit.")
    parser.add_argument(
        "--completion-script-executable-name", metavar="<name>",
        default=os.path.basename(sys.argv[0]),
        help="Set the executable name of the completion script to <name>.")
    parser.add_argument(
        "--version", action="store_true",
        help="Print the program version and exit.")

    repo_classes = [
        models.model(model_name) for model_name in models.models_list()
    ] + [
        formats.format(format_name) for format_name in formats.formats_list()
    ] + [
        mediums.media(media_name) for media_name in mediums.mediums_list()
    ] + [
        mappings.mapping(map_name) for map_name in mappings.mappings_list()
    ] + [
        generics.generic(generic_name)
        for generic_name in generics.generics_list()
    ]

    # Add arguments of all the repos to the parser
    for repo_class in repo_classes:
        group = parser.add_argument_group(
            title=repo_class.args_group_title,
            description=repo_class.args_group_description)
        repo_class.add_arguments(group)

    generics.hook("post_add_args", parser=parser)

    try:
        import argcomplete
    except ModuleNotFoundError:
        pass
    else:
        # This method is the entry point to the autocomplete. It must
        # be called after ArgumentParser construction is complete, but
        # before the ArgumentParser.parse_args() method is called.
        # More info:
        # https://github.com/kislyuk/argcomplete#argcompleteautocompleteparser
        argcomplete.autocomplete(parser)

    args = parser.parse_args()

    generics.hook("post_parse_args", args=args)

    if args.version:
        sys.stderr.write(f"Python {sys.version}\nAvalon {__version__}\n")
        exit(0)

    if args.completion_script:
        sys.stdout.write(argcomplete.shellcode(
            [args.completion_script_executable_name],
            shell=args.completion_script))
        exit(0)

    if args.list_models:
        sys.stderr.write("\n".join(models.models_list()))
        sys.stderr.write("\n")
        exit(0)

    if args.list_formats:
        sys.stderr.write("\n".join(formats.formats_list()))
        sys.stderr.write("\n")
        exit(0)

    if args.list_mediums:
        sys.stderr.write("\n".join(mediums.mediums_list()))
        sys.stderr.write("\n")
        exit(0)

    if args.list_mappings:
        sys.stderr.write("\n".join(mappings.mappings_list()))
        sys.stderr.write("\n")
        exit(0)

    if args.list_generics:
        sys.stderr.write("\n".join(generics.generics_list()))
        sys.stderr.write("\n")
        exit(0)

    if args.batch_size is None:
        args.batch_size = min(args.number, 1000)

    if args.output_media is None:
        compat_mediums = mediums.compatible_mediums(namespace=args)
        if not compat_mediums:
            args.output_media = "file"
        else:
            args.output_media = compat_mediums[0]
            if len(compat_mediums) == 1:
                sys.stderr.write(
                    f"NOTE: {args.output_media!r} will be used as output "
                    f"media.\n")
            else:
                sys.stderr.write(
                    f"WARNING: The choice of output media is ambiguous ("
                    f"{', '.join(compat_mediums)}). "
                    f"{args.output_media!r} will be used as output "
                    f"media.\n")

    media_class = mediums.media(args.output_media)

    if args.output_format is None:
        compat_formats = formats.compatible_formats(namespace=args)

        if compat_formats:
            # If there is a compatible format according to input
            # arguments we choose it as the defualt
            if len(compat_formats) == 1:
                args.output_format = compat_formats[0]
                sys.stderr.write(
                    f"NOTE: {args.output_format!r} will be used as output "
                    f"format.\n")
            else:
                args.output_format = (
                    media_class.default_format
                    if media_class.default_format in compat_formats
                    else compat_formats[0])
                sys.stderr.write(
                    f"WARNING: The choice of output format is ambiguous ("
                    f"{', '.join(compat_formats)}). "
                    f"{args.output_format!r} will be used as output "
                    f"format.\n")
        elif media_class.default_format is not None:
            # If there is no compatible format, second choice is the
            # media class default format
            args.output_format = media_class.default_format
            sys.stderr.write(
                f"NOTE: {args.output_format!r} will be used as output "
                f"format.\n")
        else:
            # The ultimate default if other strategies to select the
            # default failed:
            args.output_format = "json-lines"

    format_class = formats.format(args.output_format)
    _format = format_class(**format_class.namespace_to_kwargs(args))

    # Automatically add mappings if they are compatible with the input
    # arguments (i.e. releated arguments of the mappings are present)
    current_mappings = set(get_mapping_names(args.model) + args.mappings)
    compat_mappings = mappings.compatible_mappings(namespace=args)
    new_mappings = [i for i in compat_mappings if i not in current_mappings]
    if new_mappings:
        args.mappings.extend(new_mappings)
        sys.stderr.write(
            f"NOTE: {', '.join(repr(i) for i in new_mappings)} "
            f"mapping{'s' if len(new_mappings) > 1 else ''} will be used.\n")

    batch_generators = []

    for model_str in args.model:
        model_match = re.match(
            r"(?:(\d+))?([A-Za-z_]+)(?:(\d+))?(?:b(\d+))?(?:{([^}]+)})?",
            model_str)
        if not model_match:
            sys.stderr.write(f"Invalid syntax: {model_str}\n")
            exit(1)

        instances, model_name, ratio, batch_size, mapping_names = \
            model_match.groups()
        if model_name not in models.models_list():
            sys.stderr.write(f"Invalid model: {model_name}\n")
            exit(1)

        mapping_names = mapping_names.split(",") if mapping_names else []
        applied_mappings = [mappings.mapping(mapping_name)
                            for mapping_name in mapping_names]
        applied_mappings += [mappings.mapping(mapping_name)
                             for mapping_name in args.mappings]

        instances = int(instances) if instances is not None else 1
        ratio = int(ratio) if ratio is not None else None
        batch_size = (int(batch_size) if batch_size is not None
                      else args.batch_size)

        # All instances together should generate the ratio
        ratio = ratio / instances if ratio is not None else None

        model_class = models.model(model_name)
        model = model_class(**model_class.namespace_to_kwargs(args))

        for mapping_class in applied_mappings:
            mapping = mapping_class(**mapping_class.namespace_to_kwargs(args))

            # let the mappings to access avalon cli arguments
            mapping.avalon_args = args

            model = mapping.map_model(model)

        batch_generators.extend(
            processors.BatchGenerator(
                model,
                _format, batch_size, ratio)
            for _ in range(instances))

    try:
        media = media_class(max_writers=args.output_writers,
                            ignore_errors=args.media_ignore_errors,
                            **media_class.namespace_to_kwargs(args))
    except argparse.ArgumentError as exp:
        parser.error(exp.message)

    processor = processors.Processor(batch_generators, media, args.rate,
                                     args.number, args.duration)

    progress = processors.ProgressReport(processor, args.progress)

    try:
        progress.start()
        processor.process()
    except KeyboardInterrupt:
        processor.stop()
    finally:
        progress.stop()

    progress.print_progress()


if __name__ == "__main__":
    main()
