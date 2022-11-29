#!/usr/bin/env python3

import csv
import ctypes
import io
import itertools
import json
import multiprocessing


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
    def __init__(self, **kwargs):
        self.filters = kwargs.get("filters", [])
        self.filters_nonexistent_default = Ellipsis

    def apply_filters(self, model_data):
        """
        """
        if not self.filters:
            return model_data

        return {key: model_data.get(key, self.filters_nonexistent_default)
                for key in self.filters
                if self.filters_nonexistent_default is not Ellipsis or
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


class SqlFormat(BaseFormat):
    """
    Creates SQL insert query values from dictionaries
    """
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

    def batch(self, model, size):
        return [self.apply_filters(model.next()) for _ in range(size)]


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
    _formats.register("sql", SqlFormat)

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
