import abc
import json
import subprocess
import typing


class _String(str, abc.ABC):
    # Inherit from `str` instead of `collections.UserString` for immutability

    def __eq__(self, other):
        return isinstance(other, type(self)) and super().__eq__(other)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash((type(self), super().__hash__()))

    def __repr__(self):
        return f"{type(self).__name__}({self})"

    def __getitem__(self, index):
        return type(self)(str(self)[index])

    def __iter__(self):
        return (type(self)(item) for item in super().__iter__())

    def __add__(self, other):
        return type(self)(str(self) + str(other))

    def __radd__(self, other):
        return type(self)(str(other) + str(self))

    def __mul__(self, n):
        return type(self)(str(self) * n)

    __rmul__ = __mul__

    def __mod__(self, args):
        return type(self)(str(self) % args)

    def __rmod__(self, template):
        return type(self)(str(template) % str(self))

    def __getattribute__(self, name):
        # May be bypassed for special methods (e.g. __add__)
        # (https://docs.python.org/3/reference/datamodel.html#object.__getattribute__)

        if (
            # Not a `str` method
            name not in dir(str)
            # Special attribute (needed for `__class__` and `__ne__`)
            or (name.startswith("__") and name.endswith("__"))
        ):
            return super().__getattribute__(name)

        def cast(value, method_name):
            if isinstance(value, str):
                return type(self)(value)
            if isinstance(value, int):  # Includes `bool`
                return value
            if isinstance(value, bytes):
                return value
            if isinstance(value, list):
                return [cast(item, method_name) for item in value]
            if isinstance(value, tuple):
                return tuple(cast(item, method_name) for item in value)
            if method_name == "maketrans":
                return value
            raise NotImplementedError(
                f"Unsupported override for {method_name=}. Please file a bug report"
            )

        def wrapper_method(self, *args, **kwargs):
            original_method = getattr(super(), name)
            return_value = original_method(*args, **kwargs)
            return cast(return_value, name)

        # Bind method to instance
        return wrapper_method.__get__(self)


class Status(_String, abc.ABC):
    @property
    @abc.abstractmethod
    def _PRIORITY(self) -> int:
        """Higher number status takes priority"""

    def __lt__(self, other):
        if not isinstance(other, Status):
            raise TypeError(
                f"'<' not supported between instances of '{type(self)}' and '{type(other)}'"
            )
        if self._PRIORITY == other._PRIORITY:
            return super().__lt__(other)
        if self._PRIORITY < other._PRIORITY:
            return True
        return False

    def __le__(self, other):
        if not isinstance(other, Status):
            raise TypeError(
                f"'<=' not supported between instances of '{type(self)}' and '{type(other)}'"
            )
        if self._PRIORITY == other._PRIORITY:
            return super().__le__(other)
        if self._PRIORITY <= other._PRIORITY:
            return True
        return False

    def __gt__(self, other):
        if not isinstance(other, Status):
            raise TypeError(
                f"'>' not supported between instances of '{type(self)}' and '{type(other)}'"
            )
        if self._PRIORITY == other._PRIORITY:
            return super().__gt__(other)
        if self._PRIORITY > other._PRIORITY:
            return True
        return False

    def __ge__(self, other):
        if not isinstance(other, Status):
            raise TypeError(
                f"'>=' not supported between instances of '{type(self)}' and '{type(other)}'"
            )
        if self._PRIORITY == other._PRIORITY:
            return super().__ge__(other)
        if self._PRIORITY >= other._PRIORITY:
            return True
        return False


class ActiveStatus(Status):
    _PRIORITY = 0


class WaitingStatus(Status):
    _PRIORITY = 1


class MaintenanceStatus(Status):
    _PRIORITY = 2


class BlockedStatus(Status):
    _PRIORITY = 3


_STATUS_CODES: dict[type[Status], str] = {
    ActiveStatus: "active",
    WaitingStatus: "waiting",
    MaintenanceStatus: "maintenance",
    BlockedStatus: "blocked",
}


def get(*, app=False) -> typing.Optional[Status]:
    command = ["status-get", "--include-data" "--format", "json"]
    if app:
        command.append("--application")
    result = json.loads(subprocess.run(command, check=True, capture_output=True).stdout)
    status_types: dict[str, type[Status]] = {
        code: status for status, code in _STATUS_CODES.items()
    }
    if status_type := status_types.get(result["status"]):
        return status_type(result["message"])


def set_(value: Status, *, app=False):
    command = ["status-set", _STATUS_CODES[type(value)], str(value)]
    if app:
        command.append("--application")
    subprocess.run(command, check=True)
