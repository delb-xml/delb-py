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


import re
from copy import copy
from functools import lru_cache, partial
from string import ascii_lowercase
from typing import (
    TYPE_CHECKING,
    Any,
    Iterable,
    Iterator,
    List,
    Optional,
    Sequence,
)

from cssselect import GenericTranslator  # type: ignore
from lxml import etree

from _delb.typing import Filter

if TYPE_CHECKING:
    from _delb.nodes import NodeBase


DEFAULT_PARSER = etree.XMLParser(remove_blank_text=False)


_crunch_whitespace = partial(re.compile(r"\s+").sub, " ")
css_translator = GenericTranslator()


def _collect_subclasses(cls: type, classes: List[type]):
    for subclass in cls.__subclasses__():
        _collect_subclasses(subclass, classes)
        classes.append(subclass)


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


# TODO make cachesize configurable via environment variable?
@lru_cache(maxsize=64)
def _css_to_xpath(expression: str) -> str:
    return css_translator.css_to_xpath(expression, prefix="descendant-or-self::")


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
    etree.register_namespace(prefix, namespace)


# tree traversers


def traverse_df_ltr_btt(root: "NodeBase", *filters: Filter) -> Iterator["NodeBase"]:
    def yield_children(node):
        for child in tuple(node.child_nodes(*filters)):
            yield from yield_children(child)
        yield node

    yield from yield_children(root)


def traverse_df_ltr_ttb(root: "NodeBase", *filters: Filter) -> Iterator["NodeBase"]:
    yield root
    yield from root.child_nodes(*filters, recurse=True)


TRAVERSERS = {
    (True, True, True): traverse_df_ltr_ttb,
    (True, True, False): traverse_df_ltr_btt,
}


__all__ = (
    first.__name__,
    get_traverser.__name__,
    last.__name__,
    register_namespace.__name__,
)
