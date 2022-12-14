#!/usr/bin/env python3

import csv
import ctypes
import datetime
import io
import itertools
import json
import multiprocessing
import pickle
import socket
import struct
import time
from xml.sax.saxutils import escape as xmlescape

from . import auxiliary


class Formats:
    """
    An abstraction for keeping a list of available formats.
    """
    def __init__(self):
        self._formats = {}

    def register(self, format_name, format_class):
        """
        Register a new format class.
        """
        self._formats[format_name] = format_class

    def formats_list(self):
        """
        Returns the list of available formats.
        """
        return list(self._formats.keys())

    def format(self, format_name, **kwargs):
        return self._formats[format_name](**kwargs)


class BaseFormat:
    """
    A generic parent for the Formats. Each Fromat is responsible
    for serializing the output of a Model instance.

    Options could be passed to the init constructor by keyword
    arguments. The BaseFormat will only store the "filters" option as
    an attribute of the created object.
    """
    class NOTSET:
        pass

    def __init__(self, **kwargs):
        self.filters = kwargs.get("filters", [])
        self.filters_nonexistent_default = self.NOTSET

    def apply_filters(self, model_data):
        """
        """
        if not self.filters:
            return model_data

        return {key: model_data.get(key, self.filters_nonexistent_default)
                for key in self.filters
                if self.filters_nonexistent_default is not self.NOTSET or
                key in self.filters}

    def batch(self, model, size):
        """
        Return a batch with the given `size` by using the given
        model instance.
        """
        raise NotImplementedError


class LineBaseFormat(BaseFormat):
    """
    A generic parent for the Formats that serialize the model
    data, an item per line (separated by new-line character).
    """
    def batch(self, model, size):
        return "\n".join(itertools.chain(
            (self._to_line(self.apply_filters(model.next()))
             for _ in range(size)),
            [""]))  # add a \n to the end of the chain

    def _to_line(self, item):
        raise NotImplementedError


class JsonLinesFormat(LineBaseFormat):
    """
    Serialize data by generating a JSON Object per line.
    """
    def __init__(self, *args, **kwargs):
        super().__init__()

    def _to_line(self, item):
        return json.dumps(item, default=str)


class CSVFormat(LineBaseFormat):
    """
    Serialize data by generating a comma separated values per line.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self._fieldnames = []
        self._fieldnames_set = set()

        if self.filters:
            self._fieldnames = self.filters
            self._fieldnames_set = set(self.filters)

        self.filters_nonexistent_default = ""

    def _to_line(self, item):
        fp = io.StringIO()

        for key in item.keys():
            if not self.filters and key not in self._fieldnames_set:
                self._fieldnames.append(key)
                self._fieldnames_set.add(key)

        writer = csv.DictWriter(fp, self._fieldnames)
        writer.writerow(item)

        return fp.getvalue()[:-1]

    def get_headers(self):
        return list(self._fieldnames)


class BatchHeaderedCSVFormat(CSVFormat):
    """
    Serialize data by generating a comma separated values per line
    and each batch contains header
    """
    def batch(self, model, size):  # every batch can be considered as a file
        """
        Produces headered batches.

        Paremeters:
          - `model`: the data generator model
          - `size`: the batch size

        Returns a headered batch as a string.
        """
        data = super().batch(model, size)
        fp = io.StringIO()
        writer = csv.DictWriter(fp, self.get_headers())
        writer.writeheader()
        return f"{fp.getvalue()}{data}"


class HeaderedCSVFormat(BatchHeaderedCSVFormat):
    """
    Serialize data by generating a comma separated values per line
    and the first batch contains header
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._first = multiprocessing.Value(ctypes.c_bool, True)

    def batch(self, model, size):
        """
        Produces batches for the model. The first batch contains
        header.

        Paremeters:
          - `model`: the data generator model
          - `size`: the batch size

        Returns the data batch as a string.
        """
        with self._first:
            if self._first.value:
                self._first.value = False
                # Use the partent class method which produce a header
                # for the batch
                return super().batch(model, size)

        # Use the grand parent class method witch will not produce the
        # header
        return CSVFormat.batch(self, model, size)


class ListFormat(BaseFormat):
    """
    Serialize data as a Python list
    """
    def batch(self, model, size):
        """
        Call model next method `size` times and return it as a
        list.
        """
        return [self.apply_filters(model.next()) for _ in range(size)]


class SQLFormat(ListFormat):
    """
    Creates SQL insert query values from dictionaries
    """
    pass


class GRPCFormat(ListFormat):
    """
    Creates GRPC batches i.e. a list of dictionaries
    """
    pass


class IDMEFBaseFormat(BaseFormat):
    """
    A Base Format for all the Formats implementing RFC 4765.
    """

    time_id_counter = multiprocessing.Value("i")

    @classmethod
    def _metadata(cls):
        now = time.time()
        ts = int(now)
        ms = int((now % 1) * 1000000)
        dt = datetime.datetime.fromtimestamp(now).astimezone()
        _id = auxiliary.new_oid(ts)

        return {"_id": _id, "_ts": ts, "_ms": ms,
                "timestamp": dt, "isotime": dt.isoformat()}


class IDMEFFormat(LineBaseFormat, IDMEFBaseFormat):
    """
    Serialize data by generating a new-line separated IDMEF (RFC
    4765) XML documents.
    """
    analyzer_node = (
        '<Analyzer analyzerid="avalon" name="avalon" '
        'class="34" model="6">')

    def _to_line(self, item):
        return self._template(item).format_map(self._convert(item))

    def _template(self, keys):
        """
        Given an iteration of keys, this method will return an
        IDMEF template string ready to apply fromat on it to convert
        the template to a valid XML IDMEF.
        """
        metadata = self._metadata()

        parts = [f'<IDMEF-Message><Alert messageid="{metadata["_id"]}">']

        parts += [f"<AnalyzerTime>{metadata['isotime']}</AnalyzerTime>"]

        # CreateTime is a mandatory field in RFC 4765 and we have to
        # add it in all cases
        if "ctime" in keys:
            parts += ["<CreateTime>{ctime}</CreateTime>"]
        else:
            parts += [f"<CreateTime>{metadata['isotime']}</CreateTime>"]

        # Analyzer is a mandatory field, so we add it unconditionally
        parts += [self.analyzer_node]

        if any(i in keys for i in ["aname", "aclass", "amodel", "aid",
                                   "amanufacturer"]):
            attrs = " ".join('{}="{{{}}}"'.format(xmlattr, key)
                             for key, xmlattr in {
                                     "aname": "name",
                                     "aclass": "class",
                                     "amodel": "model",
                                     "aid": "analyzerid",
                                     "amanufacturer": "amanufacturer",
                             }.items() if key in keys)
            parts += [f"<Analyzer {attrs}/>"]

        parts += ["</Analyzer>"]

        # Classification text is mandatory, so we add it in all cases
        if "ident" in keys and "clstext" in keys:
            parts += ['<Classification ident="{ident}" text="{clstext}"/>']
        elif "clstext" in keys:
            parts += ['<Classification text="{clstext}"/>']
        elif "ident" in keys:
            parts += ['<Classification ident="{ident}" text="{ident}"/>']
        else:
            parts += '<Classification text="avalon"/>'

        # Add Assessment node if it is necessary
        if any(i in keys for i in ["severity", "impacttype", "impact"]):
            attrs = " ".join('{}="{{{}}}"'.format(xmlattr, key)
                             for key, xmlattr in {
                                     "severity": "severity",
                                     "impacttype": "type",
                             }.items() if key in keys)
            parts += [f"<Assessment><Impact{' ' + attrs if attrs else ''}>"]
            if "impact" in keys:
                parts += ["{impact}"]
            parts += ["</Impact></Assessment>"]

        # Both Source and Target nodes use the same nodes inside them
        # and _source_target function could be used for both of them.
        def _source_target(ip=None, port=None):
            result = []
            if ip is not None:
                result += ["<Node><Address><address>{{{}}}</address></Address>"
                           "</Node>".format(ip)]
            if port is not None:
                result += ["<Service><port>{{{}}}</port>"
                           "</Service>".format(port)]
            return result

        # Add Source node if it is necessary
        if any(i in keys for i in ["srcip", "srcport"]):
            parts += ["<Source>"] + \
                _source_target(ip="srcip" if "srcip" in keys else None,
                               port="srcport" if "srcport" in keys else None) \
                + ["</Source>"]

        # Add Target node if it is necessary
        if any(i in keys for i in ["dstip", "dstport"]):
            parts += ["<Target>"] + \
                _source_target(ip="dstip" if "dstip" in keys else None,
                               port="dstport" if "dstport" in keys else None) \
                + ["</Target>"]

        # Add CorrelatedAlert if it is necessary
        if any(i in keys for i in ["calertname", "calertidents"]):
            parts += ["<CorrelatedAlert>"]
            if "calertname" in keys:
                parts += ["<name>{calertname}</name>"]
            if "calertidents" in keys:
                # calertidents is a complex object (a list of dicts)
                # and not a string, so it should be handled in
                # _convert method
                parts += ["{calertidents}"]

            parts += ["</CorrelatedAlert>"]

        # All other keys will be added as AdditionalData
        for key in keys:
            if key in ["ctime", "aname", "aclass", "amodel", "aid",
                       "amanufacturer", "severity", "impact", "impacttype",
                       "srcip", "srcport", "dstip", "dstport", "ident",
                       "clstext", "calertname", "calertidents"]:
                continue
            elif key == "msg":
                meaning = "RawLog"
            else:
                meaning = key

            parts += ['<AdditionalData type="string" meaning="{}">'
                      '<string>{{{}}}</string></AdditionalData>'.format(
                          meaning, key)]

        parts += ["</Alert></IDMEF-Message>"]

        return "".join(parts)

    def _convert(self, mapping):
        """
        Returns a copy of the mapping by converting the values in
        it to XML compatible values for IDMEF RFC.
        """
        # Create a shallow copy of the mapping
        mapping = {**mapping}

        # Escape strings to be compatible with XML. We will
        # additionally convert \n to &#10; to make sure each line of
        # the batch only contains a single XML.
        mapping = {key: xmlescape(value, {'"': "&quot;",
                                          "\n": "&#10;"})
                   if isinstance(value, str) else value
                   for key, value in mapping.items()}

        # Convert ctime from timestamp format to iso format as it is
        # required by RFC 4765
        ctime = mapping.get("ctime")
        if ctime:
            mapping["ctime"] = datetime.datetime.fromtimestamp(
                ctime).astimezone().isoformat()

        # Convert srcip and dstip from int format to dot notation
        for ipkey in ["srcip", "dstip"]:
            ip = mapping.get(ipkey)
            if ip and isinstance(ip, int):
                mapping[ipkey] = socket.inet_ntoa(struct.pack("!l", ip))

        # Convert calertidents to appropriate nodes
        mapping["calertidents"] = "".join(
            f'<alertident analyzerid="{aident["aid"]}">'
            f'{aident["ident"]}</alertident>'
            for aident in mapping["calertidents"]
        )

        return mapping


class CorrelatedIDMEFFormat(IDMEFFormat):
    """
    Serialize data just like the IDMEFFormat class but it will add
    a CorrelationAlert Node to all the items.
    """
    analyzer_node = (
        '<Analyzer analyzerid="avalon-correlation" name="avalon-correlation" '
        'class="2">')

    def _to_line(self, item):
        extras = {
            "impacttype": "other",
            "impact": "OtherEvents",
            "calertname": f"Avalon Correlated Alert: {item.get('msg') or '-'}",
            "calertidents": [{"aid": item.get("aid", "1"),
                              "ident": self._metadata()["_id"]}],
        }
        return super()._to_line({**extras, **item})


class PickledIDMEFFormat(IDMEFBaseFormat):
    """
    Serialize data by generating a binary Python pickled list. The
    list will contain tuples of metadata and IDMEF (RFC 4765) list of
    tuples. The IDMEF is a list of tuples which the first item is an
    XPath from IDMEF XML and the second item is its value.
    """

    class PLACEHOLDER:
        pass

    idmef_paths = {
        "ctime": "/Alert/CreateTime",
        "aname": "/Alert/Analyzer/@name",
        "aclass": "/Alert/Analyzer/@class",
        "amodel": "/Alert/Analyzer/@model",
        "aid": "/Alert/Analyzer/@analyzerid",
        "severity": "/Alert/Assessment/Impact/@severity",
        "srcip": "/Alert/Source[]/Node/Address/address",
        "srcport": "/Alert/Source[-1]/Service/port",
        "dstip": "/Alert/Target[]/Node/Address/address",
        "dstport": "/Alert/Target[-1]/Service/port",
        "ident": "/Alert/Classification/@ident",
        "msg": [("/Alert/AdditionalData[]/@type", "string"),
                ("/Alert/AdditionalData[-1]/@meaning", "RawLog"),
                ("/Alert/AdditionalData[-1]/string", PLACEHOLDER)],
        "clstext": "/Alert/Classification/@text",
    }

    def batch(self, model, size):
        """
        Produces binary Python pickled batches.

        Paremeters:
          - `model`: the data generator model
          - `size`: the batch size

        Returns a binary batch in bytes.
        """
        idmef_batch = []

        for _ in range(size):
            idmef = []
            for key, value in model.next().items():
                idmef.extend(self._get_key_value_tuples(key, value))

            metadata = self._metadata()

            idmef_batch.append((metadata, idmef))

        return pickle.dumps(idmef_batch)

    def _get_key_value_tuples(self, key, value):
        tuples = []

        new_key = self.idmef_paths.get(key)
        if new_key is not None:
            if isinstance(new_key, str):
                tuples.append((new_key, value))
            else:
                for tuple_key, tuple_value in new_key:
                    if tuple_value is self.PLACEHOLDER:
                        tuple_value = value
                    tuples.append((tuple_key, tuple_value))
        else:
            tuples.extend([("/Alert/AdditionalData[]/@type", "string"),
                          ("/Alert/AdditionalData[-1]/@meaning", key),
                          ("/Alert/AdditionalData[-1]/string", value)])

        return tuples


def get_formats():
    """
    Returns a singleton instance of Formats class in which all the
    available formats are registered.
    """
    global _formats

    try:
        return _formats
    except NameError:
        _formats = Formats()

    _formats.register("json-lines", JsonLinesFormat)
    _formats.register("csv", CSVFormat)
    _formats.register("headered-csv", HeaderedCSVFormat)
    _formats.register("batch-headered-csv", BatchHeaderedCSVFormat)
    _formats.register("sql", SQLFormat)
    _formats.register("grpc", GRPCFormat)
    _formats.register("idmef", IDMEFFormat)
    _formats.register("correlated-idmef", CorrelatedIDMEFFormat)
    _formats.register("pickled-idmef", PickledIDMEFFormat)

    return _formats


def formats_list():
    """
    Syntactic suger to get the list of foramts from the formats
    singleton from get_formats() method.
    """
    return get_formats().formats_list()


def format(format_name, **kwargs):
    """
    Syntactic suger to get a format from the formats singleton
    from get_formats() method.
    """
    return get_formats().format(format_name, **kwargs)
