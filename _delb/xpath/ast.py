# Copyright (C) 2018-'25  Frank Sachsenheim
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

import inspect
import operator
from collections.abc import Callable, Iterable, Iterator, Sequence
from functools import cached_property, wraps
from textwrap import indent
from typing import TYPE_CHECKING, cast, Any, NamedTuple, Optional


from _delb.exceptions import InvalidCodePath, XPathEvaluationError, XPathParsingError
from _delb.plugins import plugin_manager as _plugin_manager
from _delb.utils import _is_node_of_type


if TYPE_CHECKING:
    from typing import Final
    from _delb.names import Namespaces
    from _delb.nodes import NodeBase, ProcessingInstructionNode, TagNode
    from _delb.typing import NodeTypeNameLiteral


xpath_functions: Final = _plugin_manager.xpath_functions


# helper


class _DocumentNode:
    """
    This class mimics enough behaviour of a node to act as item in a node set for
    evaluation of absolute location paths.
    It represents what is defined as "root node" in `section 5.1`_ of the XPath 1.0
    specs, which is not the same as :attr:`Document.root`. It's a structural equivalent
    of the :class:`Document` class and used solely for the evaluation of XPath
    expressions.

    .. _section 5.1: https://www.w3.org/TR/1999/REC-xpath-19991116/#root-node
    """

    __slots__ = ("__root_node",)

    def __init__(self, node: NodeBase):
        while node.parent is not None:
            node = node.parent
        self.__root_node = node

    def iterate_descendants(self, *args) -> Iterator[NodeBase]:
        yield self.__root_node
        yield from self.__root_node.iterate_descendants(*args)

    def iterate_children(self, *args) -> Iterator[NodeBase]:
        yield self.__root_node


def ensure_prefix(func):
    @wraps(func)
    def wrapper(self, node, **kwargs):
        prefix = self.prefix

        if "context" in kwargs:
            namespaces = kwargs["context"].namespaces
        else:
            namespaces = kwargs["namespaces"]

        if prefix is not None and prefix not in namespaces:
            raise XPathEvaluationError(
                f"The namespace prefix `{prefix}` is unknown in the evaluation "
                "context."
            )
        return func(self, node, **kwargs)

    return wrapper


def nested_repr(obj: Any) -> str:  # pragma: no cover
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


# structs


class EvaluationContext(NamedTuple):
    """
    Instances of this class are passed to XPath functions in order to pass contextual
    information.
    """

    node: NodeBase
    """ The node that is evaluated. """
    position: int
    """
    The node's position within all nodes that matched a location step's node test in
    order of the step's axis' direction. The first position is 1.
    """
    size: int
    """ The number of all nodes that matched a location step's node test. """
    namespaces: Namespaces
    """ A mapping of prefixes to namespaces that is used in the whole evaluation. """


# base classes for nodes


class Node:
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

    @property
    def _derived_attributes(self):
        raise InvalidCodePath

    def _is_unambiguously_locatable(self) -> bool:
        return False


class NodeTestNode(Node):
    def evaluate(self, node: NodeBase, namespaces: Namespaces) -> bool:
        raise NotImplementedError


# aggregators


class Axis(Node):
    __slots__ = ("generator",)

    def __init__(self, name: str):
        generator = getattr(self, name.replace("-", "_"), None)
        if generator is None:
            raise XPathParsingError(message="Invalid axis specifier.")
        self.generator = generator

    def __eq__(self, other):
        return (
            isinstance(other, Axis)
            and self.generator.__name__ == other.generator.__name__
        )

    def __repr__(self):
        return f"{self.__class__.__name__}({self.generator.__name__})"

    def ancestor(self, node: NodeBase) -> Iterator[_DocumentNode | NodeBase]:
        yield from node.iterate_ancestors()
        yield _DocumentNode(node)

    def ancestor_or_self(self, node: NodeBase) -> Iterator[_DocumentNode | NodeBase]:
        yield node
        yield from node.iterate_ancestors()
        yield _DocumentNode(node)

    def evaluate(
        self, node: _DocumentNode | NodeBase, namespaces: Namespaces
    ) -> Iterator[NodeBase]:
        yield from self.generator(node)

    def child(self, node: NodeBase) -> Iterator[NodeBase]:
        yield from node.iterate_children()

    def descendant(self, node: NodeBase) -> Iterator[NodeBase]:
        yield from node.iterate_descendants()

    def descendant_or_self(self, node: NodeBase) -> Iterator[NodeBase]:
        yield node
        yield from node.iterate_descendants()

    def following(self, node: NodeBase) -> Iterator[NodeBase]:
        yield from node.iterate_following()

    def following_sibling(self, node: NodeBase) -> Iterator[NodeBase]:
        yield from node.iterate_following_siblings()

    def parent(self, node: NodeBase) -> Iterator[_DocumentNode | NodeBase]:
        parent = node.parent
        if parent:
            yield parent
        else:
            yield _DocumentNode(node)

    def preceding(self, node: NodeBase) -> Iterator[NodeBase]:
        yield from node.iterate_preceding()

    def preceding_sibling(self, node: NodeBase) -> Iterator[NodeBase]:
        yield from node.iterate_preceding_siblings()

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
            yield from self.location_steps[-1].evaluate(
                node_set=self.parent_path.evaluate(node=node, namespaces=namespaces),
                namespaces=namespaces,
            )

        else:
            node_set: Iterable[_DocumentNode | NodeBase]
            if self.absolute:
                node_set = (_DocumentNode(node),)
            else:
                node_set = (node,)

            yield from self.location_steps[0].evaluate(
                node_set=node_set, namespaces=namespaces
            )

    def _is_unambiguously_locatable(self) -> bool:
        return all(s._is_unambiguously_locatable() for s in self.location_steps)


class LocationStep(Node):
    __slots__ = ("axis", "node_test", "predicates")

    def __init__(
        self,
        axis: Axis,
        node_test: NodeTestNode,
        predicates: Sequence[EvaluationNode] = (),
    ):
        self.axis = axis
        self.node_test = node_test
        self.predicates = tuple(predicates)

    @cached_property
    def _anders_predicates(self) -> BooleanOperator:
        right = self.predicates[-1]
        for predicate in self.predicates[-2::-1]:
            right = BooleanOperator(operator=operator.and_, left=predicate, right=right)
        assert isinstance(right, BooleanOperator)
        return right

    @cached_property
    def _derived_attributes(self) -> list[tuple[str, str, str]]:
        predicates_count = len(self.predicates)
        if predicates_count == 0:
            return []
        elif predicates_count == 1:
            return self.predicates[0]._derived_attributes
        else:
            return self._anders_predicates._derived_attributes

    def evaluate(
        self, node_set: Iterable[_DocumentNode | NodeBase], namespaces: Namespaces
    ) -> Iterator[NodeBase]:
        yielded_nodes = set()
        for node in node_set:
            for result_node in self._evaluate(node=node, namespaces=namespaces):
                _id = id(result_node)
                if _id not in yielded_nodes:
                    yielded_nodes.add(_id)
                    yield result_node

    def _evaluate(
        self, node: _DocumentNode | NodeBase, namespaces: Namespaces
    ) -> Sequence[NodeBase]:
        node_test = self.node_test
        predicates = self.predicates

        if not predicates:
            return tuple(
                n
                for n in self.axis.evaluate(node=node, namespaces=namespaces)
                if node_test.evaluate(node=n, namespaces=namespaces)
            )

        candidates = [
            n
            for n in self.axis.evaluate(node=node, namespaces=namespaces)
            if node_test.evaluate(node=n, namespaces=namespaces)
        ]
        for predicate in predicates:
            size = len(candidates)
            next_candidates = []
            for position, candidate in enumerate(candidates, start=1):
                if predicate.evaluate(
                    node=candidate,
                    context=EvaluationContext(
                        node=candidate,
                        position=position,
                        size=size,
                        namespaces=namespaces,
                    ),
                ):
                    next_candidates.append(candidate)
            candidates = next_candidates

        return candidates

    def _is_unambiguously_locatable(self) -> bool:
        if not (
            self.axis.generator.__name__ == "child"
            and isinstance(self.node_test, NameMatchTest)
        ):
            return False

        predicates_count = len(self.predicates)
        if predicates_count == 0:
            return True
        elif predicates_count == 1:
            return self.predicates[0]._is_unambiguously_locatable()
        else:
            return self._anders_predicates._is_unambiguously_locatable()


class XPathExpression(Node):
    __slots__ = ("location_paths",)

    def __init__(self, location_paths: list[LocationPath]):
        self.location_paths = location_paths

    def __repr__(self):
        return nested_repr(self)

    def evaluate(self, node: NodeBase, namespaces: Namespaces) -> Iterator[NodeBase]:
        yielded_nodes: set[int] = set()
        for path in self.location_paths:
            for result in path.evaluate(node=node, namespaces=namespaces):
                assert not isinstance(result, _DocumentNode)
                _id = id(result)
                if _id not in yielded_nodes:
                    yielded_nodes.add(_id)
                    yield result

    @cached_property
    def _is_unambiguously_locatable(self) -> bool:
        return (
            len(self.location_paths) == 1
            and self.location_paths[0]._is_unambiguously_locatable()
        )


# node tests


class AnyNameTest(NodeTestNode):
    __slots__ = ("prefix",)

    def __init__(self, prefix: Optional[str]):
        self.prefix = prefix

    @ensure_prefix
    def evaluate(self, node: NodeBase, namespaces: Namespaces) -> bool:
        if not _is_node_of_type(node, "TagNode"):
            return False
        node = cast("TagNode", node)

        if self.prefix:
            return node.namespace == namespaces[self.prefix]
        else:
            return True


class NameMatchTest(NodeTestNode):
    __slots__ = ("local_name", "prefix")

    def __init__(self, prefix: Optional[str], local_name: str):
        self.prefix = prefix
        self.local_name = local_name

    @ensure_prefix
    def evaluate(self, node: NodeBase, namespaces: Namespaces) -> bool:
        if not _is_node_of_type(node, "TagNode"):
            return False
        node = cast("TagNode", node)

        # this intentionally deviates from the spec, which states that
        # "if the QName does not have a prefix, then the namespace URI is null".
        # instead it refers to the default namespace if such has been declared.
        # cmp. https://www.w3.org/TR/1999/REC-xpath-19991116/#node-tests
        #
        # to make that clear the following is not compacted and optimization is
        # delegated to the (JIT) compiler.

        if self.prefix is None:
            if "" in namespaces:  # a default namespace was declared  # noqa: SIM401
                # delb's capability to address a default namespace
                # an empty/null namespace is represented as ""
                namespace = namespaces[""]
            else:
                # XPath spec behaviour
                # an undefined namespace is represented as None
                namespace = None
        else:
            namespace = namespaces[self.prefix]

        if namespace is None:  # noqa: SIM114
            # XPath spec behaviour
            if node.namespace:
                return False
        elif namespace == "":
            # delb's specific behaviour
            if node.namespace:
                return False
        else:
            if node.namespace != namespace:
                return False

        return node.local_name == self.local_name


class NodeTypeTest(NodeTestNode):
    __slots__ = ("type_name",)

    def __init__(self, type_name: NodeTypeNameLiteral):
        self.type_name = type_name

    def evaluate(self, node: NodeBase, namespaces: Namespaces) -> bool:
        return _is_node_of_type(node, self.type_name) or isinstance(node, _DocumentNode)


class ProcessingInstructionTest(NodeTypeTest):
    __slots__ = ("target", "type_name")

    def __init__(self, target: str):
        super().__init__("ProcessingInstructionNode")
        self.target = target

    def evaluate(self, node: NodeBase, namespaces: Namespaces) -> bool:
        if not super().evaluate(node=node, namespaces=namespaces):
            return False
        assert _is_node_of_type(node, "ProcessingInstructionNode")
        return cast("ProcessingInstructionNode", node).target == self.target


# predicate evaluation


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

        if (
            attribute := cast("TagNode", node).attributes.get(
                (context.namespaces.get(self.prefix or "", ""), self.local_name)
            )
        ) is None:
            return ""
        else:
            return attribute.value


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

    @property
    def _derived_attributes(self) -> list[tuple[str, str, str]]:
        if self.operator is operator.and_:
            return self.left._derived_attributes + self.right._derived_attributes

        elif self.operator is operator.eq:
            left, right = self.left, self.right
            if isinstance(left, AttributeValue):
                assert isinstance(right, AnyValue)
                return [
                    (left.prefix or "", left.local_name, right.value),
                ]
            else:
                assert isinstance(left, AnyValue)
                assert isinstance(right, AttributeValue)
                return [
                    (right.prefix or "", right.local_name, left.value),
                ]

        raise InvalidCodePath

    def evaluate(self, node: NodeBase, context: EvaluationContext) -> Any:
        return self.operator(
            self.left.evaluate(node=node, context=context),
            self.right.evaluate(node=node, context=context),
        )

    def _is_unambiguously_locatable(self) -> bool:
        if self.operator is operator.and_:
            return (
                self.left._is_unambiguously_locatable()
                and self.right._is_unambiguously_locatable()
            )
        elif self.operator is operator.eq:
            return (
                isinstance(self.left, AttributeValue)
                and (
                    isinstance(self.right, AnyValue)
                    and isinstance(self.right.value, str)
                )
            ) or (
                (isinstance(self.left, AnyValue) and isinstance(self.left.value, str))
                and isinstance(self.right, AttributeValue)
            )
        else:
            return False


class Function(EvaluationNode):
    __slots__ = ("arguments", "function")

    def __init__(self, name: str, arguments: Sequence[EvaluationNode]):
        function = xpath_functions.get(name)
        if function is None:
            raise XPathParsingError(message=f"Unknown function: `{name}`")
        parameters = inspect.signature(function).parameters
        if (
            len(parameters) > 1
            and tuple(parameters.values())[-1].kind != inspect.Parameter.VAR_POSITIONAL
            and len(parameters) != len(arguments) + 1
        ):
            raise XPathParsingError(
                message=f"Arguments to function `{name}` don't match its signature."
            )
        self.function = function
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
            node.attributes.get(
                (context.namespaces.get(self.prefix, ""), self.local_name)
            )
            is not None
        )


__all__ = (
    Axis.__name__,
    LocationPath.__name__,
    LocationStep.__name__,
    NameMatchTest.__name__,
    XPathExpression.__name__,
)
