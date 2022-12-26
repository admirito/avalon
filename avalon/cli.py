#!/usr/bin/env python3

import argparse
import re
import os
import sys

from . import __version__
from . import auxiliary
from . import formats
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


def main():
    """
    The main entrypoint for the application
    """
    parser = argparse.ArgumentParser(
        description="real-time streaming data generator")

    metadata_file_default_path = "/etc/avalon/metadata-list.sh"
    if not os.path.exists(metadata_file_default_path):
        metadata_file_default_path = os.path.join(
            os.path.dirname(__file__), "models", "rflowdata",
            "metadata-list.sh")

    format_group = parser.add_mutually_exclusive_group()

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
        "--metadata-file", metavar="<file>", type=str,
        default=metadata_file_default_path, dest="metadata_file_name",
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
    format_group.add_argument(
        "--output-format", choices=formats.formats_list(),
        default="json-lines",
        help="Set the output format for serialization.")
    parser.add_argument(
        "--output-media", default="file",
        choices=["file", "http", "directory", "sql", "psycopg", "clickhouse",
                 "kafka", "soap", "grpc", "syslog"],
        help="Set the output media for transferring data.")
    parser.add_argument(
        "--output-writers", metavar="<N>", type=int, default=4,
        help="Limit the maximum number of simultaneous output writers to <N>.")
    parser.add_argument(
        "--media-ignore-errors", action="store_true",
        help="Ignore errors while sending data over media.")
    parser.add_argument(
        "--filter", metavar="<keys>", type=str, action="append",
        dest="filters", default=[],
        help="Only the specified <keys> will be generated. This option \
        could be repeated or a list of comma separated <keys> should \
        be provieded. The output will use the same order as it is \
        provided here in the command-line so it could be used to set \
        the csv columns order.")
    parser.add_argument(
        "--map", type=str, action="append", dest="mappings", default=[],
        metavar=f"{{{','.join(mappings.mappings_list())},[custom url]}}",
        help="Map the model output with the specified map. This argument "
        "could be used multiple times."
    ).completer = lambda **kwargs: mappings.mappings_list() + ["file:///"]
    format_group.add_argument(
        "--rawlog", action="store_true",
        help="Equivalent to --filter=msg --format=csv.")
    parser.add_argument(
        "--bootstrap-servers", metavar="<addr>", type=str,
        dest="bootstrap_servers",
        help="used with kafka media, a comma seperated list \
        determines servers addresses.")
    parser.add_argument(
        "--topic", metavar="<t>", type=str, dest="topic",
        help="used with kafka media, determines the topic.")
    parser.add_argument(
        "--force-flush", action="store_true",
        dest="force_flush",
        help="used with kafka media, force to flush kafka producer for \
        each batch, may have bad effect of performance.")
    parser.add_argument(
        "--output-file-name", metavar="<file>", default="-",
        type=argparse.FileType("wb"), dest="output_file",
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
        "--blocking-max-files", action="store_true",
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
        "--ordered-name", action="store_true", dest="ordered_mode",
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
        this should be in form of \
        'dialect[+driver]://user:password@host/dbname'")
    parser.add_argument(
        "--table-name", metavar="<tbl>", type=str, dest="table_name",
        help="used with SQL media, determines database table name. \
        this name should contain fields order for exmaple 'tbl (a, b, c)'")
    parser.add_argument(
        "--autocommit", action="store_true", dest="autocommit",
        help="used with SQL media, enables query autocommit\
             (is not valid for psycopg media).")
    parser.add_argument(
        "--sql-driver-execute", action="store_true",
        help="used with SQL media, enables sqlalchemy native driver execute \
        to improve performance.")
    parser.add_argument(
        "--output-http-url", metavar="<url>",
        default="http://localhost:8081/mangolc",
        help="For http media, use <url> to send output.")
    parser.add_argument(
        "--output-http-gzip", action="store_true",
        help="For http media, enable gzip compression.")
    parser.add_argument(
        "--soap-wsdl-url", metavar="<url>",
        help="For soap media, use WSDL at <url>.")
    parser.add_argument(
        "--soap-location", metavar="<url>",
        help="For soap media, send requests to <url>.")
    parser.add_argument(
        "--soap-method-name", metavar="<name>",
        help="For soap media, use <name> as the name of the method to call.")
    parser.add_argument(
        "--soap-timeout", metavar="<n>", default=10, type=int,
        help="For soap media, use <n> as the timeout value.")
    parser.add_argument(
        "--soap-ignore-errors", action="store_true",
        help="For soap media, if set, ignore all the connection errors.")
    parser.add_argument(
        "--soap-disable-cache", action="store_true",
        help="For soap media, disable envelope caching.")
    parser.add_argument(
        "--grpc-endpoint", metavar="<endpoint>",
        help="For grpc media, send requests to <endpoint>.")
    parser.add_argument(
        "--grpc-method-name", metavar="<fullname>",
        help="For grpc media, use <fullname> as the name of the method to \
        call.")
    parser.add_argument(
        "--grpc-proto", metavar="<file>", type=argparse.FileType("rb"),
        help="For grpc media, Use proto <file> to create grpc stubs instead of \
        using reflection.")
    parser.add_argument(
        "--syslog-address", metavar="<address>", default="/dev/log",
        help="For syslog media, send data to <address>. It could be host:port \
        or path to syslog socket")
    parser.add_argument(
        "--syslog-level", metavar="<level>", default="info",
        choices=["debug", "info", "warn", "error", "fatal"],
        help="For syslog media, set the logging level to <level>.")
    parser.add_argument(
        "--syslog-tag", metavar="<name>", default="avalon",
        help="For syslog media, set the tag to <name>.")
    parser.add_argument(
        "--list-models", action="store_true",
        help="Print the list of available data models and exit.")
    parser.add_argument(
        "--list-mappings", action="store_true",
        help="Print the list of available mappings and exit.")
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

    if args.list_mappings:
        sys.stderr.write("\n".join(mappings.mappings_list()))
        sys.stderr.write("\n")
        exit(0)

    if (args.output_file.fileno() == sys.stdout.fileno() and
            "b" not in args.output_file.mode):
        # This is a workaround for older versions of python (before
        # 3.10) in which the output_file will not be opened as
        # "binary" for stdout by argparse, so we have to do it
        # manually.
        args.output_file = os.fdopen(args.output_file.fileno(), "wb",
                                     closefd=False)

    if args.rawlog:
        if args.filters:
            sys.stderr.write(
                "WARNING: filter argument will be ignored when output format"
                "is rawlog.\n")

        args.output_format = "csv"
        args.filters = ["msg"]

    filters = [i.split(",") for i in args.filters]
    filters = sum(filters, [])  # flatten the list

    dsn_dict = auxiliary.parse_db_url(args.dsn) if args.dsn else {}

    if dsn_dict:
        scheme = dsn_dict.pop("scheme")
        if args.output_media not in ["sql", "psycopg", "clickhouse"]:
            args.output_media = {
                "clickhouse": "clickhouse",
                "postgresql": "psycopg",
            }.get(scheme, "sql")

            sys.stderr.write(
                f"NOTE: Output media changed to '{args.output_media}' "
                f"according to the provided dsn.\n")

    if args.output_media in ["sql", "psycopg", "clickhouse"]:
        if not args.table_name:
            parser.error(
                f"The --table-name argument must be specified if the output "
                f"media is '{args.output_media}'\n")
        if not args.dsn:
            parser.error(
                f"The --dsn argument must be specified if the output "
                f"media is '{args.output_media}'\n")

        if args.output_format != "sql":
            args.output_format = "sql"
            sys.stderr.write(
                f"NOTE: Output format changed to 'sql' because output "
                f"media is '{args.output_media}'\n")

    if args.output_media == "grpc":
        if args.output_format != "grpc":
            args.output_format = "grpc"
            sys.stderr.write(
                "WARNING: Output format changed to 'grpc' because output "
                "media is 'grpc'\n")

    _format = formats.format(args.output_format, filters=filters)

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
        applied_mappings = [mappings.get_mappings().mapping(mapping_name)
                            for mapping_name in mapping_names]
        applied_mappings += [mappings.get_mappings().mapping(mapping_name)
                             for mapping_name in args.mappings]

        instances = int(instances) if instances is not None else 1
        ratio = int(ratio) if ratio is not None else None
        batch_size = (int(batch_size) if batch_size is not None
                      else args.batch_size)

        # All instances together should generate the ratio
        ratio = ratio / instances if ratio is not None else None

        models_options = {"metadata_file_name": args.metadata_file_name}
        model = models.model(model_name, **models_options)

        for mapping in applied_mappings:
            # let the mappings to access avalon cli arguments
            mapping.avalon_args = args

            model = mapping.map_model(model)

        batch_generators.extend(
            processors.BatchGenerator(
                model,
                _format, batch_size, ratio)
            for _ in range(instances))

    common_media_kwargs = {"max_writers": args.output_writers,
                           "ignore_errors": args.media_ignore_errors}

    if args.output_media == "file":
        media = mediums.FileMedia(
            file=args.output_file,
            **common_media_kwargs)
    elif args.output_media == "http":
        media = mediums.SingleHTTPRequest(
            url=args.output_http_url,
            gzip=args.output_http_gzip,
            **common_media_kwargs)
    elif args.output_media == "directory":
        media = mediums.DirectoryMedia(
            directory=args.dir_path,
            suffix=args.suffix,
            max_file_count=args.max_file_count,
            tmp_dir_path=args.tmp_dir_path,
            dir_blocking_enable=args.dir_blocking_enable,
            ordered_mode=args.ordered_mode,
            instances=instances,
            **common_media_kwargs)
    elif args.output_media == "sql":
        media = mediums.SqlMedia(
            table_name=args.table_name,
            dsn=args.dsn,
            autocommit=args.autocommit,
            driver_execute=args.sql_driver_execute,
            **common_media_kwargs)
    elif args.output_media == "psycopg":
        media = mediums.PsycopgMedia(
            table_name=args.table_name,
            dsn=args.dsn,
            **common_media_kwargs)
    elif args.output_media == "clickhouse":
        media = mediums.ClickHouseMedia(
            table_name=args.table_name,
            dsn=dsn_dict or args.dsn,
            **common_media_kwargs)
    elif args.output_media == "kafka":
        media = mediums.KafkaMedia(
            instances=instances,
            bootstrap_servers=args.bootstrap_servers,
            topic=args.topic,
            force_flush=args.force_flush,
            **common_media_kwargs)
    elif args.output_media == "soap":
        if not args.soap_wsdl_url:
            parser.error(
                "The --soap-wsdl-url argument must be specified if the output "
                "media is 'soap'\n")
        if not args.soap_method_name:
            parser.error(
                "The --soap-method-name argument must be specified if the "
                "output media is 'soap'\n")
        if not args.soap_location:
            parser.error(
                "The --soap-location argument must be specified if the output "
                "media is 'soap'\n")

        media = mediums.SOAPMedia(
            wsdl_url=args.soap_wsdl_url,
            method_name=args.soap_method_name,
            location=args.soap_location,
            timeout=args.soap_timeout,
            ignore_errors=args.soap_ignore_errors,
            enable_cache=not args.soap_disable_cache,
            **common_media_kwargs)
    elif args.output_media == "grpc":
        if not args.grpc_endpoint:
            parser.error(
                "The --grpc-endpoint argument must be specified if the output "
                "media is 'grpc'\n")
        if not args.grpc_method_name:
            parser.error(
                "The --grpc-method-name argument must be specified if the "
                "output media is 'grpc'\n")

        media = mediums.GRPCMedia(
            endpoint=args.grpc_endpoint,
            method_name=args.grpc_method_name,
            proto=getattr(args.grpc_proto, "name", None),
            **common_media_kwargs)
    elif args.output_media == "syslog":
        media = mediums.SyslogMedia(
            address=args.syslog_address,
            level=args.syslog_level,
            tag=args.syslog_tag,
            **common_media_kwargs)

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
