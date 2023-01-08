import argparse
import multiprocessing
import os
import sys

from . import BaseMedia
from .. import auxiliary


class FileMedia(BaseMedia):
    """
    Initialize keyword options:
     - `file`:  an IO stream with a write method

    Write the data into an IO stream.
    """

    __title__ = "file"

    def __init__(self, max_writers=None, **options):
        super().__init__(max_writers, **options)

        self._lock = self._lock = multiprocessing.Lock()

        if (self.fp.fileno() == sys.stdout.fileno() and
                "b" not in self.fp.mode):
            # This is a workaround for older versions of python (before
            # 3.10) in which the output_file will not be opened as
            # "binary" for stdout by argparse, so we have to do it
            # manually.
            self.fp = os.fdopen(self.fp.fileno(), "wb", closefd=False)

    @classmethod
    def add_arguments(cls, group):
        """
        Add class arguemtns to the argparse group
        """
        super().add_arguments(group)

        group.add_argument(
            "--file-name", metavar="<file>", default="-",
            type=argparse.FileType("wb"), dest="file_fp",
            help="Write output to <file> instead of stdout.")

    def _write(self, batch):
        with self._lock:
            self.fp.write(batch if isinstance(batch, bytes)
                          else batch.encode("utf8"))
            self.fp.flush()


class DirectoryMedia(BaseMedia):
    """
    Initialize keyword options:
     - `directory`: a path to the target directory
     - `suffix`: files suffix
     - `max_file_count`: maximum allowed file count

    Create a new file with specified suffix in directory
    with each call to _write()
    """

    __title__ = "directory"
    args_prefix = "dir_"

    def __init__(self,  max_writers=None, **options):
        self.ordered_mode = False
        self.max_file_count = 0

        super().__init__(max_writers, **options)

        if self.ordered_mode:
            self._index = multiprocessing.Value("l")
            self._oldest_index = multiprocessing.Value("l")
        else:
            self._index = 0
            self._oldest_index = 0
            self._max_file_allowed = int(
                abs(self.max_file_count)
                / self.max_writers) \
                + (1 if self.max_writers > 1 else 0)

    @classmethod
    def add_arguments(cls, group):
        """
        Add class arguemtns to the argparse group
        """
        super().add_arguments(group)

        group.add_argument(
            "--dir-name", metavar="<dir>", default="avalon-output",
            type=str, dest="dir_path",
            help="Determines the directory relative name.")
        group.add_argument(
            "--dir-tmp-name", metavar="<dir>", type=str, dest="dir_tmp_path",
            help="Activate tmp directory and determines the directory \
            relative name. Files are created in this first and then moved \
            (renamed) to the destination directory. this directory and the \
            main directory specified with '--dir-name' should be in same \
            mount point to avoid copy and extra write operation.")
        group.add_argument(
            "--dir-blocking-max-files", action="store_true",
            dest="dir_blocking_enable",
            help="Blocks avalon when directory file count bigger than \
            '--dir-max-files' and wait until some files be deleted by an \
            exteral entity.")
        group.add_argument(
            "--dir-max-files", metavar="<N>", type=int,
            dest="dir_max_file_count", default=0,
            help="Determines maximum file count in directory, old files \
            will be truncated to zero (or remove if value is negative). \
            This value in not accurate and  max count of directory files \
            can be in range [<N>, <N> + writers_count - 1]")
        group.add_argument(
            "--dir-ordered-name", action="store_true", dest="dir_ordered_mode",
            help="Choose name using global index (between avalon writers) \
            and ensures file with lower index is older than biger one. \
            This needs some inter process lock so it has more overhead \
            in compared with 'unordered mode'")
        group.add_argument(
            "--dir-suffix", metavar="<suffix>", type=str,
            help="Determines output files' suffix.")

    def _blocking_max_file(self):
        def _check_files_count():
            return sum(
                1 for i in os.scandir(self.path)
                if i.is_file()
            ) >= abs(self.max_file_count)

        if _check_files_count():
            notifier = auxiliary.DirectoryNotifier(self.path)
            notifier.notify = _check_files_count
            notifier.wait()

    def _remove_or_truncate(self, raw_file_name):
        oldest_file_path = os.path.join(
            self.path, raw_file_name + self.suffix)
        if self.max_file_count > 0:
            with open(oldest_file_path, "w") as f:
                f.truncate(0)
        else:
            os.remove(oldest_file_path)

    def _ordered_get_name_and_remove_truncate_oldest(self):
        with self._index, self._oldest_index:
            curr_file_name = str(self._index.value) + self.suffix
            self._index.value += 1

            if self.max_file_count:
                if not self.blocking_enable:
                    if (self._index.value - self._oldest_index.value >
                            abs(self.max_file_count)):
                        self._remove_or_truncate(str(self._oldest_index.value))
                        self._oldest_index.value += 1
                else:
                    self._blocking_max_file()

        return curr_file_name

    def _unorderd_get_name_and_remove_truncate_oldest(self):
        curr_file_name = str(self._index) \
            + "_" + str(os.getpid()) + self.suffix
        self._index += 1

        if self.max_file_count:
            if not self.blocking_enable:
                if self._index - self._oldest_index > self._max_file_allowed:
                    self._remove_or_truncate(
                        str(self._oldest_index) + "_" + str(os.getpid()))
                    self._oldest_index += 1
            else:
                self._blocking_max_file()

        return curr_file_name

    def _write(self, batch):
        """
        Creates a new file with specified suffix and write the
        batch to it, if count of directory's files exceed from the
        specified value this function removes the oldest file and the
        create it

        @param batch is data should be written to the file

        """
        if self.ordered_mode:
            curr_file_name = \
                self._ordered_get_name_and_remove_truncate_oldest()
        else:
            curr_file_name = \
                self._unorderd_get_name_and_remove_truncate_oldest()

        # TODO: if we want to be ensure that count of directory files never
        # exceed from 'max-files' in 'ordered mode', we should open the file
        # in 'ordered_get_name_and_remove_oldest' under it's lock
        # and write in and close it here, but do we really need this?
        if self.tmp_path:
            curr_file_path = os.path.join(self.tmp_path, curr_file_name)
            with open(curr_file_path, "w") as f:
                f.write(batch)
                os.rename(
                    curr_file_path,
                    os.path.join(self.path, curr_file_name))
        else:
            with open(os.path.join(self.path, curr_file_name), "w") as f:
                f.write(batch)
