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

import re
import sys
from collections import defaultdict, deque
from collections.abc import Iterable, Iterator, Sequence
from functools import partial
from itertools import chain
from typing import TYPE_CHECKING, cast, Any, Final, Optional


if TYPE_CHECKING:
    from _delb.nodes import NodeBase, TagNode
    from _delb.typing import Filter, NodeTypeNameLiteral


NODE_MODULE_FQN: Final = f"{__package__}.nodes"


_crunch_whitespace: Final = partial(re.compile(r"\s+").sub, " ")


class _NodesSorter:
    def __init__(self):
        self.__node = None
        self.__items = defaultdict(_NodesSorter)

    def add(self, path: Sequence[int], node: TagNode):
        assert _is_node_of_type(node, "TagNode")
        if path:
            self.__items[path[0]].add(path[1:], node)
        else:
            self.__node = node

    def emit(self) -> Iterator[NodeBase]:
        if self.__node is not None:
            yield self.__node
        for index in sorted(self.__items):
            yield from self.__items[index].emit()


class _StringMixin:  # pragma: no cover
    # copied from CPython 3.10.0's stdlib collections.UserString and adjusted

    __slots__ = ()

    def __str__(self):
        return str(self._data)

    def __int__(self):
        return int(self._data)

    def __float__(self):
        return float(self._data)

    def __complex__(self):
        return complex(self._data)

    def __hash__(self):
        return hash(self._data)

    def __eq__(self, string):
        return self._data == string

    def __lt__(self, string):
        return self._data < string

    def __le__(self, string):
        return self._data <= string

    def __gt__(self, string):
        return self._data > string

    def __ge__(self, string):
        return self._data >= string

    def __contains__(self, char):
        return char in self._data

    def __len__(self):
        return len(self._data)

    def __getitem__(self, index):
        return self._data[index]

    def __add__(self, other):
        if isinstance(other, str):
            return self._data + other
        return self._data + str(other)

    def __radd__(self, other):
        if isinstance(other, str):
            return other + self._data
        return str(other) + self._data

    def __mul__(self, n):
        return self._data * n

    __rmul__ = __mul__

    def __mod__(self, args):
        return self._data % args

    def __rmod__(self, template):
        return str(template) % self

    def capitalize(self):
        return self._data.capitalize()

    def casefold(self):
        return self._data.casefold()

    def center(self, width, *args):
        return self._data.center(width, *args)

    def count(self, sub, start=0, end=sys.maxsize):
        return self._data.count(sub, start, end)

    def removeprefix(self, prefix):
        return self._data.removeprefix(prefix)

    def removesuffix(self, suffix):
        return self._data.removesuffix(suffix)

    def encode(self, encoding="utf-8", errors="strict"):
        encoding = "utf-8" if encoding is None else encoding
        errors = "strict" if errors is None else errors
        return self._data.encode(encoding, errors)

    def endswith(self, suffix, start=0, end=sys.maxsize):
        return self._data.endswith(suffix, start, end)

    def expandtabs(self, tabsize=8):
        return self._data.expandtabs(tabsize)

    def find(self, sub, start=0, end=sys.maxsize):
        return self._data.find(sub, start, end)

    def format(self, *args, **kwds):
        return self._data.format(*args, **kwds)

    def format_map(self, mapping):
        return self._data.format_map(mapping)

    def index(self, sub, start=0, end=sys.maxsize):
        return self._data.index(sub, start, end)

    def isalpha(self):
        return self._data.isalpha()

    def isalnum(self):
        return self._data.isalnum()

    def isascii(self):
        return self._data.isascii()

    def isdecimal(self):
        return self._data.isdecimal()

    def isdigit(self):
        return self._data.isdigit()

    def isidentifier(self):
        return self._data.isidentifier()

    def islower(self):
        return self._data.islower()

    def isnumeric(self):
        return self._data.isnumeric()

    def isprintable(self):
        return self._data.isprintable()

    def isspace(self):
        return self._data.isspace()

    def istitle(self):
        return self._data.istitle()

    def isupper(self):
        return self._data.isupper()

    def join(self, seq):
        return self._data.join(seq)

    def ljust(self, width, *args):
        return self._data.ljust(width, *args)

    def lower(self):
        return self._data.lower()

    def lstrip(self, chars=None):
        return self._data.lstrip(chars)

    def partition(self, sep):
        return self._data.partition(sep)

    def replace(self, old, new, maxsplit=-1):
        return self._data.replace(old, new, maxsplit)

    def rfind(self, sub, start=0, end=sys.maxsize):
        return self._data.rfind(sub, start, end)

    def rindex(self, sub, start=0, end=sys.maxsize):
        return self._data.rindex(sub, start, end)

    def rjust(self, width, *args):
        return self._data.rjust(width, *args)

    def rpartition(self, sep):
        return self._data.rpartition(sep)

    def rstrip(self, chars=None):
        return self._data.rstrip(chars)

    def split(self, sep=None, maxsplit=-1):
        return self._data.split(sep, maxsplit)

    def rsplit(self, sep=None, maxsplit=-1):
        return self._data.rsplit(sep, maxsplit)

    def splitlines(self, keepends=False):
        return self._data.splitlines(keepends)

    def startswith(self, prefix, start=0, end=sys.maxsize):
        return self._data.startswith(prefix, start, end)

    def strip(self, chars=None):
        return self._data.strip(chars)

    def swapcase(self):
        return self._data.swapcase()

    def title(self):
        return self._data.title()

    def translate(self, *args):
        return self._data.translate(*args)

    def upper(self):
        return self._data.upper()

    def zfill(self, width):
        return self._data.zfill(width)


def first(iterable: Iterable) -> Optional[Any]:
    """
    Returns the first item of the given :term:`iterable` or :obj:`None` if it's empty.
    Note that the first item is consumed when the iterable is an :term:`iterator`.
    """
    match iterable:
        case Iterator():
            try:
                return next(iterable)
            except StopIteration:
                return None
        case Sequence():
            return iterable[0] if len(iterable) else None
        case _:
            raise TypeError


def get_traverser(*, from_left=True, depth_first=True, from_top=True):
    """
    Returns a function that can be used to traverse a (sub)tree with the given node as
    root.

    :param from_left: The traverser yields sibling nodes from left to right if
                      :obj:`True`, or starting from the right if :obj:`False`.
    :param depth_first: The child nodes resp. the parent node are yielded before the
                        siblings of a node by a traverser if :obj:`True`. Siblings are
                        favored if :obj:`False`.
    :param from_top: The traverser starts yielding nodes with the lowest depth if
                     :obj:`True`. When :obj:`False`, again, the opposite is in effect.

    While traversing the given root node is yielded at some point if it also passes the
    filters. The globally set default filters are not considered by the traverser
    routines.

    The returned functions have this signature:

    .. code-block:: python

        def traverser(root: NodeBase, *filters: Filter) -> Iterator[NodeBase]:
            ...
    """
    if (result := TRAVERSERS.get((from_left, depth_first, from_top))) is None:
        raise NotImplementedError
    return result


def _is_node_of_type(
    node: NodeBase,
    type_name: NodeTypeNameLiteral,
) -> bool:
    return (
        node.__class__.__module__ == NODE_MODULE_FQN
        and node.__class__.__qualname__ == type_name
    )


def last(iterable: Iterable) -> Optional[Any]:
    """
    Returns the last item of the given :term:`iterable` or :obj:`None` if it's empty.
    Note that the whole :term:`iterator` is consumed when such is given.
    """
    match iterable:
        case Iterator():
            result = None
            for result in iterable:
                pass
            return result
        case Sequence():
            return iterable[-1] if len(iterable) else None
        case _:
            raise TypeError


def _sort_nodes_in_document_order(nodes: Iterable[NodeBase]) -> Iterator[NodeBase]:
    node_index_cache: dict[int, int] = {}
    sorter = _NodesSorter()

    for node in nodes:  # pragma: no cover
        if not _is_node_of_type(node, "TagNode"):
            raise NotImplementedError(
                "Support for sorting other node types than TagNodes isn't scheduled"
                "yet."
            )

        node = cast("TagNode", node)
        ancestors_indexes: deque[int] = deque()

        for cursor in chain((node,), node._iterate_ancestors()):
            if cursor._parent is None:
                break

            if (node_id := id(cursor)) in node_index_cache:
                index = node_index_cache[node_id]
            else:
                node_index_cache[node_id] = index = cursor._parent._child_nodes.index(
                    cursor
                )
            ancestors_indexes.appendleft(index)

        sorter.add(tuple(ancestors_indexes), node)

    yield from sorter.emit()


# tree traversers


def traverse_bf_ltr_ttb(root: NodeBase, *filters: Filter) -> Iterator[NodeBase]:
    queue = deque((root,))
    while queue:
        node = queue.popleft()
        if _is_node_of_type(node, "TagNode"):
            queue.extend(node._child_nodes)
        if all(f(node) for f in filters):
            yield node


def traverse_df_ltr_btt(root: NodeBase, *filters: Filter) -> Iterator[NodeBase]:
    stack = [(root, deque(root._child_nodes))]

    while stack:
        node, remaining_children = stack.pop()

        while remaining_children:
            child = remaining_children.popleft()
            if _is_node_of_type(child, "TagNode") and child._child_nodes:
                stack.extend(
                    ((node, remaining_children), (child, deque(child._child_nodes)))
                )
                break
            else:
                if all(f(child) for f in filters):
                    yield child

        else:
            if all(f(node) for f in filters):
                yield node


def traverse_df_ltr_ttb(root: NodeBase, *filters: Filter) -> Iterator[NodeBase]:
    for node in chain((root,), root._iterate_descendants()):
        if all(f(node) for f in filters):
            yield node


def traverse_df_rtl_btt(root: NodeBase, *filters: Filter) -> Iterator[NodeBase]:
    for node in root._iterate_reversed_descendants():
        if all(f(node) for f in filters):
            yield node


TRAVERSERS = {
    (True, False, True): traverse_bf_ltr_ttb,
    (True, True, True): traverse_df_ltr_ttb,
    (True, True, False): traverse_df_ltr_btt,
    (False, True, False): traverse_df_rtl_btt,
}


__all__: tuple[str, ...] = (
    first.__name__,
    get_traverser.__name__,
    last.__name__,
    _sort_nodes_in_document_order.__name__,
)
