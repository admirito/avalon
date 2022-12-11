#!/usr/bin/env python3

import csv
import io
import itertools
import json


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
    """
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
            (self._to_line(model.next()) for _ in range(size)),
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
    def __init__(self, *args, **kwargs):
        super().__init__()
        self._fieldnames = []
        self._fieldnames_set = set()

    def _to_line(self, item):
        fp = io.StringIO()

        for key in item.keys():
            if key not in self._fieldnames_set:
                self._fieldnames.append(key)
                self._fieldnames_set.add(key)

        writer = csv.DictWriter(fp, self._fieldnames)
        writer.writerow(item)

        return fp.getvalue()[:-1]

    def get_headers(self):
        return list(self._fieldnames)



class BatchHeaderedCSVFormat(CSVFormat):
    """
    Serialize data by generating a comma separated values per line and 
    each batch contains header 
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
       
    def batch(self, model, size): # every batch can be considered as a file
        """
        produces headered batches.
        
        @param model is data generator model
        @param size is batch size
        @return a headered batch
        """
        data = super().batch(model, size)
        fp = io.StringIO()
        writer = csv.DictWriter(fp, self.get_headers())
        writer.writeheader()
        return  f"{fp.getvalue()}{data}"


class SqlFormat(BaseFormat):
    """
    Creates SQL insert query values from dictionaries
    """
    def __init__(self, *args, **kwargs) -> None:
        super().__init__()

    def batch(self, model, size):
        return [model.next() for _ in range(size)] 
            

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
