import sys as _sys
import typing as _typing

from . import _main, _status
from ._logging import set_up_logging
from ._main import (
    ActionEvent,
    ConfigChangedEvent,
    Endpoint,
    Event,
    InstallEvent,
    LeaderElectedEvent,
    LeaderSettingsChangedEvent,
    PeerRelation,
    PostSeriesUpgradeEvent,
    PreSeriesUpgradeEvent,
    Relation,
    RelationBrokenEvent,
    RelationChangedEvent,
    RelationCreatedEvent,
    RelationDepartedEvent,
    RelationEvent,
    RelationJoinedEvent,
    RemoveEvent,
    StartEvent,
    StopEvent,
    Unit,
    UpdateStatusEvent,
    UpgradeCharmEvent,
    set_app_workload_version,
)
from ._status import ActiveStatus, BlockedStatus, MaintenanceStatus, Status, WaitingStatus


class _ThisModule(_sys.modules[__name__].__class__):
    """Contains properties for this module

    https://stackoverflow.com/a/34829743
    """

    @property
    def unit(self):
        return _main.unit()

    @property
    def app(self):
        return _main.app()

    @property
    def model(self):
        return _main.model()

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

    @property
    def is_leader(self):
        return _main.is_leader()

    @property
    def config(self):
        return _main._Config()

    @property
    def event(self):
        return _main.event()


unit: Unit
"""The unit that this charm code is running on

https://documentation.ubuntu.com/juju/latest/reference/unit/
"""
app: str
"""This unit's app

https://documentation.ubuntu.com/juju/latest/reference/application/
"""
model: str
"""This unit's model

https://documentation.ubuntu.com/juju/latest/reference/model/
"""
# TODO: document that if you set + get unit status you won't see unit status you set (not the case for app status)
unit_status: _typing.Optional[Status]
"""This unit's status

https://documentation.ubuntu.com/juju/latest/reference/status/
"""
app_status: _typing.Optional[Status]
"""This app's status

https://documentation.ubuntu.com/juju/latest/reference/status/
"""
is_leader: bool
"""Whether this unit is the app's leader

https://documentation.ubuntu.com/juju/latest/reference/unit/#leader-unit
"""
config: _typing.Mapping[str, _typing.Union[str, int, float, bool]]
"""User-specified configuration

https://documentation.ubuntu.com/juju/latest/reference/juju-cli/list-of-juju-cli-commands/config/
"""
event: Event
"""The current Juju event

Also referred to as a "hook"

When the Juju agent on the unit receives an event from the Juju controller, it executes the charm
code. The charm code's process must exit before another event can be processed. The charm code is
re-executed for each Juju event.

https://documentation.ubuntu.com/juju/latest/reference/hook/
"""

_sys.modules[__name__].__class__ = _ThisModule
