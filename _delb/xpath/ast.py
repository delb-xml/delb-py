from __future__ import annotations

from textwrap import indent
from tokenize import TokenInfo
from typing import TYPE_CHECKING, Iterable, Iterator, List, Optional


if TYPE_CHECKING:
    from delb import TagNode


# base classes for nodes


class Node:
    def __eq__(self, other):
        return type(self) is type(other) and vars(self) == vars(other)

    def __repr__(self):
        result = f"{self.__class__.__name__}(\n"
        for name, value in vars(self).items():
            result += f"  {name}="
            if isinstance(value, list):
                result += (
                    "[\n" + "\n".join(indent(repr(x), "    ") for x in value) + "\n]\n"
                )
            else:
                result += f"{value!r}\n"
        result += ")"
        return result


class AggregationNode(Node):
    def evaluate(self, node_set: Iterable[TagNode]) -> Iterator[TagNode]:
        raise NotImplementedError


class FilterNode(Node):
    def evaluate(self, node: TagNode) -> bool:
        raise NotImplementedError


# node classes


class XPathExpression(AggregationNode):
    def __init__(self, location_paths: List[LocationPath]):
        self.location_paths = location_paths

    def evaluate(self, node_set: Iterable[TagNode]) -> Iterator[TagNode]:
        # TODO optimize for one location path
        yielded_nodes: set[int] = set()
        for path in self.location_paths:
            for node in (
                n for n in path.evaluate(node_set) if id(n) not in yielded_nodes
            ):
                yielded_nodes.add(id(node))
                yield node


class LocationPath(AggregationNode):
    def __init__(self, location_steps: List[LocationStep], absolute: bool = False):
        self.location_steps = location_steps
        self.absolute = absolute

    def evaluate(self, node_set: Iterable[TagNode]) -> Iterator[TagNode]:
        result = tuple(node_set)
        for step in self.location_steps:
            result = step.evaluate(result)
        yield from result


class LocationStep(AggregationNode):
    def __init__(self, axis: Axis, name_test: Optional[NameTest]):
        self.axis = axis
        self.name_test = name_test

    def evaluate(self, node_set: Iterable[TagNode]) -> Iterator[TagNode]:
        candidates = self.axis.evaluate(node_set)
        if self.name_test is None:
            raise NotImplementedError
        else:
            yield from (n for n in candidates if self.name_test.evaluate(n))


class Axis(AggregationNode):
    def __init__(self, name: str):
        self.name = name
        assert hasattr(self, self.name)

    def evaluate(self, node_set: Iterable[TagNode]) -> Iterator[TagNode]:
        yield from getattr(self, self.name)(node_set)

    def child(self, node_set: Iterable[TagNode]) -> Iterator[TagNode]:
        for node in node_set:
            yield from node.child_nodes(recurse=False)

    def descendant(self, node_set: Iterable[TagNode]) -> Iterator[TagNode]:
        yielded_nodes: set[int] = set()
        for node in node_set:
            if id(node) in yielded_nodes:
                continue
            for result_item in node.child_nodes(recurse=True):
                yielded_nodes.add(id(result_item))
                yield result_item

    def descendant_or_self(self, node_set: Iterable[TagNode]) -> Iterator[TagNode]:
        yield self
        yield from self.descendant(node_set)

    def self(self, node_set: Iterable[TagNode]) -> Iterator[TagNode]:
        yield from node_set


class NameTest(FilterNode):
    def __init__(self, token: str | TokenInfo):
        # TODO sanitize acc. to XPath

        if isinstance(token, TokenInfo):
            self.pattern = token.string
        else:
            assert isinstance(token, str)
            self.pattern = token

    def evaluate(self, node: TagNode) -> bool:
        return node.local_name == self.pattern
