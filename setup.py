#!/usr/bin/env python3

import setuptools

from avalon_build import OrgToRst


with OrgToRst():
    setuptools.setup()
