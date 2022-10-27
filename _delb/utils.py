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

import re
import sys
from collections import defaultdict
from copy import copy
from functools import partial
from string import ascii_lowercase
from typing import (
    TYPE_CHECKING,
    cast,
    Any,
    Callable,
    Iterable,
    Iterator,
    Optional,
    Sequence,
    Union,
)
from warnings import warn

from lxml import etree

from _delb.typing import Filter

if TYPE_CHECKING:
    from _delb.nodes import NodeBase, TagNode

_crunch_whitespace = partial(re.compile(r"\s+").sub, " ")


class _Nodes_Sorter:
    def __init__(self):
        self.__node = None
        self.__items = defaultdict(_Nodes_Sorter)

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
        return str(self.data)

    def __int__(self):
        return int(self.data)

    def __float__(self):
        return float(self.data)

    def __complex__(self):
        return complex(self.data)

    def __hash__(self):
        return hash(self.data)

    def __eq__(self, string):
        return self.data == string

    def __lt__(self, string):
        return self.data < string

    def __le__(self, string):
        return self.data <= string

    def __gt__(self, string):
        return self.data > string

    def __ge__(self, string):
        return self.data >= string

    def __contains__(self, char):
        return char in self.data

    def __len__(self):
        return len(self.data)

    def __getitem__(self, index):
        return self.data[index]

    def __add__(self, other):
        if isinstance(other, str):
            return self.data + other
        return self.data + str(other)

    def __radd__(self, other):
        if isinstance(other, str):
            return other + self.data
        return str(other) + self.data

    def __mul__(self, n):
        return self.data * n

    __rmul__ = __mul__

    def __mod__(self, args):
        return self.data % args

    def __rmod__(self, template):
        return str(template) % self

    def capitalize(self):
        return self.data.capitalize()

    def casefold(self):
        return self.data.casefold()

    def center(self, width, *args):
        return self.data.center(width, *args)

    def count(self, sub, start=0, end=sys.maxsize):
        return self.data.count(sub, start, end)

    def removeprefix(self, prefix):
        return self.data.removeprefix(prefix)

    def removesuffix(self, suffix):
        return self.data.removesuffix(suffix)

    def encode(self, encoding="utf-8", errors="strict"):
        encoding = "utf-8" if encoding is None else encoding
        errors = "strict" if errors is None else errors
        return self.data.encode(encoding, errors)

    def endswith(self, suffix, start=0, end=sys.maxsize):
        return self.data.endswith(suffix, start, end)

    def expandtabs(self, tabsize=8):
        return self.data.expandtabs(tabsize)

    def find(self, sub, start=0, end=sys.maxsize):
        return self.data.find(sub, start, end)

    def format(self, *args, **kwds):
        return self.data.format(*args, **kwds)

    def format_map(self, mapping):
        return self.data.format_map(mapping)

    def index(self, sub, start=0, end=sys.maxsize):
        return self.data.index(sub, start, end)

    def isalpha(self):
        return self.data.isalpha()

    def isalnum(self):
        return self.data.isalnum()

    def isascii(self):
        return self.data.isascii()

    def isdecimal(self):
        return self.data.isdecimal()

    def isdigit(self):
        return self.data.isdigit()

    def isidentifier(self):
        return self.data.isidentifier()

    def islower(self):
        return self.data.islower()

    def isnumeric(self):
        return self.data.isnumeric()

    def isprintable(self):
        return self.data.isprintable()

    def isspace(self):
        return self.data.isspace()

    def istitle(self):
        return self.data.istitle()

    def isupper(self):
        return self.data.isupper()

    def join(self, seq):
        return self.data.join(seq)

    def ljust(self, width, *args):
        return self.data.ljust(width, *args)

    def lower(self):
        return self.data.lower()

    def lstrip(self, chars=None):
        return self.data.lstrip(chars)

    def partition(self, sep):
        return self.data.partition(sep)

    def replace(self, old, new, maxsplit=-1):
        return self.data.replace(old, new, maxsplit)

    def rfind(self, sub, start=0, end=sys.maxsize):
        return self.data.rfind(sub, start, end)

    def rindex(self, sub, start=0, end=sys.maxsize):
        return self.data.rindex(sub, start, end)

    def rjust(self, width, *args):
        return self.data.rjust(width, *args)

    def rpartition(self, sep):
        return self.data.rpartition(sep)

    def rstrip(self, chars=None):
        return self.data.rstrip(chars)

    def split(self, sep=None, maxsplit=-1):
        return self.data.split(sep, maxsplit)

    def rsplit(self, sep=None, maxsplit=-1):
        return self.data.rsplit(sep, maxsplit)

    def splitlines(self, keepends=False):
        return self.data.splitlines(keepends)

    def startswith(self, prefix, start=0, end=sys.maxsize):
        return self.data.startswith(prefix, start, end)

    def strip(self, chars=None):
        return self.data.strip(chars)

    def swapcase(self):
        return self.data.swapcase()

    def title(self):
        return self.data.title()

    def translate(self, *args):
        return self.data.translate(*args)

    def upper(self):
        return self.data.upper()

    def zfill(self, width):
        return self.data.zfill(width)


def _better_call(f: Union[Callable, property]) -> Callable:
    def decorator(d: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            """:meta category: deprecated"""
            warn(
                f"{d.__name__} is deprecated, use {f.__name__} instead.",
                category=DeprecationWarning,
            )
            return f(*args, **kwargs)

        d.__doc__ = ":meta: private"
        return wrapper

    return decorator


def _better_yield(f: Callable) -> Callable:
    def decorator(d: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            """:meta category: deprecated"""
            warn(
                f"{d.__name__} is deprecated, use {f.__name__} instead.",
                category=DeprecationWarning,
            )
            yield from f(*args, **kwargs)

        return wrapper

    return decorator


def _copy_root_siblings(source: etree._Element, target: etree._Element):
    stack = []
    current_element = source.getprevious()
    while current_element is not None:
        stack.append(current_element)
        current_element = current_element.getprevious()
    while stack:
        target.addprevious(copy(stack.pop()))

    stack = []
    current_element = source.getnext()
    while current_element is not None:
        stack.append(current_element)
        current_element = current_element.getnext()
    while stack:
        target.addnext(copy(stack.pop()))


def first(iterable: Iterable) -> Optional[Any]:
    """
    Returns the first item of the given :term:`iterable` or ``None`` if it's empty.
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


def get_traverser(from_left=True, depth_first=True, from_top=True):
    """
    Returns a function that can be used to traverse a (sub)tree with the given node as
    root. While traversing the given root node is yielded at some point.

    The returned functions have this signature:

    .. code-block:: python

        def traverser(root: NodeBase, *filters: Filter) -> Iterator[NodeBase]:
            ...

    :param from_left: The traverser yields sibling nodes from left to right if ``True``,
                      or starting from the right if ``False``.
    :param depth_first: The child nodes resp. the parent node are yielded before the
                        siblings of a node by a traverser if ``True``. Siblings are
                        favored if ``False``.
    :param from_top: The traverser starts yielding nodes with the lowest depth if
                     ``True``. When ``False``, again, the opposite is in effect.
    """

    result = TRAVERSERS.get((from_left, depth_first, from_top))
    if result is None:
        raise NotImplementedError
    return result


def _is_node_of_type(node: NodeBase, type_name: str) -> bool:
    if type_name not in {
        "CommentNode",
        "ProcessingInstructionNode",
        "TagNode",
        "TextNode",
    }:
        raise ValueError
    return (
        node.__class__.__module__ == f"{__package__}.nodes"
        and node.__class__.__qualname__ == type_name
    )


def last(iterable: Iterable) -> Optional[Any]:
    """
    Returns the last item of the given :term:`iterable` or ``None`` if it's empty.
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


# REMOVE eventually
def _random_unused_prefix(namespaces: "etree._NSMap") -> str:
    for prefix in ascii_lowercase:
        if prefix not in namespaces:
            return prefix
    raise RuntimeError(
        "You really are using all latin letters as prefix in a document. "
        "Fair enough, please open a bug report."
    )


def register_namespace(prefix: str, namespace: str):
    """
    Registers a namespace prefix that newly created :class:`TagNode` instances in that
    namespace will use in serializations.

    The registry is global, and any existing mapping for either the given prefix or the
    namespace URI will be removed. It has however no effect on the serialization of
    existing nodes, see :meth:`Document.cleanup_namespace` for that.

    :param prefix: The prefix to register.
    :param namespace: The targeted namespace.
    """
    warn(
        "This function will be replaced with a different mechanism in a future version "
        "without a backward-compatible facilitation through this function.",
        category=PendingDeprecationWarning,
    )
    etree.register_namespace(prefix, namespace)


def sort_nodes_in_document_order(nodes: Iterable[NodeBase]) -> Iterator[NodeBase]:
    sorter = _Nodes_Sorter()
    for node in nodes:
        if not _is_node_of_type(node, "TagNode"):
            raise NotImplementedError(
                "Support for sorting other node types than TagNodes isn't scheduled"
                "yet."
            )
        node = cast("TagNode", node)
        if node.parent is None:
            path = []
        else:
            path = [int(x[2:-1]) for x in node.location_path.split("/")[1:]]
        sorter.add(path, node)
    yield from sorter.emit()


# tree traversers


def traverse_df_ltr_btt(root: "NodeBase", *filters: Filter) -> Iterator["NodeBase"]:
    def yield_children(node):
        for child in tuple(node.iterate_children(*filters)):
            yield from yield_children(child)
        yield node

    yield from yield_children(root)


def traverse_df_ltr_ttb(root: "NodeBase", *filters: Filter) -> Iterator["NodeBase"]:
    yield root
    yield from root.iterate_descendants(*filters)


TRAVERSERS = {
    (True, True, True): traverse_df_ltr_ttb,
    (True, True, False): traverse_df_ltr_btt,
}


__all__ = (
    first.__name__,
    get_traverser.__name__,
    last.__name__,
    register_namespace.__name__,
    sort_nodes_in_document_order.__name__,
)
