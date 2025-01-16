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
from collections import defaultdict
from collections.abc import Iterable, Iterator, Sequence
from functools import partial
from typing import TYPE_CHECKING, cast, Any, Final, Optional


if TYPE_CHECKING:
    from _delb.nodes import NodeBase, TagNode
    from _delb.typing import Filter, NodeTypeNameLiteral


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
    if isinstance(iterable, Iterator):
        try:
            return next(iterable)
        except StopIteration:
            return None
    elif isinstance(iterable, Sequence):
        return iterable[0] if len(iterable) else None
    else:
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

    While traversing the given root node is yielded at some point.

    The returned functions have this signature:

    .. code-block:: python

        def traverser(root: NodeBase, *filters: Filter) -> Iterator[NodeBase]:
            ...
    """
    result = TRAVERSERS.get((from_left, depth_first, from_top))
    if result is None:
        raise NotImplementedError
    return result


def _is_node_of_type(
    node: NodeBase,
    type_name: NodeTypeNameLiteral,
) -> bool:
    return (
        node.__class__.__module__ == f"{__package__}.nodes"
        and node.__class__.__qualname__ == type_name
    )


def last(iterable: Iterable) -> Optional[Any]:
    """
    Returns the last item of the given :term:`iterable` or :obj:`None` if it's empty.
    Note that the whole :term:`iterator` is consumed when such is given.
    """
    if isinstance(iterable, Iterator):
        result = None
        for result in iterable:
            pass
        return result
    elif isinstance(iterable, Sequence):
        return iterable[-1] if len(iterable) else None
    else:
        raise TypeError


def _sort_nodes_in_document_order(nodes: Iterable[NodeBase]) -> Iterator[NodeBase]:
    node_index_cache: dict[int, int] = {}
    sorter = _NodesSorter()
    for node in nodes:
        if not _is_node_of_type(node, "TagNode"):
            raise NotImplementedError(
                "Support for sorting other node types than TagNodes isn't scheduled"
                "yet."
            )

        node = cast("TagNode", node)
        ancestors_indexes = []

        cursor = node
        while cursor.parent is not None:
            node_id = id(cursor)
            if node_id in node_index_cache:
                index = node_index_cache[node_id]
            else:
                assert cursor.index is not None
                node_index_cache[node_id] = index = cursor.index
            ancestors_indexes.append(index)
            cursor = cursor.parent

        sorter.add(tuple(reversed(ancestors_indexes)), node)
    yield from sorter.emit()


# tree traversers


def traverse_bf_ltr_ttb(root: NodeBase, *filters: Filter) -> Iterator[NodeBase]:
    if all(f(root) for f in filters):
        yield root

    queue = list(root.iterate_children())
    while queue:
        node = queue.pop(0)
        if _is_node_of_type(node, "TagNode"):
            queue.extend(node.iterate_children())
        if all(f(node) for f in filters):
            yield node


def traverse_df_ltr_btt(root: NodeBase, *filters: Filter) -> Iterator[NodeBase]:
    def yield_children(node):
        for child in tuple(node.iterate_children(*filters)):
            yield from yield_children(child)
        yield node

    yield from yield_children(root)


def traverse_df_ltr_ttb(root: NodeBase, *filters: Filter) -> Iterator[NodeBase]:
    yield root
    yield from root.iterate_descendants(*filters)


TRAVERSERS = {
    (True, False, True): traverse_bf_ltr_ttb,
    (True, True, True): traverse_df_ltr_ttb,
    (True, True, False): traverse_df_ltr_btt,
}


__all__: tuple[str, ...] = (
    first.__name__,
    get_traverser.__name__,
    last.__name__,
    _sort_nodes_in_document_order.__name__,
)
