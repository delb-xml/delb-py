# Copyright (C) 2018-'26  Frank Sachsenheim
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
from collections.abc import Iterable, Iterator, Mapping, Sequence
from functools import partial
from itertools import chain
from typing import TYPE_CHECKING, Any, Final, Optional, cast

from _delb.typing import _DocumentNodeType, TagNodeType

if TYPE_CHECKING:
    from _delb.typing import Filter, T, _TranslateTable, Traverser, XMLNodeType


_crunch_whitespace: Final = partial(re.compile(r"\s+").sub, " ")


class _NodesSorter:
    def __init__(self) -> None:
        self.__node: TagNodeType | None = None
        self.__items: Final[defaultdict[int, _NodesSorter]] = defaultdict(_NodesSorter)

    def add(self, path: Sequence[int], node: TagNodeType) -> None:
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

    def __int__(self) -> int:
        return int(str(self))

    def __float__(self) -> float:
        return float(str(self))

    def __complex__(self) -> complex:
        return complex(str(self))

    def __hash__(self) -> int:
        return hash(str(self))

    def __lt__(self, string: str) -> bool:
        return str(self) < string

    def __gt__(self, string: str) -> bool:
        return str(self) > string

    def __ge__(self, string: str) -> bool:
        return str(self) >= string

    def __contains__(self, char: str) -> bool:
        return char in str(self)

    def __len__(self) -> int:
        return len(str(self))

    def __getitem__(self, index: int | slice) -> str:
        return str(self)[index]

    def __add__(self, other: Any) -> str:
        if isinstance(other, str):
            return str(self) + other
        return str(self) + str(other)

    def __radd__(self, other: Any) -> str:
        if isinstance(other, str):
            return other + str(self)
        return str(other) + str(self)

    def __mul__(self, n: int) -> str:
        return str(self) * n

    __rmul__ = __mul__

    def __mod__(self, args: Sequence[Any]) -> str:
        return str(self) % args

    def __rmod__(self, template: str) -> str:
        return str(template) % self

    def capitalize(self) -> str:
        return str(self).capitalize()

    def casefold(self) -> str:
        return str(self).casefold()

    def center(self, width: int, fillchar: str = " ") -> str:
        return str(self).center(width, fillchar)

    def count(self, sub: str, start: int = 0, end: int = sys.maxsize) -> int:
        return str(self).count(sub, start, end)

    def removeprefix(self, prefix: str) -> str:
        return str(self).removeprefix(prefix)

    def removesuffix(self, suffix: str) -> str:
        return str(self).removesuffix(suffix)

    def encode(self, encoding: str = "utf-8", errors: str = "strict") -> bytes:
        encoding = "utf-8" if encoding is None else encoding
        errors = "strict" if errors is None else errors
        return str(self).encode(encoding, errors)

    def endswith(self, suffix: str, start: int = 0, end: int = sys.maxsize) -> bool:
        return str(self).endswith(suffix, start, end)

    def expandtabs(self, tabsize: int = 8) -> str:
        return str(self).expandtabs(tabsize)

    def find(self, sub: str, start: int = 0, end: int = sys.maxsize) -> int:
        return str(self).find(sub, start, end)

    def format(self, *args: str, **kwds: str) -> str:
        return str(self).format(*args, **kwds)

    def format_map(self, mapping: Mapping[str, Any]) -> str:
        return str(self).format_map(mapping)

    def index(self, sub: str, start: int = 0, end: int = sys.maxsize) -> int:
        return str(self).index(sub, start, end)

    def isalpha(self) -> bool:
        return str(self).isalpha()

    def isalnum(self) -> bool:
        return str(self).isalnum()

    def isascii(self) -> bool:
        return str(self).isascii()

    def isdecimal(self) -> bool:
        return str(self).isdecimal()

    def isdigit(self) -> bool:
        return str(self).isdigit()

    def isidentifier(self) -> bool:
        return str(self).isidentifier()

    def islower(self) -> bool:
        return str(self).islower()

    def isnumeric(self) -> bool:
        return str(self).isnumeric()

    def isprintable(self) -> bool:
        return str(self).isprintable()

    def isspace(self) -> bool:
        return str(self).isspace()

    def istitle(self) -> bool:
        return str(self).istitle()

    def isupper(self) -> bool:
        return str(self).isupper()

    def join(self, seq: Iterable[str]) -> str:
        return str(self).join(seq)

    def ljust(self, width: int, fillchar: str = "") -> str:
        return str(self).ljust(width, fillchar)

    def lower(self) -> str:
        return str(self).lower()

    def lstrip(self, chars: Optional[str] = None) -> str:
        return str(self).lstrip(chars)

    def partition(self, sep: str) -> tuple[str, str, str]:
        return str(self).partition(sep)

    def replace(self, old: str, new: str, count: int = -1) -> str:
        return str(self).replace(old, new, count)

    def rfind(self, sub: str, start: int = 0, end: int = sys.maxsize) -> int:
        return str(self).rfind(sub, start, end)

    def rindex(self, sub: str, start: int = 0, end: int = sys.maxsize) -> int:
        return str(self).rindex(sub, start, end)

    def rjust(self, width: int, fillchar: str = " ") -> str:
        return str(self).rjust(width, fillchar)

    def rpartition(self, sep: str) -> tuple[str, str, str]:
        return str(self).rpartition(sep)

    def rstrip(self, chars: Optional[str] = None) -> str:
        return str(self).rstrip(chars)

    def split(self, sep: Optional[str] = None, maxsplit: int = -1) -> list[str]:
        return str(self).split(sep, maxsplit)

    def rsplit(self, sep: Optional[str] = None, maxsplit: int = -1) -> list[str]:
        return str(self).rsplit(sep, maxsplit)

    def splitlines(self, keepends: bool = False) -> list[str]:
        return str(self).splitlines(keepends)

    def startswith(self, prefix: str, start: int = 0, end: int = sys.maxsize) -> bool:
        return str(self).startswith(prefix, start, end)

    def strip(self, chars: Optional[str] = None) -> str:
        return str(self).strip(chars)

    def swapcase(self) -> str:
        return str(self).swapcase()

    def title(self) -> str:
        return str(self).title()

    def translate(self, table: _TranslateTable) -> str:
        return str(self).translate(table)

    def upper(self) -> str:
        return str(self).upper()

    def zfill(self, width: int) -> str:
        return str(self).zfill(width)


def first(iterable: Iterable[T]) -> Optional[T]:
    """
    Returns the first item of the given :term:`iterable` or :obj:`None` if it's empty.
    Note that the first item is consumed when the iterable is an :term:`iterator`.
    """
    match iterable:
        case Iterator():
            try:
                return next(cast("Iterator[T]", iterable))
            except StopIteration:
                return None
        case Sequence():
            return iterable[0] if len(iterable) else None
        case _:
            raise TypeError


def get_traverser(
    *, from_left: bool = True, depth_first: bool = True, from_top: bool = True
) -> Traverser:
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


def last(iterable: Iterable[T]) -> Optional[T]:
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
