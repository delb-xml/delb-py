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

"""
This implementation is not compliant with one of the XPath specifications.
It mostly covers the `XPath 1.0 specs`_ , but focuses on the querying via path with
simple constraints while it omits computations (for which there are programming
languages) and has therefore these intended deviations from that standard:

- Default namespaces can be addressed, by simply using no prefix.
- The attribute and namespaces axes are not supported in location steps.
- In Predicates only the attribute axis form can be used in its abbreviated form
  (``@name``).
- Path evaluations within predicates are not available.
- Only these functions are provided and tested:
    - ``bool``
    - ``concat``
    - ``contains``
    - ``last``
    - ``not``
    - ``position``
    - ``starts-with``
    - Please refrain from extension requests without a proper, concrete implementation
      proposal.

Custom functions can be defined as shown in the follwing example. The first argument is
always the evaluation context which holds the properties ``node``, ``position``,
``size`` and ``namespaces``.

.. testcode::

    from delb import register_xpath_function, Document
    from _delb.xpath.ast import EvaluationContext


    @register_xpath_function("is-last")
    def is_last(context: EvaluationContext) -> bool:
        return context.position == context.size

    @register_xpath_function
    def lowercase(_, string: str) -> str:
        return string.lower()


    document = Document("<root><node foo='BAR'/></root>")
    assert document.xpath("/*[is-last() and lower(@foo)='bar']").size == 1


.. _XPath 1.0 specs: https://www.w3.org/TR/1999/REC-xpath-19991116/
"""  # TODO include in docs

from __future__ import annotations

from abc import ABC
from collections import UserString
from functools import lru_cache
from typing import (
    TYPE_CHECKING,
    Collection,
    Dict,
    Iterable,
    Iterator,
    List,
    Mapping,
    Optional,
    Sequence,
    Set,
    Tuple,
)

from cssselect import GenericTranslator  # type: ignore

from _delb.names import Namespaces
from _delb.typing import Filter
from _delb.utils import sort_nodes_in_document_order
from _delb.xpath.functions import register_xpath_function
from _delb.xpath.parser import parse


if TYPE_CHECKING:
    from delb import NodeBase, TagNode


_css_translator = GenericTranslator()


class QueryResults(Sequence["NodeBase"]):
    """
    A sequence with the results of a CSS or XPath query with some helpers for readable
    Python expressions.
    """

    def __init__(self, results: Iterable[NodeBase]):
        self.__items = tuple(results)

    def __eq__(self, other):
        if not isinstance(other, Collection):
            raise TypeError

        return len(self.__items) == len(other) and all(x in other for x in self.__items)

    def __getitem__(self, item):
        return self.__items[item]

    def __len__(self) -> int:
        return len(self.__items)

    def __repr__(self):
        return str([repr(x) for x in self.__items])

    def as_list(self) -> List[NodeBase]:
        """The contained nodes as a new :class:`list`."""
        return list(self.__items)

    @property
    def as_tuple(self) -> Tuple[NodeBase, ...]:
        """The contained nodes in a :class:`tuple`."""
        return self.__items

    def filtered_by(self, *filters: Filter) -> "QueryResults":
        """
        Returns another :class:`QueryResults` instance that contains all nodes filtered
        by the provided :term:`filter` s.
        """
        items = self.__items
        for filter in filters:
            items = (x for x in items if filter(x))  # type: ignore
        return self.__class__(items)  # type: ignore

    @property
    def first(self) -> Optional[NodeBase]:
        """The first node from the results or ``None`` if there are none."""
        if len(self.__items):
            return self.__items[0]
        else:
            return None

    def in_document_order(self) -> QueryResults:
        """
        Returns a new object where the contained nodes are sorted in document order.
        """
        return QueryResults(sort_nodes_in_document_order(self))

    @property
    def last(self) -> Optional[NodeBase]:
        """The last node from the results or ``None`` if there are none."""
        if len(self.__items):
            return self.__items[-1]
        else:
            return None

    @property
    def size(self) -> int:
        """The amount of contained nodes."""
        return len(self.__items)


# TODO make cachesize configurable via environment variable?
@lru_cache(maxsize=64)
def _css_to_xpath(expression: str) -> str:
    return _css_translator.css_to_xpath(expression, prefix="descendant-or-self::")


def evaluate(
    node: TagNode,
    expression: str,
    namespaces: Optional[Mapping[Optional[str], str]] = None,
) -> Iterable[NodeBase]:
    if namespaces is None:
        namespaces = node.namespaces
    elif not isinstance(namespaces, Namespaces):
        namespaces = Namespaces(namespaces)
    return parse(expression).evaluate(node, namespaces)


__all__ = (
    _css_to_xpath.__name__,  # type:ignore
    evaluate.__name__,
    parse.__name__,  # type: ignore
    register_xpath_function.__name__,
    QueryResults.__name__,
)


# REMOVE as much as possible, but retain the TagNode._etree_xpath functionality

#  L E G A C Y  #


""" This is not an XPath implementation. """

# ordered by alphabet
AXIS_NAMES = (
    "ancestor",
    "ancestor-or-self",
    "attribute",
    "child",
    "descendant",
    "descendant-or-self",
    "following",
    "following-sibling",
    "namespace",
    "parent",
    "preceding",
    "preceding-sibling",
    "self",
)
# ordered by weight (ascending)
BOOLEAN_OPERATORS = ("or", "and", "!=", "=", ">", ">=", "<", "<=")
BOOLEAN_FUNCTIONS = ("contains", "not", "starts-with")


def _in_parenthesis(expression: str) -> bool:
    """
    Determines whether an expression is surrounded by parenthesis in its
    entirety.

    >>> _in_parenthesis('foo and bar')
    False

    >>> _in_parenthesis('(foo)(bar)')
    False

    >>> _in_parenthesis('foo)') == _in_parenthesis('(foo') == False
    True

    >>> _in_parenthesis('((foo)(bar))')
    True

    """
    if not expression.startswith("(") or not expression.endswith(")"):
        return False
    level = 1
    for character in expression[1:-1]:
        if character == "(":
            level += 1
        elif character == ")":
            level -= 1
        if level < 1:
            return False
    return True


def _partition_terms(expression: str) -> List[str]:  # noqa: C901
    """
    Split up expression into partitions under consideration of quotes and
    parentheses.

    >>> _partition_terms('(@foo="1") and (@bar="2")')
    ['@foo="1"', 'and', '@bar="2"']

    >>> _partition_terms('@foo = "1"')
    ['@foo', '=', '"1"']

    >>> _partition_terms('((@foo="1") or (@bar="2")) and @baz!="3"')
    ['(@foo="1") or (@bar="2")', 'and', '@baz!="3"']

    >>> _partition_terms('@href and starts-with(@href,"https://")')
    ['@href', 'and', 'starts-with(@href,"https://")']

    >>> _partition_terms('@href and not(starts-with(@href,"https://"))')
    ['@href', 'and', 'not(starts-with(@href,"https://"))']

    >>> _partition_terms('not(@foo) and (@bar)')
    ['not(@foo)', 'and', '@bar']

    """
    bracket_level = 0
    function_args = False
    current_term = ""
    quote = ""
    result = []

    for character in expression:
        if quote or bracket_level:
            if character == quote:
                quote = ""
            elif character == "(":
                bracket_level += 1
            elif character == ")":
                bracket_level -= 1
                if not bracket_level and not function_args:
                    continue
                function_args = function_args and bool(bracket_level)
            current_term += character
        # TODO escaped characters
        elif character in ("'", '"'):
            quote = character
            current_term += character
        elif character == "(":
            bracket_level += 1
            if current_term in BOOLEAN_FUNCTIONS:
                current_term += character
                function_args = True
        elif character == ")":
            pass
        elif character == " ":
            result.append(current_term)
            current_term = ""
        else:
            current_term += character

    if current_term:
        result.append(current_term)

    return result


def _reduce_whitespace(expression: str) -> str:
    """
    Remove unnecessary whitespace from xpath predicate expression.

    >>> _reduce_whitespace('[@a = "1" or  @b = "2"][@c = "3"]')
    '[@a="1" or @b="2"][@c="3"]'

    >>> _reduce_whitespace('[contains(@a, "1")]')
    '[contains(@a,"1")]'

    """
    quote = ""
    result = ""
    skip = 0

    for i, character in enumerate(expression):
        if skip:
            skip -= 1
        elif character == " " and not quote:
            if expression[i : i + 4] == " or ":
                result += " or "
                skip = 3
            elif expression[i : i + 5] == " and ":
                result += " and "
                skip = 4
            else:
                pass  # result += ""
        elif character in ("'", '"'):
            quote = "" if quote else character
            result += character
        else:
            result += character

    return result


def _split(expression: str, separator: str) -> Iterator[str]:
    """
    Split expression at occurrences of specified seperator, except
    where within quotation marks.

    >>> list(_split('./root/path[@a="n/a"]', '/'))
    ['.', 'root', 'path[@a="n/a"]']

    >>> list(_split('@type="translation" and @xml:lang="en"', ' and '))
    ['@type="translation"', '@xml:lang="en"']

    """
    assert separator not in ('"', "'")
    cursor = 0
    part = ""
    quote = ""
    separator_length = len(separator)

    for i, character in enumerate(expression):
        if i < cursor:
            continue

        if expression[i : i + separator_length] == separator and not quote:
            yield part
            part = ""
            cursor += separator_length
            continue

        if character == quote:
            quote = ""
        elif character in ('"', "'"):
            quote = character

        part += character
        cursor += 1

    yield part


class LegacyXPathExpression(UserString):
    __slots__ = ("location_paths",)

    def __init__(self, expression: str):
        self.location_paths = [
            LegacyLocationPath(x) for x in _split(_reduce_whitespace(expression), "|")
        ]

    @property
    def data(self):
        return " | ".join(str(x) for x in self.location_paths)

    def is_unambiguously_locatable(self) -> bool:
        """
        Determine whether an xpath expression addresses exactly one possible node.

        Examples::

        >>> LegacyXPathExpression('./path1|./path2').is_unambiguously_locatable()
        False

        >>> LegacyXPathExpression('/path').is_unambiguously_locatable()
        False

        >>> LegacyXPathExpression(
        './root/node/descendant::foo').is_unambiguously_locatable()
        False

        >>> LegacyXPathExpression('./node[@a="1" or @b="2"]').is_unambiguously_locatable()
        False

        >>> LegacyXPathExpression('./root/node[@a="1"][@b="2"]').is_unambiguously_locatable()
        True

        """  # noqa: E501
        if len(self.location_paths) != 1:
            return False

        steps = self.location_paths[0].location_steps

        if steps[0].axis != "self":
            return False

        for step in steps[1:]:
            if step.axis != "child":
                return False

            predicates = step.predicates
            if predicates is None:
                continue

            if not predicates._can_describe_attributes:
                return False

        return True


class LegacyLocationPath:
    __slots__ = ("location_steps",)

    def __init__(self, expression: str):
        step_expressions = list(_split(expression, "/"))
        if not step_expressions[0]:
            step_expressions = step_expressions[1:]
        self.location_steps = [LegacyLocationStep(x) for x in step_expressions]

    def __str__(self):
        return "/".join(str(x) for x in self.location_steps)


class LegacyLocationStep:
    __slots__ = ("axis", "node_test", "predicates")

    def __init__(self, expression: str):
        self.axis: str
        self.node_test: LegacyNodeTest
        self.predicates: Optional[LegacyPredicateExpression] = None

        if expression == "":
            self.axis = "descendant-or-self"
            self.node_test = LegacyNodeTest("node()")
        elif expression == ".":
            self.axis = "self"
            self.node_test = LegacyNodeTest("node()")
        elif expression == "..":
            self.axis = "parent"
            self.node_test = LegacyNodeTest("node()")
        else:
            if "[" in expression:
                # FIXME mind quotes:
                expression, predicates_part = expression.split("[", maxsplit=1)
                assert predicates_part[-1] == "]", predicates_part
                self.predicates = LegacyPredicateExpression.parse("[" + predicates_part)

            if expression.startswith("@"):
                expression = "attribute::" + expression[1:]

            if "::" not in expression:
                self.axis = "child"
                self.node_test = LegacyNodeTest(expression)
            else:
                self.axis, node_test_part = expression.split("::")
                self.node_test = LegacyNodeTest(node_test_part)

        if self.axis not in AXIS_NAMES:
            raise ValueError(f"`{self.axis}` is not a valid axis name.")

    def __str__(self):
        result = self.axis + "::" + str(self.node_test)
        if self.predicates is not None:
            result += "[" + str(self.predicates) + "]"
        return result

    def _derive_attributes(self):
        return self.predicates._derive_attributes()


class LegacyNodeTest:
    __slots__ = ("data", "type")

    def __init__(self, expression: str):
        self.data = expression

        if expression.endswith(")"):
            self.type = "type_test"
        else:
            self.type = "name_test"

    def __str__(self):
        return self.data


class LegacyPredicateExpression(ABC):
    def evaluate(self, node_set: Set["TagNode"]) -> Set["TagNode"]:
        # shall not be implemented
        raise NotImplementedError

    @staticmethod
    @lru_cache(64)
    def parse(expression: str) -> "LegacyPredicateExpression":
        """
                Parse string expression into ``PredicateExpression`` subclass instance.

        import _delb.xpath.parser        >>> isinstance(_delb.xpath.parser.parse('[(@foo)]'),
                LegacyAttributePredicate)
                True

        import _delb.xpath.parser        >>> isinstance(_delb.xpath.parser.parse('[@a="1" or
        @b="2"]'),
                BooleanPredicate) # noqa: E501
                True

        import _delb.xpath.parser        >>> isinstance(_delb.xpath.parser.parse('[1]'),
        LegacyIndexPredicate)
                True

        import _delb.xpath.parser        >>> str(_delb.xpath.parser.parse(
                ...     '[@href and starts-with(@href, "https://")]'))
                '(@href and starts-with(@href,"https://"))'

        """
        if expression.startswith("["):
            expression = expression[1:-1]
        expressions = tuple(_split(expression, "]["))

        if len(expressions) > 1:
            parsed_expressions = [
                LegacyPredicateExpression.parse(e) for e in expressions[::-1]
            ]

            while len(parsed_expressions) > 1:
                parsed_expressions.append(
                    LegacyBooleanPredicate(
                        "and", parsed_expressions.pop(), parsed_expressions.pop()
                    ),
                )
            return parsed_expressions[0]

        while _in_parenthesis(expression):
            expression = expression[1:-1]

        partitions = _partition_terms(expression)

        if len(partitions) == 1:
            if expression.startswith("@") or expression.startswith("attribute::"):
                return LegacyAttributePredicate.parse(expression)
            elif expression.isdigit():
                return LegacyIndexPredicate(expression)
            elif any(expression.startswith(f) for f in BOOLEAN_FUNCTIONS):
                return LegacyFunctionExpression(expression)
            elif expression.startswith('"') or expression.endswith("'"):
                return LegacyLiteral(expression)
            else:
                return LegacyUnsupportedPredicate(expression)

        else:
            return LegacyBooleanPredicate.from_partitions(partitions)

    @property
    def _can_describe_attributes(self) -> bool:
        return False

    def _derive_attributes(self) -> Dict[str, str]:
        raise RuntimeError


class LegacyAttributePredicate(LegacyPredicateExpression):
    __slots__ = ("name", "value")

    def __init__(self, name: str, value: Optional[str]):
        self.name = name
        self.value = value

    @staticmethod
    # related: https://github.com/python/mypy/issues/5107
    def parse(expression: str) -> "LegacyAttributePredicate":  # type: ignore
        """
                Parse an xpath predicate string expression into an ``AttributePredicate``
                instance.

        import _delb.xpath.parser        >>> isinstance(
                ...     _delb.xpath.parser.parse('@type="translation"'),
                LegacyAttributePredicate
                ... )
                True

        """  # noqa: E501
        if expression.startswith("attribute::"):
            raise NotImplementedError
        assert expression.startswith("@")

        parts = tuple(_split(expression[1:], "="))
        if len(parts) == 1:
            return LegacyAttributePredicate(parts[0], None)
        elif len(parts) == 2:
            return LegacyAttributePredicate(parts[0], parts[1][1:-1])
        else:
            raise ValueError

    def __str__(self):
        value = self.value
        if value is None:
            return f"@{self.name}"
        quote = "'" if '"' in value else '"'
        return f"@{self.name}={quote}{self.value}{quote}"

    @property
    def _can_describe_attributes(self) -> bool:
        return self.value is not None

    def _derive_attributes(self) -> Dict[str, str]:
        assert self.value is not None
        return {self.name: self.value}


class LegacyBooleanPredicate(LegacyPredicateExpression):
    __slots__ = ("operator", "left_operand", "right_operand")

    def __init__(
        self,
        operator: str,
        left_operand: LegacyPredicateExpression,
        right_operand: LegacyPredicateExpression,
    ):
        self.operator = operator
        self.left_operand = left_operand
        self.right_operand = right_operand

    def __str__(self):
        sep = " " if self.operator in ("and", "or") else ""
        return f"({self.left_operand}{sep}{self.operator}{sep}{self.right_operand})"

    @staticmethod
    def from_partitions(partitions: List[str]) -> LegacyPredicateExpression:
        """
        Instantiates a boolean predicate from a list of string expressions. If the
        expression list passed contains only 1 element, an attribute or index predicate
        object gets instantiated.

        >>> bp = LegacyBooleanPredicate.from_partitions(['@foo="1"', 'and', '@bar="2"'])
        >>> bp.operator
        'and'

        >>> isinstance(bp.left_operand, LegacyAttributePredicate)
        True

        """
        if len(partitions) == 1:
            return LegacyPredicateExpression.parse(partitions[0])

        for operator in BOOLEAN_OPERATORS:
            for i, token in tuple(enumerate(partitions))[-2::-2]:
                if token == operator:
                    return LegacyBooleanPredicate(
                        operator,
                        LegacyBooleanPredicate.from_partitions(partitions[:i]),
                        LegacyBooleanPredicate.from_partitions(partitions[i + 1 :]),
                    )

        raise RuntimeError

    @property
    def _can_describe_attributes(self) -> bool:
        return (
            self.operator == "and"
            and self.left_operand._can_describe_attributes
            and self.right_operand._can_describe_attributes
        )

    def _derive_attributes(self) -> Dict[str, str]:
        if self.operator != "and":
            raise RuntimeError

        return {
            **self.left_operand._derive_attributes(),
            **self.right_operand._derive_attributes(),
        }


class LegacyFunctionExpression(LegacyPredicateExpression):
    __slots__ = ("arguments", "name")

    def __init__(self, expression: str):
        self.name, rest = expression.split("(", maxsplit=1)
        # FIXME this fails where an argument itself is a function call,
        #       _split would have to consider brackets as it does with quotes
        self.arguments = tuple(
            LegacyPredicateExpression.parse(e) for e in _split(rest[:-1], ",")
        )

    def __str__(self):
        return f"{self.name}({','.join(str(a) for a in self.arguments)})"


class LegacyIndexPredicate(LegacyPredicateExpression):
    __slots__ = ("index",)

    def __init__(self, index: str):
        self.index = int(index)

    def __str__(self):
        return str(self.index)


class LegacyLiteral(LegacyPredicateExpression):
    __slots__ = ("value",)

    def __init__(self, expression: str):
        assert expression.endswith(expression[0])
        self.value = expression[1:-1]

    def __str__(self):
        value = self.value
        quote = "'" if '"' in value else '"'
        return f"{quote}{value}{quote}"


class LegacyUnsupportedPredicate(LegacyPredicateExpression):
    __slots__ = ("expression",)

    def __init__(self, expression: str):
        self.expression = expression

    def __str__(self):
        return self.expression
