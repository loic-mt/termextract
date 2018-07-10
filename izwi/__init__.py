#!/usr/bin/env python
"""
Izwi - terminology extraction tool
"""
import logging


__all__ = ['IzwiException', 'ArgumentException', 'izwi_main', 'get_izwi_argparser']

__version__ = '0.0.0'
__author__ = 'Loic Dugast'
__author_email__ = "dugasl@unisa.ac.za"

show_progress_bar = True

_logger = logging.getLogger(__name__)


def get_version():
    return __version__

# The public api imports need to be at the end of the file,
# so that the package global names are available to the modules
# when they are imported.

from .cmd import izwi_main, get_izwi_argparser
from .exception import IzwiException, ArgumentException

