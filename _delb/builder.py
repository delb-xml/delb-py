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

import warnings
from collections import deque
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, overload, Optional

from _delb.exceptions import ParsingEmptyStream, ParsingValidityError
from _delb.names import XML_NAMESPACE
from _delb.nodes import (
    DETACHED,
    altered_default_filters,
    new_comment_node,
    new_processing_instruction_node,
    new_tag_node,
    _reduce_whitespace_between_siblings,
    _wrapper_cache,
    Attribute,
    NodeBase,
    _TagDefinition,
    TagNode,
    TextNode,
)
from _delb.parser import Event, EventType, ParserOptions, TagEventData, parse_events


if TYPE_CHECKING:
    from collections.abc import Iterator

    from _delb.typing import AttributeAccessor, NodeSource, InputStream


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
        attributes: Mapping[AttributeAccessor, str],
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
    __slots__ = (
        "children",
        "event_feed",
        "options",
        "preserve_space",
        "started_tags",
        "xml_ids",
    )

    def __init__(
        self, data: InputStream, parse_options: ParserOptions, base_url: str | None
    ):
        self.children: deque[list[NodeBase]] = deque()
        self.event_feed = parse_events(data, parse_options, base_url)
        self.options = parse_options
        self.preserve_space: deque[bool] = deque()
        self.started_tags: deque[TagNode] = deque()
        self.xml_ids: set[str] = set()

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
            assert isinstance(data, tuple)
            result = new_processing_instruction_node(data[0], data[1])
        elif type_ is EventType.TagStart:
            assert isinstance(data, TagEventData)
            self.handle_tag_start(data)
            result = None
        elif type_ is EventType.TagEnd:
            assert isinstance(data, TagEventData)
            result = self.handle_tag_end(data)
        elif type_ is EventType.Text:
            assert isinstance(data, str)
            result = TextNode(data, DETACHED)

        if result is not None:
            if self.started_tags:
                self.children[-1].append(result)
            else:
                assert not self.children
                assert not self.started_tags
                assert not self.preserve_space
                assert isinstance(result, NodeBase)
                self.xml_ids.clear()
                return result

        return None

    def handle_tag_end(self, data: TagEventData | None) -> TagNode:
        result = self.started_tags.pop()
        if __debug__ and data:
            assert result.namespace == data.namespace
            assert result.local_name == data.local_name
            if data.attributes is not None:
                assert result.attributes == data.attributes

        children = self.children.pop()
        if (not self.preserve_space.pop()) and children:
            _reduce_whitespace_between_siblings(children, False)

        # TODO optimize with the native data model
        for node in children:
            result.append_children(node)

        return result

    def handle_tag_start(self, data):
        assert isinstance(data.namespace, str)

        if (id_ := data.attributes.get((XML_NAMESPACE, "id"))) is not None:
            if id_ in self.xml_ids:
                raise ParsingValidityError(f"Redundantly used xml:id: {id_}")
            else:
                self.xml_ids.add(id_)

        self.children.append([])

        self.started_tags.append(
            new_tag_node(
                local_name=data.local_name,
                attributes=data.attributes,
                namespace=data.namespace,
            )
        )

        if not self.options.reduce_whitespace:
            self.preserve_space.append(True)
            return

        xml_space = data.attributes.get((XML_NAMESPACE, "space"))

        if xml_space not in (None, "default", "preserve"):
            warnings.warn(
                "Encountered and ignoring an invalid `xml:space` attribute: "
                + xml_space,
                category=UserWarning,
            )

        if not self.preserve_space:
            self.preserve_space.append(xml_space == "preserve")
            return

        if xml_space is None:  # most common
            self.preserve_space.append(self.preserve_space[-1])
        elif xml_space == "default":
            self.preserve_space.append(False)
        elif xml_space == "preserve":
            self.preserve_space.append(True)
        else:  # invalid values
            self.preserve_space.append(self.preserve_space[-1])


def parse_nodes(
    data: InputStream,
    options: Optional[ParserOptions] = None,
    *,
    base_url: str | None = None,
) -> Iterator[NodeBase]:
    """Parses the provided input data to a sequence of nodes."""
    if options is None:
        options = ParserOptions()
    # TODO remove contexts with optimized TreeBuilder
    with altered_default_filters(), _wrapper_cache:
        yield from TreeBuilder(data, options, base_url)


def parse_tree(
    data: InputStream,
    options: Optional[ParserOptions] = None,
    *,
    base_url: str | None = None,
) -> NodeBase:
    """Parses the provided input to a single node."""
    result = None
    for node in parse_nodes(data, options, base_url=base_url):
        if result is not None:
            raise ParsingValidityError("The stream contained extra contents.", node)
        result = node

    if result is None:
        raise ParsingEmptyStream()

    return node


__all__ = (parse_nodes.__name__, parse_tree.__name__, tag.__name__)
