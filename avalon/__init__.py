#!/usr/bin/env python3

import pkgutil


# Extend __path__ to enable avlaon namespace package extensions
__path__ = pkgutil.extend_path(__path__, __name__)

__version__ = "1.0.0"
