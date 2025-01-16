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


# this module is intentionally not duplicated in the `delb` package

from __future__ import annotations

from collections import deque
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, overload, Optional

from _delb.nodes import (
    DETACHED,
    altered_default_filters,
    new_comment_node,
    new_processing_instruction_node,
    new_tag_node,
    Attribute,
    NodeBase,
    _TagDefinition,
    TagNode,
    TextNode,
)
from _delb.parser import parse_events, Event, EventType, ParserOptions
from _delb.parser.base import TagEventData

if TYPE_CHECKING:
    from collections.abc import Iterator

    from _delb.typing import AttributeAccessor, NodeSource, ParseInput


# defining tag node templates


@overload
def tag(local_name: str):  # pragma: no cover
    ...


@overload
def tag(
    local_name: str, attributes: Mapping[AttributeAccessor, str]
):  # pragma: no cover
    ...


@overload
def tag(local_name: str, child: NodeSource):  # pragma: no cover
    ...


@overload
def tag(local_name: str, children: Sequence[NodeSource]):  # pragma: no cover
    ...


@overload
def tag(
    local_name: str, attributes: Mapping[AttributeAccessor, str], child: NodeSource
):  # pragma: no cover
    ...


@overload
def tag(
    local_name: str,
    attributes: Mapping[AttributeAccessor, str],
    children: Sequence[NodeSource],
):  # pragma: no cover
    ...


def tag(*args):  # noqa: C901
    """
    This function can be used for in-place creation (or call it templating if you
    want to) of :class:`TagNode` instances as:

    - ``node`` argument to methods that add nodes to a tree
    - items in the ``children`` argument of :func:`new_tag_node`

    The first argument to the function is always the local name of the tag node.
    Optionally, the second argument can be a :term:`mapping` that specifies attributes
    for that node.
    The optional last argument is either a single object that will be appended as child
    node or a sequence of such, these objects can be node instances of any type, strings
    (for derived :class:`TextNode` instances) or other definitions from this function
    (for derived :class:`TagNode` instances).

    The actual nodes that are constructed always inherit the namespace of the context
    node they are created in. That also applies to attribute names that are given as
    single string.

    >>> root = new_tag_node('root', children=[
    ...     tag("head", {"lvl": "1"}, "Hello!"),
    ...     tag("items", (
    ...         tag("item1"),
    ...         tag("item2"),
    ...         )
    ...     )
    ... ])
    >>> str(root)
    '<root><head lvl="1">Hello!</head><items><item1/><item2/></items></root>'
    >>> root.append_children(tag("addendum"))  # doctest: +ELLIPSIS
    (<TagNode("addendum", {}, /*/*[3]) [0x...]>,)
    >>> str(root)[-26:]
    '</items><addendum/></root>'
    """

    def prepare_attributes(
        attributes: Mapping[AttributeAccessor, str]
    ) -> dict[AttributeAccessor, str]:
        result: dict[AttributeAccessor, str] = {}

        for key, value in attributes.items():
            if isinstance(value, Attribute):
                result[value._qualified_name] = value.value
            elif isinstance(key, (str, tuple)):
                result[key] = value
            else:
                raise TypeError

        return result

    if len(args) == 1:
        return _TagDefinition(local_name=args[0])

    if len(args) == 2:
        second_arg = args[1]
        if isinstance(second_arg, Mapping):
            return _TagDefinition(
                local_name=args[0], attributes=prepare_attributes(second_arg)
            )
        if isinstance(second_arg, (str, NodeBase, _TagDefinition)):
            return _TagDefinition(local_name=args[0], children=(second_arg,))
        if isinstance(second_arg, Sequence):
            if not all(
                isinstance(x, (str, NodeBase, _TagDefinition)) for x in second_arg
            ):
                raise TypeError(
                    "Either node instances, strings or objects from :func:`delb.tag` "
                    "must be provided as children argument."
                )
            return _TagDefinition(local_name=args[0], children=tuple(second_arg))

    if len(args) == 3:
        third_arg = args[2]
        if isinstance(third_arg, (str, NodeBase, _TagDefinition)):
            return _TagDefinition(
                local_name=args[0],
                attributes=prepare_attributes(args[1]),
                children=(third_arg,),
            )
        if isinstance(third_arg, Sequence):
            if not all(
                isinstance(x, (str, NodeBase, _TagDefinition)) for x in third_arg
            ):
                raise TypeError(
                    "Either node instances, strings or objects from :func:`delb.tag` "
                    "must be provided as children argument."
                )
            return _TagDefinition(
                local_name=args[0],
                attributes=prepare_attributes(args[1]),
                children=tuple(third_arg),
            )

    raise ValueError


# deserializing streams


class TreeBuilder:
    __slots__ = ("event_feed", "open_tags", "options")

    def __init__(self, data: ParseInput, parse_options: ParserOptions):
        self.event_feed = parse_events(data, parse_options)
        self.open_tags: deque[TagNode] = deque()
        self.options = parse_options

    def __iter__(self):
        return self

    def __next__(self) -> NodeBase:
        while True:
            event = next(self.event_feed)
            result = self.handle_event(event)
            if result is not None:
                return result

    def handle_event(self, event: Event) -> NodeBase | None:
        # TODO instantiate objects directly with the native data model
        result: NodeBase | None
        type_, data = event
        if type_ is EventType.Comment:
            assert isinstance(data, str)
            result = new_comment_node(data)
        elif type_ is EventType.ProcessingInstruction:
            result = new_processing_instruction_node(*data)
        elif type_ is EventType.TagStart:
            assert isinstance(data, TagEventData)
            assert isinstance(data.namespace, str)
            self.open_tags.append(
                new_tag_node(
                    local_name=data.local_name,
                    attributes=data.attributes,
                    namespace=data.namespace,
                )
            )
            result = None
        elif type_ is EventType.TagEnd:
            assert isinstance(data, TagEventData)
            if __debug__:
                leaf = self.open_tags[-1]
                assert leaf.namespace == data.namespace
                assert leaf.local_name == data.local_name
                assert leaf.attributes == data.attributes
            result = self.open_tags.pop()
            if self.options.reduce_whitespace:
                # TODO consider xml:space
                # TODO use a specialized variant of _reduce_whitespace_of-descendants
                result._reduce_whitespace()
        elif type_ is EventType.Text:
            assert isinstance(data, str)
            result = TextNode(data, DETACHED)

        if result is not None:
            if self.open_tags:
                # TODO optimize with the native data model
                self.open_tags[-1].append_children(result, clone=False)
            else:
                assert not self.open_tags
                assert isinstance(result, NodeBase)
                return result

        return None


def parse_nodes(
    data: ParseInput, options: Optional[ParserOptions] = None
) -> Iterator[NodeBase]:
    if options is None:
        options = ParserOptions()
    with altered_default_filters():  # TODO remove with optimized TreeBuilder
        yield from TreeBuilder(data, options)


def parse_tree(data: ParseInput, options: Optional[ParserOptions] = None) -> NodeBase:
    result = None
    for node in parse_nodes(data, options):
        if result is not None:
            # TODO
            raise RuntimeError(f"Encountered extra content: {node}")
        result = node

    if result is None:
        # TODO
        raise RuntimeError("No content :-(")

    return node


__all__ = (parse_nodes.__name__, parse_tree.__name__, tag.__name__)
