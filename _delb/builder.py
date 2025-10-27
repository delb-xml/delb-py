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
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, overload, Final, Optional

from _delb.exceptions import ParsingValidityError
from _delb.names import XML_NAMESPACE
from _delb.nodes import (
    _reduce_whitespace_between_siblings,
    Attribute,
    CommentNode,
    ProcessingInstructionNode,
    _TagDefinition,
    TagNode,
    TextNode,
)
from _delb.parser import Event, EventType, ParserOptions, TagEventData, parse_events
from _delb.typing import XMLNodeType


if TYPE_CHECKING:
    from collections.abc import Iterator

    from _delb.typing import (
        AttributeAccessor,
        NodeSource,
        InputStream,
        TagNodeType,
    )


# defining tag node templates


@overload
def tag(local_name: str): ...


@overload
def tag(local_name: str, attributes: Mapping[AttributeAccessor, str]): ...


@overload
def tag(local_name: str, child: NodeSource): ...


@overload
def tag(local_name: str, children: Sequence[NodeSource]): ...


@overload
def tag(
    local_name: str, attributes: Mapping[AttributeAccessor, str], child: NodeSource
): ...


@overload
def tag(
    local_name: str,
    attributes: Mapping[AttributeAccessor, str],
    children: Sequence[NodeSource],
): ...


def tag(*args):  # noqa: C901
    """
    This function can be used for in-place creation (or call it templating if you
    want to) of :class:`delb.nodes.TagNode` instances as:

    - ``node`` argument to methods that add nodes to a tree
    - items in the ``children`` argument of :class:`delb.nodes.TagNode`

    The first argument to the function is always the local name of the tag node.
    Optionally, the second argument can be a :term:`mapping` that specifies attributes
    for that node.
    The optional last argument is either a single object that will be appended as child
    node or a sequence of such, these objects can be node instances of any type, strings
    (for derived :class:`delb.nodes.TextNode` instances) or other definitions from this
    function (for derived :class:`delb.nodes.TagNode` instances).

    The actual nodes that are constructed always inherit the namespace of the context
    node they are created in. That also applies to attribute names that are given as
    single string.

    >>> root = TagNode('root', children=[
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
    (<TagNode("{}addendum", {}, /*/*[3]) [0x...]>,)
    >>> str(root)[-26:]
    '</items><addendum/></root>'
    """

    def prepare_attributes(
        attributes: Mapping[AttributeAccessor, str],
    ) -> dict[AttributeAccessor, str]:
        result: dict[AttributeAccessor, str] = {}

        for key, value in attributes.items():
            match value:
                case Attribute():
                    result[(value.namespace, value.local_name)] = value.value
                case str() | tuple():
                    result[key] = value
                case _:
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
        if isinstance(second_arg, (str, XMLNodeType, _TagDefinition)):
            return _TagDefinition(local_name=args[0], children=(second_arg,))
        if isinstance(second_arg, Sequence):
            if not all(
                isinstance(x, (str, XMLNodeType, _TagDefinition)) for x in second_arg
            ):
                raise TypeError(
                    "Either node instances, strings or objects from :func:`delb.tag` "
                    "must be provided as children argument."
                )
            return _TagDefinition(local_name=args[0], children=tuple(second_arg))

    if len(args) == 3:
        third_arg = args[2]
        if isinstance(third_arg, (str, XMLNodeType, _TagDefinition)):
            return _TagDefinition(
                local_name=args[0],
                attributes=prepare_attributes(args[1]),
                children=(third_arg,),
            )
        if isinstance(third_arg, Sequence):
            if not all(
                isinstance(x, (str, XMLNodeType, _TagDefinition)) for x in third_arg
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

    raise ValueError("Unrecognized arguments.")


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
        self.children: Final[list[list[XMLNodeType]]] = []
        self.event_feed: Final = parse_events(data, parse_options, base_url)
        self.options: Final = parse_options
        self.preserve_space: Final[list[bool]] = []
        self.started_tags: Final[list[TagNodeType]] = []
        self.xml_ids: Final[set[str]] = set()

    def __iter__(self):
        return self

    def __next__(self) -> XMLNodeType:
        while True:
            event = next(self.event_feed)
            result = self.handle_event(event)
            if result is not None:
                return result

    def handle_event(self, event: Event) -> XMLNodeType | None:
        result: XMLNodeType | None
        type_, data = event

        match type_:
            case EventType.Comment:
                assert isinstance(data, str)
                result = CommentNode(data)
            case EventType.ProcessingInstruction:
                assert isinstance(data, tuple)
                result = ProcessingInstructionNode(data[0], data[1])
            case EventType.TagStart:
                assert isinstance(data, TagEventData)
                self.handle_tag_start(data)
                result = None
            case EventType.TagEnd:
                assert isinstance(data, TagEventData)
                result = self.handle_tag_end(data)
            case EventType.Text:
                assert isinstance(data, str)
                result = TextNode(data)

        if result is not None:
            if self.started_tags:
                self.children[-1].append(result)
            else:
                assert not self.children
                assert not self.started_tags
                assert not self.preserve_space
                self.xml_ids.clear()
                return result

        return None

    def handle_tag_end(self, data: TagEventData | None) -> TagNodeType:
        result = self.started_tags.pop()
        if __debug__ and data:
            assert result.namespace == data.namespace
            assert result.local_name == data.local_name
            if data.attributes is not None:
                assert result.attributes == data.attributes

        children = self.children.pop()
        if (not self.preserve_space.pop()) and children:
            _reduce_whitespace_between_siblings(children)

        for node in children:
            result._child_nodes.append(node)

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
            TagNode(
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

        match xml_space:
            case None:  # most common
                self.preserve_space.append(self.preserve_space[-1])
            case "default":
                self.preserve_space.append(False)
            case "preserve":
                self.preserve_space.append(True)
            case _:  # invalid values
                self.preserve_space.append(self.preserve_space[-1])


def parse_nodes(
    data: InputStream,
    options: Optional[ParserOptions] = None,
    *,
    base_url: str | None = None,
) -> Iterator[XMLNodeType]:
    """Parses the provided input data to a sequence of nodes."""
    if options is None:
        options = ParserOptions()
    yield from TreeBuilder(data, options, base_url)


def parse_tree(
    data: InputStream,
    options: Optional[ParserOptions] = None,
    *,
    base_url: str | None = None,
) -> XMLNodeType:
    """Parses the provided input to a single node."""
    result = None
    for node in parse_nodes(data, options, base_url=base_url):
        if result is not None:
            raise ParsingValidityError("The stream contained extra contents.", node)
        result = node

    assert result is not None
    return result


__all__ = (parse_nodes.__name__, parse_tree.__name__, tag.__name__)
