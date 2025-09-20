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
from typing import TYPE_CHECKING, Any, Final, Optional

from _delb.typing import _DocumentNodeType, TagNodeType


if TYPE_CHECKING:
    from _delb.typing import Filter, XMLNodeType


_crunch_whitespace: Final = partial(re.compile(r"\s+").sub, " ")


class _NodesSorter:
    def __init__(self):
        self.__node = None
        self.__items: Final = defaultdict(_NodesSorter)

    def add(self, path: Sequence[int], node: TagNodeType):
        assert isinstance(node, TagNodeType)
        if path:
            self.__items[path[0]].add(path[1:], node)
        else:
            self.__node = node

    def emit(self) -> Iterator[XMLNodeType]:
        if self.__node is not None:
            yield self.__node
        for index in sorted(self.__items):
            yield from self.__items[index].emit()


class _StringMixin:  # pragma: no cover
    # copied from CPython 3.10.0's stdlib collections.UserString and adjusted

    __slots__ = ()

    def __int__(self):
        return int(str(self))

    def __float__(self):
        return float(str(self))

    def __complex__(self):
        return complex(str(self))

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, string):
        return str(self) == string

    def __lt__(self, string):
        return str(self) < string

    def __le__(self, string):
        return str(self) <= string

    def __gt__(self, string):
        return str(self) > string

    def __ge__(self, string):
        return str(self) >= string

    def __contains__(self, char):
        return char in str(self)

    def __len__(self):
        return len(str(self))

    def __getitem__(self, index):
        return str(self)[index]

    def __add__(self, other):
        if isinstance(other, str):
            return str(self) + other
        return str(self) + str(other)

    def __radd__(self, other):
        if isinstance(other, str):
            return other + str(self)
        return str(other) + str(self)

    def __mul__(self, n):
        return str(self) * n

    __rmul__ = __mul__

    def __mod__(self, args):
        return str(self) % args

    def __rmod__(self, template):
        return str(template) % self

    def capitalize(self):
        return str(self).capitalize()

    def casefold(self):
        return str(self).casefold()

    def center(self, width, *args):
        return str(self).center(width, *args)

    def count(self, sub, start=0, end=sys.maxsize):
        return str(self).count(sub, start, end)

    def removeprefix(self, prefix):
        return str(self).removeprefix(prefix)

    def removesuffix(self, suffix):
        return str(self).removesuffix(suffix)

    def encode(self, encoding="utf-8", errors="strict"):
        encoding = "utf-8" if encoding is None else encoding
        errors = "strict" if errors is None else errors
        return str(self).encode(encoding, errors)

    def endswith(self, suffix, start=0, end=sys.maxsize):
        return str(self).endswith(suffix, start, end)

    def expandtabs(self, tabsize=8):
        return str(self).expandtabs(tabsize)

    def find(self, sub, start=0, end=sys.maxsize):
        return str(self).find(sub, start, end)

    def format(self, *args, **kwds):
        return str(self).format(*args, **kwds)

    def format_map(self, mapping):
        return str(self).format_map(mapping)

    def index(self, sub, start=0, end=sys.maxsize):
        return str(self).index(sub, start, end)

    def isalpha(self):
        return str(self).isalpha()

    def isalnum(self):
        return str(self).isalnum()

    def isascii(self):
        return str(self).isascii()

    def isdecimal(self):
        return str(self).isdecimal()

    def isdigit(self):
        return str(self).isdigit()

    def isidentifier(self):
        return str(self).isidentifier()

    def islower(self):
        return str(self).islower()

    def isnumeric(self):
        return str(self).isnumeric()

    def isprintable(self):
        return str(self).isprintable()

    def isspace(self):
        return str(self).isspace()

    def istitle(self):
        return str(self).istitle()

    def isupper(self):
        return str(self).isupper()

    def join(self, seq):
        return str(self).join(seq)

    def ljust(self, width, *args):
        return str(self).ljust(width, *args)

    def lower(self):
        return str(self).lower()

    def lstrip(self, chars=None):
        return str(self).lstrip(chars)

    def partition(self, sep):
        return str(self).partition(sep)

    def replace(self, old, new, maxsplit=-1):
        return str(self).replace(old, new, maxsplit)

    def rfind(self, sub, start=0, end=sys.maxsize):
        return str(self).rfind(sub, start, end)

    def rindex(self, sub, start=0, end=sys.maxsize):
        return str(self).rindex(sub, start, end)

    def rjust(self, width, *args):
        return str(self).rjust(width, *args)

    def rpartition(self, sep):
        return str(self).rpartition(sep)

    def rstrip(self, chars=None):
        return str(self).rstrip(chars)

    def split(self, sep=None, maxsplit=-1):
        return str(self).split(sep, maxsplit)

    def rsplit(self, sep=None, maxsplit=-1):
        return str(self).rsplit(sep, maxsplit)

    def splitlines(self, keepends=False):
        return str(self).splitlines(keepends)

    def startswith(self, prefix, start=0, end=sys.maxsize):
        return str(self).startswith(prefix, start, end)

    def strip(self, chars=None):
        return str(self).strip(chars)

    def swapcase(self):
        return str(self).swapcase()

    def title(self):
        return str(self).title()

    def translate(self, *args):
        return str(self).translate(*args)

    def upper(self):
        return str(self).upper()

    def zfill(self, width):
        return str(self).zfill(width)


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

        def traverser(root: XMLNodeType, *filters: Filter) -> Iterator[XMLNodeType]:
            ...
    """
    if (result := TRAVERSERS.get((from_left, depth_first, from_top))) is None:
        raise NotImplementedError
    return result


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


def _sort_nodes_in_document_order(
    nodes: Iterable[XMLNodeType],
) -> Iterator[XMLNodeType]:
    node_index_cache: dict[int, int] = {}
    sorter = _NodesSorter()

    for node in nodes:  # pragma: no cover
        if not isinstance(node, TagNodeType):
            raise NotImplementedError(
                "Support for sorting other node types than TagNodes isn't scheduled"
                "yet."
            )

        ancestors_indexes: deque[int] = deque()

        for cursor in chain((node,), node._iterate_ancestors()):
            if cursor._parent is None or isinstance(cursor._parent, _DocumentNodeType):
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


def traverse_bf_ltr_ttb(root: XMLNodeType, *filters: Filter) -> Iterator[XMLNodeType]:
    queue = deque((root,))
    while queue:
        node = queue.popleft()
        if isinstance(node, TagNodeType):
            queue.extend(node._child_nodes)
        if all(f(node) for f in filters):
            yield node


def traverse_df_ltr_btt(root: XMLNodeType, *filters: Filter) -> Iterator[XMLNodeType]:
    stack = [(root, deque(root._child_nodes))]

    while stack:
        node, remaining_children = stack.pop()

        while remaining_children:
            child = remaining_children.popleft()
            if isinstance(child, TagNodeType) and child._child_nodes:
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


def traverse_df_ltr_ttb(root: XMLNodeType, *filters: Filter) -> Iterator[XMLNodeType]:
    for node in chain((root,), root._iterate_descendants()):
        if all(f(node) for f in filters):
            yield node


def traverse_df_rtl_btt(root: XMLNodeType, *filters: Filter) -> Iterator[XMLNodeType]:
    for node in root._iterate_reversed_descendants():
        if all(f(node) for f in filters):
            yield node


TRAVERSERS: Final = {
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
