from __future__ import annotations

from textwrap import indent
from tokenize import TokenInfo
from typing import TYPE_CHECKING, Iterable


if TYPE_CHECKING:
    from delb import TagNode


class Node:
    def __eq__(self, other):
        return type(self) is type(other) and vars(self) == vars(other)

    def __repr__(self):
        result = f"{self.__class__.__name__}(\n"
        for name, value in vars(self).items():
            result += f"  {name}="
            if isinstance(value, list):
                result += "[\n"
                for x in value:
                    result += indent(f"{x!r}\n", "    ")
                result += "]"
            else:
                result += repr(value)
            result += "\n"

        result += ")"
        return result

    def evaluate(self, node_set: Iterable[TagNode]) -> Iterable[TagNode]:
        raise NotImplementedError


class NameTest(Node):
    def __init__(self, token: str | TokenInfo):
        # TODO sanitize acc. to XPath

        if isinstance(token, TokenInfo):
            self.pattern = token.string
        else:
            assert isinstance(token, str)
            self.pattern = token


class LocationStep(Node):
    def __init__(self, name_test: NameTest):
        self.name_test = name_test


class LocationPath(Node):
    def __init__(self, location_steps: Iterable[LocationStep]):
        self.location_steps = location_steps


class XPathExpression(Node):
    def __init__(self, location_paths: Iterable[LocationPath]):
        self.location_paths = location_paths
