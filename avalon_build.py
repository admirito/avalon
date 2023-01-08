"""
Avalon PEP 517 custom build system which calls
setuptools.build_meta but converts README.org to README.rst along the
way.

PiPI `doesn't support Org format:

https://packaging.python.org/en/latest/guides/making-a-pypi-friendly-readme/
"""

import os
import shutil
import subprocess
import sys

import setuptools.build_meta
from setuptools.build_meta import *


def absolute_avalon_url(s):
    return s.replace(
        "<./",
        "<https://github.com/admirito/avalon/blob/master/")


class OrgToRst(object):
    def __init__(self, org_file="README.org", rst_file="README.rst",
                 header_note=True, modifiers=[absolute_avalon_url]):
        self.org_file = org_file
        self.rst_file = rst_file
        self.header_note = header_note
        self.modifiers = modifiers
        self.already_exists = os.path.exists(rst_file)

    def __get_rst_description(self):
        fallback = True
        if shutil.which("pandoc"):
            try:
                proc = subprocess.Popen(["pandoc", "-t", "rst", self.org_file],
                                        stdout=subprocess.PIPE)
                stdout, _ = proc.communicate()
                rst_description = stdout.decode("utf8")
            except OSError:
                sys.stderr.write(
                    f"Warning: Error while converting with {self.org_file} "
                    f"with pandoc.\n"
                    f"         Falling back to literal blocks for the "
                    f"{self.rst_file}.\n")
            else:
                fallback = False
        else:
            sys.stderr.write(
                "Warning: pandoc not found.\n"
                "         In a debian system you can install pandoc with:\n"
                "             sudo apt install pandoc\n"
                "         Falling back to literal blocks for the "
                "{self.rst_file}.\n")

        if fallback:
            with open(self.org_file) as fp:
                org_lines = fp.readlines()

            rst_description = f"::\n\n  {'  '.join(org_lines)}\n"

        for modifier in self.modifiers:
            rst_description = modifier(rst_description)

        return rst_description

    def __enter__(self):
        if not self.already_exists:
            with open(self.rst_file, "w") as fp:
                header_note = (
                    self.header_note if isinstance(self.header_note, str) else
                    f"..\n  This description is automatically generated from "
                    f"{self.org_file} file.\n\n" if self.header_note else "")
                fp.write(f"{header_note}{self.__get_rst_description()}")

    def __exit__(self, type, value, traceback):
        if not self.already_exists:
            os.remove(self.rst_file)


def build_wheel(wheel_directory, config_settings=None,
                metadata_directory=None):
    with OrgToRst():
        return setuptools.build_meta.build_wheel(
            wheel_directory,
            config_settings=config_settings,
            metadata_directory=metadata_directory)


def build_sdist(sdist_directory, config_settings=None):
    with OrgToRst():
        return setuptools.build_meta.build_sdist(
            sdist_directory,
            config_settings=config_settings)
