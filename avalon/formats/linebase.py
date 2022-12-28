import csv
import ctypes
import io
import itertools
import json
import multiprocessing

from . import BaseFormat


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
