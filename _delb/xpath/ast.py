# Copyright (C) 2018-'22  Frank Sachsenheim
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from __future__ import annotations

from functools import wraps
from textwrap import indent
from typing import (
    TYPE_CHECKING,
    cast,
    Any,
    Callable,
    Iterable,
    Iterator,
    List,
    NamedTuple,
    Optional,
)

from _delb.names import Namespaces
from _delb.xpath.functions import xpath_functions
from _delb.utils import _is_node_of_type, last

if TYPE_CHECKING:
    from delb import NodeBase, TagNode


# helper


def ensure_prefix(func):
    @wraps(func)
    def wrapper(self, node, **kwargs):
        prefix = self.prefix

        if "context" in kwargs:
            namespaces = kwargs["context"].namespaces
        else:
            namespaces = kwargs["namespaces"]

        if prefix is not None and prefix not in namespaces:
            # TODO XPathEvaluationError
            raise RuntimeError(
                f"The namespace prefix `{prefix}` is unknown in the the evaluation "
                "context."
            )
        return func(self, node, **kwargs)

    return wrapper


def nested_repr(obj: Any) -> str:
    result = f"{obj.__class__.__name__}(\n"
    for name, value in ((x, getattr(obj, x)) for x in obj.__slots__):
        result += f"  {name}="
        if isinstance(value, Iterable):
            result += (
                "[\n" + "\n".join(indent(repr(x), "    ") for x in value) + "\n]\n"
            )
        else:
            result += f"{value!r}\n"
    result += ")"
    return result


class EvaluationContext(NamedTuple):
    node: NodeBase
    position: int
    size: int
    namespaces: Namespaces


# base classes for nodes


class Node:
    # TODO create one object per definition

    def __eq__(self, other):
        return type(self) is type(other) and all(
            getattr(self, x) == getattr(other, x) for x in self.__slots__
        )

    def __repr__(self):
        return (
            f"{self.__class__.__qualname__}("
            f"{', '.join(f'{x}={getattr(self, x)!r}' for x in self.__slots__)})"
        )


class EvaluationNode(Node):
    def evaluate(self, node: NodeBase, context: EvaluationContext) -> bool:
        raise NotImplementedError


class NodeTestNode(Node):
    def evaluate(self, node: NodeBase, namespaces: Namespaces) -> bool:
        raise NotImplementedError


# aggregators


# TODO unit test
class Axis(Node):
    __slots__ = ("generator",)

    def __init__(self, name: str):
        self.generator = getattr(self, name.replace("-", "_"))

    def __eq__(self, other):
        return (
            isinstance(other, Axis)
            and self.generator.__name__ == other.generator.__name__
        )

    def __repr__(self):
        return f"{self.__class__.__name__}({self.generator.__name__})"

    def ancestor(self, node: NodeBase) -> Iterator[NodeBase]:
        yield from node.ancestors()

    def ancestor_or_self(self, node: NodeBase) -> Iterator[NodeBase]:
        yield node
        yield from node.ancestors()

    def evaluate(self, node: NodeBase, namespaces: Namespaces) -> Iterator[NodeBase]:
        yield from self.generator(node)

    def child(self, node: NodeBase) -> Iterator[NodeBase]:
        yield from node.child_nodes(recurse=False)

    def descendant(self, node: NodeBase) -> Iterator[NodeBase]:
        yield from node.child_nodes(recurse=True)

    def descendant_or_self(self, node: NodeBase) -> Iterator[NodeBase]:
        yield node
        yield from node.child_nodes(recurse=True)

    def following(self, node: NodeBase) -> Iterator[NodeBase]:
        raise NotImplementedError

    def following_sibling(self, node: NodeBase) -> Iterator[NodeBase]:
        yield from node.iterate_next_nodes()

    def parent(self, node: NodeBase) -> Iterator[NodeBase]:
        parent = node.parent
        if parent:
            yield parent

    def preceding(self, node: NodeBase) -> Iterator[NodeBase]:
        raise NotImplementedError

    def preceding_sibling(self, node: NodeBase) -> Iterator[NodeBase]:
        yield from node.iterate_previous_nodes()

    def self(self, node: NodeBase) -> Iterator[NodeBase]:
        yield node


class LocationPath(Node):
    __slots__ = ("absolute", "location_steps", "parent_path")

    def __init__(self, location_steps: Iterable[LocationStep], absolute: bool = False):
        location_steps = tuple(location_steps)
        self.parent_path = (
            LocationPath(location_steps=location_steps[:-1], absolute=absolute)
            if len(location_steps) > 1
            else None
        )
        self.location_steps = location_steps
        self.absolute = absolute

    def __repr__(self):
        return nested_repr(self)

    def evaluate(self, node: NodeBase, namespaces: Namespaces) -> Iterator[NodeBase]:

        if self.parent_path:
            parent_paths_result_generator = self.parent_path.evaluate(
                node=node, namespaces=namespaces
            )
            yield from self.location_steps[-1].evaluate(
                node_set=parent_paths_result_generator, namespaces=namespaces
            )

        elif self.absolute:
            first_node = node
            assert first_node is not None
            root = last(first_node.ancestors()) or first_node
            yield from self.location_steps[0].evaluate(
                node_set=(root,), namespaces=namespaces
            )

        else:
            yield from self.location_steps[0].evaluate(
                node_set=(node,), namespaces=namespaces
            )


class LocationStep(Node):
    __slots__ = ("axis", "node_test", "predicate")

    def __init__(
        self,
        axis: Axis,
        node_test: NodeTestNode,
        predicate: EvaluationNode = None,
    ):
        self.axis = axis
        self.node_test = node_test
        self.predicate = predicate

    def evaluate(
        self, node_set: Iterable[NodeBase], namespaces: Namespaces
    ) -> Iterator[NodeBase]:
        for node in node_set:
            yield from self._evaluate(node=node, namespaces=namespaces)

    def _evaluate(self, node: NodeBase, namespaces: Namespaces) -> Iterator[NodeBase]:
        node_test = self.node_test
        predicate = self.predicate

        # TODO set default_filters per node_test

        if predicate is None:
            yield from (
                n
                for n in self.axis.evaluate(node=node, namespaces=namespaces)
                if node_test.evaluate(node=n, namespaces=namespaces)
            )
            return

        assert isinstance(predicate, EvaluationNode)
        candidates = [
            n
            for n in self.axis.evaluate(node=node, namespaces=namespaces)
            if node_test.evaluate(node=n, namespaces=namespaces)
        ]
        size = len(candidates)
        for position, candidate in enumerate(candidates, start=1):
            if predicate.evaluate(
                node=candidate,
                context=EvaluationContext(
                    node=candidate, position=position, size=size, namespaces=namespaces
                ),
            ):
                yield candidate


class XPathExpression(Node):
    __slots__ = ("location_paths",)

    def __init__(self, location_paths: List[LocationPath]):
        self.location_paths = location_paths

    def __repr__(self):
        return nested_repr(self)

    def evaluate(self, node: NodeBase, namespaces: Namespaces) -> Iterator[NodeBase]:
        yielded_nodes: set[int] = set()
        for path in self.location_paths:
            for result in path.evaluate(node=node, namespaces=namespaces):
                _id = id(result)
                if _id not in yielded_nodes:
                    yielded_nodes.add(_id)
                    yield result


# node tests


class NameMatchTest(NodeTestNode):
    __slots__ = ("local_name", "prefix")

    def __init__(self, prefix: Optional[str], local_name: str):
        self.prefix = prefix
        self.local_name = local_name

    @ensure_prefix
    def evaluate(self, node: NodeBase, namespaces) -> bool:
        if not _is_node_of_type(node, "TagNode"):
            return False
        node = cast("TagNode", node)
        if (self.prefix or None in namespaces) and node.namespace != namespaces.get(
            self.prefix
        ):
            return False
        return node.local_name == self.local_name


class NameStartTest(NodeTestNode):
    __slots__ = ("prefix", "start")

    def __init__(self, prefix: Optional[str], start: str):
        self.prefix = prefix
        self.start = start

    @ensure_prefix
    def evaluate(self, node: NodeBase, namespaces) -> bool:
        if not _is_node_of_type(node, "TagNode"):
            return False
        node = cast("TagNode", node)
        if (self.prefix or None in namespaces) and node.namespace != namespaces.get(
            self.prefix
        ):
            return False
        return node.local_name.startswith(self.start)


class NodeTypeTest(NodeTestNode):
    __slots__ = ("type_name",)

    def __init__(self, type_name: str):
        self.type_name = type_name

    def evaluate(self, node: NodeBase, namespaces) -> bool:
        return _is_node_of_type(node, self.type_name)


# evaluation


class AnyValue(EvaluationNode):
    __slots__ = ("value",)

    def __init__(self, value: Any):
        self.value = value

    def evaluate(self, node: NodeBase, context: EvaluationContext) -> Any:
        return self.value


class AttributeValue(EvaluationNode):
    __slots__ = ("local_name", "prefix")

    def __init__(self, prefix: Optional[str], name: str):
        self.prefix = prefix
        self.local_name = name

    @ensure_prefix
    def evaluate(self, node: NodeBase, context: EvaluationContext) -> Optional[str]:
        if not _is_node_of_type(node, "TagNode"):
            return None
        node = cast("TagNode", node)
        result = node.attributes[
            context.namespaces.get(self.prefix) : self.local_name  # type: ignore
        ]
        return None if result is None else result.value


class BooleanOperator(EvaluationNode):
    __slots__ = ("left", "operator", "right")

    def __init__(
        self,
        operator: Callable,
        left: EvaluationNode,
        right: EvaluationNode,
    ):
        self.operator = operator
        self.left = left
        self.right = right

    def evaluate(self, node: NodeBase, context: EvaluationContext) -> Any:
        return self.operator(
            self.left.evaluate(node=node, context=context),
            self.right.evaluate(node=node, context=context),
        )


class Function(EvaluationNode):
    __slots__ = ("arguments", "function")

    def __init__(self, name: str, arguments: Iterable[EvaluationNode]):
        self.function = xpath_functions[name]
        self.arguments = tuple(arguments)

    def __eq__(self, other):
        return (
            isinstance(other, Function)
            and self.function is other.function
            and self.arguments == other.arguments
        )

    def evaluate(self, node: NodeBase, context: EvaluationContext) -> Any:
        return self.function(
            context, *(x.evaluate(node=node, context=context) for x in self.arguments)
        )


class HasAttribute(EvaluationNode):
    __slots__ = ("local_name", "prefix")

    def __init__(self, prefix: Optional[str], local_name: str):
        self.prefix = prefix
        self.local_name = local_name

    @ensure_prefix
    def evaluate(self, node: NodeBase, context: EvaluationContext) -> bool:
        if not _is_node_of_type(node, "TagNode"):
            return False
        node = cast("TagNode", node)
        return (
            node.attributes[
                context.namespaces.get(self.prefix) : self.local_name  # type: ignore
            ]
            is not None
        )


__all__ = (
    Axis.__name__,
    LocationPath.__name__,
    LocationStep.__name__,
    NameMatchTest.__name__,
    XPathExpression.__name__,
)
