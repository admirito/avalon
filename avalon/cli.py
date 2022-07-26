#!/usr/bin/env python3

import argparse
import re
import sys

from . import __version__
from . import formats
from . import mediums
from . import models
from . import processors


def main():
    """
    The main entrypoint for the application
    """
    parser = argparse.ArgumentParser(
        description="real-time streaming data generator")

    parser.add_argument(
        "model", nargs="*", metavar="[I]model[R][bB]", default=["test"],
        help="create 'I' instances from the 'model' data model which should "
        "generate the 'R' ratio from the total output with the 'B' batch size "
        "e.g. '10snort1000b100' which means 10 instances of snort model with "
        "1000 ratio (compared to other instances of models) with batch size "
        "of 100. The data will be generated based on the specified "
        "composition.")
    parser.add_argument(
        "--rate", metavar="<N>", type=int, default=1,
        help="Set avarage transfer rate to to <N> items per seconds.")
    parser.add_argument(
        "--duration", metavar="<N>", type=int, default=None,
        help="Set the maximum transfering time to <N> seconds.")
    parser.add_argument(
        "--number", metavar="<N>", type=int, default=100,
        help="Set the maximum number of generated items to <N>.")
    parser.add_argument(
        "--batch-size", metavar="<N>", type=int, default=1000,
        help="Set the default batch size to <N>.")
    parser.add_argument(
        "--progress", metavar="<N>", type=int, default=5,
        help="Show the progress every <N> seconds.")
    parser.add_argument(
        "--output-format", choices=formats.formats_list(),
        default="json-lines",
        help="Set the output format for serialization.")
    parser.add_argument(
        "--output-media", choices=["file", "http"], default="file",
        help="Set the output media for transferring data.")
    parser.add_argument(
        "--output-writers", metavar="<N>", type=int, default=4,
        help="Limit the maximum number of simultaneous output writers to <N>.")
    parser.add_argument(
        "--output-file-name", metavar="<file>", default="-",
        type=argparse.FileType("w"), dest="output_file",
        help="For file media, write output to <file> instead of stdout.")
    parser.add_argument(
        "--output-http-url", metavar="<url>",
        default="http://localhost:8081/mangolc",
        help="For http media, use <url> to send output.")
    parser.add_argument(
        "--output-http-gzip", action="store_true",
        help="For http media, enable gzip compression.")
    parser.add_argument(
        "--list-models", action="store_true",
        help="Print the list of available data models and exit.")
    parser.add_argument(
        "--version", action="store_true",
        help="Print the program version and exit.")

    args = parser.parse_args()

    if args.version:
        sys.stderr.write(f"Python {sys.version}\nAvalon {__version__}\n")
        exit(0)

    if args.list_models:
        sys.stderr.write("\n".join(models.models_list()))
        sys.stderr.write("\n")
        exit(0)

    _format = formats.format(args.output_format)

    batch_generators = []

    for model_str in args.model:
        model_match = re.match(
            r"(?:(\d+))?([A-Za-z_]+)(?:(\d+))?(?:b(\d+))?",
            model_str)
        if not model_match:
            sys.stderr.write(f"Invalid syntax: {model_str}\n")
            exit(1)

        instances, model_name, ratio, batch_size = model_match.groups()
        if model_name not in models.models_list():
            sys.stderr.write(f"Invalid model: {model_name}\n")
            exit(1)

        instances = int(instances) if instances is not None else 1
        ratio = int(ratio) if ratio is not None else None
        batch_size = (int(batch_size) if batch_size is not None
                      else args.batch_size)

        # All instances together should generate the ratio
        ratio = ratio / instances if ratio is not None else None

        batch_generators.extend(
            processors.BatchGenerator(models.model(model_name), _format,
                                      batch_size, ratio)
            for _ in range(instances))

    if args.output_media == "file":
        media = mediums.FileMedia(
            max_writers=args.output_writers,
            file=args.output_file)
    elif args.output_media == "http":
        media = mediums.SingleHTTPRequest(
            max_writers=args.output_writers,
            url=args.output_http_url,
            gzip=args.output_http_gzip)

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
