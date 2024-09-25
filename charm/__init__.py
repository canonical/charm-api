import sys as _sys
import typing as _typing

from . import _status
from ._status import (
    ActiveStatus,
    BlockedStatus,
    MaintenanceStatus,
    Status,
    WaitingStatus,
)


class _ThisModule(_sys.modules[__name__].__class__):
    """Contains properties for this module

    https://stackoverflow.com/a/34829743
    """

    @property
    def unit_status(self):
        return _status.get()

    @unit_status.setter
    def unit_status(self, value: Status):
        _status.set_(value)

    @property
    def app_status(self):
        return _status.get(app=True)

    @app_status.setter
    def app_status(self, value: Status):
        _status.set_(value, app=True)


# TODO: add docstrings
unit_status: _typing.Optional[Status]
"""example docstring"""
# TODO: document that if you set + get unit status you won't see unit status you set (not the case for app status)

app_status: _typing.Optional[Status]

_sys.modules[__name__].__class__ = _ThisModule
