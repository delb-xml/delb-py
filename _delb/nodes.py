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

import warnings
from collections.abc import Iterable, Iterator, Mapping, MutableMapping
from itertools import chain
from typing import (
    TYPE_CHECKING,
    cast,
    overload,
    Any,
    Final,
    Literal,
    NamedTuple,
    Optional,
)

from _delb.exceptions import AmbiguousTreeError, InvalidCodePath, InvalidOperation
from _delb.filters import altered_default_filters, default_filters, is_tag_node
from _delb.grammar import _is_xml_char, _is_xml_name
from _delb.names import (
    XML_NAMESPACE,
    deconstruct_clark_notation,
    Namespaces,
)
from _delb.serializer import (
    DefaultStringOptions,
    FormatOptions,
    _StringWriter,
    _get_serializer,
)
from _delb.utils import (
    _StringMixin,
    _crunch_whitespace,
    last,
)
from _delb.typing import (
    CommentNodeType,
    _DocumentNodeType,
    ParentNodeType,
    ProcessingInstructionNodeType,
    TagNodeType,
    TextNodeType,
    XMLNodeType,
)
from _delb.xpath import QueryResults, _css_to_xpath
from _delb.xpath import evaluate as evaluate_xpath, parse as parse_xpath
from _delb.xpath.ast import NameMatchTest, XPathExpression

if TYPE_CHECKING:
    from delb import Document
    from _delb.typing import (
        AttributeAccessor,
        _AttributesData,
        Filter,
        NamespaceDeclarations,
        NodeSource,
        QualifiedName,
    )


# constants


ATTRIBUTE_ACCESSOR_MSG: Final = (
    "An attribute name must be provided as string (either a local name or a "
    "universal in Clark notation) or as namespace and local name packed in a tuple."
)


# functions


def new_comment_node(content: str) -> CommentNode:  # pragma: no cover
    """
    Deprecated. Use :class:`CommentNode` directly.
    """
    warnings.warn(
        "This function is deprecated. Use CommentNode directly.",
        category=DeprecationWarning,
    )
    return CommentNode(content)


def new_processing_instruction_node(  # pragma: no cover
    target: str, content: str
) -> ProcessingInstructionNode:
    """Deprecated. Use :class:`ProcessingInstructionsNode` directly."""
    warnings.warn(
        "This function is deprecated. Use ProcessingInstructionsNode directly.",
        category=DeprecationWarning,
    )
    return ProcessingInstructionNode(target, content)


def new_tag_node(  # pragma: no cover
    local_name: str,
    attributes: Optional[
        _AttributesData | dict[AttributeAccessor, str] | TagAttributes
    ] = None,
    namespace: Optional[str] = None,
    children: Iterable[NodeSource] = (),
) -> TagNode:
    """
    Deprecated. Use :class:`TagNode` directly.
    """
    warnings.warn(
        "This function is deprecated. Use TagNode directly to instantiate new tag "
        "nodes.",
        category=DeprecationWarning,
    )
    return TagNode(
        local_name=local_name,
        attributes=attributes,
        namespace=namespace,
        children=children,
    )


def _reduce_whitespace_between_siblings(nodes: list[XMLNodeType] | Siblings):
    if not (
        text_nodes := tuple(
            (i, n) for i, n in enumerate(nodes) if isinstance(n, TextNode)
        )
    ):
        return

    in_tree = isinstance(nodes, Siblings)
    first_node = nodes[0]
    last_node = nodes[-1]
    empty_nodes = []

    for i, text_node in text_nodes:
        if reduced_content := _reduce_whitespace_content(
            text_node.content,
            text_node is first_node,
            text_node is last_node,
        ):
            text_node.content = reduced_content
        else:
            if in_tree:
                text_node.detach()
            else:
                empty_nodes.append(i)

    if empty_nodes:
        assert isinstance(nodes, list)
        for i in reversed(empty_nodes):
            del nodes[i]


def _reduce_whitespace_content(content: str, is_first: bool, is_last: bool) -> str:
    collapsed = _crunch_whitespace(content)
    collapsed_and_stripped = collapsed.strip()
    has_non_whitespace_content = bool(collapsed_and_stripped)
    has_trailing_whitespace = collapsed.endswith(" ")

    # 1 Retain one leading space
    #   if the node isn't first, has non-space content, and has leading space.
    if not is_first and has_non_whitespace_content and collapsed.startswith(" "):
        result = f" {collapsed_and_stripped}"
    else:
        result = collapsed_and_stripped

    # Retain one trailing space
    if (
        # 2 … if the node isn't last, isn't first, and has trailing space.
        (not (is_last or is_first) and has_trailing_whitespace)
        or
        # 3 … if the node isn't last, is first, has trailing space, and has
        #   non-space content.
        (
            not is_last
            and is_first
            and has_trailing_whitespace
            and has_non_whitespace_content
        )
        or
        # 4 … if the node is an only child and only has space content.
        (is_first and is_last and not has_non_whitespace_content)
    ):
        result += " "

    return result


# abstract tag definitions


class _TagDefinition(NamedTuple):
    """
    Instances of this class describe tag nodes that are constructed from the context
    they are used in (commonly additions to a tree) and the properties that this
    description holds. For the sake of slick code they are not instantiated directly,
    but with the :func:`delb.tag` function.
    """

    local_name: str
    attributes: Optional[dict[AttributeAccessor, str]] = None
    children: tuple[NodeSource, ...] = ()


# attributes


class Attribute(_StringMixin):
    """
    Attribute objects represent a tag node's attributes. See the
    :meth:`TagNode.attributes` documentation for capabilities.
    """

    __slots__ = ("_attributes", "__qualified_name", "__value")

    def __init__(self, qualified_name: QualifiedName, value: str):
        self._attributes: TagAttributes | None = None
        self.__qualified_name = qualified_name
        self.value = value

    def __repr__(self):
        return (
            f'<{self.__class__.__name__}({self.universal_name}="{self.value}")'
            f" [{hex(id(self))}]>"
        )

    def __str__(self):
        return self.__value

    def __set_new_key(self, namespace: str, name: str):
        assert self.__qualified_name != (namespace, name)

        if (attributes := self._attributes) is not None:
            if __debug__:
                assert attributes.pop(self.__qualified_name) is self
            else:
                del attributes[self.__qualified_name]
            attributes[(namespace, name)] = self
        self.__qualified_name = (namespace, name)

    @property
    def local_name(self) -> str:
        """The attribute's local name."""
        return self.__qualified_name[1]

    @local_name.setter
    def local_name(self, name: str):
        if not _is_xml_name(name):
            raise ValueError(f"`{name}` is not a valid xml name.")
        self.__set_new_key(self.namespace, name)

    @property
    def namespace(self) -> str:
        """The attribute's namespace"""
        return self.__qualified_name[0]

    @namespace.setter
    def namespace(self, namespace: str):
        # TODO see https://github.com/delb-xml/delb-py/issues/69
        if namespace and not _is_xml_char(namespace):
            raise ValueError("Invalid XML character data.")
        self.__set_new_key(namespace, self.local_name)

    @property
    def universal_name(self) -> str:
        """
        The attribute's namespace and local name in `Clark notation`_.

        .. _Clark notation: http://www.jclark.com/xml/xmlns.htm
        """
        if namespace := self.namespace:
            return f"{{{namespace}}}{self.local_name}"
        else:
            return self.local_name

    @property
    def value(self) -> str:
        """The attribute's value."""
        return self.__value

    @value.setter
    def value(self, value: str):
        if not isinstance(value, str):
            raise TypeError
        if value and not _is_xml_char(value):
            raise ValueError("Invalid XML character data.")
        self.__value = value


class TagAttributes(MutableMapping):
    """
    A data type to access a tag node's attributes.
    """

    __slots__ = (
        "__data",
        "__node",
    )

    def __init__(
        self,
        data: _AttributesData | dict[AttributeAccessor, str] | TagAttributes,
        node: TagNodeType,
    ):
        if not isinstance(data, Mapping):
            raise TypeError

        self.__data: dict[QualifiedName, Attribute] = {}
        self.__node = node
        self.update(data)

    def __contains__(self, item: Any) -> bool:
        return self.__resolve_accessor(item) in self.__data

    def __delitem__(self, item: AttributeAccessor):
        name = self.__resolve_accessor(item)
        self.__data[name]._attributes = None
        del self.__data[name]

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Mapping):
            return False

        if len(self) != len(other):
            return False

        if isinstance(other, TagAttributes):
            return self.__data == other.__data

        return self.__data == {self.__resolve_accessor(k): v for k, v in other.items()}

    def __getitem__(self, item: AttributeAccessor) -> Attribute:
        return self.__data[self.__resolve_accessor(item)]

    def __iter__(self) -> Iterator[QualifiedName]:
        return iter(self.__data)

    def __len__(self) -> int:
        return len(self.__data)

    def __setitem__(self, item: AttributeAccessor, value: str | Attribute):
        name = self.__resolve_accessor(item)

        match value:
            case Attribute():
                if value._attributes is None:
                    attribute = value
                else:
                    attribute = Attribute(name, value.value)
            case str():
                attribute = Attribute(name, value)
            case _:
                raise TypeError

        assert attribute._attributes in (self, None)
        attribute._attributes = self
        self.__data[name] = attribute

    def __str__(self):
        return str(self.as_dict_with_strings())

    __repr__ = __str__

    def __resolve_accessor(self, item: AttributeAccessor) -> QualifiedName:
        match item:
            case tuple():
                assert item[0] is not None
                return item
            case str():
                namespace, name = deconstruct_clark_notation(item)
                if namespace is None:
                    return (self.__node.namespace, name)
                else:
                    return (namespace, name)
            case _:
                raise TypeError(ATTRIBUTE_ACCESSOR_MSG)

    def as_dict_with_strings(self) -> dict[str, str]:
        """Returns the attributes as :class:`str` instances in a :class:`dict`."""
        return {a.universal_name: a.value for a in self.values()}


# containers


class Siblings:
    """
    Container for the sisterhood of nodes.
    Everyone's taken care of.
    """

    __slots__ = (
        "__belongs_to",
        "__data",
    )

    def __init__(
        self,
        belongs_to: None | _ParentNode,
        nodes: Optional[Iterable[NodeSource]],
    ):
        self.__data: Final[list[XMLNodeType]] = []
        self.__belongs_to: Final = belongs_to
        if nodes is not None:
            for node in nodes:
                self.__data.append(self._handle_new_sibling(node))

    @overload
    def __getitem__(self, index: int) -> XMLNodeType:
        pass

    @overload
    def __getitem__(self, index: slice) -> list[XMLNodeType]:
        pass

    def __getitem__(self, index: int | slice) -> XMLNodeType | list[XMLNodeType]:
        if not isinstance(index, (int, slice)):
            raise TypeError

        return self.__data[index]

    def __iter__(self) -> Iterator[XMLNodeType]:
        return iter(self.__data)

    def __len__(self) -> int:
        return len(self.__data)

    def append(self, node: NodeSource) -> XMLNodeType:
        result = self._handle_new_sibling(node)
        self.__data.append(result)
        return result

    def clear(self):
        for node in self.__data:
            node._parent = None
        self.__data.clear()

    def index(self, node: XMLNodeType) -> int:
        for result, n in enumerate(self.__data):
            if n is node:
                return result
        else:
            raise IndexError

    def insert(self, index: int, node: NodeSource) -> XMLNodeType:
        result = self._handle_new_sibling(node)
        self.__data.insert(index, result)
        return result

    def remove(self, node: XMLNodeType):
        node._parent = None
        del self.__data[self.index(node)]

    def _handle_new_sibling(self, node: NodeSource) -> XMLNodeType:
        if isinstance(self.__belongs_to, _DocumentNode):
            if isinstance(node, (str, _TagDefinition)):
                raise TypeError
            if isinstance(node, TagNode) and any(
                isinstance(n, TagNode) for n in self.__data
            ):
                raise InvalidCodePath

        match node:
            case str():
                node = TextNode(node)
            case _TagDefinition():
                assert isinstance(self.__belongs_to, TagNode)
                node = self.__belongs_to._new_tag_node_from_definition(node)
            case XMLNodeType():
                if node._parent is not None:
                    raise InvalidOperation(
                        "Only a detached node can be added to the tree. Use "
                        ":meth:`XMLNodeType.clone` or :meth:`XMLNodeType.detach` to "
                        "get one."
                    )
            case _:
                raise TypeError(
                    "Either node instances, strings or objects from :func:`delb.tag` "
                    "must be provided as child node."
                )

        node._parent = self.__belongs_to
        return node


# nodes


class _NodeCommons(XMLNodeType):

    __slots__ = ("_parent",)

    def __init__(self):
        self._parent = None

    def __copy__(self):
        return self.clone(deep=False)

    def __deepcopy__(self, memo):
        return self.clone(deep=True)

    def __str__(self) -> str:
        return self.serialize(
            format_options=DefaultStringOptions.format_options,
            namespaces=DefaultStringOptions.namespaces,
            newline=DefaultStringOptions.newline,
        )

    def add_following_siblings(
        self, *node: NodeSource, clone: bool = False
    ) -> tuple[XMLNodeType, ...]:
        if self._parent is None:
            raise InvalidOperation("Can't add sibling to a node without parent node.")

        return tuple(
            reversed(
                self._parent.insert_children(
                    self._parent._child_nodes.index(self) + 1, *node, clone=clone
                )
            )
        )

    def add_preceding_siblings(
        self, *node: NodeSource, clone: bool = False
    ) -> tuple[XMLNodeType, ...]:
        if self._parent is None:
            raise InvalidOperation("Can't add sibling to a node without parent node.")

        return self._parent.insert_children(
            self._parent._child_nodes.index(self), *reversed(node), clone=clone
        )

    @property
    def depth(self) -> int:
        result = 0
        pointer: XMLNodeType | None = self
        assert pointer is not None
        while True:
            pointer = pointer._parent
            if pointer is None or isinstance(pointer, _DocumentNode):
                break
            result += 1
        return result

    def detach(self, retain_child_nodes: bool = False) -> XMLNodeType:
        if (parent := self._parent) is not None:
            parent._child_nodes.remove(self)
        return self

    def fetch_following(self, *filter: Filter) -> Optional[XMLNodeType]:
        all_filters = default_filters[-1] + filter
        for node in self._iterate_following():
            if all(f(node) for f in all_filters):
                return node
        else:
            return None

    def _fetch_following(self) -> Optional[XMLNodeType]:
        for node in self._iterate_following():
            return node
        else:
            return None

    def fetch_following_sibling(self, *filter: Filter) -> Optional[XMLNodeType]:
        all_filters = default_filters[-1] + filter
        for node in self._iterate_following_siblings():
            if all(f(node) for f in all_filters):
                return node
        else:
            return None

    def _fetch_following_sibling(self) -> Optional[XMLNodeType]:
        if self._parent is None:
            return None
        if (siblings := self._parent._child_nodes)[-1] is self:
            return None
        return siblings[siblings.index(self) + 1]

    def fetch_preceding(self, *filter: Filter) -> Optional[XMLNodeType]:
        all_filters = default_filters[-1] + filter
        for node in self._iterate_preceding():
            if all(f(node) for f in all_filters):
                return node
        else:
            return None

    def _fetch_preceding(self) -> Optional[XMLNodeType]:
        for node in self._iterate_preceding():
            return node
        else:
            return None

    def fetch_preceding_sibling(self, *filter: Filter) -> Optional[XMLNodeType]:
        all_filters = default_filters[-1] + filter
        for node in self._iterate_preceding_siblings():
            if all(f(node) for f in all_filters):
                return node
        else:
            return None

    def _fetch_preceding_sibling(self) -> Optional[XMLNodeType]:
        if self._parent is None:
            return None

        if (siblings := self._parent._child_nodes)[0] is self:
            return None
        return siblings[siblings.index(self) - 1]

    @property
    def index(self) -> Optional[int]:
        if self._parent is not None:
            for result, node in enumerate(
                n
                for n in self._parent._child_nodes
                if all(f(n) for f in default_filters[-1])
            ):
                if node is self:
                    return result

        return None

    def iterate_ancestors(self, *filter: Filter) -> Iterator[ParentNodeType]:
        all_filters = default_filters[-1] + filter
        for node in self._iterate_ancestors():
            if all(f(node) for f in all_filters):
                yield node

    def _iterate_ancestors(
        self, *, _include_document_node: bool = False
    ) -> Iterator[ParentNodeType]:
        node: None | XMLNodeType = self
        assert node is not None
        if _include_document_node:
            while (node := node._parent) is not None:
                yield node
        else:
            while True:
                node = node._parent
                if node is None or isinstance(node, _DocumentNode):
                    return
                yield node

    def iterate_following(
        self, *filter: Filter, include_descendants: bool = True
    ) -> Iterator[XMLNodeType]:
        all_filters = default_filters[-1] + filter
        for node in self._iterate_following(include_descendants=include_descendants):
            if all(f(node) for f in all_filters):
                yield node

    def _iterate_following(
        self, *, include_descendants: bool = True
    ) -> Iterator[XMLNodeType]:
        if include_descendants:
            yield from self._iterate_descendants()

        if self._parent is None:
            return

        for following_sibling in self._iterate_following_siblings():
            yield following_sibling
            yield from following_sibling._iterate_descendants()

        for ancestor in self._iterate_ancestors():
            if (
                ancestors_following_sibling := ancestor._fetch_following_sibling()
            ) is not None:
                break
        else:
            return

        yield ancestors_following_sibling
        yield from ancestors_following_sibling._iterate_following(
            include_descendants=True
        )

    def iterate_following_siblings(self, *filter: Filter) -> Iterator[XMLNodeType]:
        all_filters = default_filters[-1] + filter
        for node in self._iterate_following_siblings():
            if all(f(node) for f in all_filters):
                yield node

    def _iterate_following_siblings(self) -> Iterator[XMLNodeType]:
        if self._parent is None:
            return

        siblings = self._parent._child_nodes
        for index in range(siblings.index(self) + 1, len(siblings)):
            yield siblings[index]

    def iterate_preceding(
        self, *filter: Filter, include_ancestors: bool = True
    ) -> Iterator[XMLNodeType]:
        all_filters = default_filters[-1] + filter
        for node in self._iterate_preceding(include_ancestors=include_ancestors):
            if all(f(node) for f in all_filters):
                yield node

    def _iterate_preceding(
        self, *, include_ancestors: bool = True
    ) -> Iterator[XMLNodeType]:
        if (parent := self._parent) is None:
            return

        for preceding_sibling in self._iterate_preceding_siblings():
            yield from preceding_sibling._iterate_reversed_descendants()

        if isinstance(parent, _DocumentNode):
            return

        if include_ancestors:
            yield parent
        yield from parent._iterate_preceding(include_ancestors=include_ancestors)

    def iterate_preceding_siblings(self, *filter: Filter) -> Iterator[XMLNodeType]:
        all_filters = default_filters[-1] + filter
        for node in self._iterate_preceding_siblings():
            if all(f(node) for f in all_filters):
                yield node

    def _iterate_preceding_siblings(self) -> Iterator[XMLNodeType]:
        if self._parent is None:
            return

        siblings = self._parent._child_nodes
        for index in range(siblings.index(self) - 1, -1, -1):
            yield siblings[index]

    def _iterate_reversed_descendants(self) -> Iterator[XMLNodeType]:
        if not isinstance(self, TagNode) or not self._child_nodes:
            yield self
            return

        stack = [(self, list(self._child_nodes))]

        while stack:
            parent, children = stack[-1]

            if children:
                node = children.pop()
                if isinstance(node, TagNode) and node._child_nodes:
                    stack.append((node, list(node._child_nodes)))
                else:
                    yield node
            else:
                stack.pop()
                yield parent

    @property
    def parent(self) -> Optional[ParentNodeType]:
        return None if isinstance(self._parent, _DocumentNode) else self._parent

    def replace_with(self, node: NodeSource, clone: bool = False) -> XMLNodeType:
        if (parent := self._parent) is None:
            raise InvalidOperation(
                "Cannot replace a root node of a tree. Maybe you want to set the "
                "`root` property of a Document instance?"
            )

        if clone and isinstance(node, _NodeCommons):
            node = node.clone(deep=True)
        parent._child_nodes.insert(parent._child_nodes.index(self), node)
        return self.detach(retain_child_nodes=False)

    def serialize(
        self,
        *,
        format_options: Optional[FormatOptions] = None,
        namespaces: Optional[NamespaceDeclarations] = None,
        newline: Optional[str] = None,
    ) -> str:
        serializer = _get_serializer(
            _StringWriter(newline=newline),
            format_options=format_options,
            namespaces=namespaces,
        )
        serializer.serialize_node(self)
        return serializer.writer.result

    def xpath(
        self,
        expression: str,
        namespaces: Optional[NamespaceDeclarations] = None,
    ) -> QueryResults:
        return evaluate_xpath(node=self, expression=expression, namespaces=namespaces)


class _LeafNode(_NodeCommons):
    """Node types using this mixin also can't be root nodes of a document."""

    __slots__ = ()

    first_child = None
    """ The node's first child. """
    last_child = None
    """ The node's last child node. """
    last_descendant = None
    """ The node's last descendant. """

    def __len__(self):
        return 0

    @property
    def document(self) -> Optional[Document]:
        if self._parent is None:
            return None
        else:
            return self._parent.document

    @property
    def full_text(self) -> str:
        return ""

    # the following yield statements are there to trick mypy

    def iterate_children(self, *filter: Filter) -> Iterator[XMLNodeType]:
        """
        A :term:`generator iterator` that yields nothing.

        :meta category: Methods to iterate over related node
        """
        return
        yield from ()

    def iterate_descendants(self, *filter: Filter) -> Iterator[XMLNodeType]:
        """
        A :term:`generator iterator` that yields nothing.

        :meta category: Methods to iterate over related node
        """
        return
        yield from ()

    def _iterate_descendants(self) -> Iterator[XMLNodeType]:
        return
        yield from ()


class _ParentNode(_NodeCommons, ParentNodeType):

    __slots__ = ("_child_nodes",)

    def __init__(
        self,
        children: Iterable[NodeSource] = (),
    ):
        super().__init__()
        self._child_nodes = Siblings(nodes=children, belongs_to=self)

    def __len__(self) -> int:
        result = 0
        for node in self._child_nodes:
            if all(f(node) for f in default_filters[-1]):
                result += 1

        return result

    def append_children(
        self, *node: NodeSource, clone: bool = False
    ) -> tuple[XMLNodeType, ...]:
        if not node:
            return ()

        result: list[XMLNodeType] = []

        for _node in node:
            if clone and isinstance(_node, _NodeCommons):
                _node = _node.clone(deep=True)
            result.append(self._child_nodes.append(_node))

        return tuple(result)

    @property
    def first_child(self) -> Optional[XMLNodeType]:
        for node in self._child_nodes:
            if all(f(node) for f in default_filters[-1]):
                return node
        else:
            return None

    @property
    def full_text(self) -> str:
        return "".join(
            n.content for n in self._iterate_descendants() if isinstance(n, TextNode)
        )

    def insert_children(
        self, index: int, *node: NodeSource, clone: bool = False
    ) -> tuple[XMLNodeType, ...]:
        children_size = len(self._child_nodes)
        if not (children_size * -1 <= index <= children_size):
            raise IndexError

        result = []
        for _node in reversed(node):
            if clone and isinstance(_node, _NodeCommons):
                _node = _node.clone(deep=True)
            result.append(self._child_nodes.insert(index, _node))
        return tuple(result)

    def iterate_children(self, *filter: Filter) -> Iterator[XMLNodeType]:
        all_filters = default_filters[-1] + filter
        for node in self._child_nodes:
            if all(f(node) for f in all_filters):
                yield node

    def iterate_descendants(self, *filter: Filter) -> Iterator[XMLNodeType]:
        if not self._child_nodes:
            return

        all_filters = default_filters[-1] + filter
        for node in self._iterate_descendants():
            if all(f(node) for f in all_filters):
                yield node

    def _iterate_descendants(self) -> Iterator[XMLNodeType]:
        stack = [(self._child_nodes, 0)]

        while stack:
            siblings, pointer = stack.pop()

            for node in siblings[pointer:]:
                pointer += 1
                yield node

                if isinstance(node, TagNode) and node._child_nodes:
                    stack.extend(((siblings, pointer), (node._child_nodes, 0)))
                    break

    @property
    def last_child(self) -> Optional[XMLNodeType]:
        if self._child_nodes:
            filters = default_filters[-1]
            for node in self._child_nodes[::-1]:
                if all(f(node) for f in filters):
                    return node
        return None

    @property
    def last_descendant(self) -> Optional[XMLNodeType]:
        for node in self._iterate_reversed_descendants():
            if node is not self and all(f(node) for f in default_filters[-1]):
                return node
        else:
            return None

    def merge_text_nodes(self, deep: bool = False):
        empty_nodes: list[TextNodeType] = []

        for index in range(len(self._child_nodes) - 1, -1, -1):
            node = self._child_nodes[index]
            if isinstance(node, TextNode):
                if not node.content:
                    empty_nodes.append(node)

                elif index and isinstance(
                    (preceding_node := self._child_nodes[index - 1]), TextNode
                ):
                    preceding_node.content += node.content
                    empty_nodes.append(node)

        for node in empty_nodes:
            node.content = ""
            node.detach()

        if deep:
            for node in (n for n in self._child_nodes if isinstance(n, TagNode)):
                node.merge_text_nodes(deep=True)

    def prepend_children(
        self, *node: XMLNodeType, clone: bool = False
    ) -> tuple[XMLNodeType, ...]:
        return self.insert_children(0, *node, clone=clone)


class CommentNode(_LeafNode, CommentNodeType):
    """
    The instances of this class represent comment nodes of a tree.

    This class implements :class:`delb.typing.CommentNodeType`.

    :param content: The comment's content a.k.a. text.
    """

    __slots__ = ("__content",)

    def __init__(self, content: str):
        super().__init__()
        self.content = content

    def __eq__(self, other) -> bool:
        return isinstance(other, CommentNode) and self.content == other.content

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}("{self.content}") [{hex(id(self))}]>'

    def __str__(self) -> str:
        return f"<!--{self.content}-->"

    def clone(self, deep: bool = False) -> CommentNode:
        return CommentNode(self.__content)

    @property
    def content(self) -> str:
        return self.__content

    @content.setter
    def content(self, value: str):
        if value and not _is_xml_char(value):
            raise ValueError("Invalid XML character data.")
        if "--" in value or value.endswith("-"):
            raise ValueError("Invalid Comment content.")
        self.__content = value


class _DocumentNode(_ParentNode, _DocumentNodeType):
    """
    This node type is only supposed to facilitate tree traversal beyond a root node via
    its :attr:`_DocumentNode._child_nodes` attribute. Therefore it shall be only
    accessible by :attr:`XMLNodeType._parent` and yielded by
    :meth:`XMLNodeType._iterate_ancestors` if requested with an argument.
    It also holds information to the related :class:`Document` instance of a tree.
    In the context of XPath evaluations it acts like :class:`xpath.ast._DocumentNode`
    that is used as shim for queries that target trees that are not associated to a
    :class:`Document` instance.
    """

    __slots__ = ("__document",)

    def __init__(self, document: Document | None, children: Iterable[XMLNodeType]):
        super().__init__(children)
        self.__document: Final = document

    def clone(self, deep: bool = False) -> XMLNodeType:  # pragma: no cover
        raise InvalidCodePath

    @property
    def document(self) -> Document:
        assert self.__document is not None
        return self.__document

    def add_following_siblings(  # pragma: no cover
        self, *node: NodeSource, clone: bool = False
    ) -> tuple[XMLNodeType, ...]:
        raise InvalidCodePath

    def add_preceding_siblings(  # pragma: no cover
        self, *node: NodeSource, clone: bool = False
    ) -> tuple[XMLNodeType, ...]:
        raise InvalidCodePath

    def detach(
        self, retain_child_nodes: bool = False
    ) -> XMLNodeType:  # pragma: no cover
        raise InvalidCodePath

    @property
    def _parent(self) -> None:
        return None

    @_parent.setter
    def _parent(self, value):  # pragma: no cover
        if value is not None:
            raise InvalidCodePath

    def replace_with(  # pragma: no cover
        self, node: NodeSource, clone: bool = False
    ) -> XMLNodeType:
        raise InvalidCodePath


class ProcessingInstructionNode(_LeafNode, ProcessingInstructionNodeType):
    """
    The instances of this class represent processing instruction nodes of a tree.

    This class implements :class:`delb.typing.ProcessingInstructionNodeType`.

    :param target: The processing instruction's target name.
    :param content: The processing instruction's text.
    """

    __slots__ = ("__content", "__target")

    def __init__(self, target: str, content: str):
        super().__init__()
        self.content = content
        self.target = target

    def __eq__(self, other) -> bool:
        return (
            isinstance(other, ProcessingInstructionNode)
            and self.target == other.target
            and self.content == other.content
        )

    def __repr__(self) -> str:
        return (
            f'<{self.__class__.__name__}("{self.target}", "{self.content}") '
            f"[{hex(id(self))}]>"
        )

    def __str__(self) -> str:
        return f"<?{self.target} {self.content}?>"

    def clone(self, deep: bool = False) -> ProcessingInstructionNode:
        return ProcessingInstructionNode(self.__target, self.__content)

    @property
    def content(self) -> str:
        return self.__content

    @content.setter
    def content(self, value: str):
        if value and not _is_xml_char(value):
            raise ValueError("Invalid XML character data.")
        if "?>" in value:
            raise ValueError("Content text must not contain '?>'.")
        self.__content = value

    @property
    def target(self) -> str:
        """
        The processing instruction's target.

        :meta category: Node content properties
        """
        return self.__target

    @target.setter
    def target(self, value: str):
        if not _is_xml_name(value):
            raise ValueError("Invalid target name.")
        if value.lower() == "xml":
            raise ValueError(f"{value} is a reserved target name.")
        self.__target = value


class TagNode(_ParentNode, TagNodeType):
    """
    The instances of this class represent tag nodes of a tree, the equivalent of DOM's
    elements.

    This class implements :class:`delb.typing.TagNodeType`.

    :param local_name: The tag name.
    :param attributes: Optional attributes that are assigned to the new node.
    :param namespace: An optional tag namespace.
    :param children: An optional iterable of objects that will be appended as child
                     nodes. This can be existing nodes, strings that will be inserted
                     as text nodes and in-place definitions of :class:`TagNode`
                     instances from :func:`tag`. The latter will be assigned to the
                     same namespace.

    Some syntactic sugar is baked in:

    Attributes and nodes can be tested for membership in a node.

    >>> root = Document('<root ham="spam"><child/></root>').root
    >>> "ham" in root
    True
    >>> root.first_child in root
    True

    Nodes can be copied. Note that this relies on :meth:`TagNode.clone`.

    >>> from copy import copy, deepcopy
    >>> root = Document("<root>Content</root>").root
    >>> print(copy(root))
    <root/>
    >>> print(deepcopy(root))
    <root>Content</root>

    Attribute values and child nodes can be obtained, set and deleted with the subscript
    notation.

    >>> root = Document('<root x="y"><child_1/>child_2<child_3/></root>').root
    >>> print(root["x"])
    y
    >>> print(root[0])
    <child_1/>
    >>> print(root[-1])
    <child_3/>
    >>> print([str(x) for x in root[1::-1]])
    ['child_2', '<child_1/>']

    How much child nodes has this node anyway?

    >>> root = Document("<root><child_1/><child_2/></root>").root
    >>> len(root)
    2
    >>> len(root[0])
    0

    As seen in the examples above, a tag nodes string representation yields a serialized
    XML representation of a sub-/tree. See :doc:`/api/serialization` for details.
    """

    __slots__ = (
        "__attributes",
        "__local_name",
        "__namespace",
    )

    def __init__(
        self,
        local_name: str,
        attributes: Optional[
            _AttributesData | dict[AttributeAccessor, str] | TagAttributes
        ] = None,
        namespace: Optional[str] = None,
        children: Iterable[NodeSource] = (),
    ):
        self.namespace = namespace or ""
        self.local_name = local_name
        self.__attributes = TagAttributes(data=attributes or {}, node=self)
        super().__init__(children)

    def __contains__(self, item: AttributeAccessor | XMLNodeType) -> bool:
        match item:
            case str() | tuple():
                return item in self.attributes
            case XMLNodeType():
                return item in self._child_nodes
            case _:
                raise TypeError(
                    "Argument must be a node instance or an attribute name. "
                    + ATTRIBUTE_ACCESSOR_MSG
                )

    def __delitem__(self, item: AttributeAccessor | int):
        match item:
            case str() | tuple():
                del self.attributes[item]
            case int():
                self[item].detach(retain_child_nodes=False)
            case slice():
                if all(
                    isinstance(x, int) or x is None for x in (item.start, item.stop)
                ):
                    for node in self[item]:
                        node.detach(retain_child_nodes=False)
                else:
                    del self.attributes[(item.start, item.stop)]
            case _:
                raise TypeError(  # TODO or a slice
                    "Argument must be an integer or an attribute name. "
                    + ATTRIBUTE_ACCESSOR_MSG
                )

    @overload
    def __getitem__(self, item: int) -> XMLNodeType: ...

    @overload
    def __getitem__(self, item: AttributeAccessor) -> Attribute | None: ...

    def __getitem__(self, item):
        match item:
            case str() | tuple():
                return self.attributes[item]

            case int():
                if item < 0:
                    item = len(self) + item

                for index, child_node in enumerate(self.iterate_children()):
                    if index == item:
                        return child_node

                raise IndexError("Node index out of range.")

            case slice() if all(
                (isinstance(x, int) or x is None) for x in (item.start, item.stop)
            ):
                return list(self.iterate_children())[item]

        raise TypeError(
            "Argument must be an integer as index for a child node, a "
            ":term:`slice` to grab an indexed range of nodes or an attribute "
            "name. " + ATTRIBUTE_ACCESSOR_MSG
        )

    def __repr__(self) -> str:
        return (
            f'<{self.__class__.__name__}("{self.universal_name}", '
            f"{self.attributes}, {self.location_path}) [{hex(id(self))}]>"
        )

    @overload
    def __setitem__(self, item: int, value: NodeSource): ...

    @overload
    def __setitem__(self, item: AttributeAccessor, value: str | Attribute): ...

    def __setitem__(self, item, value):
        match item:
            case str() | tuple():
                self.attributes[item] = value
            case int():
                children_size = len(self._child_nodes)
                if children_size == item:
                    self._child_nodes.append(value)
                elif 0 <= item < children_size or (
                    item < 0 and abs(item) <= children_size
                ):
                    self[item].replace_with(value)
                else:
                    raise IndexError
            case _:
                raise TypeError(
                    "Argument must be an integer or an attribute name. "
                    + ATTRIBUTE_ACCESSOR_MSG
                )

    def add_following_siblings(
        self, *node: NodeSource, clone: bool = False
    ) -> tuple[XMLNodeType, ...]:
        if self._parent is None:
            raise InvalidOperation("Can't add sibling to a node without parent node.")

        return super().add_following_siblings(*node)

    def add_preceding_siblings(
        self, *node: NodeSource, clone: bool = False
    ) -> tuple[XMLNodeType, ...]:
        if self._parent is None:
            raise InvalidOperation("Can't add sibling to a node without parent node.")

        return super().add_preceding_siblings(*node)

    @property
    def attributes(self) -> TagAttributes:
        """
        A :term:`mapping` that can be used to access the node's attributes.

        :meta category: Node content properties

        >>> node = TagNode("node", attributes={"foo": "0", "bar": "0"})
        >>> node.attributes
        {'foo': '0', 'bar': '0'}
        >>> node.attributes.pop("bar")  # doctest: +ELLIPSIS
        <Attribute(bar="0") [0x...]>
        >>> node.attributes["foo"] = "1"
        >>> node.attributes["peng"] = "1"
        >>> print(node)
        <node foo="1" peng="1"/>
        >>> node.attributes.update({"foo": "2", "zong": "2"})
        >>> print(node)
        <node foo="2" peng="1" zong="2"/>

        Namespaced names are accessed with two-value tuples or a string. The two-value
        holds the namespace and the local name in that order. A string can either be a
        fully qualified name in `Clark notation`_ or a local name that belongs to the
        containing node's namespace.

        .. _Clark notation: http://www.jclark.com/xml/xmlns.htm

        >>> DefaultStringOptions.namespaces = {"": "http://namespace"}
        >>> node = TagNode(
        ...     "node",
        ...     namespace="http://namespace",
        ... )
        >>> node.attributes.update({("http://namespace", "foo"): "0"})
        >>> print(node)
        <node xmlns="http://namespace" foo="0"/>
        >>> attribute = node.attributes[("http://namespace", "foo")]
        >>> node.attributes["foo"] is attribute
        True
        >>> node.attributes["{http://namespace}foo"] is attribute
        True

        Attributes behave like strings, but also expose namespace, local name and
        value for manipulation.

        >>> node = TagNode("node")
        >>> node.attributes["foo"] = "0"
        >>> node.attributes["foo"].local_name = "bar"
        >>> node.attributes["bar"].namespace = "http://namespace"
        >>> node.attributes[("http://namespace", "bar")].value = "X"
        >>> print(node)
        <node xmlns:ns0="http://namespace" ns0:bar="X"/>
        >>> "ref-" + node.attributes[("http://namespace", "bar")].lower()
        'ref-x'
        """
        return self.__attributes

    def clone(self, deep: bool = False) -> TagNodeType:
        result = TagNode(
            local_name=self.__local_name,
            namespace=self.__namespace,
            attributes=self.attributes,
        )
        if deep:
            result.append_children(*(n.clone(deep=True) for n in self._child_nodes))
        return result

    def css_select(
        self, expression: str, namespaces: Optional[NamespaceDeclarations] = None
    ) -> QueryResults:
        """
        Queries the tree with a CSS selector expression with this node as initial
        context node.

        :param expression: A CSS selector expression.
        :param namespaces: A mapping of prefixes that are used in the expression to
                           namespaces.  If not provided the node's namespace will serve
                           as default, mapped to an empty prefix.
        :return: All nodes that match the evaluation of the provided CSS selector
                 expression.
        :meta category: Methods to query the tree

        See :doc:`/api/querying` regarding the extent of the supported grammar.

        Namespace prefixes are delimited with a ``|`` before a name test, for example
        ``div svg|metadata`` selects all descendants of ``div`` named nodes that belong
        to the default namespace or have no namespace and whose name is ``metadata``
        and have a namespace that is mapped to the ``svg`` prefix.
        """
        return self.xpath(expression=_css_to_xpath(expression), namespaces=namespaces)

    def detach(self, retain_child_nodes: bool = False) -> TagNodeType:
        if isinstance(self._parent, _DocumentNode):
            raise InvalidOperation("The root node of a document cannot be detached.")

        if self._parent is None:
            if retain_child_nodes:
                raise InvalidOperation(
                    "Child nodes can't be retained when the node to detach has no "
                    "parent node."
                )
            return self

        index = self._parent._child_nodes.index(self)
        if retain_child_nodes:
            children = tuple(self._child_nodes)
            self._child_nodes.clear()
            self._parent.insert_children(index, *children)

        self._parent._child_nodes.remove(self)
        return self

    @property
    def document(self) -> Optional[Document]:
        document_node = last(self._iterate_ancestors(_include_document_node=True))
        if isinstance(document_node, _DocumentNode):
            return document_node.document
        else:
            return None

    def fetch_or_create_by_xpath(
        self,
        expression: str,
        namespaces: Optional[NamespaceDeclarations] = None,
    ) -> TagNodeType:
        ast = parse_xpath(expression)
        if not ast._is_unambiguously_locatable:
            raise ValueError(
                "The XPath expression doesn't determine a distinct branch."
            )

        query_result = self.xpath(expression, namespaces=namespaces)

        if query_result.size == 1:
            result = query_result.first
            assert isinstance(result, TagNode)
            return result

        if query_result:
            raise AmbiguousTreeError(
                f"The tree already contains {query_result.size} matching branches."
            )

        return self._create_by_xpath(
            ast=ast,
            namespaces=Namespaces(namespaces or Namespaces({"": self.namespace})),
        )

    def _create_by_xpath(
        self,
        ast: XPathExpression,
        namespaces: Namespaces,
    ) -> TagNode:
        node: _ParentNode
        if ast.location_paths[0].absolute:
            match root := last(self._iterate_ancestors(_include_document_node=True)):
                case _DocumentNode():
                    node = root
                case TagNode():
                    node = _DocumentNode(None, (root,))
                case None:
                    node = _DocumentNode(None, (self,))
        else:
            node = self

        for i, step in enumerate(ast.location_paths[0].location_steps):
            candidates = tuple(step.evaluate(node_set=(node,), namespaces=namespaces))

            match len(candidates):
                case 0:
                    node_test = step.node_test
                    assert isinstance(node, TagNode)
                    assert isinstance(node_test, NameMatchTest)

                    new_node = TagNode(
                        local_name=node_test.local_name,
                        attributes=None,
                        namespace=namespaces.get(node_test.prefix),
                    )

                    for prefix, local_name, value in step._derived_attributes:
                        new_node.attributes[
                            (namespaces.get(prefix) or "", local_name)
                        ] = value

                    node.append_children(new_node)
                    node = new_node

                case 1:
                    node = cast("TagNode", candidates[0])

                case _:
                    raise AmbiguousTreeError(
                        f"The tree has multiple possible branches at location step {i}."
                    )
        assert isinstance(node, TagNode)
        return node

    def _get_normalize_space_directive(
        self, default: Literal["default", "preserve"] = "default"
    ) -> Literal["default", "preserve"]:
        if (attribute := self.attributes.get((XML_NAMESPACE, "space"))) is None:
            return default

        if attribute in ("default", "preserve"):
            return attribute

        warnings.warn(
            "Encountered and ignoring an invalid `xml:space` attribute: "
            + attribute.value,
            category=UserWarning,
        )
        return default

    @property
    def id(self) -> Optional[str]:
        return self.attributes.get((XML_NAMESPACE, "id"))

    @id.setter
    def id(self, value: Optional[str]):
        match value:
            case None:
                del self.attributes[(XML_NAMESPACE, "id")]
            case str():
                if not _is_xml_name(value):
                    raise ValueError("Value is not a valid xml name.")
                root = cast("TagNode", last(self._iterate_ancestors())) or self
                for node in chain((root,), root._iterate_descendants()):
                    if not isinstance(node, TagNode):
                        continue
                    if node.attributes.get((XML_NAMESPACE, "id"), "") == value:
                        raise ValueError(
                            "An xml:id-attribute with that value is already assigned "
                            "in the tree."
                        )
                self.attributes[(XML_NAMESPACE, "id")] = value
            case _:
                raise TypeError("Value must be None or a string.")

    @property
    def local_name(self) -> str:

        return self.__local_name

    @local_name.setter
    def local_name(self, value: str):
        if not _is_xml_name(value):
            raise ValueError("Value is not a valid xml name.")
        self.__local_name = value

    @property
    def location_path(self) -> str:
        if not isinstance(self._parent, TagNode):
            return "/*"

        steps: list[XMLNodeType] = list(self._iterate_ancestors())
        steps.pop()  # root
        steps.reverse()
        steps.append(self)
        with altered_default_filters(is_tag_node):  # to affect the .index value
            return "/*" + "".join(f"/*[{cast('int', n.index)+1}]" for n in steps)

    @property
    def namespace(self) -> str:
        """
        The node's namespace. An empty string represents an empty namespace.

        :meta category: Node properties
        """
        return self.__namespace

    @namespace.setter
    def namespace(self, value: str):
        # TODO see https://github.com/delb-xml/delb-py/issues/69
        if value and not _is_xml_char(value):
            raise ValueError("Invalid XML character data.")
        self.__namespace = value

    def _new_tag_node_from_definition(self, definition: _TagDefinition) -> TagNode:
        return TagNode(
            local_name=definition.local_name,
            attributes=definition.attributes,
            namespace=self.namespace,
            children=definition.children,
        )

    @staticmethod
    def parse(text, parser_options):  # pragma: no cover
        # REMOVE with version 0.7
        """This method has been replaced by :func:`delb.parse_tree`."""
        raise InvalidOperation(
            "This method has been replaced by `delb.parse_tree`.",
        )

    def _reduce_whitespace(
        self, normalize_space: Literal["default", "preserve"] = "default"
    ):
        self._reduce_whitespace_of_descendants(normalize_space)

    def _reduce_whitespace_of_descendants(
        self, normalize_space: Literal["default", "preserve"]
    ):
        if not (child_nodes := self._child_nodes):
            return

        self.merge_text_nodes(deep=False)

        if (
            normalize_space := self._get_normalize_space_directive(normalize_space)
        ) == "default":
            assert isinstance(child_nodes, Siblings)
            _reduce_whitespace_between_siblings(child_nodes)

        for child_node in (n for n in child_nodes if isinstance(n, TagNode)):
            child_node._reduce_whitespace_of_descendants(normalize_space)

    def serialize(
        self,
        *,
        format_options: Optional[FormatOptions] = None,
        namespaces: Optional[NamespaceDeclarations] = None,
        newline: Optional[str] = None,
    ) -> str:
        serializer = _get_serializer(
            _StringWriter(newline=newline),
            format_options=format_options,
            namespaces=namespaces,
        )
        serializer.serialize_root(self)
        return serializer.writer.result

    @property
    def universal_name(self) -> str:
        return "{" + self.__namespace + "}" + self.__local_name


class TextNode(_LeafNode, _StringMixin, TextNodeType):  # type: ignore
    """
    TextNodes contain the textual data of a document. The class shall not be initialized
    by client code, just throw strings into the trees.

    This class implements :class:`delb.typing.TextNodeType`.

    Instances expose all methods of :class:`str` except :meth:`str.index`:

    >>> node = TextNode("Show us the way to the next whisky bar.")
    >>> node.split()
    ['Show', 'us', 'the', 'way', 'to', 'the', 'next', 'whisky', 'bar.']

    Instances can be tested for inequality with other text nodes and strings:

    >>> TextNode("ham") == TextNode("spam")
    False
    >>> TextNode("Patsy") == "Patsy"
    True

    And they can be tested for substrings:

    >>> "Sir" in TextNode("Sir Bedevere the Wise")
    True

    Attributes that rely to child nodes yield nothing respectively :obj:`None`.
    """

    __slots__ = ("__content",)

    def __init__(
        self,
        text: str | TextNode,
    ):
        super().__init__()
        match text:
            case str():
                self.content = text
            case TextNode():
                self.content = text.__content
            case _:
                raise TypeError

    def __eq__(self, other):
        if isinstance(other, TextNode):
            return self.__content == other.content
        else:
            return super().__eq__(other)

    def __getitem__(self, item):
        return self.content[item]

    def __len__(self):
        return len(self.__content)

    def __repr__(self):
        return f'<{self.__class__.__name__}(text="{self.content}",  [{hex(id(self))}]>'

    def __str__(self):
        return self.__content

    def clone(self, deep: bool = False) -> TextNodeType:
        return TextNode(self.__content)

    @property
    def content(self) -> str:
        return self.__content

    @content.setter
    def content(self, text: str):
        if not isinstance(text, str):
            raise TypeError
        self.__content = text

    @property
    def full_text(self) -> str:
        return self.__content


#


__all__ = (
    Attribute.__name__,
    CommentNode.__name__,
    ProcessingInstructionNode.__name__,
    QueryResults.__name__,
    Siblings.__name__,
    TagAttributes.__name__,
    TagNode.__name__,
    TextNode.__name__,
)
