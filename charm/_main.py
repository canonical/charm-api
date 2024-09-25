import os


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


def unit():
    return Unit(os.environ["JUJU_UNIT_NAME"])


def app():
    return unit().app
