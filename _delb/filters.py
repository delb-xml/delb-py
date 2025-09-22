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

from contextlib import contextmanager
from typing import TYPE_CHECKING, Final

from _delb.typing import (
    CommentNodeType,
    _DocumentNodeType,
    Filter,
    ProcessingInstructionNodeType,
    TagNodeType,
    TextNodeType,
)

if TYPE_CHECKING:
    from _delb.typing import XMLNodeType


# default filters


def _is_tag_or_text_node(node: XMLNodeType) -> bool:
    return isinstance(node, (TagNodeType, TextNodeType))


default_filters: Final[list[tuple[Filter, ...]]] = [(_is_tag_or_text_node,)]


@contextmanager
def altered_default_filters(*filter: Filter, extend: bool = False):
    """
    This function can be either used as as :term:`context manager` or :term:`decorator`
    to define a set of :obj:`default_filters` for the encapsuled code block or callable.

    :param filter: The filters to set or append.
    :param extend: Extends the currently active filters with the given ones instead of
                   replacing them.

    These are then applied in all operations that allow node filtering, like
    :meth:`delb.nodes.TagNode.iterate_children`. Mind that they also affect a node's
    index property as well as indexed access to child nodes and properties like
    :attr:`nodes.delb.TagNode.first_child`.

    >>> root = Document(
    ...     '<root xmlns="foo"><a/><!--x--><b/><!--y--><c/></root>'
    ... ).root
    >>> with altered_default_filters(is_comment_node):
    ...     print([x.content for x in root.iterate_children()])
    ['x', 'y']

    As the default filters shadow comments and processing instructions by default,
    use no argument to unset this in order to access all type of nodes.
    """
    if extend:
        default_filters.append(default_filters[-1] + filter)
    else:
        default_filters.append(filter)

    try:
        yield
    finally:
        default_filters.pop()


# contributed node filters and filter wrappers


def any_of(*filter: Filter) -> Filter:
    """
    A node filter wrapper that matches when any of the given filters is matching, like a
    boolean ``or``.
    """

    def any_of_wrapper(node: XMLNodeType) -> bool:
        return any(x(node) for x in filter)

    return any_of_wrapper


def is_comment_node(node: XMLNodeType) -> bool:
    """
    A node filter that matches :class:`delb.typing.CommentNodeType` instances.
    """
    return isinstance(node, CommentNodeType)


def is_processing_instruction_node(node: XMLNodeType) -> bool:
    """
    A node filter that matches :class:`delb.typing.ProcessingInstructionNodeType`
    instances.
    """
    return isinstance(node, ProcessingInstructionNodeType)


def is_root_node(node: XMLNodeType) -> bool:
    """
    A node filter that matches root nodes.
    """
    return node._parent is None or isinstance(node._parent, _DocumentNodeType)


def is_tag_node(node: XMLNodeType) -> bool:
    """
    A node filter that matches :class:`delb.typing.TagNodeType` instances.
    """
    return isinstance(node, TagNodeType)


def is_text_node(node: XMLNodeType) -> bool:
    """
    A node filter that matches :class:`delb.typing.TextNodeType` instances.
    """
    return isinstance(node, TextNodeType)


def not_(*filter: Filter) -> Filter:
    """
    A node filter wrapper that matches when the given filter is not matching,
    like a boolean ``not``.
    """

    def not_wrapper(node: XMLNodeType) -> bool:
        return not all(f(node) for f in filter)

    return not_wrapper


#


__all__ = (
    altered_default_filters.__name__,
    any_of.__name__,
    is_comment_node.__name__,
    is_processing_instruction_node.__name__,
    is_root_node.__name__,
    is_tag_node.__name__,
    is_text_node.__name__,
    not_.__name__,
)
