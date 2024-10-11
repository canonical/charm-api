import collections.abc
import json
import logging
import os
import subprocess
import types
import typing

logger = logging.getLogger(__name__)


class Unit(str):
    @property
    def app(self):
        app_, _ = self.split("/")
        return app_

    @property
    def number(self):
        _, number_ = self.split("/")
        return int(number_)

    def __hash__(self):
        return hash((type(self), super().__hash__()))

    def __repr__(self):
        return f"{type(self).__name__}({repr(str(self))})"

    def __lt__(self, other):
        if not isinstance(other, Unit):
            raise TypeError(
                f"'<' not supported between instances of '{type(self)}' and '{type(other)}'"
            )
        if self.app != other.app:
            raise ValueError(
                f'Unable to compare units with different apps: "{self.app}" and "{other.app}" ("{self}" and "{other}")'
            )
        return self.number < other.number

    def __le__(self, other):
        if not isinstance(other, Unit):
            raise TypeError(
                f"'<=' not supported between instances of '{type(self)}' and '{type(other)}'"
            )
        if self.app != other.app:
            raise ValueError(
                f'Unable to compare units with different apps: "{self.app}" and "{other.app}" ("{self}" and "{other}")'
            )
        return self.number <= other.number

    def __gt__(self, other):
        if not isinstance(other, Unit):
            raise TypeError(
                f"'>' not supported between instances of '{type(self)}' and '{type(other)}'"
            )
        if self.app != other.app:
            raise ValueError(
                f'Unable to compare units with different apps: "{self.app}" and "{other.app}" ("{self}" and "{other}")'
            )
        return self.number > other.number

    def __ge__(self, other):
        if not isinstance(other, Unit):
            raise TypeError(
                f"'>=' not supported between instances of '{type(self)}' and '{type(other)}'"
            )
        if self.app != other.app:
            raise ValueError(
                f'Unable to compare units with different apps: "{self.app}" and "{other.app}" ("{self}" and "{other}")'
            )
        return self.number >= other.number


class _Databag(typing.Mapping[str, str]):
    def __init__(self, *, relation_id: int, unit_or_app: str):
        self._relation_id = relation_id
        self._unit_or_app = unit_or_app

    def __repr__(self):
        return f"{type(self).__name__}(relation_id={self._relation_id}, unit_or_app={repr(self._unit_or_app)})"

    def _command_get(self, *, key: str) -> typing.List[str]:
        """relation-get hook tool command"""
        command = [
            "relation-get",
            "--format",
            "json",
            "--relation",
            str(self._relation_id),
            key,
            self._unit_or_app,
        ]
        if "/" not in self._unit_or_app:
            # `self._unit_or_app` is app
            command.append("--app")
        return command

    def __getitem__(self, key: str) -> str:
        result = json.loads(
            subprocess.run(
                self._command_get(key=key), capture_output=True, check=True, text=True
            ).stdout
        )
        if result is None:
            raise KeyError(key)
        return result

    def __iter__(self):
        result: typing.Dict[str, str] = json.loads(
            subprocess.run(
                self._command_get(key="-"), capture_output=True, check=True, text=True
            ).stdout
        )
        return iter(result.keys())

    def __len__(self):
        result: typing.Dict[str, str] = json.loads(
            subprocess.run(
                self._command_get(key="-"), capture_output=True, check=True, text=True
            ).stdout
        )
        return len(result)


class _WriteableDatabag(_Databag, typing.MutableMapping[str, str]):
    def __setitem__(self, key: str, value: typing.Optional[str]):
        command = ["relation-set", "--relation", str(self._relation_id), "--file", "-"]
        if "/" not in self._unit_or_app:
            # `self._unit_or_app` is app
            command.append("--app")
        subprocess.run(command, input=json.dumps({key: value}), check=True, text=True)
        logger.debug(f"Set {repr(self)}[{repr(key)}] = {repr(value)}")

    def __delitem__(self, key):
        self.__setitem__(key, None)


class _RelationSubset(typing.Mapping[str, typing.Mapping[str, str]]):
    """Lazy loaded read-only mapping for subset of a `Relation`"""

    def __init__(self, *, relation: "Relation", keys: typing.List[str]):
        self._relation = relation
        self._keys = keys

    def __repr__(self):
        return f"{type(self).__name__}(relation={repr(self._relation)}, keys={repr(self._keys)})"

    def __getitem__(self, key):
        if key not in self._keys:
            raise KeyError(key)
        return self._relation[key]

    def __iter__(self):
        return iter(self._keys)

    def __len__(self):
        return len(self._keys)


class Relation(typing.Mapping[str, typing.Mapping[str, str]]):
    @property
    def _other_units(self):
        return [
            Unit(unit_name)
            for unit_name in json.loads(
                subprocess.run(
                    ["relation-list", "--format", "json", "--relation", str(self.id)],
                    capture_output=True,
                    check=True,
                    text=True,
                ).stdout
            )
        ]

    @property
    def _other_app(self) -> str:
        # TODO: make public and rename to other_app_name?
        return json.loads(
            subprocess.run(
                [
                    "relation-list",
                    "--format",
                    "json",
                    "--relation",
                    str(self.id),
                    "--app",
                ],
                capture_output=True,
                check=True,
                text=True,
            ).stdout
        )

    @property
    def _units_and_apps(self) -> typing.Set[str]:
        units_and_apps = {unit()}  # This unit
        if is_leader():
            # In a peer relation, this unit's app will be added later regardless of `is_leader()`
            units_and_apps.add(app())  # This unit's app
        units_and_apps.update(self._other_units)
        # In a peer relation, `self._other_app` is this unit's app
        units_and_apps.add(self._other_app)
        return units_and_apps

    def __init__(self, id_: int, /):
        self._id = id_

    def __eq__(self, other):
        return isinstance(other, Relation) and self.id == other.id

    def __repr__(self):
        return f"{type(self).__name__}({self.id})"

    def __getitem__(self, key):
        if key == unit() or (key == app() and is_leader()):
            return _WriteableDatabag(relation_id=self.id, unit_or_app=key)
        return _Databag(relation_id=self.id, unit_or_app=key)

    def __iter__(self):
        return iter(self._units_and_apps)

    def __len__(self):
        return len(self._units_and_apps)

    @property
    def id(self):
        return self._id

    @property
    def my_unit(self) -> typing.MutableMapping[str, str]:
        return self[unit()]

    # TODO: add setter for my_unit (but don't override databag keys that Juju sets automatically)

    @property
    def my_app(self) -> typing.Mapping[str, str]:
        return self[app()]

    # TODO: add setter for my_app

    @property
    def other_units(self) -> typing.Mapping[Unit, typing.Mapping[str, str]]:
        # TODO docstring: for peer, this is other units. for subordinate, this is only 1 principal unit
        return _RelationSubset(relation=self, keys=self._other_units)

    @property
    def other_app(self) -> typing.Mapping[str, str]:
        # TODO docstring: for peer, this is same as my_app
        return self[self._other_app]


class Endpoint(typing.Collection[Relation]):
    # Convenience for subclasses
    _Relation: typing.Type[Relation] = Relation

    @property
    def _relations(self):
        # Example: ["database:5", "database:6"]
        result: list[str] = json.loads(
            subprocess.run(
                ["relation-ids", "--format", "json", self._name],
                capture_output=True,
                check=True,
                text=True,
            ).stdout
        )
        ids = (int(id_.removeprefix(f"{self._name}:")) for id_ in result)
        return [self._Relation(id_) for id_ in ids]

    def __init__(self, name: str, /):
        self._name = name

    def __eq__(self, other):
        return isinstance(other, Endpoint) and self._name == other._name

    def __repr__(self):
        return f"{type(self).__name__}({repr(self._name)})"

    def __contains__(self, item):
        return item in self._relations

    def __iter__(self):
        return iter(self._relations)

    def __len__(self):
        return len(self._relations)

    @property
    def relation(self) -> typing.Optional[Relation]:
        # TODO docstring: raises error if more than one
        if len(self) > 1:
            raise ValueError(
                f"{len(self)} relations on {repr(self)}. `Endpoint.relation` expects 0 or 1 relations"
            )
        for relation in self:
            return relation


class PeerRelation(Relation):
    @classmethod
    def from_endpoint(
        cls, endpoint: typing.Union[str, Endpoint], /
    ) -> typing.Optional["PeerRelation"]:
        if isinstance(endpoint, str):
            endpoint = Endpoint(endpoint)
        if relation := endpoint.relation:
            return cls(relation.id)

    @property
    def all_units(self) -> typing.Mapping[Unit, typing.Mapping[str, str]]:
        return _RelationSubset(relation=self, keys=[unit(), *self._other_units])


# Do not expose this class publicly (i.e. in top-level __init__.py)
class Config(typing.Mapping[str, typing.Union[str, int, float, bool]]):
    # TODO: add support for secrets
    def __repr__(self):
        return f"{type(self).__name__}()"

    def __getitem__(self, key: str):
        result = json.loads(
            subprocess.run(
                ["config-get", "--format", "json", key],
                capture_output=True,
                check=True,
                text=True,
            ).stdout
        )
        if result is None:
            raise KeyError(key)
        return result

    def __iter__(self):
        result: typing.Dict[str, typing.Union[str, int, float, bool]] = json.loads(
            subprocess.run(
                ["config-get", "--format", "json"],
                capture_output=True,
                check=True,
                text=True,
            ).stdout
        )
        return iter(result.keys())

    def __len__(self):
        result: typing.Dict[str, typing.Union[str, int, float, bool]] = json.loads(
            subprocess.run(
                ["config-get", "--format", "json"],
                capture_output=True,
                check=True,
                text=True,
            ).stdout
        )
        return len(result)


# TODO: add pebble, secret, and storage events
class Event:
    def __repr__(self):
        return f"{type(self).__name__}()"


class ConfigChangedEvent(Event):
    pass


class InstallEvent(Event):
    pass


class LeaderElectedEvent(Event):
    pass


class LeaderSettingsChangedEvent(Event):
    pass


class PostSeriesUpgradeEvent(Event):
    pass


class PreSeriesUpgradeEvent(Event):
    pass


class RemoveEvent(Event):
    pass


class StartEvent(Event):
    pass


class StopEvent(Event):
    pass


class UpdateStatusEvent(Event):
    pass


class UpgradeCharmEvent(Event):
    pass


_ActionResult = typing.Mapping[str, typing.Union[str, "_ActionResult"]]


class ActionEvent(Event):
    @property
    def action(self) -> str:
        return os.environ["JUJU_ACTION_NAME"]

    @property
    def parameters(self) -> collections.abc.Mapping:
        return types.MappingProxyType(
            json.loads(
                subprocess.run(
                    ["action-get", "--format", "json"],
                    capture_output=True,
                    check=True,
                    text=True,
                ).stdout
            )
        )

    @staticmethod
    def log(message: str, /):
        subprocess.run(["action-log", message], check=True)

    @classmethod
    def _flatten(
        cls, old: _ActionResult, *, prefix: str = ""
    ) -> typing.Mapping[str, str]:
        new = {}
        for key, value in old.items():
            if not isinstance(key, str):
                raise TypeError(
                    f"expected key with type 'str', got '{type(key).__name__}': {repr(key)}"
                )
            for invalid_character in (".", "="):
                if invalid_character in key:
                    raise ValueError(
                        f'"{invalid_character}" character not allowed in key: "{key}"'
                    )
            if prefix:
                key = f"{prefix}.{key}"
            if isinstance(value, collections.abc.Mapping):
                new.update(cls._flatten(value, prefix=key))
            elif isinstance(value, str):
                new[key] = value
            else:
                raise TypeError(
                    f"expected value with type 'str' or 'collections.abc.Mapping', got '{type(value).__name__}': {repr(value)}"
                )
        return new

    def _set_result(self, value: _ActionResult, /):
        # TODO docstring: add note about how values are merged if called multiple times
        # TODO docstring: "." and "=" characters not allowed in keys (and other hook tool restrictions)
        # TODO: character limit of shell?
        command = ["action-set"]
        for key, value_ in self._flatten(value).items():
            command.append(f"{key}={value_}")
        subprocess.run(command, check=True)
        logger.debug(f"Set {repr(self)}.result = {repr(value)}")

    result = property(fset=_set_result)

    def fail(self, message: str = None, /):
        command = ["action-fail"]
        if message is not None:
            command.append(message)
        subprocess.run(command, check=True)
        logger.debug(
            f'Called {repr(self)}.fail({repr(message) if message is not None else ""})'
        )


class RelationEvent(Event):
    @property
    def relation(self) -> Relation:
        # Example: "database:5"
        id_ = os.environ["JUJU_RELATION_ID"]
        # Example: 5
        id_ = int(id_.removeprefix(f'{os.environ["JUJU_RELATION"]}:'))
        return Relation(id_)

    @property
    def endpoint(self) -> Endpoint:
        return Endpoint(os.environ["JUJU_RELATION"])


class RelationBrokenEvent(RelationEvent):
    pass


class RelationCreatedEvent(RelationEvent):
    pass


class _RelationUnitEvent(RelationEvent):
    @property
    def remote_unit(self) -> Unit:
        return Unit(os.environ["JUJU_REMOTE_UNIT"])


class RelationChangedEvent(_RelationUnitEvent):
    pass


class RelationDepartedEvent(_RelationUnitEvent):
    @property
    def departing_unit(self) -> Unit:
        return Unit(os.environ["JUJU_DEPARTING_UNIT"])


class RelationJoinedEvent(_RelationUnitEvent):
    pass


class _UnknownEvent(Event):
    """Temporary placeholder while not all Juju events are implemented

    (e.g. pebble, secret, and storage events)
    """


def unit():
    return Unit(os.environ["JUJU_UNIT_NAME"])


def app():
    return unit().app


def is_leader() -> bool:
    return json.loads(
        subprocess.run(
            ["is-leader", "--format", "json"],
            capture_output=True,
            check=True,
            text=True,
        ).stdout
    )


def event() -> Event:
    if os.environ.get("JUJU_ACTION_NAME"):
        return ActionEvent()
    name = os.environ["JUJU_HOOK_NAME"]
    try:
        return _STATICALLY_NAMED_EVENT_TYPES[name]()
    except KeyError:
        pass
    for suffix, type_ in _DYNAMICALLY_NAMED_EVENT_TYPES.items():
        if name.endswith(suffix):
            return type_()
    # TODO: add pebble, secret, and storage events
    return _UnknownEvent()


_STATICALLY_NAMED_EVENT_TYPES: typing.Dict[str, typing.Type[Event]] = {
    "config-changed": ConfigChangedEvent,
    "install": InstallEvent,
    "leader-elected": LeaderElectedEvent,
    "leader-settings-changed": LeaderSettingsChangedEvent,
    "post-series-upgrade": PostSeriesUpgradeEvent,
    "pre-series-upgrade": PreSeriesUpgradeEvent,
    "remove": RemoveEvent,
    "start": StartEvent,
    "stop": StopEvent,
    "update-status": UpdateStatusEvent,
    "upgrade-charm": UpgradeCharmEvent,
}
_DYNAMICALLY_NAMED_EVENT_TYPES: typing.Dict[str, typing.Type[Event]] = {
    "-relation-broken": RelationBrokenEvent,
    "-relation-changed": RelationChangedEvent,
    "-relation-created": RelationCreatedEvent,
    "-relation-departed": RelationDepartedEvent,
    "-relation-joined": RelationJoinedEvent,
}
