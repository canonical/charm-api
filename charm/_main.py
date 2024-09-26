import json
import os
import subprocess
import types
import typing


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

    def __delitem__(self, key):
        self.__setitem__(key, None)


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
        return types.MappingProxyType(
            {unit_: self[unit_] for unit_ in self._other_units}
        )

    @property
    def other_app(self) -> typing.Mapping[str, str]:
        # TODO docstring: for peer, this is same as my_app
        return self[self._other_app]


class Endpoint(typing.Collection[Relation]):
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
        return [Relation(id_) for id_ in ids]

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
