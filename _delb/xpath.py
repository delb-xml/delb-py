# Copyright (C) 2018-'21  Frank Sachsenheim
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

""" This is not an XPath implementation. """

from abc import ABC
from collections import UserString
from functools import lru_cache
from typing import TYPE_CHECKING, Dict, Iterator, List, Optional, Set


if TYPE_CHECKING:
    from delb import TagNode


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
            raise AssertionError
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


class XPathExpression(UserString):
    __slots__ = ("location_paths",)

    def __init__(self, expression: str):
        self.location_paths = [
            LocationPath(x) for x in _split(_reduce_whitespace(expression), "|")
        ]

    @property
    def data(self):
        return " | ".join(str(x) for x in self.location_paths)

    def is_unambiguously_locatable(self) -> bool:
        """
        Determine whether an xpath expression addresses exactly one possible node.

        Examples::

        >>> XPathExpression('./path1|./path2').is_unambiguously_locatable()
        False

        >>> XPathExpression('/path').is_unambiguously_locatable()
        False

        >>> XPathExpression('./root/node/descendant::foo').is_unambiguously_locatable()
        False

        >>> XPathExpression('./node[@a="1" or @b="2"]').is_unambiguously_locatable()
        False

        >>> XPathExpression('./root/node[@a="1"][@b="2"]').is_unambiguously_locatable()
        True

        """
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


class LocationPath:
    __slots__ = ("location_steps",)

    def __init__(self, expression: str):
        self.location_steps = [LocationStep(x) for x in _split(expression, "/")]

    def __str__(self):
        return "/".join(str(x) for x in self.location_steps)


class LocationStep:
    __slots__ = ("axis", "node_test", "predicates")

    def __init__(self, expression: str):
        self.axis: str
        self.node_test: NodeTest
        self.predicates: Optional[PredicateExpression] = None

        if expression == "":
            self.axis = "descendant-or-self"
            self.node_test = NodeTest("node()")
        elif expression == ".":
            self.axis = "self"
            self.node_test = NodeTest("node()")
        elif expression == "..":
            self.axis = "parent"
            self.node_test = NodeTest("node()")
        else:
            if "[" in expression:
                # FIXME mind quotes:
                expression, predicates_part = expression.split("[", maxsplit=1)
                assert predicates_part[-1] == "]", predicates_part
                self.predicates = PredicateExpression.parse("[" + predicates_part)

            if expression.startswith("@"):
                expression = "attribute::" + expression[1:]

            if "::" not in expression:
                self.axis = "child"
                self.node_test = NodeTest(expression)
            else:
                self.axis, node_test_part = expression.split("::")
                self.node_test = NodeTest(node_test_part)

        if self.axis not in AXIS_NAMES:
            raise ValueError(f"`{self.axis}` is not a valid axis name.")

    def __str__(self):
        result = self.axis + "::" + str(self.node_test)
        if self.predicates is not None:
            result += "[" + str(self.predicates) + "]"
        return result

    def _derive_attributes(self):
        return self.predicates._derive_attributes()


class NodeTest:
    __slots__ = ("data", "type")

    def __init__(self, expression: str):
        self.data = expression

        if expression.endswith(")"):
            self.type = "type_test"
        else:
            self.type = "name_test"

    def __str__(self):
        return self.data


class PredicateExpression(ABC):
    def evaluate(self, node_set: Set["TagNode"]) -> Set["TagNode"]:
        # shall not be implemented
        raise NotImplementedError

    @staticmethod
    @lru_cache(64)
    def parse(expression: str) -> "PredicateExpression":
        """
        Parse string expression into ``PredicateExpression`` subclass instance.

        >>> isinstance(PredicateExpression.parse('[(@foo)]'), AttributePredicate)
        True

        >>> isinstance(PredicateExpression.parse('[@a="1" or @b="2"]'), BooleanPredicate) # noqa: E501
        True

        >>> isinstance(PredicateExpression.parse('[1]'), IndexPredicate)
        True

        >>> str(PredicateExpression.parse('[@href and starts-with(@href,"https://")]'))
        '(@href and starts-with(@href,"https://"))'

        """
        if expression.startswith("["):
            expression = expression[1:-1]
        expressions = tuple(_split(expression, "]["))

        if len(expressions) > 1:
            parsed_expressions = [
                PredicateExpression.parse(e) for e in expressions[::-1]
            ]

            while len(parsed_expressions) > 1:
                parsed_expressions.append(
                    BooleanPredicate(
                        "and", parsed_expressions.pop(), parsed_expressions.pop()
                    ),
                )
            return parsed_expressions[0]

        while _in_parenthesis(expression):
            expression = expression[1:-1]

        partitions = _partition_terms(expression)

        if len(partitions) == 1:
            if expression.startswith("@") or expression.startswith("attribute::"):
                return AttributePredicate.parse(expression)
            elif expression.isdigit():
                return IndexPredicate(expression)
            elif any(expression.startswith(f) for f in BOOLEAN_FUNCTIONS):
                return FunctionExpression(expression)
            elif expression.startswith('"') or expression.endswith("'"):
                return Literal(expression)
            else:
                return UnsupportedPredicate(expression)

        else:
            return BooleanPredicate.from_partitions(partitions)

    @property
    def _can_describe_attributes(self) -> bool:
        return False

    def _derive_attributes(self) -> Dict[str, str]:
        raise RuntimeError


class AttributePredicate(PredicateExpression):
    __slots__ = ("name", "value")

    def __init__(self, name: str, value: Optional[str]):
        self.name = name
        self.value = value

    @staticmethod
    # related: https://github.com/python/mypy/issues/5107
    def parse(expression: str) -> "AttributePredicate":  # type: ignore
        """
        Parse an xpath predicate string expression into an ``AttributePredicate``
        instance.

        >>> isinstance(
        ...     AttributePredicate.parse('@type="translation"'), AttributePredicate
        ... )
        True

        """
        if expression.startswith("attribute::"):
            raise NotImplementedError
        assert expression.startswith("@")

        parts = tuple(_split(expression[1:], "="))
        if len(parts) == 1:
            return AttributePredicate(parts[0], None)
        elif len(parts) == 2:
            return AttributePredicate(parts[0], parts[1][1:-1])
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


class BooleanPredicate(PredicateExpression):
    __slots__ = ("operator", "left_operand", "right_operand")

    def __init__(
        self,
        operator: str,
        left_operand: PredicateExpression,
        right_operand: PredicateExpression,
    ):
        self.operator = operator
        self.left_operand = left_operand
        self.right_operand = right_operand

    def __str__(self):
        sep = " " if self.operator in ("and", "or") else ""
        return f"({self.left_operand}{sep}{self.operator}{sep}{self.right_operand})"

    @staticmethod
    def from_partitions(partitions: List[str]) -> PredicateExpression:
        """
        Instantiates a boolean predicate from a list of string expressions. If the
        expression list passed contains only 1 element, an attribute or index predicate
        object gets instantiated.

        >>> bp = BooleanPredicate.from_partitions(['@foo="1"', 'and', '@bar="2"'])
        >>> bp.operator
        'and'

        >>> isinstance(bp.left_operand, AttributePredicate)
        True

        """
        if len(partitions) == 1:
            return PredicateExpression.parse(partitions[0])

        for operator in BOOLEAN_OPERATORS:
            for i, token in tuple(enumerate(partitions))[-2::-2]:
                if token == operator:
                    return BooleanPredicate(
                        operator,
                        BooleanPredicate.from_partitions(partitions[:i]),
                        BooleanPredicate.from_partitions(partitions[i + 1 :]),
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


class FunctionExpression(PredicateExpression):
    __slots__ = ("arguments", "name")

    def __init__(self, expression: str):
        self.name, rest = expression.split("(", maxsplit=1)
        assert rest.endswith(")")
        # FIXME this fails where an argument itself is a function call,
        #       _split would have to consider brackets as it does with quotes
        self.arguments = tuple(
            PredicateExpression.parse(e) for e in _split(rest[:-1], ",")
        )

    def __str__(self):
        return f"{self.name}({','.join(str(a) for a in self.arguments)})"


class IndexPredicate(PredicateExpression):
    __slots__ = ("index",)

    def __init__(self, index: str):
        self.index = int(index)

    def __str__(self):
        return str(self.index)


class Literal(PredicateExpression):
    __slots__ = ("value",)

    def __init__(self, expression: str):
        assert expression.endswith(expression[0])
        self.value = expression[1:-1]

    def __str__(self):
        value = self.value
        quote = "'" if '"' in value else '"'
        return f"{quote}{value}{quote}"


class UnsupportedPredicate(PredicateExpression):
    __slots__ = ("expression",)

    def __init__(self, expression: str):
        self.expression = expression

    def __str__(self):
        return self.expression
