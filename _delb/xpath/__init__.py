# Copyright (C) 2018-'24  Frank Sachsenheim
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
*delb* allows querying of nodes with CSS selector and XPath expressions. CSS selectors
are converted to XPath expressions with a third-party library before evaluation and they
are only supported as far as their computed XPath equivalents are supported by *delb*'s
very own XPath implementation.

This implementation is not fully compliant with one of the W3C's XPath specifications.
It mostly covers the `XPath 1.0 specs`_, but focuses on the querying via path
expressions with simple constraints while it omits a broad employment of  computations
(that's what programming languages are for) and has therefore these intended deviations
from that standard:

- Default namespaces can be addressed in node and attribute names, by simply using no
  prefix.
- The attribute and namespace axes are not supported in location steps (see also below).
- In predicates only the attribute axis can be used in its abbreviated form (``@name``).
- Path evaluations within predicates are not available.
- Only these predicate functions are provided and tested:
    - ``boolean``
    - ``concat``
    - ``contains``
    - ``last``
    - ``not``
    - ``position``
    - ``starts-with``
    - ``text``
        - Behaves as if deployed as a single step location path that only tests for the
          node type *text*. Hence it returns the contents of the context node's first
          child node that is a text node or an empty string when there is none.
    - Please refrain from extension requests without a proper, concrete implementation
      proposal.

If you're accustomed to retrieve attribute values with XPath expressions, employ the
functionality of the higher programming language at hand like this:

    >>> [x.attributes["target"] for x in root.xpath("//foo")
    ...  if "target" in x.attributes ]  # doctest: +SKIP

Instead of:

    >>> root.xpath("//foo/@target")  # doctest: +SKIP

See :meth:`_delb.plugins.PluginManager.register_xpath_function` regarding the use of
custom functions.

.. _XPath 1.0 specs: https://www.w3.org/TR/1999/REC-xpath-19991116/
"""

from __future__ import annotations

import warnings
from functools import lru_cache
from typing import TYPE_CHECKING, Optional

# DROPWITH Python 3.8 and replace w/ imports from collections.abc
from typing import Collection, Iterable, Iterator, Mapping, Sequence

from cssselect import GenericTranslator

from _delb.names import Namespaces
from _delb.utils import _sort_nodes_in_document_order
from _delb.xpath.ast import EvaluationContext
from _delb.xpath import functions  # noqa: F401
from _delb.xpath.parser import parse


if TYPE_CHECKING:
    from _delb.nodes import NodeBase
    from _delb.typing import Filter, NamespaceDeclarations

_css_translator = GenericTranslator()


class QueryResults(Sequence["NodeBase"]):
    """
    A container with the the results of a CSS selector or XPath query with some helpers
    for better readable Python expressions.
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

    def as_list(self) -> list[NodeBase]:
        """The contained nodes as a new :class:`list`."""
        return list(self.__items)

    @property
    def as_tuple(self) -> tuple[NodeBase, ...]:
        """The contained nodes in a :class:`tuple`."""
        return self.__items

    def filtered_by(self, *filters: Filter) -> QueryResults:
        """
        Returns another :class:`QueryResults` instance that contains all nodes filtered
        by the provided :term:`filter` s.
        """
        items: Sequence[NodeBase] = self.__items
        for filter in filters:
            items = [x for x in items if filter(x)]
        return self.__class__(items)

    @property
    def first(self) -> Optional[NodeBase]:
        """The first node from the results or :obj:`None` if there are none."""
        if len(self.__items):
            return self.__items[0]
        else:
            return None

    def in_document_order(self) -> QueryResults:
        """
        Returns another :class:`QueryResults` instance where the contained nodes are
        sorted in document order.
        """
        return QueryResults(_sort_nodes_in_document_order(self))

    @property
    def last(self) -> Optional[NodeBase]:
        """The last node from the results or :obj:`None` if there are none."""
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
    return _css_translator.css_to_xpath(expression, prefix="descendant::")


def evaluate(
    node: NodeBase,
    expression: str,
    namespaces: Optional[NamespaceDeclarations] = None,
) -> QueryResults:
    # global namespaces are guaranteed by the Namespaces implementation
    if namespaces is None:
        warnings.warn(
            "Default namespace declarations that are carried over won't be available "
            "in future versions. The declarations need to be passed explicitly.",
            category=DeprecationWarning,
        )
        _namespaces = node.namespaces
    elif isinstance(namespaces, Namespaces):
        # b/c it would break fallback chains
        raise TypeError
    elif isinstance(namespaces, Mapping):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=DeprecationWarning)
            _namespaces = Namespaces(namespaces, fallback=node.namespaces)
    else:
        raise TypeError

    return QueryResults(parse(expression).evaluate(node=node, namespaces=_namespaces))


__all__ = (
    _css_to_xpath.__name__,  # type:ignore
    evaluate.__name__,
    parse.__name__,  # type: ignore
    EvaluationContext.__name__,
    QueryResults.__name__,
)


# REMOVE eventually

#  L E G A C Y  #


""" This was neither an XPath implementation. """


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


def _split(expression: str, separator: str) -> Iterator[str]:  # pragma: no cover
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


class LegacyXPathExpression:
    __slots__ = ("location_paths",)

    def __init__(self, expression: str):
        self.location_paths = [
            LegacyLocationPath(x) for x in _split(_reduce_whitespace(expression), "|")
        ]

    def __str__(self):
        return " | ".join(str(x) for x in self.location_paths)


class LegacyLocationPath:
    __slots__ = ("location_steps",)

    def __init__(self, expression: str):
        step_expressions = list(_split(expression, "/"))
        if not step_expressions[0]:
            step_expressions = step_expressions[1:]
        self.location_steps = [LegacyLocationStep(x) for x in step_expressions]

    def __str__(self):
        return "/".join(str(x) for x in self.location_steps)


class LegacyLocationStep:  # pragma: no cover
    __slots__ = ("axis", "node_test", "predicates")

    def __init__(self, expression: str):
        self.axis: str
        self.node_test: LegacyNodeTest
        self.predicates = ""

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
                expression, predicates_part = expression.split("[", maxsplit=1)
                assert predicates_part[-1] == "]", predicates_part
                self.predicates = "[" + predicates_part

            if "::" not in expression:
                self.axis = "child"
                self.node_test = LegacyNodeTest(expression)
            else:
                self.axis, node_test_part = expression.split("::")
                self.node_test = LegacyNodeTest(node_test_part)

    def __str__(self):
        return self.axis + "::" + self.node_test.data + self.predicates


class LegacyNodeTest:
    __slots__ = ("data", "type")

    def __init__(self, expression: str):
        self.data = expression

        if expression.endswith(")"):
            self.type = "type_test"
        else:
            self.type = "name_test"
