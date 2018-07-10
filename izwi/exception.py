from __future__ import unicode_literals


class IzwiException(Exception):
    """Base class for exceptions in this module."""
    pass


class ArgumentException(Exception):
    """Exception in command line argument parsing."""
    pass

class TimeoutException(Exception):
    """Exception in command line argument parsing."""
    pass
