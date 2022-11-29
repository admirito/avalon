#!/usr/bin/env python3

import argparse
import re
import os
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
        "--metadata-file", metavar="<file>", type=str,
        default=os.path.join(os.path.dirname(__file__), "models", "rflowdata",
                             "metadata-list.sh"),
        dest="metadata_file_name",
        help="Used with RFlow Model, determines the metadata list file.")
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
        "--output-media",
        choices=["file", "http", "directory", "sql", "psycopg", "clickhouse",
                 "kafka"],
        default="file", help="Set the output media for transferring data.")
    parser.add_argument(
        "--output-writers", metavar="<N>", type=int, default=4,
        help="Limit the maximum number of simultaneous output writers to <N>.")
    parser.add_argument(
        "--filter", metavar="<keys>", type=str, action="append",
        dest="filters", default=[],
        help="Only the specified <keys> will be generated. This option \
        could be repeated or a list of comma separated <keys> should \
        be provieded. The output will use the same order as it is \
        provided here in the command-line so it could be used to set \
        the csv columns order.")
    parser.add_argument(
        "--bootstrap-servers", metavar="<addr>", type=str,
        dest="bootstrap_servers",
        help="used with kafka media, a comma seperated list \
            determines servers addresses.")
    parser.add_argument(
        "--topic", metavar="<t>", type=str, dest="topic",
        help="used with kafka media, determines the topic.")
    parser.add_argument(
        "--force-flush", action='store_true',
        dest="force_flush",
        help="used with kafka media, force to flush kafka producer for \
            each batch, may have bad effect of performance.")
    parser.add_argument(
        "--output-file-name", metavar="<file>", default="-",
        type=argparse.FileType("w"), dest="output_file",
        help="For file media, write output to <file> instead of stdout.")
    parser.add_argument(
        "--dir-name", metavar="<dir>", default="avalon-output",
        type=str, dest="dir_path",
        help="Used with directory media, \
            determines the directory relative name.")
    parser.add_argument(
        "--tmp-dir-name", metavar="<dir>", type=str, dest="tmp_dir_path",
        help="Used with directory media, \
            activate tmp directory and determines the directory relative name.\
             files are created in this first and then moved (renamed) to the \
            destination directory. this directory and the main directory \
            specified with '--dir-name' should be in same mount point \
            to avoid copy and extra write operation.")
    parser.add_argument(
        "--blocking-max-files", action='store_true', 
        dest="dir_blocking_enable",
        help="Used with directory media, \
            blocks avalon when directory file count bigger than '--max-files' \
            and wait until some files be deleted by an exteral entity.")
    parser.add_argument(
        "--max-files", metavar="<N>", type=int, dest="max_file_count",
        default=0,
        help="used with directory media, determines maximum file \
            count in directory, old files will be truncated to zero \
            (or remove if value is negative). this value in not accurate and \
            max count of directory files \
            can be in range [<N>, <N> + instances_count - 1]")
    parser.add_argument(
        "--ordered-name", action='store_true', dest="ordered_mode",
        help="used with directory media, choose name using global \
            index (between avalon instances) and ensures \
            file with lower index is older than biger one. this needs some \
            inter process lock so it has more overhead \
            in compared with 'unordered mode'")
    parser.add_argument(
        "--suffix", metavar="<suffix>", type=str, dest="suffix",
        help="used with directory media, determines output files' suffix.")
    parser.add_argument(
        "--dsn", metavar="<DSN>", type=str, dest="dsn",
        help="used with SQL media, determines database 'Data source name'. \
        this should be in form of 'dialect[+driver]://user:password@host/dbname'")
    parser.add_argument(
        "--table-name", metavar="<tbl>", type=str, dest="table_name",
        help="used with SQL media, determines database table name. \
        this name should contain fields order for exmaple 'tbl (a, b, c)'")
    parser.add_argument(
        "--autocommit", action="store_true", dest="autocommit",
        help="used with SQL media, enables query autocommit\
             (is not valid for psycopg media).")
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

    filters = [i.split(",") for i in args.filters]
    filters = sum(filters, [])  # flatten the list

    _format = formats.format(args.output_format, filters=filters)

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

        models_options = {"metadata_file_name" : args.metadata_file_name}
        batch_generators.extend(
            processors.BatchGenerator(
                models.model(model_name, **models_options),
                _format, batch_size, ratio)
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
    elif args.output_media == "directory":
        media = mediums.DirectoryMedia(
            max_writers=args.output_writers,
            directory=args.dir_path,
            suffix=args.suffix,
            max_file_count=args.max_file_count,
            tmp_dir_path=args.tmp_dir_path,
            dir_blocking_enable=args.dir_blocking_enable,
            ordered_mode=args.ordered_mode,
            instances=instances
        )
    elif args.output_media == "sql":
        media = mediums.SqlMedia(
            max_writers=args.output_writers,
            table_name=args.table_name,
            dsn=args.dsn,
            autocommit=args.autocommit
        )
    elif args.output_media == "psycopg":
        media = mediums.PsycopgMedia(
            max_writers=args.output_writers,
            table_name=args.table_name,
            dsn=args.dsn
        )
    elif args.output_media == "clickhouse":
        media = mediums.ClickHouseMedia(
            max_writers=args.output_writers,
            table_name=args.table_name,
            dsn=args.dsn
        )
    elif args.output_media == "kafka":
        media = mediums.KafkaMedia(
            max_writers=args.output_writers,
            instances=instances,
            bootstrap_servers=args.bootstrap_servers,
            topic=args.topic,
            force_flush=args.force_flush
        )

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
