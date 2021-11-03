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

from collections import UserString
from functools import lru_cache
from typing import Dict, Iterator, List, Optional

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
        self.location_paths = [LocationPath(x.strip()) for x in _split(expression, "|")]

    @property
    def data(self):
        return " | ".join(str(x) for x in self.location_paths)

    def is_unambiguously_locatable(self) -> bool:
        """ determine whether an xpath expression addresses exactly one possible node.

        can't have multiple paths:

        >>> XPathExpression('./path1|./path2').is_unambiguously_locatable()
        False

        can't have path not starting at root:

        >>> XPathExpression('/path').is_unambiguously_locatable()
        False

        can't have path that is not strictly hierarchical:

        >>> XPathExpression('./root/node/descendant::foo').is_unambiguously_locatable()
        False

        can't have predicates with OR operator:

        >>> XPathExpression('./node[@a="1" or @b="2"]').is_unambiguously_locatable()
        False

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
            if not predicates:
                continue

            predicate = predicates[0]
            if predicate.type != "attribute_test":
                return False

            if len(tuple(_split(predicate.expression, " or "))) > 1:
                return False

            if any(
                v is None for v in predicate.parse_attribute_test_to_dict().values()
            ):
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
        self.predicates: List[Predicate] = []

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
                expression, predicates_part = expression.split("[", maxsplit=1)
                assert predicates_part[-1] == "]", predicates_part
                self.predicates = [
                    Predicate(x) for x in predicates_part[:-1].split("][")
                ]

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
        return (
            self.axis
            + "::"
            + str(self.node_test)
            + "".join(str(x) for x in self.predicates)
        )


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


class Predicate:
    __slots__ = ("expression", "type")

    def __init__(self, expression: str):
        self.expression = expression
        if expression.startswith("@"):
            self.type = "attribute_test"
        elif expression.isdigit():
            self.type = "index_test"
        else:
            self.type = "unsupported_test"

    def __str__(self):
        return f"[{self.expression}]"

    __repr__ = __str__

    @lru_cache(1)
    def parse_attribute_test_to_dict(self) -> Dict[str, Optional[str]]:
        """ Creates a dictionary of attribute-value pairs (with the attributes' leading
        ``@``s removed) from an expression consisting of one ore more
        ``and``-concatenated attribute test predicates.

        >>> Predicate(
        ...     '@type="translation" and @xml:lang="en"'
        ... ).parse_attribute_test_to_dict()
        {'type': 'translation', 'xml:lang': 'en'}

        """
        # assumes that this is called after the containing
        # XPathExpression.is_unambiguously_locatable has returned True
        if not self.type == "attribute_test":
            raise ValueError

        result: Dict[str, Optional[str]] = {}

        for test in _split(self.expression, " and "):
            assert test.strip().startswith("@")
            parts = tuple(_split(test.strip()[1:], "="))
            if len(parts) == 1:
                result[parts[0]] = None
            elif len(parts) == 2:
                result[parts[0]] = parts[1][1:-1]
            else:
                raise AssertionError

        return result
