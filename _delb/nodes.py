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

import gc
import warnings
from abc import abstractmethod, ABC
from collections import deque
from collections.abc import (
    Iterable,
    Iterator,
    Mapping,
    MutableMapping,
    MutableSequence,
    Sequence,
)
from contextlib import contextmanager
from copy import copy
from io import StringIO, TextIOWrapper
from itertools import chain
from sys import getrefcount
from typing import (
    TYPE_CHECKING,
    cast,
    overload,
    Any,
    ClassVar as ClassWar,
    Final,
    Literal,
    NamedTuple,
    Optional,
)

from lxml import etree

from _delb.exceptions import AmbiguousTreeError, InvalidCodePath, InvalidOperation
from _delb.names import (
    GLOBAL_PREFIXES,
    XML_NAMESPACE,
    deconstruct_clark_notation,
    Namespaces,
)
from _delb.utils import (
    _StringMixin,
    _crunch_whitespace,
    last,
    traverse_bf_ltr_ttb,
)
from _delb.xpath import QueryResults, _css_to_xpath
from _delb.xpath import evaluate as evaluate_xpath, parse as parse_xpath
from _delb.xpath.ast import _DocumentNode, NameMatchTest, XPathExpression

if TYPE_CHECKING:
    from typing import TextIO

    from delb import Document
    from _delb.typing import (
        AttributeAccessor,
        _AttributesData,
        Filter,
        NamespaceDeclarations,
        NodeSource,
        QualifiedName,
    )


# shortcuts


Comment = etree.Comment
_Element = etree._Element
PI = etree.PI
QName = etree.QName


# constants


CTRL_CHAR_ENTITY_NAME_MAPPING: Final = (
    ("&", "amp"),
    (">", "gt"),
    ("<", "lt"),
    ('"', "quot"),
)
CCE_TABLE_FOR_ATTRIBUTES: Final = str.maketrans(
    {ord(k): f"&{v};" for k, v in CTRL_CHAR_ENTITY_NAME_MAPPING}
)
CCE_TABLE_FOR_TEXT: Final = str.maketrans(
    {ord(k): f"&{v};" for k, v in CTRL_CHAR_ENTITY_NAME_MAPPING if k != '"'}
)

DETACHED, DATA, TAIL, APPENDED = 0, 1, 2, 3


ATTRIBUTE_ACCESSOR_MSG: Final = (
    "An attribute name must be provided as string (either a local name or a "
    "universal in Clark notation) or as namespace and local name packed in a tuple."
)


# wrapper cache


class _WrapperCache:
    __slots__ = ("locks", "wrappers")

    def __init__(self):
        self.wrappers = {}
        self.locks = 0
        gc.callbacks.append(self.__gc_callback__)

    def __call__(self, element: _Element) -> _ElementWrappingNode:
        result = self.wrappers.get(element)
        if result is None:
            tag = element.tag
            if tag is Comment:
                result = CommentNode(element)
            elif tag is PI:
                result = ProcessingInstructionNode(element)
            else:
                result = TagNode(element)
            self.wrappers[element] = result
            # turn on when running tests, turn off when using a debugger:
            # assert getrefcount(result) == 3, getrefcount(result)  # noqa: E800
        return result

    def __enter__(self):
        self.locks += 1
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.locks -= 1
        return False

    def __gc_callback__(self, phase: str, info: dict):  # noqa: C901
        """
        This is the verbose implementation, please verify changes with this one:

        .. code-block:

            def __gc_callback__(self, phase: str, info: dict):
                if phase != "stop" or self.locks:
                    return

                for element, node in tuple(self.wrappers.items()):
                    node_user_references = (
                        getrefcount(node)
                        - 1  # `getrefcount`
                        - 1  # `self.wrappers`
                        - 1  # the iterated tuple
                        - 1  # `node`
                        - isinstance(node, TagNode)  # node.attributes._node
                    )

                    # if referenced as a document's root node that itself isn't
                    # referenced:
                    if getattr(node, "__document__", None) is not None:
                        document_user_references = (
                            getrefcount(node.__document__)
                            - 1  # `getrefcount`
                            - 1  # `document.root.__document__
                            - 1  # `document.head_nodes._document`
                            - 1  # `document.tail_nodes._document`
                        )
                        assert document_user_references >= 0
                        if document_user_references == 0:
                            node_user_references -= 1

                    assert node_user_references >= 0
                    if node_user_references > 0:
                        continue

                    if isinstance(node, TagNode):
                        data_node = node._data_node
                        tail_node = node._tail_node
                        if self._appendees_are_referenced(
                            data_node
                        ) or self._appendees_are_referenced(tail_node):
                            continue
                        data_node._merge_appended_text_nodes()
                    elif isinstance(node, _ElementWrappingNode):
                        tail_node = node._tail_node
                        if self._appendees_are_referenced(tail_node):
                            continue
                    else:
                        raise RuntimeError

                    tail_node._merge_appended_text_nodes()
                    self.wrappers.pop(element)

            def _appendees_are_referenced(self, node: TextNode) -> bool:
                appendees = []
                current = node._appended_text_node
                while current is not None:
                    appendees.append(current)
                    current = current._appended_text_node

                if not appendees:
                    return False

                # the last item in a sequence of text nodes isn't pointed to as a
                # `_bound_to`:
                user_references = (
                    getrefcount(appendees.pop())
                    - 1  # `getrefcount`
                    - 1  # the predecessor's `_appended_text_node`
                )

                assert user_references >= 0
                if user_references:
                    return True

                for refcount in (getrefcount(text_node) for text_node in appendees):
                    user_references = (
                        refcount
                        - 1  # `getrefcount`
                        - 1  # the predecessor's `_appended_text_node`
                        - 1  # the subsequent's `_bound_to`
                        - 1  # `appendees`
                        - 1  # `text_node`
                    )
                    assert user_references >= 0
                    if user_references:
                        return True

                return False
        """
        if phase != "stop" or self.locks:
            return

        for element, node in tuple(self.wrappers.items()):
            if getrefcount(node) > (
                4
                + isinstance(node, TagNode)
                + (
                    getattr(node, "__document__", None) is not None
                    and getrefcount(node.__document__) == 2
                )
            ):
                continue

            skip = False
            tail_node = node._tail_node

            if isinstance(node, TagNode):
                # data node is checked first, assuming that appended text nodes tend
                # to be used in the depths of a tree
                data_node = node._data_node
                current = data_node._appended_text_node
                while current is not None:
                    _next = current._appended_text_node
                    if getrefcount(current) > 3 + (_next is not None):
                        skip = True
                        break
                    current = _next
                if skip:
                    continue

                current = tail_node._appended_text_node
                while current is not None:
                    _next = current._appended_text_node
                    if getrefcount(current) > 3 + (_next is not None):
                        skip = True
                        break
                    current = _next
                if skip:
                    continue

                data_node._merge_appended_text_nodes()

            else:  # isinstance(node, _ElementWrappingNode)
                current = tail_node._appended_text_node
                while current is not None:
                    _next = current._appended_text_node
                    if getrefcount(current) > 3 + (_next is not None):
                        skip = True
                        break
                    current = _next
                if skip:
                    continue

            tail_node._merge_appended_text_nodes()
            self.wrappers.pop(element)


_wrapper_cache = _WrapperCache()


# functions


def new_comment_node(content: str) -> CommentNode:
    """
    Creates a new :class:`CommentNode`.

    :param content: The comment's content a.k.a. text.
    :return: The newly created comment node.
    """
    CommentNode._validate_content(content)
    result = _wrapper_cache(etree.Comment(content))
    assert isinstance(result, CommentNode)
    return result


def new_processing_instruction_node(
    target: str, content: str
) -> ProcessingInstructionNode:
    """
    Creates a new :class:`ProcessingInstructionNode`.

    :param target: The processing instruction's target name.
    :param content: The processing instruction's text.
    :return: The newly created processing instruction node.
    """
    ProcessingInstructionNode._validate_target_value(target)
    result = _wrapper_cache(etree.PI(target, content))
    assert isinstance(result, ProcessingInstructionNode)
    return result


def new_tag_node(
    local_name: str,
    attributes: Optional[
        _AttributesData | dict[AttributeAccessor, str] | TagAttributes
    ] = None,
    namespace: Optional[str] = None,
    children: Iterable[NodeSource] = (),
) -> TagNode:
    """
    Creates a new :class:`TagNode` instance.

    :param local_name: The tag name.
    :param attributes: Optional attributes that are assigned to the new node.
    :param namespace: An optional tag namespace.
    :param children: An optional iterable of objects that will be appended as child
                     nodes. This can be existing nodes, strings that will be inserted
                     as text nodes and in-place definitions of :class:`TagNode`
                     instances from :func:`tag`. The latter will be assigned to the
                     same namespace.
    :return: The newly created tag node.
    """

    result = _wrapper_cache(
        etree.Element(QName(namespace or None, local_name).text),
    )
    assert isinstance(result, TagNode)
    if attributes is not None:
        for name, value in attributes.items():
            result.attributes[name] = value

    for child in children:
        if isinstance(child, (str, NodeBase, _TagDefinition)):
            result.append_children(child)
        else:
            raise TypeError(
                "Either node instances, strings or objects from :func:`delb.tag` must "
                "be provided as children argument."
            )

    return result


def _reduce_whitespace_between_siblings(
    nodes: MutableSequence[NodeBase], in_place: bool
):
    if not (text_nodes := tuple(n for n in nodes if isinstance(n, TextNode))):
        return

    first_node = nodes[0]
    last_node = nodes[-1]

    for node in text_nodes:
        if reduced_content := _reduce_whitespace_content(
            node.content,
            node is first_node,
            node is last_node,
        ):
            node.content = reduced_content
        else:
            if in_place:
                node.detach()
            else:
                nodes.remove(node)


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


# default filters


def _is_tag_or_text_node(node: NodeBase) -> bool:
    return isinstance(node, (TagNode, TextNode))


default_filters: deque[tuple[Filter, ...]] = deque()
default_filters.append((_is_tag_or_text_node,))


@contextmanager
def altered_default_filters(*filter: Filter, extend: bool = False):
    """
    This function can be either used as as :term:`context manager` or :term:`decorator`
    to define a set of :obj:`default_filters` for the encapsuled code block or callable.

    :param filter: The filters to set or append.
    :param extend: Extends the currently active filters with the given ones instead of
                   replacing them.

    These are then applied in all operations that allow node filtering, like
    :meth:`TagNode.next_node`. Mind that they also affect a node's index property and
    indexed access to child nodes.

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


# attributes


class Attribute(_StringMixin):
    """
    Attribute objects represent :term:`tag node`'s attributes. See the
    :meth:`delb.TagNode.attributes` documentation for capabilities.
    """

    __slots__ = ("_attributes", "_detached_value", "_qualified_name")

    def __init__(self, attributes: TagAttributes, qualified_name: QualifiedName):
        self._attributes: TagAttributes | None = attributes
        self._detached_value: str | None = None
        self._qualified_name = qualified_name

    def __repr__(self):
        return (
            f'<{self.__class__.__name__}({self.universal_name}="{self.value}")'
            f" [{hex(id(self))}]>"
        )

    def _set_new_key(self, namespace: str, name: str):
        if self._qualified_name == (namespace, name):
            return

        attributes = self._attributes
        current = self.namespace, self.local_name
        assert attributes is not None
        attributes[(namespace, name)] = self.value
        self._qualified_name = (namespace, name)
        del attributes[current]
        self._attributes = attributes

    @property
    def local_name(self) -> str:
        """The attribute's local name."""
        return self._qualified_name[1]

    @local_name.setter
    def local_name(self, name: str):
        self._set_new_key(self.namespace, name)

    @property
    def namespace(self) -> str:
        """The attribute's namespace"""
        return self._qualified_name[0]

    @namespace.setter
    def namespace(self, namespace: str):
        self._set_new_key(namespace, self.local_name)

    @property
    def _namespace(self) -> str:
        warnings.warn("Use Attribute.namespace instead!", category=DeprecationWarning)
        return self.namespace

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
        if self._attributes is None:
            assert self._detached_value is not None
            return self._detached_value
        else:
            value = self._attributes._etree_attrib[
                self._attributes._etree_key(self._qualified_name)
            ]
            return value.decode() if isinstance(value, bytes) else value

    @value.setter
    def value(self, value: str):
        if self._attributes is None:
            self._detached_value = value
        else:
            etree_key = self._attributes._etree_key(self._qualified_name)
            self._attributes._etree_attrib[etree_key] = value

    # for utils._StringMixin:
    _data = value


class TagAttributes(MutableMapping):
    """
    A data type to access a :term:`tag node`'s attributes.

    Note that due to the current lxml backend there's no distinction between attributes
    with no namespace and such in the default namespace, both variants access the same
    data. If you you managed yourself into a position where that matters, the only
    technical solution is to re-encode the document to not contain any empty namespace.
    This will not be an issue with delb 0.7, according to the plan.
    """

    __default = object()

    __slots__ = ("_attributes", "_etree_attrib", "_node")

    def __init__(self, node: TagNode):
        self._attributes: dict[QualifiedName, Attribute] = {}
        self._etree_attrib: etree._Attrib = node._etree_obj.attrib
        self._node = node

    def __contains__(self, item: Any) -> bool:
        return self._etree_key(self.__resolve_accessor(item)) in self._etree_attrib

    def __delitem__(self, item: AttributeAccessor):
        if item not in self:
            raise KeyError

        qualified_name = self.__resolve_accessor(item)
        attribute = self[qualified_name]
        assert attribute is not None
        attribute._detached_value = attribute.value
        del self._etree_attrib[self._etree_key(qualified_name)]
        del self._attributes[qualified_name]
        attribute._attributes = None

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Mapping):
            return False

        if len(self) != len(other):
            return False

        if isinstance(other, TagAttributes):
            # TODO optimize with native data model
            for key, attribute in self.items():
                assert isinstance(attribute, Attribute)
                other_value = other.get((attribute.namespace, attribute.local_name))
                if (other_value is None) or (attribute != other_value):
                    return False
        else:
            for key, value in other.items():
                if key not in self:
                    return False
                if self[key] != value:
                    return False

        return True

    def _etree_key(self, item: QualifiedName) -> str:
        namespace, name = item

        if namespace and self._node._etree_obj.nsmap.get(None) != namespace:
            return f"{{{namespace}}}{name}"
        else:
            return name

    def __getitem__(self, item: AttributeAccessor) -> Attribute:
        if item in self:
            qualified_name = self.__resolve_accessor(item)
            result = self._attributes.get(qualified_name)
            if result is None:
                result = Attribute(self, qualified_name)
                self._attributes[qualified_name] = result
            return result
        else:
            raise KeyError(item)

    def __iter__(self) -> Iterator[QualifiedName]:
        results = []
        for key in self._etree_attrib:
            assert isinstance(key, str)
            namespace, name = deconstruct_clark_notation(key)
            if namespace is None:
                namespace = self._node._etree_obj.nsmap.get(None, "")
            assert isinstance(namespace, str)
            results.append((namespace, name))
        return iter(results)

    def __len__(self) -> int:
        return len(self._etree_attrib)

    def __setitem__(self, item: AttributeAccessor, value: str | Attribute):
        qualified_name = self.__resolve_accessor(item)
        key = self._etree_key(qualified_name)
        if isinstance(value, Attribute):
            value = value.value
        self._etree_attrib[key] = value
        self._attributes[qualified_name] = Attribute(self, qualified_name)

    def __str__(self):
        return str(self.as_dict_with_strings())

    __repr__ = __str__

    def __resolve_accessor(self, item: AttributeAccessor) -> QualifiedName:
        if isinstance(item, str):
            namespace, name = deconstruct_clark_notation(item)
        elif isinstance(item, tuple):
            namespace, name = item
        else:
            namespace = name = None

        if name is None:
            raise TypeError(ATTRIBUTE_ACCESSOR_MSG)

        if namespace is None:
            namespace = self._node.namespace

        return namespace, name

    def as_dict_with_strings(self) -> dict[str, str]:
        """Returns the attributes as :class:`str` instances in a :class:`dict`."""
        return {a.universal_name: a.value for a in self.values()}


# containers


class Siblings:
    """
    Container for the sisterhood of nodes.
    Everyone's taken care of.
    """

    __slots__ = ("__data",)

    def __init__(self, nodes: Optional[Iterable[NodeBase]] = None):
        self.__data: list[NodeBase] = []
        if nodes is not None:
            for node in nodes:
                self.__data.append(self._handle_new_sibling(node))

    def __add__(self, other: Any):
        if isinstance(other, Iterable):
            for item in other:
                self.append(self._handle_new_sibling(item))
            return self

        raise TypeError

    def __delitem__(self, index: int):
        del self.__data[index]

    @overload
    def __getitem__(self, index: int) -> NodeBase:
        pass

    @overload
    def __getitem__(self, index: slice) -> tuple[NodeBase, ...]:
        pass

    def __getitem__(self, index: int | slice) -> NodeBase | tuple[NodeBase, ...]:
        if isinstance(index, int):
            return self.__data[index]
        elif isinstance(index, slice):
            return tuple(self.__data[index])
        else:
            raise TypeError

    def __iter__(self) -> Iterator[NodeBase]:
        return iter(self.__data)

    def __len__(self) -> int:
        return len(self.__data)

    def __setitem__(self, index: int, node: NodeSource):
        self.__data[index] = self._handle_new_sibling(node)

    def append(self, node: NodeBase):
        self.__data.append(self._handle_new_sibling(node))

    def insert(self, index: int, node: NodeSource):
        self.__data.insert(index, self._handle_new_sibling(node))

    def prepend(self, node: NodeSource):
        self.insert(0, node)

    @classmethod
    def _handle_new_sibling(cls, node: NodeSource) -> NodeBase:
        if isinstance(node, str):  # noqa: SIM114
            raise NotImplementedError
        elif isinstance(node, _TagDefinition):
            raise NotImplementedError
        elif isinstance(node, NodeBase):
            if node.parent is not None:
                raise InvalidOperation(
                    "Only a detached node can be added to the tree. Use "
                    ":meth:`TagNode.clone` or :meth:`TagNode.detach` to get one."
                )
        else:
            raise InvalidOperation("Item must be a `delb.NodeBase` instance.")

        return node


# nodes


class NodeBase(ABC):
    __slots__ = ("__weakref__",)

    def __str__(self) -> str:
        return self.serialize(
            format_options=DefaultStringOptions.format_options,
            namespaces=DefaultStringOptions.namespaces,
            newline=DefaultStringOptions.newline,
        )

    def add_following_siblings(
        self, *node: NodeSource, clone: bool = False
    ) -> tuple[NodeBase, ...]:
        """
        Adds one or more nodes to the right of the node this method is called on.

        :param node: The node(s) to be added.
        :param clone: Clones the concrete nodes before adding if :obj:`True`.
        :return: The concrete nodes that were added.
        :meta category: Methods to add nodes to a tree

        The nodes can be concrete instances of any node type or rather abstract
        descriptions in the form of strings or objects returned from the :func:`tag`
        function that are used to derive :class:`TextNode` respectively :class:`TagNode`
        instances from.
        """
        if not node:
            return ()

        this, queue = self._prepare_new_relative(node, clone)
        self._validate_sibling_operation(this)
        self._add_following_sibling(this)
        result: tuple[NodeBase, ...] = (this,)
        if queue:
            result += this.add_following_siblings(*queue, clone=clone)
        return result

    @abstractmethod
    def _add_following_sibling(self, node: NodeBase):
        pass

    def add_preceding_siblings(
        self, *node: NodeSource, clone: bool = False
    ) -> tuple[NodeBase, ...]:
        """
        Adds one or more nodes to the left of the node this method is called on.

        :param node: The node(s) to be added.
        :param clone: Clones the concrete nodes before adding if :obj:`True`.
        :return: The concrete nodes that were added.
        :meta category: Methods to add nodes to a tree

        The nodes can be concrete instances of any node type or rather abstract
        descriptions in the form of strings or objects returned from the :func:`tag`
        function that are used to derive :class:`TextNode` respectively :class:`TagNode`
        instances from.
        """
        if not node:
            return ()

        this, queue = self._prepare_new_relative(node, clone)
        self._validate_sibling_operation(this)
        self._add_preceding_sibling(this)
        result: tuple[NodeBase, ...] = (this,)
        if queue:
            result += this.add_preceding_siblings(*queue, clone=clone)
        return result

    @abstractmethod
    def _add_preceding_sibling(self, node: NodeBase):
        pass

    @abstractmethod
    def clone(self, deep: bool = False) -> NodeBase:
        """
        Creates a new node of the same type with duplicated contents.

        :param deep: Clones the whole subtree if :obj:`True`.
        :return: A copy of the node.
        """
        pass

    @property
    @abstractmethod
    def depth(self) -> int:
        """
        The depth (or level) of the node in its tree.

        :meta category: Node properties
        """
        pass

    @abstractmethod
    def detach(self, retain_child_nodes: bool = False) -> NodeBase:
        """
        Removes the node from its tree.

        :param retain_child_nodes: Keeps the node's descendants in the originating
                                   tree if :obj:`True`.
        :return: The removed node.
        :meta category: Methods to remove a node
        """
        pass

    @property
    @abstractmethod
    def document(self) -> Optional[Document]:
        """
        The :class:`Document` instance that the node is associated with or
        :obj:`None`.

        :meta category: Related document and nodes properties
        """
        pass

    def fetch_following(self, *filter: Filter) -> Optional[NodeBase]:
        """
        Retrieves the next filter matching node on the following axis.

        :param filter: Any number of :term:`filter` s.
        :return: The next node in document order that matches all filters or
                 :obj:`None`.
        :meta category: Methods to fetch a relative node
        """
        try:
            return next(self.iterate_following(*filter))
        except StopIteration:
            return None

    def fetch_following_sibling(self, *filter: Filter) -> Optional[NodeBase]:
        """
        Retrieves the next filter matching node on the following-sibling axis.

        :param filter: Any number of :term:`filter` s.
        :return: The next sibling to the right that matches all filters or
                 :obj:`None`.
        :meta category: Methods to fetch a relative node
        """
        all_filters = default_filters[-1] + filter
        candidate = self._fetch_following_sibling()
        while candidate is not None:
            if all(f(candidate) for f in all_filters):
                return candidate
            candidate = candidate._fetch_following_sibling()

        return None

    @abstractmethod
    def _fetch_following_sibling(self):
        pass

    def fetch_preceding(self, *filter: Filter) -> Optional[NodeBase]:
        """
        Retrieves the next filter matching node on the preceding axis.

        :param filter: Any number of :term:`filter` s.
        :return: The previous node in document order that matches all filters or
                 :obj:`None`.
        :meta category: Methods to fetch a relative node
        """
        try:
            return next(self.iterate_preceding(*filter))
        except StopIteration:
            return None

    @abstractmethod
    def fetch_preceding_sibling(self, *filter: Filter) -> Optional[NodeBase]:
        """
        Retrieves the next filter matching node on the preceding-sibling axis.

        :param filter: Any number of :term:`filter` s.
        :return: The next sibling to the left that matches all filters or
                 :obj:`None`.
        :meta category: Methods to fetch a relative node
        """
        pass

    @property
    @abstractmethod
    def first_child(self) -> Optional[NodeBase]:
        """
        The node's first child node.

        :meta category: Related document and nodes properties
        """
        pass

    @property
    @abstractmethod
    def full_text(self) -> str:
        """
        The concatenated contents of all text node descendants in document order.

        :meta category: Node content properties
        """
        pass

    @property
    def index(self) -> Optional[int]:
        """
        The node's index within the parent's collection of child nodes or :obj:`None`
        when the node has no parent.

        :meta category: Node properties
        """
        parent = self.parent

        if parent is None:
            return None

        for index, node in enumerate(parent.iterate_children()):
            if node is self:
                return index

        raise InvalidCodePath

    def iterate_ancestors(self, *filter: Filter) -> Iterator[TagNode]:
        """
        Iterator over the filter matching nodes on the ancestor axis.

        :param filter: Any number of :term:`filter` s that a node must match to be
               yielded.
        :return: A :term:`generator iterator` that yields the ancestor nodes from bottom
                 to top.
        :meta category: Methods to iterate over related node
        """
        parent = self.parent
        if parent:
            if all(f(parent) for f in filter):
                yield parent
            yield from parent.iterate_ancestors(*filter)

    @abstractmethod
    def iterate_children(self, *filter: Filter) -> Iterator[NodeBase]:
        """
        Iterator over the filter matching nodes on the child axis.

        :param filter: Any number of :term:`filter` s that a node must match to be
                       yielded.
        :return: A :term:`generator iterator` that yields the child nodes of the node.
        :meta category: Methods to iterate over related node
        """
        pass

    @abstractmethod
    def iterate_descendants(self, *filter: Filter) -> Iterator[NodeBase]:
        """
        Iterator over the filter matching nodes on the ancestor axis.

        :param filter: Any number of :term:`filter` s that a node must match to be
                       yielded.
        :return: A :term:`generator iterator` that yields the descending nodes of the
                 node.
        :meta category: Methods to iterate over related node
        """
        pass

    def iterate_following(self, *filter: Filter) -> Iterator[NodeBase]:
        """
        Iterator over the filter matching nodes on the following axis.

        :param filter: Any number of :term:`filter` s that a node must match to be
               yielded.
        :return: A :term:`generator iterator` that yields the following nodes in
                 document order.
        :meta category: Methods to iterate over related node
        """
        for node in self._iterate_following():
            if all(f(node) for f in chain(default_filters[-1], filter)):
                yield node

    def _iterate_following(self) -> Iterator[NodeBase]:
        def next_sibling_of_an_ancestor(
            node: NodeBase,
        ) -> Optional[_ElementWrappingNode]:
            parent = node.parent
            if parent is None:
                return None
            parents_next = parent._fetch_following_sibling()
            if parents_next is None:
                return next_sibling_of_an_ancestor(parent)
            return parents_next

        pointer = self
        while True:
            next_node = pointer.first_child
            if next_node is None:
                next_node = pointer._fetch_following_sibling()

            if next_node is None:
                next_node = next_sibling_of_an_ancestor(pointer)

            if next_node is None:
                return

            yield next_node
            pointer = next_node

    def iterate_following_siblings(self, *filter: Filter) -> Iterator[NodeBase]:
        """
        Iterator over the filter matching nodes on the following-sibling axis.

        :param filter: Any number of :term:`filter` s that a node must match to be
               yielded.
        :return: A :term:`generator iterator` that yields the siblings to the node's
                 right.
        :meta category: Methods to iterate over related node
        """
        next_node = self.fetch_following_sibling(*filter)
        while next_node is not None:
            yield next_node
            next_node = next_node.fetch_following_sibling(*filter)

    def iterate_preceding(self, *filter: Filter) -> Iterator[NodeBase]:
        """
        Iterator over the filter matching nodes on the preceding axis.

        :param filter: Any number of :term:`filter` s that a node must match to be
               yielded.
        :return: A :term:`generator iterator` that yields the previous nodes in document
                 order.
        :meta category: Methods to iterate over related node
        """
        for node in self._iterate_preceding():
            if all(f(node) for f in filter):
                yield node

    @altered_default_filters()
    def _iterate_preceding(self) -> Iterator[NodeBase]:
        def iter_children(node: NodeBase) -> Iterator[NodeBase]:
            for child_node in reversed(tuple(node.iterate_children())):
                yield from iter_children(child_node)
                yield child_node

        pointer: NodeBase | None = self
        assert pointer is not None
        last_yield: NodeBase = pointer

        while True:
            pointer = pointer.fetch_preceding_sibling()

            if pointer is not None:
                yield from iter_children(pointer)
                yield pointer
                last_yield = pointer

            else:
                parent = last_yield.parent
                if parent is None:
                    return
                yield parent
                pointer = last_yield = parent

    def iterate_preceding_siblings(self, *filter: Filter) -> Iterator[NodeBase]:
        """
        Iterator over the filter matching nodes on the preceding-sibling axis.

        :param filter: Any number of :term:`filter` s that a node must match to be
               yielded.
        :return: A :term:`generator iterator` that yields the siblings to the node's
                 left.
        :meta category: Methods to iterate over related node
        """
        previous_node = self.fetch_preceding_sibling(*filter)
        while previous_node is not None:
            yield previous_node
            previous_node = previous_node.fetch_preceding_sibling(*filter)

    @property
    @abstractmethod
    def last_child(self) -> Optional[NodeBase]:
        """
        The node's last child node.

        :meta category: Related document and nodes properties
        """
        pass

    @property
    @abstractmethod
    def last_descendant(self) -> Optional[NodeBase]:
        """
        The node's last descendant.

        :meta category: Related document and nodes properties
        """
        pass

    def _new_tag_node_from(
        self,
        context: _Element,
        local_name: str,
        attributes: Optional[dict[AttributeAccessor, str]],
        namespace: Optional[str],
        children: Sequence[NodeSource],
    ) -> TagNode:
        tag: QName

        context_namespace = QName(context).namespace

        if namespace:
            tag = QName(namespace or None, local_name)
        elif context_namespace:
            tag = QName(context_namespace, local_name)
        else:
            tag = QName(local_name)

        result = _wrapper_cache(
            context.makeelement(
                tag.text,
                # TODO https://github.com/lxml/lxml-stubs/issues/62
                nsmap=context.nsmap,  # type: ignore
            ),
        )
        assert isinstance(result, TagNode)

        if attributes is not None:
            for name, value in attributes.items():
                if isinstance(name, str):
                    namespace, local_name = deconstruct_clark_notation(name)
                    if namespace is None:
                        result.attributes[(context_namespace, local_name)] = value
                    else:
                        result[(namespace, local_name)] = value
                else:
                    assert isinstance(name, tuple)
                    result.attributes[name] = value

        if children:
            result.append_children(*children)

        return result

    def _new_tag_node_from_definition(self, definition: _TagDefinition) -> TagNode:
        return self.parent._new_tag_node_from_definition(definition)

    @property
    @abstractmethod
    def parent(self):
        """
        The node's parent or :obj:`None`.

        :meta category: Related document and nodes properties
        """
        pass

    @altered_default_filters()
    def _prepare_new_relative(
        self, nodes: tuple[NodeSource, ...], clone: bool
    ) -> tuple[NodeBase, list[NodeSource]]:
        this, *queue = nodes
        if isinstance(this, str):
            this = TextNode(this)
        elif isinstance(this, NodeBase):
            if clone:
                this = this.clone(deep=True)
        elif isinstance(this, _TagDefinition):
            this = self._new_tag_node_from_definition(this)
        else:
            raise TypeError(
                "Either node instances, strings or objects from :func:`delb.tag` must "
                "be provided as children argument."
            )

        if not all(
            x is None
            for x in (
                this.parent,
                this._fetch_following_sibling(),
                this.fetch_preceding_sibling(),
            )
        ):
            raise InvalidOperation(
                "A node that shall be added to a tree must have neither a parent nor "
                "any sibling node. Use :meth:`NodeBase.detach` or a `clone` argument "
                "to move a node within or between trees."
            )

        return this, queue

    def replace_with(self, node: NodeSource, clone: bool = False) -> NodeBase:
        """
        Removes the node and places the given one in its tree location.

        The node can be a concrete instance of any node type or a rather abstract
        description in the form of a string or an object returned from the :func:`tag`
        function that is used to derive a :class:`TextNode` respectively
        :class:`TagNode` instance from.

        :param node: The replacing node.
        :param clone: A concrete, replacing node is cloned if :obj:`True`.
        :return: The removed node.
        :meta category: Methods to remove a node
        """
        if self.parent is None:
            raise InvalidOperation(
                "Cannot replace a root node of a tree. Maybe you want to set the "
                "`root` property of a Document instance?"
            )

        self.add_following_siblings(node, clone=clone)
        return self.detach()

    @altered_default_filters()
    def serialize(
        self,
        *,
        format_options: Optional[FormatOptions] = None,
        namespaces: Optional[NamespaceDeclarations] = None,
        newline: Optional[str] = None,
    ):
        """
        Returns a string that contains the serialization of the node. See
        :doc:`/api/serialization` for details.

        :param format_options: An instance of :class:`FormatOptions` can be provided to
                               configure formatting.
        :param namespaces: A mapping of prefixes to namespaces.  If not provided the
                           node's namespace will serve as default namespace.  Prefixes
                           for undeclared namespaces are enumerated with the prefix
                           ``ns``.
        :param newline: See :class:`io.TextIOWrapper` for a detailed explanation of the
                        parameter with the same name.
        """
        serializer = _get_serializer(
            _StringWriter(newline=newline),
            format_options=format_options,
            namespaces=namespaces,
        )
        with _wrapper_cache:
            serializer.serialize_node(self)
        return serializer.writer.result

    def _validate_sibling_operation(self, node):
        if self.parent is None and not (
            # is happening among valid root node siblings
            isinstance(node, (CommentNode, ProcessingInstructionNode))
            and (isinstance(self, (CommentNode, ProcessingInstructionNode)))
        ):
            raise InvalidOperation(
                "Not all node types can be added as siblings to a root node."
            )

    @altered_default_filters()
    def xpath(
        self,
        expression: str,
        namespaces: Optional[NamespaceDeclarations] = None,
    ) -> QueryResults:
        """
        Queries the tree with an XPath expression with this node as initial context
        node.

        :param expression: A supported XPath 1.0 expression that contains one or more
                           location paths.
        :param namespaces: A mapping of prefixes that are used in the expression to
                           namespaces. If not provided the node's namespace will serve
                           as default, mapped to an empty prefix.
        :return: All nodes that match the evaluation of the provided XPath expression.
        :meta category: Methods to query the tree

        See :doc:`/api/querying` for details on the extent of the XPath implementation.
        """
        return evaluate_xpath(node=self, expression=expression, namespaces=namespaces)


class _ChildLessNode(NodeBase):
    """Node types using this mixin also can't be root nodes of a document."""

    __slots__ = ()

    first_child = None
    """ The node's first child. """
    last_child = None
    """ The node's last child node. """
    last_descendant = None
    """ The node's last descendant. """

    @property
    def depth(self) -> int:
        return cast("TagNode", self.parent).depth + 1

    @property
    def document(self) -> Optional[Document]:
        parent = self.parent
        if parent is None:
            return None
        return parent.document

    def iterate_children(self, *filter: Filter) -> Iterator[NodeBase]:
        """
        A :term:`generator iterator` that yields nothing.

        :meta category: Methods to iterate over related node
        """
        yield from ()

    def iterate_descendants(self, *filter: Filter) -> Iterator[NodeBase]:
        """
        A :term:`generator iterator` that yields nothing.

        :meta category: Methods to iterate over related node
        """
        yield from ()


class _ElementWrappingNode(NodeBase):
    __slots__ = ("_etree_obj", "__namespaces", "_tail_node")

    def __init__(self, etree_element: _Element):
        self._etree_obj = etree_element
        self._tail_node = TextNode(etree_element, position=TAIL)

    def __copy__(self) -> _ElementWrappingNode:
        return self.clone(deep=False)

    def __deepcopy__(self, memodict=None) -> _ElementWrappingNode:
        return self.clone(deep=True)

    def _add_following_sibling(self, node: NodeBase):
        if isinstance(node, _ElementWrappingNode):
            my_old_tail = self._tail_node

            if self._tail_node._exists:
                my_old_tail._bind_to_tail(node)
                self._etree_obj.tail = None
                self._etree_obj.addnext(node._etree_obj)
                self._tail_node = TextNode(self._etree_obj, TAIL)

                assert self._tail_node is not my_old_tail
                assert node._tail_node is my_old_tail
            else:
                self._etree_obj.addnext(node._etree_obj)

                assert self._tail_node is my_old_tail
                assert node._tail_node is not my_old_tail

        elif isinstance(node, TextNode):
            assert node._position is DETACHED
            assert node._appended_text_node is None

            if self._tail_node._exists:
                my_old_tail = self._tail_node
                my_old_tail_content = my_old_tail.content

                node._bind_to_tail(self)
                node._appended_text_node = my_old_tail
                my_old_tail._bound_to = node
                my_old_tail._position = APPENDED
                my_old_tail.content = my_old_tail_content
            else:
                node._bind_to_tail(self)

    def _add_preceding_sibling(self, node: NodeBase):
        previous = self.fetch_preceding_sibling()

        if previous is None:
            if isinstance(node, _ElementWrappingNode):
                self._etree_obj.addprevious(node._etree_obj)

            else:
                assert isinstance(node, TextNode)
                parent = self.parent
                assert parent is not None
                assert not parent._data_node._exists
                node._bind_to_data(parent)

        else:
            previous._add_following_sibling(node)

    def clone(self, deep: bool = False) -> _ElementWrappingNode:
        etree_clone = copy(self._etree_obj)
        etree_clone.tail = None
        return _wrapper_cache(etree_clone)

    @altered_default_filters()
    def detach(self, retain_child_nodes: bool = False) -> _ElementWrappingNode:
        parent = self.parent

        if parent is None:
            return self

        etree_obj = self._etree_obj

        if self._tail_node._exists:
            if self.index == 0:
                self._tail_node._bind_to_data(parent)

            else:
                previous_node = self.fetch_preceding_sibling()
                if isinstance(previous_node, _ElementWrappingNode):
                    self._tail_node._bind_to_tail(previous_node)
                elif isinstance(previous_node, TextNode):
                    previous_node._insert_text_node_as_next_appended(self._tail_node)
                else:
                    raise InvalidCodePath

            etree_obj.tail = None
            self._tail_node = TextNode(etree_obj, position=TAIL)

        cast("_Element", etree_obj.getparent()).remove(etree_obj)

        return self

    def _fetch_following_sibling(self) -> Optional[NodeBase]:
        if self._tail_node._exists:
            return self._tail_node

        next_etree_obj = self._etree_obj.getnext()
        if next_etree_obj is None:
            return None
        return _wrapper_cache(next_etree_obj)

    def fetch_preceding_sibling(self, *filter: Filter) -> Optional[NodeBase]:
        candidate: NodeBase | None = None

        previous_etree_obj = self._etree_obj.getprevious()

        if previous_etree_obj is None:
            parent = self.parent

            if parent is not None and parent._data_node._exists:
                candidate = parent._data_node
                assert isinstance(candidate, TextNode)
                while candidate._appended_text_node:
                    candidate = candidate._appended_text_node

        else:
            wrapper_of_previous = _wrapper_cache(previous_etree_obj)

            if wrapper_of_previous._tail_node._exists:
                candidate = wrapper_of_previous._tail_node
                assert isinstance(candidate, TextNode)
                while candidate._appended_text_node:
                    candidate = candidate._appended_text_node

            else:
                candidate = wrapper_of_previous

        if candidate is None:
            return None

        if all(f(candidate) for f in chain(default_filters[-1], filter)):
            return candidate
        else:
            return candidate.fetch_preceding_sibling(*filter)

    @property
    def full_text(self) -> str:
        return ""

    @property
    def parent(self) -> Optional[TagNode]:
        etree_parent = self._etree_obj.getparent()
        if etree_parent is None:
            return None
        result = _wrapper_cache(etree_parent)
        assert isinstance(result, TagNode)
        return result


class CommentNode(_ChildLessNode, _ElementWrappingNode, NodeBase):
    """
    The instances of this class represent comment nodes of a tree.

    To instantiate new nodes use :func:`new_comment_node`.
    """

    __slots__ = ()

    def __eq__(self, other) -> bool:
        return isinstance(other, CommentNode) and self.content == other.content

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}("{self.content}") [{hex(id(self))}]>'

    def __str__(self) -> str:
        return f"<!--{self.content}-->"

    @property
    def content(self) -> str:
        """
        The comment's text.

        :meta category: Node content properties
        """
        return cast("str", self._etree_obj.text)

    @content.setter
    def content(self, value: str):
        self._validate_content(value)
        self._etree_obj.text = value

    @staticmethod
    def _validate_content(value: str):
        if "--" in value or value.endswith("-"):
            raise ValueError("Invalid Comment content.")


class ProcessingInstructionNode(_ChildLessNode, _ElementWrappingNode, NodeBase):
    """
    The instances of this class represent processing instruction nodes of a tree.

    To instantiate new nodes use :func:`new_processing_instruction_node`.
    """

    __slots__ = ()

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

    @property
    def content(self) -> str:
        """
        The processing instruction's text.

        :meta category: Node content properties
        """
        return cast("str", self._etree_obj.text)

    @content.setter
    def content(self, value: str):
        self._etree_obj.text = value

    @property
    def target(self) -> str:
        """
        The processing instruction's target.

        :meta category: Node content properties
        """
        etree_obj = self._etree_obj
        assert isinstance(etree_obj, etree._ProcessingInstruction)
        return cast("str", etree_obj.target)

    @target.setter
    def target(self, value: str):
        self._validate_target_value(value)
        etree_obj = self._etree_obj
        assert isinstance(etree_obj, etree._ProcessingInstruction)
        etree_obj.target = value

    @staticmethod
    def _validate_target_value(value):
        if not value:
            # TODO this should rather validate that value is a valid XML name
            raise ValueError("Invalid target name.")
        if value.lower() == "xml":
            raise ValueError(f"{value} is a reserved target name.")


class TagNode(_ElementWrappingNode, NodeBase):
    """
    The instances of this class represent :term:`tag node` s of a tree, the equivalent
    of DOM's elements.

    To instantiate new nodes use :func:`new_tag_node`.

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
        "_attributes",
        "_data_node",
        "__document__",
    )

    def __init__(self, etree_element: _Element):
        super().__init__(etree_element)
        self._data_node = TextNode(etree_element, position=DATA)
        self._attributes = TagAttributes(self)
        self.__document__: Document | None = None

    def __contains__(self, item: AttributeAccessor | NodeBase) -> bool:
        if isinstance(item, (str, tuple)):
            return item in self.attributes
        elif isinstance(item, NodeBase):
            return any(n is item for n in self.iterate_children())
        else:
            raise TypeError(
                "Argument must be a node instance or an attribute name. "
                + ATTRIBUTE_ACCESSOR_MSG
            )

    def __delitem__(self, item: AttributeAccessor | int):
        if isinstance(item, (str, tuple)):
            del self.attributes[item]
        elif isinstance(item, int):
            self[item].detach(retain_child_nodes=False)
        elif isinstance(item, slice):
            if isinstance(item.start, int) or isinstance(item.stop, int):
                raise NotImplementedError(
                    "This will be implemented in a later version."
                )
            else:
                del self.attributes[(item.start, item.stop)]
        else:
            raise TypeError(
                "Argument must be an integer or an attribute name. "
                + ATTRIBUTE_ACCESSOR_MSG
            )

    @overload
    def __getitem__(self, item: int) -> NodeBase: ...

    @overload
    def __getitem__(self, item: AttributeAccessor) -> Attribute | None: ...

    def __getitem__(self, item):
        if isinstance(item, (str, tuple)):
            return self.attributes[item]

        elif isinstance(item, int):
            if item < 0:
                item = len(self) + item

            for index, child_node in enumerate(self.iterate_children()):
                if index == item:
                    return child_node

            raise IndexError("Node index out of range.")

        elif isinstance(item, slice) and all(
            (isinstance(x, int) or x is None) for x in (item.start, item.stop)
        ):
            return list(self.iterate_children())[item]

        raise TypeError(
            "Argument must be an integer as index for a child node, a "
            ":term:`slice` to grab an indexed range of nodes or an attribute "
            "name. " + ATTRIBUTE_ACCESSOR_MSG
        )

    def __len__(self) -> int:
        i = 0
        for i, _ in enumerate(self.iterate_children(), start=1):
            pass
        return i

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
        if isinstance(item, (str, tuple)):
            self.attributes[item] = value
        elif isinstance(item, int):
            children_size = len(self)
            if not children_size and item == 0:
                self.__add_first_child(value)
            else:
                if not 0 <= item < children_size:
                    raise IndexError
                self[item].replace_with(value)
        else:
            raise TypeError(
                "Argument must be an integer or an attribute name. "
                + ATTRIBUTE_ACCESSOR_MSG
            )

    def __add_first_child(self, node: NodeBase):
        assert not len(self)
        if isinstance(node, _ElementWrappingNode):
            self._etree_obj.append(node._etree_obj)
        elif isinstance(node, TextNode):
            node._bind_to_data(self)

    def _add_following_sibling(self, node: NodeBase):
        if self.parent is None:
            # assert False
            if (document := self.document) is None:
                raise InvalidOperation
            document.epilogue.prepend(node)
        else:
            super()._add_following_sibling(node)

    def _add_preceding_sibling(self, node: NodeBase):
        if self.parent is None:
            # assert False
            if (document := self.document) is None:
                raise InvalidOperation
            document.prologue.append(node)
        else:
            super()._add_preceding_sibling(node)

    def append_children(
        self, *node: NodeSource, clone: bool = False
    ) -> tuple[NodeBase, ...]:
        """
        Adds one or more nodes as child nodes after any existing to the child nodes of
        the node this method is called on.

        :param node: The node(s) to be added.
        :param clone: Clones the concrete nodes before adding if :obj:`True`.
        :return: The concrete nodes that were appended.
        :meta category: Methods to add nodes to a tree

        The nodes can be concrete instances of any node type or rather abstract
        descriptions in the form of strings or objects returned from the :func:`tag`
        function that are used to derive :class:`TextNode` respectively :class:`TagNode`
        instances from.
        """
        if not node:
            return ()

        queue: Sequence[NodeSource]

        if (last_child := self.last_child) is None:
            last_child, queue = self._prepare_new_relative(node, clone=clone)
            self.__add_first_child(last_child)
            result: tuple[NodeBase, ...] = (last_child,)

        else:
            queue = node
            result = ()

        if queue:
            result += last_child.add_following_siblings(*queue, clone=clone)

        return result

    @property
    def attributes(self) -> TagAttributes:
        """
        A :term:`mapping` that can be used to access the node's attributes.

        :meta category: Node content properties

        >>> node = new_tag_node("node", attributes={"foo": "0", "bar": "0"})
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
        >>> node = new_tag_node(
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

        >>> node = new_tag_node("node")
        >>> node.attributes["foo"] = "0"
        >>> node.attributes["foo"].local_name = "bar"
        >>> node.attributes["bar"].namespace = "http://namespace"
        >>> node.attributes[("http://namespace", "bar")].value = "X"
        >>> print(node)
        <node xmlns:ns0="http://namespace" ns0:bar="X"/>
        >>> "ref-" + node.attributes[("http://namespace", "bar")].lower()
        'ref-x'
        """
        return self._attributes

    @altered_default_filters()
    def clone(self, deep: bool = False) -> TagNode:
        return new_tag_node(
            local_name=self.local_name,
            attributes=self.attributes,
            namespace=self.namespace,
            children=(
                [n.clone(deep=True) for n in self.iterate_children()] if deep else ()
            ),
        )

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

    @property
    def depth(self) -> int:
        result = 0
        node = self
        while node.parent:
            node = node.parent
            result += 1
        return result

    @altered_default_filters()
    def detach(self, retain_child_nodes: bool = False) -> _ElementWrappingNode:
        parent = self.parent
        index = self.index

        if self.__document__ is not None:
            raise InvalidOperation("The root node of a document cannot be detached.")

        if retain_child_nodes and parent is None:
            raise InvalidOperation(
                "Child nodes can't be retained when the node to detach has no parent "
                "node."
            )

        super().detach()

        parent_has_default_namespace = False
        if parent is None:
            parent_namespaces = None
        else:
            parent_namespaces = parent._etree_obj.nsmap
            if None in parent_namespaces:
                parent_has_default_namespace = True

        if not (parent_has_default_namespace or retain_child_nodes):
            return self

        child_nodes = tuple(self.iterate_children())
        for child_node in child_nodes:
            child_node.detach()

        # workaround to keep a default namespace:
        if parent_has_default_namespace:
            _wrapper_cache.wrappers.pop(self._etree_obj)
            assert isinstance(parent, TagNode)
            self._etree_obj = parent._etree_obj.makeelement(
                etree.QName(self._etree_obj),
                attrib=dict(self._etree_obj.attrib),  # type: ignore
                # TODO https://github.com/lxml/lxml-stubs/issues/62
                nsmap=parent_namespaces,  # type: ignore
            )
            self._attributes._attributes.clear()
            self._attributes._etree_attrib = self._etree_obj.attrib
            self._attributes._node = self
            _wrapper_cache.wrappers[self._etree_obj] = self

        if retain_child_nodes:
            if child_nodes:
                assert isinstance(parent, TagNode)
                assert isinstance(index, int)
                parent.insert_children(index, *child_nodes)
        else:
            self.append_children(*child_nodes)

        return self

    @property
    def document(self) -> Optional[Document]:
        if self.parent is None:
            root_node = self
        else:
            root_node = cast("TagNode", last(self.iterate_ancestors()))
        return root_node.__document__

    def fetch_or_create_by_xpath(
        self,
        expression: str,
        namespaces: Optional[NamespaceDeclarations] = None,
    ) -> TagNode:
        """
        Fetches a single node that is locatable by the provided XPath expression. If
        the node doesn't exist, the non-existing branch will be created.

        :param expression: An XPath expression that can unambiguously locate a
                           descending node in a tree that has any state.
        :param namespaces: A mapping of prefixes that are used in the expression to
                           namespaces.  If not provided the node's namespace will serve
                           as default, mapped to an empty prefix.
        :return: The existing or freshly created node descibed with ``expression``.
        :meta category: Methods to query the tree

        These rules are imperative in your endeavour:

        - All location steps must use the child axis.
        - Each step needs to provide a name test.
        - Attribute comparisons against literals are the only allowed predicates.
        - Multiple attribute comparisons must be joined with the `and` operator and / or
          contained in more than one predicate expression.
        - The logical validity of multiple attribute comparisons isn't checked. E.g.
          one could provide ``foo[@p="her"][@p="him"]``, but expect an undefined
          behaviour.

        >>> root = Document("<root/>").root
        >>> grandchild = root.fetch_or_create_by_xpath(
        ...     "child[@a='b']/grandchild"
        ... )
        >>> grandchild is root.fetch_or_create_by_xpath(
        ...     "child[@a='b']/grandchild"
        ... )
        True
        >>> str(root)
        '<root><child a="b"><grandchild/></child></root>'
        """
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
        node: _DocumentNode | TagNode

        if ast.location_paths[0].absolute:
            node = self
            while node.parent is not None:
                node = node.parent
            node = _DocumentNode(node)
        else:
            node = self

        for i, step in enumerate(ast.location_paths[0].location_steps):
            candidates = tuple(step.evaluate(node_set=(node,), namespaces=namespaces))

            if len(candidates) == 0:
                node_test = step.node_test
                assert isinstance(node, TagNode)
                assert isinstance(node_test, NameMatchTest)

                new_node = new_tag_node(
                    local_name=node_test.local_name,
                    attributes=None,
                    namespace=namespaces.get(node_test.prefix),
                )

                for prefix, local_name, value in step._derived_attributes:
                    new_node.attributes[(namespaces.get(prefix) or "", local_name)] = (
                        value
                    )

                node.append_children(new_node)
                node = new_node

            elif len(candidates) == 1:
                node = cast("TagNode", candidates[0])

            else:
                raise AmbiguousTreeError(
                    f"The tree has multiple possible branches at location step {i}."
                )
        assert isinstance(node, TagNode)
        return node

    @property
    def first_child(self) -> Optional[NodeBase]:
        for result in self.iterate_children():
            return result
        return None

    @property
    def full_text(self) -> str:
        return "".join(
            n.content for n in self.iterate_descendants() if isinstance(n, TextNode)
        )

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
        """
        This is a shortcut to retrieve and set the ``id``  attribute in the XML
        namespace. The client code is responsible to pass properly formed id names.

        :meta category: Node content properties
        """
        return self.attributes.get((XML_NAMESPACE, "id"))

    @id.setter
    def id(self, value: Optional[str]):
        if value is None:
            del self.attributes[(XML_NAMESPACE, "id")]
        elif isinstance(value, str):
            root = cast("TagNode", last(self.iterate_ancestors())) or self
            if root._etree_obj.xpath(f"descendant-or-self::*[@xml:id='{value}']"):
                raise ValueError(
                    "An xml:id-attribute with that value is already assigned in the "
                    "tree."
                )
            self.attributes[(XML_NAMESPACE, "id")] = value
        else:
            raise TypeError("Value must be None or a string.")

    @property
    def index(self) -> Optional[int]:
        if self.parent is None:
            return None
        return super().index

    def insert_children(
        self, index: int, *node: NodeSource, clone: bool = False
    ) -> tuple[NodeBase, ...]:
        """
        Inserts one or more child nodes.

        :param index: The index at which the first of the given nodes will be inserted,
                      the remaining nodes are added afterwards in the given order.
        :param node: The node(s) to be added.
        :param clone: Clones the concrete nodes before adding if :obj:`True`.
        :return: The concrete nodes that were inserted.
        :meta category: Methods to add nodes to a tree

        The nodes can be concrete instances of any node type or rather abstract
        descriptions in the form of strings or objects returned from the :func:`tag`
        function that are used to derive :class:`TextNode` respectively :class:`TagNode`
        instances from.
        """
        if index < 0:
            raise ValueError("Index must be zero or a positive integer.")

        children_count = len(self)

        if index > children_count:
            raise IndexError("The given index is beyond the target's size.")

        this, *queue = node
        result: tuple[NodeBase, ...]

        if index == 0:
            if children_count:
                result = self[0].add_preceding_siblings(this, clone=clone)
            else:
                result = (self._prepare_new_relative((this,), clone=clone)[0],)
                self.__add_first_child(result[0])

        else:
            result = self[index - 1].add_following_siblings(this, clone=clone)

        if queue:
            result += self[index].add_following_siblings(*queue, clone=clone)

        return result

    def iterate_children(self, *filter: Filter) -> Iterator[NodeBase]:
        all_filters = default_filters[-1] + filter
        candidate: NodeBase | None

        assert isinstance(self._data_node, TextNode)
        if self._data_node._exists:
            candidate = self._data_node
        elif len(self._etree_obj):
            candidate = _wrapper_cache(self._etree_obj[0])
        else:
            candidate = None

        while candidate is not None:
            if all(f(candidate) for f in all_filters):
                yield candidate

            candidate = candidate._fetch_following_sibling()

    def iterate_descendants(self, *filter: Filter) -> Iterator[NodeBase]:
        all_filters = default_filters[-1] + filter
        with altered_default_filters():
            candidate = self.first_child
            if candidate is None:
                return

            next_candidates: list[NodeBase | None] = []
            while candidate is not None:
                if all(f(candidate) for f in all_filters):
                    yield candidate

                if isinstance(candidate, TagNode):
                    next_candidates.append(candidate._fetch_following_sibling())
                    candidate = candidate.first_child
                else:
                    candidate = candidate._fetch_following_sibling()

                while candidate is None and next_candidates:
                    candidate = next_candidates.pop()

    @property
    def last_child(self) -> Optional[NodeBase]:
        result = None
        for result in self.iterate_children():
            pass
        return result

    @property
    def last_descendant(self) -> Optional[NodeBase]:
        node = self.last_child
        while node is not None:
            candidate = node.last_child
            if candidate is None:
                break
            node = candidate
        return node

    @property
    def local_name(self) -> str:
        """
        The node's name.

        :meta category: Node properties
        """
        return cast("str", QName(self._etree_obj).localname)

    @local_name.setter
    def local_name(self, value: str):
        self._etree_obj.tag = QName(self.namespace or None, value).text

    @property
    def location_path(self) -> str:
        """
        An unambiguous XPath location path that points to this node from its tree root.

        :meta category: Node properties
        """
        if self.parent is None:
            return "/*"

        with altered_default_filters(is_tag_node):
            steps = list(self.iterate_ancestors())
            steps.pop()  # root
            steps.reverse()
            steps.append(self)
            return "/*" + "".join(f"/*[{cast('int', n.index)+1}]" for n in steps)

    @altered_default_filters()
    def merge_text_nodes(self):
        """
        Merges all consecutive text nodes in the subtree into one.
        Text nodes without content are dropped.
        """
        with _wrapper_cache:
            empty_nodes: list[TextNode] = []

            for node in self.iterate_descendants():
                if not isinstance(node, TextNode):
                    continue
                node._merge_appended_text_nodes()
                if not node.content:
                    empty_nodes.append(node)

            for node in empty_nodes:
                node.detach()

    @property
    def namespace(self) -> str:
        """
        The node's namespace.

        :meta category: Node properties
        """
        return QName(self._etree_obj.tag).namespace or ""

    @namespace.setter
    def namespace(self, value: str):
        self._etree_obj.tag = QName(value or None, self.local_name).text

    @property
    def _namespace(self) -> str:
        warnings.warn("Use TagNode.namespace instead!")
        return self.namespace

    def _new_tag_node_from_definition(self, definition: _TagDefinition) -> TagNode:
        return self._new_tag_node_from(
            context=self._etree_obj,
            local_name=definition.local_name,
            attributes=definition.attributes,
            namespace=self.namespace,
            children=definition.children,
        )

    @staticmethod
    def parse(text, parser_options):
        """This method has been replaced by :func:`delb.parse_tree`."""
        raise InvalidOperation(
            "This method has been replaced by `delb.parse_tree`.",
        )

    @property
    def prefix(self) -> Optional[str]:  # pragma: nocover
        """
        The prefix that the node's namespace is currently mapped to.

        :meta category: Node properties
        """
        warnings.warn("This attribute will be removed.", category=DeprecationWarning)

        target = QName(self._etree_obj).namespace

        if target is None:
            return None

        for prefix, namespace in self._etree_obj.nsmap.items():
            assert isinstance(prefix, str) or prefix is None
            if namespace == target:
                return prefix
        raise InvalidCodePath

    def prepend_children(
        self, *node: NodeBase, clone: bool = False
    ) -> tuple[NodeBase, ...]:
        """
        Adds one or more nodes as child nodes before any existing to the child nodes of
        the node this method is called on.

        :param node: The node(s) to be added.
        :param clone: Clones the concrete nodes before adding if :obj:`True`.
        :return: The concrete nodes that were prepended.
        :meta category: Methods to add nodes to a tree

        The nodes can be concrete instances of any node type or rather abstract
        descriptions in the form of strings or objects returned from the :func:`tag`
        function that are used to derive :class:`TextNode` respectively :class:`TagNode`
        instances from.
        """
        return self.insert_children(0, *node, clone=clone)

    @altered_default_filters()
    def _reduce_whitespace(
        self, normalize_space: Literal["default", "preserve"] = "default"
    ):
        with _wrapper_cache:
            self._reduce_whitespace_of_descendants(normalize_space)

    def _reduce_whitespace_of_descendants(
        self, normalize_space: Literal["default", "preserve"]
    ):
        if not (child_nodes := list(self.iterate_children())):
            return

        self.merge_text_nodes()

        if (
            normalize_space := self._get_normalize_space_directive(normalize_space)
        ) == "default":
            _reduce_whitespace_between_siblings(child_nodes, True)

        for child_node in (n for n in child_nodes if isinstance(n, TagNode)):
            child_node._reduce_whitespace_of_descendants(normalize_space)

    @altered_default_filters()
    def serialize(
        self,
        *,
        format_options: Optional[FormatOptions] = None,
        namespaces: Optional[NamespaceDeclarations] = None,
        newline: Optional[str] = None,
    ):
        serializer = _get_serializer(
            _StringWriter(newline=newline),
            format_options=format_options,
            namespaces=namespaces,
        )
        with _wrapper_cache:
            serializer.serialize_root(self)
        return serializer.writer.result

    @property
    def universal_name(self) -> str:
        """
        The node's qualified name in `Clark notation`_.

        :meta category: Node properties

        .. _Clark notation: http://www.jclark.com/xml/xmlns.htm
        """
        return cast("str", self._etree_obj.tag)

    def _validate_sibling_operation(self, node):
        if self.parent is None and not (
            isinstance(node, (CommentNode, ProcessingInstructionNode))
            and (
                isinstance(self, (CommentNode, ProcessingInstructionNode))
                or self.__document__ is not None
            )
        ):
            raise TypeError(
                "Not all node types can be added as siblings to a root node."
            )


class TextNode(_ChildLessNode, NodeBase, _StringMixin):  # type: ignore
    """
    TextNodes contain the textual data of a document. The class shall not be initialized
    by client code, just throw strings into the trees.

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

    __slots__ = ("_appended_text_node", "_bound_to", "__content", "_position")

    def __init__(
        self,
        reference_or_text: _Element | str | TextNode,
        position: int = DETACHED,
    ):
        self._bound_to: _Element | TextNode | None
        self.__content: str | None

        self._appended_text_node: TextNode | None = None
        self._position: int = position

        if position is DETACHED:
            assert isinstance(reference_or_text, str)
            self._bound_to = None
            self.__content = reference_or_text

        elif position in (DATA, TAIL):
            assert isinstance(reference_or_text, _Element)
            self._bound_to = reference_or_text
            self.__content = None

        else:
            raise ValueError

    def __eq__(self, other):
        if isinstance(other, TextNode):
            return self.content == other.content
        else:
            return super().__eq__(other)

    def __getitem__(self, item):
        return self.content[item]

    def __repr__(self):
        if self._exists:
            return (
                f'<{self.__class__.__name__}(text="{self.content}", '
                f"pos={self._position}) [{hex(id(self))}]>"
            )
        else:
            return (
                f"<{self.__class__.__name__}(pos={self._position}) [{hex(id(self))}]>"
            )

    def _add_following_sibling(self, node: NodeBase):
        if isinstance(node, TextNode):
            self._insert_text_node_as_next_appended(node)

        elif isinstance(node, _ElementWrappingNode):
            self._add_next_element_wrapping_node(node)

    def _add_next_element_wrapping_node(self, node: _ElementWrappingNode):
        if self._position is DATA:
            assert isinstance(self._bound_to, _Element)
            appended_text_node = self._appended_text_node
            self._bound_to.insert(0, node._etree_obj)
            if appended_text_node is not None:
                self._appended_text_node = None
                appended_text_node._bind_to_tail(node)

        elif self._position is TAIL:
            assert isinstance(self._bound_to, _Element)
            data = self._bound_to.tail
            text_sibling = self._appended_text_node
            self._appended_text_node = None

            assert not node._tail_node._exists

            self._bound_to.addnext(node._etree_obj)
            self._bound_to.tail = data
            node._etree_obj.tail = None

            assert not node._tail_node._exists, repr(node._tail_node)

            if text_sibling is not None:
                text_sibling._bind_to_tail(node)

        elif self._position is APPENDED:
            appended_text_node = self._appended_text_node
            self._appended_text_node = None

            head = self._tail_sequence_head
            assert head._position in (DATA, TAIL)
            if head._position is DATA:
                assert isinstance(head._bound_to, _Element)
                head._bound_to.insert(0, node._etree_obj)
            elif head._position is TAIL:
                head_anchor = head._bound_to
                assert isinstance(head_anchor, _Element)
                head_content = head.content

                head_anchor.addnext(node._etree_obj)

                head_anchor.tail = head_content
                node._etree_obj.tail = None

            if appended_text_node is not None:
                appended_text_node._bind_to_tail(node)

    def _add_preceding_sibling(self, node: NodeBase):
        if isinstance(node, TextNode):
            self._prepend_text_node(node)

        elif isinstance(node, _ElementWrappingNode):
            if self._position is DATA:
                content = self.content
                current_bound = self._bound_to
                assert isinstance(current_bound, _Element)
                current_bound.insert(0, node._etree_obj)

                current_bound_wrapper = _wrapper_cache(current_bound)
                assert isinstance(current_bound_wrapper, TagNode)
                current_bound_wrapper._data_node = TextNode(current_bound, DATA)
                self._bind_to_tail(node)
                current_bound.text = None
                self.content = content

            elif self._position is TAIL:
                assert isinstance(self._bound_to, _Element)
                _wrapper_cache(self._bound_to)._add_following_sibling(node)

            elif self._position is APPENDED:
                assert isinstance(self._bound_to, TextNode)
                self._bound_to._add_following_sibling(node)

    def _bind_to_data(self, target: TagNode):
        target._etree_obj.text = self.content
        target._data_node = self
        self._bound_to = target._etree_obj
        self._position = DATA
        self.__content = None
        assert isinstance(self.content, str)

    def _bind_to_tail(self, target: _ElementWrappingNode):
        assert isinstance(target, _ElementWrappingNode)
        target._etree_obj.tail = self.content
        target._tail_node = self
        self._bound_to = target._etree_obj
        self._position = TAIL
        self.__content = None
        assert isinstance(self.content, str)

    def clone(self, deep: bool = False) -> NodeBase:
        assert self.content is not None
        return self.__class__(self.content)

    @property
    def content(self) -> str:
        """
        The node's text content.

        :meta category: Node content properties
        """
        if self._position is DATA:
            assert isinstance(self._bound_to, _Element)
            return cast("str", self._bound_to.text)

        elif self._position is TAIL:
            assert isinstance(self._bound_to, _Element)
            return cast("str", self._bound_to.tail)

        elif self._position in (APPENDED, DETACHED):
            assert self._bound_to is None or isinstance(self._bound_to, TextNode)
            return cast("str", self.__content)

        else:
            raise ValueError(
                f"A TextNode._position must not be set to {self._position}"
            )

    @content.setter
    def content(self, text: str):
        if not isinstance(text, str):
            raise TypeError

        if self._position is DATA:
            assert isinstance(self._bound_to, _Element)
            self._bound_to.text = text or None

        elif self._position is TAIL:
            assert isinstance(self._bound_to, _Element)
            self._bound_to.tail = text or None

        elif self._position in (APPENDED, DETACHED):
            assert self._bound_to is None or isinstance(self._bound_to, TextNode)
            self.__content = text

    # for utils._StringMixin:
    _data = content

    @property
    def depth(self) -> int:
        if self._position is DETACHED:
            return 0
        return super().depth

    def detach(self, retain_child_nodes: bool = False) -> TextNode:
        if self._position is DETACHED:
            return self

        content = self.content
        text_sibling = self._appended_text_node

        if self._position is DATA:
            current_parent = self.parent
            assert current_parent is not None

            assert isinstance(self._bound_to, _Element)
            assert current_parent._etree_obj is self._bound_to

            if text_sibling:
                text_sibling._bind_to_data(current_parent)
            else:
                current_parent._data_node = TextNode(current_parent._etree_obj, DATA)
                assert self not in current_parent
                self._bound_to.text = None
                assert not current_parent._data_node._exists

        elif self._position is TAIL:
            current_bound = self._bound_to
            assert isinstance(current_bound, _Element)
            current_previous = _wrapper_cache(current_bound)

            if text_sibling:
                text_sibling._bind_to_tail(current_previous)
            else:
                current_previous._tail_node = TextNode(
                    current_previous._etree_obj, TAIL
                )
                current_bound.tail = None
                assert not current_previous._tail_node._exists

        elif self._position is APPENDED:
            assert isinstance(self._bound_to, TextNode)
            self._bound_to._appended_text_node = text_sibling
            if text_sibling:
                text_sibling._bound_to = self._bound_to

        else:
            raise ValueError(
                f"A TextNode._position must not be set to {self._position}"
            )

        self._appended_text_node = None
        self._bound_to = None
        self._position = DETACHED
        self.content = content or ""

        assert self.parent is None
        assert self._fetch_following_sibling() is None

        return self

    @property
    def _exists(self) -> bool:
        if self._position is DATA:
            assert isinstance(self._bound_to, _Element)
            return self._bound_to.text is not None
        elif self._position is TAIL:
            assert isinstance(self._bound_to, _Element)
            return self._bound_to.tail is not None
        else:
            return True

    def _fetch_following_sibling(self) -> Optional[NodeBase]:
        if self._position is DETACHED:
            return None

        if self._appended_text_node:
            return self._appended_text_node

        elif self._position is DATA:
            assert isinstance(self._bound_to, _Element)
            if len(self._bound_to):
                return _wrapper_cache(self._bound_to[0])
            else:
                return None

        elif self._position is TAIL:
            return self.__next_candidate_of_tail()

        elif self._position is APPENDED:  # and last in tail sequence
            return self.__next_candidate_of_last_appended()

        raise InvalidCodePath

    def fetch_preceding_sibling(self, *filter: Filter) -> Optional[NodeBase]:
        candidate: NodeBase | None

        if self._position in (DATA, DETACHED):
            return None
        elif self._position is TAIL:
            assert isinstance(self._bound_to, _Element)
            candidate = _wrapper_cache(self._bound_to)
        elif self._position is APPENDED:
            assert isinstance(self._bound_to, TextNode)
            candidate = self._bound_to
        else:
            raise ValueError(
                f"A TextNode._position must not be set to {self._position}"
            )

        if candidate is None:
            return None

        if all(f(candidate) for f in chain(default_filters[-1], filter)):
            return candidate
        else:
            return candidate.fetch_preceding_sibling(*filter)

    @property
    def full_text(self) -> str:
        return self.content or ""

    def _merge_appended_text_nodes(self):
        sibling = self._appended_text_node
        if sibling is None:
            return

        current_node, appendix = sibling, ""
        while current_node is not None:
            assert isinstance(current_node.content, str)
            appendix += current_node.content
            current_node = current_node._appended_text_node

        self.content += appendix
        self._appended_text_node = None
        sibling._bound_to = None

    def _insert_text_node_as_next_appended(self, node: TextNode):
        old = self._appended_text_node
        content = node.content
        node._bound_to = self
        node._position = APPENDED
        node.content = content
        self._appended_text_node = node
        if old:
            assert old._position is APPENDED, old
            node._insert_text_node_as_next_appended(old)

        assert isinstance(self.content, str)
        assert isinstance(node.content, str)

    def __next_candidate_of_last_appended(self) -> Optional[NodeBase]:
        head = self._tail_sequence_head
        assert isinstance(head._bound_to, _Element)
        if head._position is DATA:
            assert head.parent is not None
            if len(head.parent._etree_obj):
                return _wrapper_cache(head.parent._etree_obj[0])
            else:
                return None
        elif head._position is TAIL:
            next_etree_element = head._bound_to.getnext()
            if next_etree_element is None:
                return None
            else:
                return _wrapper_cache(next_etree_element)

        raise InvalidCodePath

    def __next_candidate_of_tail(self) -> Optional[NodeBase]:
        assert isinstance(self._bound_to, _Element)
        next_etree_node = self._bound_to.getnext()
        if next_etree_node is None:
            return None
        return _wrapper_cache(next_etree_node)

    @property
    def parent(self) -> Optional[TagNode]:
        if self._position is DATA:
            assert isinstance(self._bound_to, _Element)
            result = _wrapper_cache(self._bound_to)
            assert isinstance(result, TagNode)
            return result

        elif self._position is TAIL:
            assert isinstance(self._bound_to, _Element)
            return _wrapper_cache(self._bound_to).parent

        elif self._position is APPENDED:
            assert isinstance(self._bound_to, TextNode)
            return self._tail_sequence_head.parent

        elif self._position is DETACHED:
            assert self._bound_to is None
            return None

        raise ValueError(f"A TextNode._position must not be set to {self._position}")

    def _prepend_text_node(self, node: TextNode):
        if self._position is DATA:
            assert isinstance(self._bound_to, _Element)
            parent = _wrapper_cache(self._bound_to)
            assert isinstance(parent, TagNode)
            content = self.content
            node._bind_to_data(parent)
            node._insert_text_node_as_next_appended(self)
            self.content = content

        elif self._position is TAIL:
            assert isinstance(self._bound_to, _Element)
            left_sibling = _wrapper_cache(self._bound_to)
            content = self.content
            node._bind_to_tail(left_sibling)
            node._insert_text_node_as_next_appended(self)
            self.content = content

        elif self._position is APPENDED:
            assert node._appended_text_node is None
            previous = self._bound_to
            assert isinstance(previous, TextNode)
            previous._appended_text_node = None
            previous._insert_text_node_as_next_appended(node)
            node._insert_text_node_as_next_appended(self)

        else:
            raise ValueError(
                f"A TextNode._position must not be set to {self._position}"
            )

    @property
    def _tail_sequence_head(self) -> TextNode:
        if self._position in (DATA, TAIL):
            return self
        elif self._position is APPENDED:
            assert isinstance(self._bound_to, TextNode)
            return self._bound_to._tail_sequence_head
        else:
            raise InvalidCodePath


# contributed node filters and filter wrappers


def any_of(*filter: Filter) -> Filter:
    """
    A node filter wrapper that matches when any of the given filters is matching, like a
    boolean ``or``.
    """

    def any_of_wrapper(node: NodeBase) -> bool:
        return any(x(node) for x in filter)

    return any_of_wrapper


def is_comment_node(node: NodeBase) -> bool:
    """
    A node filter that matches :class:`CommentNode` instances.
    """
    return isinstance(node, CommentNode)


def is_processing_instruction_node(node: NodeBase) -> bool:
    """
    A node filter that matches :class:`ProcessingInstructionNode` instances.
    """
    return isinstance(node, ProcessingInstructionNode)


def is_root_node(node: NodeBase) -> bool:
    """
    A node filter that matches root nodes.
    """
    return node.parent is None


def is_tag_node(node: NodeBase) -> bool:
    """
    A node filter that matches :class:`TagNode` instances.
    """
    return isinstance(node, TagNode)


def is_text_node(node: NodeBase) -> bool:
    """
    A node filter that matches :class:`TextNode` instances.
    """
    return isinstance(node, TextNode)


def not_(*filter: Filter) -> Filter:
    """
    A node filter wrapper that matches when the given filter is not matching,
    like a boolean ``not``.
    """

    def not_wrapper(node: NodeBase) -> bool:
        return not all(f(node) for f in filter)

    return not_wrapper


# serializer


def _get_serializer(
    writer: _SerializationWriter,
    format_options: Optional[FormatOptions],
    namespaces: Optional[NamespaceDeclarations],
) -> Serializer:
    if format_options is None:
        return Serializer(
            writer=writer,
            namespaces=namespaces,
        )

    if format_options.indentation and not format_options.indentation.isspace():
        raise ValueError("Invalid indentation characters.")

    if format_options.width:
        return TextWrappingSerializer(
            writer=writer,
            format_options=format_options,
            namespaces=namespaces,
        )
    else:
        return PrettySerializer(
            writer=writer,
            format_options=format_options,
            namespaces=namespaces,
        )


class Serializer:
    __slots__ = (
        "_namespaces",
        "_prefixes",
        "writer",
    )

    def __init__(
        self,
        writer: _SerializationWriter,
        *,
        namespaces: Optional[NamespaceDeclarations] = None,
    ):
        self._namespaces = (
            Namespaces({}) if namespaces is None else Namespaces(namespaces)
        )
        self._prefixes: dict[str, str] = {}
        self.writer = writer

    def _collect_prefixes(self, root: TagNode):
        if root.namespace not in self._namespaces.values():
            self._prefixes[root.namespace] = ""

        for node in traverse_bf_ltr_ttb(root, is_tag_node):
            assert isinstance(node, TagNode)
            for namespace in {node.namespace} | {
                a.namespace for a in node.attributes.values()
            }:
                if namespace in self._prefixes:
                    continue

                if not namespace:
                    # an empty/null namespace can't be assigned to a prefix,
                    # it must be the default namespace
                    self.__redeclare_empty_prefix()
                    self._prefixes[""] = ""
                    continue
                assert namespace is not None

                if (prefix := self._namespaces.lookup_prefix(namespace)) is None:
                    # the namespace isn't declared by the user
                    self._new_namespace_declaration(namespace)
                    continue

                if prefix == "" and "" in self._prefixes.values():
                    # a default namespace was declared, but that one is required for the
                    # empty/null namespace
                    self._new_namespace_declaration(namespace)
                    continue

                if len(prefix):
                    # that found prefix still needs a colon for faster serialisat
                    # composition later
                    assert f"{prefix}:" not in self._prefixes.values()
                    self._prefixes[namespace] = f"{prefix}:"
                else:
                    assert "" not in self._prefixes.values()
                    self._prefixes[namespace] = ""

    def __redeclare_empty_prefix(self):
        # a possibly collected declaration of an empty namespace needs to be mapped to
        # a prefix because an empty namespace needs to be serialized and such cannot be
        # mapped to a prefix in a declaration
        for other_namespace, prefix in self._prefixes.items():
            if prefix == "":
                # there is, it needs to use a prefix though as an empty namespace
                # can't be declared
                assert other_namespace is not None
                self._new_namespace_declaration(other_namespace)
                break

    def _generate_attributes_data(self, node: TagNode) -> dict[str, str]:
        data = {}
        for attribute in (node.attributes[a] for a in sorted(node.attributes)):
            assert isinstance(attribute, Attribute)
            data[self._prefixes[attribute.namespace] + attribute.local_name] = (
                f'"{attribute.value.translate(CCE_TABLE_FOR_ATTRIBUTES)}"'
            )
        return data

    def _handle_child_nodes(self, child_nodes: tuple[NodeBase, ...]):
        for child_node in child_nodes:
            self.serialize_node(child_node)

    def _new_namespace_declaration(self, namespace: str):
        for i in range(2**16):
            prefix = f"ns{i}:"
            if prefix not in self._prefixes.values():
                self._prefixes[namespace] = prefix
                return
        else:
            raise NotImplementedError("Just don't.")

    def _serialize_attributes(self, attributes_data):
        for key, value in attributes_data.items():
            self.writer(f" {key}={value}")

    def serialize_node(self, node: NodeBase):

        if isinstance(node, (CommentNode, ProcessingInstructionNode)):
            self.writer(str(node))
        elif isinstance(node, TagNode):
            self._serialize_tag(
                node,
                attributes_data=self._generate_attributes_data(node),
            )
        elif isinstance(node, TextNode) and node.content:
            self.writer(node.content.translate(CCE_TABLE_FOR_TEXT))
        else:
            raise InvalidCodePath

    def serialize_root(self, root: TagNode):
        self._collect_prefixes(root)
        attributes_data = {}
        declarations = {p: "" if n is None else n for n, p in self._prefixes.items()}
        if "" in declarations:
            default_namespace = declarations.pop("")
            if default_namespace:
                attributes_data["xmlns"] = f'"{default_namespace}"'
            # else it would be an unprefixed, empty namespace
        for prefix in sorted(p for p in declarations if p[:-1] not in GLOBAL_PREFIXES):
            assert len(prefix) >= 2  # at least a colon and one letter
            attributes_data[f"xmlns:{prefix[:-1]}"] = f'"{declarations[prefix]}"'

        attributes_data.update(self._generate_attributes_data(root))
        self._serialize_tag(root, attributes_data=attributes_data)

    def _serialize_tag(
        self,
        node: TagNode,
        attributes_data: dict[str, str],
    ):
        child_nodes = tuple(node.iterate_children())
        prefixed_name = self._prefixes[node.namespace] + node.local_name

        self.writer(f"<{prefixed_name}")
        if attributes_data:
            self._serialize_attributes(attributes_data)

        if child_nodes:
            self.writer(">")
            self._handle_child_nodes(child_nodes)
            self.writer(f"</{prefixed_name}>")
        else:
            self.writer("/>")


class _LineFittingSerializer(Serializer):
    __slots__ = ("space",)

    def __init__(
        self,
        writer: _SerializationWriter,
        *,
        namespaces: Optional[NamespaceDeclarations] = None,
    ):
        self.writer: _LengthTrackingWriter
        super().__init__(writer, namespaces=namespaces)
        self.space: Literal["default", "preserve"] = "default"

    def serialize_node(self, node: NodeBase):
        if isinstance(node, TextNode):
            if node.content:
                if self.space == "default":
                    content = _crunch_whitespace(node.content).translate(
                        CCE_TABLE_FOR_TEXT
                    )
                else:
                    content = node.content.translate(CCE_TABLE_FOR_TEXT)
                self.writer(content)
            return

        if isinstance(node, TagNode):
            space_state = self.space
            space = node._get_normalize_space_directive(self.space)
            if space != space_state:
                self.space = space
                self.writer.preserve_space = space == "default"

        super().serialize_node(node)

        if isinstance(node, TagNode) and space != space_state:
            self.space = space_state
            self.writer.preserve_space = space_state == "default"


class PrettySerializer(Serializer):
    __slots__ = (
        "_align_attributes",
        "indentation",
        "_level",
        "_serialization_root",
        "_space_preserving_serializer",
        "_text_wrapper",
        "_unwritten_text_nodes",
    )

    def __init__(
        self,
        writer: _SerializationWriter,
        format_options: FormatOptions,
        *,
        namespaces: Optional[NamespaceDeclarations] = None,
    ):
        super().__init__(writer, namespaces=namespaces)
        self._align_attributes = format_options.align_attributes
        self.indentation = format_options.indentation
        self._level = 0
        self._serialization_root: None | TagNode = None
        self._space_preserving_serializer = Serializer(
            self.writer, namespaces=self._namespaces
        )
        self._unwritten_text_nodes: list[TextNode] = []

    def _collect_prefixes(self, root: TagNode):
        super()._collect_prefixes(root)
        self._space_preserving_serializer._prefixes = self._prefixes

    def _handle_child_nodes(self, child_nodes: tuple[NodeBase, ...]):
        # newline between an opening tag and its first child
        if self._whitespace_is_legit_before_node(child_nodes[0]):
            self.writer("\n")

        self._level += 1
        self._serialize_child_nodes(child_nodes)
        self._level -= 1

        if self.indentation and self._whitespace_is_legit_after_node(child_nodes[-1]):
            # indentation before closing tag
            # newline was possibly written in self.serialize_node()
            # or self._serialize_text
            self.writer(self._level * self.indentation)

    def _normalize_text(self, text: str) -> str:
        return _crunch_whitespace(text).translate(CCE_TABLE_FOR_TEXT)

    def _serialize_attributes(self, attributes_data: dict[str, str]):
        if self._align_attributes and len(attributes_data) > 1:
            key_width = max(len(k) for k in attributes_data)
            for key, value in attributes_data.items():
                self.writer(
                    f"\n{self._level * self.indentation} {self.indentation}"
                    f"{' ' * (key_width - len(key))}{key}={value}"
                )
            if self.indentation:
                self.writer(f"\n{self._level * self.indentation}")

        else:
            super()._serialize_attributes(attributes_data)

    def _serialize_child_nodes(self, child_nodes: tuple[NodeBase, ...]):
        for node in child_nodes:
            if isinstance(node, TextNode):
                if node.content:
                    self._unwritten_text_nodes.append(node)
            else:
                self.serialize_node(node)

        if self._unwritten_text_nodes:
            self._serialize_text()

    def serialize_node(self, node: NodeBase):
        if self._unwritten_text_nodes:
            self._serialize_text()

        if self.indentation and self._whitespace_is_legit_before_node(node):
            self.writer(self._level * self.indentation)

        super().serialize_node(node)

        if self._whitespace_is_legit_after_node(node):
            self.writer("\n")

    def serialize_root(self, root: TagNode):
        self._serialization_root = root
        super().serialize_root(root)
        self._serialization_root = None

    def _serialize_tag(
        self,
        node: TagNode,
        attributes_data: dict[str, str],
    ):
        if node._get_normalize_space_directive() == "preserve":
            self._space_preserving_serializer._serialize_tag(
                node=node,
                attributes_data=attributes_data,
            )
        else:
            super()._serialize_tag(
                node,
                attributes_data=attributes_data,
            )

    def _serialize_text(self):
        nodes = self._unwritten_text_nodes
        content = self._normalize_text("".join(n.content for n in nodes))

        # a whitespace-only node can be omitted as a newline has been inserted before
        if content == " ":
            nodes.clear()
            return

        if self.indentation and self._whitespace_is_legit_before_node(nodes[0]):
            content = self._level * self.indentation + content.lstrip()

        if self._whitespace_is_legit_after_node(nodes[-1]):
            content = content.rstrip() + "\n"

        assert content
        self.writer(content)
        nodes.clear()

    def _whitespace_is_legit_after_node(self, node: NodeBase) -> bool:
        if self._serialization_root is None or node is self._serialization_root:
            # end of stream
            return False

        if node.parent.last_child is node:
            return True

        if isinstance(node, TextNode):
            return node.content[-1].isspace()

        following_sibling = node.fetch_following_sibling()
        assert following_sibling is not None
        if isinstance(following_sibling, TextNode):
            return self._whitespace_is_legit_before_node(following_sibling)
        else:
            return False

    def _whitespace_is_legit_before_node(self, node: NodeBase) -> bool:
        if self._serialization_root is None or node is self._serialization_root:
            # begin of stream
            return False

        if node.index == 0:
            return True

        if isinstance(node, TextNode):
            return node.content[0].isspace()

        preceding_sibling = node.fetch_preceding_sibling()
        assert preceding_sibling is not None
        if isinstance(preceding_sibling, TextNode):
            return self._whitespace_is_legit_after_node(preceding_sibling)
        else:
            return False


class TextWrappingSerializer(PrettySerializer):
    __slots__ = (
        "_line_fitting_serializer",
        "_width",
    )

    def __init__(
        self,
        writer: _SerializationWriter,
        format_options: FormatOptions,
        *,
        namespaces: Optional[NamespaceDeclarations] = None,
    ):
        if format_options.width < 1:
            raise ValueError
        self.writer: _LengthTrackingWriter
        super().__init__(
            writer=_LengthTrackingWriter(writer.buffer),
            format_options=format_options,
            namespaces=namespaces,
        )
        self._line_fitting_serializer = _LineFittingSerializer(
            self.writer, namespaces=self._namespaces
        )
        self._width = format_options.width

    @property
    def _available_space(self):
        return max(0, self._width - self._line_offset)

    def _collect_prefixes(self, root: TagNode):
        super()._collect_prefixes(root)
        self._line_fitting_serializer._prefixes = self._prefixes

    @property
    def _line_offset(self) -> int:
        if self.writer.offset:
            return self.writer.offset - self._level * len(self.indentation)
        else:
            return 0

    def _node_fits_remaining_line(self, node: NodeBase) -> bool:
        return self._required_space(node, self._available_space) is not None

    def _required_space(self, node: NodeBase, up_to: int) -> None | int:
        # counts required space for the serialisation of a node
        # a returned None signals that the limit up_to was hit

        if isinstance(node, TextNode):
            return self._required_space_for_text(node, up_to)
        if isinstance(node, (CommentNode, ProcessingInstructionNode)):
            length = len(str(node))
            return length if length <= up_to else None

        assert isinstance(node, TagNode)

        name_length = len(node.local_name) + len(self._prefixes[node.namespace])
        if len(node) == 0:
            used_space = 3 + name_length  # <N/>
        else:
            used_space = 5 + 2 * name_length  # <N>…<N/>

        if used_space > up_to:
            return None

        if (
            attributes_space := self._required_space_for_attributes(
                node, up_to - used_space
            )
        ) is None:
            return None
        used_space += attributes_space

        for child_node in node.iterate_children():
            if (
                child_space := self._required_space(child_node, up_to - used_space)
            ) is None:
                return None
            used_space += child_space

        if (
            following_space := self._required_space_for_following(
                node, up_to - used_space
            )
        ) is None:
            return None
        used_space += following_space

        return used_space

    def _required_space_for_attributes(self, node: TagNode, up_to: int) -> None | int:
        result = 0

        attribute_names = tuple(node.attributes)
        for attribute in (node.attributes[n] for n in attribute_names):
            assert attribute is not None
            result += (
                4  # preceding space and »="…"«
                + len(attribute.local_name)
                + len(self._prefixes[attribute.namespace])
                + len(attribute.value.translate(CCE_TABLE_FOR_ATTRIBUTES))
            )
            if result > up_to:
                return None

        return result

    def _required_space_for_following(self, node: TagNode, up_to: int) -> None | int:
        if self._whitespace_is_legit_after_node(node):
            return 0

        if (following := node.fetch_following()) is None:
            return 0

        if not isinstance(following, TextNode):
            return self._required_space(following, up_to)

        # indeed this doesn't consider the case where a first
        # whitespace would appear in one of possible subsequent text
        # nodes
        content = following.content.translate(CCE_TABLE_FOR_TEXT)
        if (length := content.find(" ")) == -1:
            length = len(content)

        return length if length <= up_to else None

    def _required_space_for_text(self, node: TextNode, up_to: int) -> None | int:
        content = self._normalize_text(node.content)
        if content.startswith(" ") and self._whitespace_is_legit_before_node(node):
            content = content.lstrip()
        if content.endswith(" ") and self._whitespace_is_legit_after_node(node):
            content = content.rstrip()
        length = len(content)
        return length if length <= up_to else None

    def _serialize_appendable_node(self, node: NodeBase):
        assert not isinstance(node, TextNode)

        if self.writer.offset == 0 and self.indentation:
            self.writer(self._level * self.indentation)

        if isinstance(node, TagNode):
            if node._get_normalize_space_directive() == "preserve":
                serializer = self._space_preserving_serializer
                self.writer.preserve_space = True
            else:
                serializer = self._line_fitting_serializer
            serializer.serialize_node(node)
            self.writer.preserve_space = False
        elif isinstance(node, (CommentNode, ProcessingInstructionNode)):
            self.writer(str(node))

    def serialize_node(self, node: NodeBase):
        if self._unwritten_text_nodes:
            self._serialize_text()

        if self._node_fits_remaining_line(node):
            self._serialize_appendable_node(node)
            if (
                (not self._available_space) or (node is node.parent.last_child)
            ) and self._whitespace_is_legit_after_node(node):
                self.writer("\n")
                return

        else:
            if self._line_offset > 0 and self._whitespace_is_legit_before_node(node):
                self.writer("\n")
                self.serialize_node(node)
                return

            if (
                self.indentation
                and self.writer.offset == 0
                and self._whitespace_is_legit_before_node(node)
            ):
                self.writer(self._level * self.indentation)

            if (
                isinstance(node, TagNode)
                and node._get_normalize_space_directive() == "preserve"
            ):
                self.writer.preserve_space = True
            super(PrettySerializer, self).serialize_node(node)
            self.writer.preserve_space = False

        if self._whitespace_is_legit_after_node(node) and not (
            (
                (following := node.fetch_following()) is not None
                and self._node_fits_remaining_line(following)
            )
        ):
            self.writer("\n")

    def _serialize_tag(
        self,
        node: TagNode,
        attributes_data: dict[str, str],
    ):
        if node is not self._serialization_root and self._node_fits_remaining_line(
            node
        ):
            self._serialize_appendable_node(node)
        else:
            super()._serialize_tag(node, attributes_data)

    def _serialize_text(self):
        nodes = self._unwritten_text_nodes
        content = self._normalize_text("".join(n.content for n in nodes))
        last_node = nodes[-1]

        if self._available_space == len(
            content.rstrip()
        ) and self._whitespace_is_legit_after_node(last_node):
            # text fits perfectly
            self.writer(content.rstrip() + "\n")

        elif self._available_space > len(content):
            # text fits current line
            if self._line_offset == 0:
                content = self._level * self.indentation + content.lstrip()

            if (
                (last_node is last_node.parent.last_child)
                or (following := last_node.fetch_following()) is not None
                and (
                    self._whitespace_is_legit_before_node(following)
                    and self._required_space(
                        following, self._available_space - len(content)
                    )
                    is None
                )
            ):
                content = content.rstrip() + "\n"

            self.writer(content)

        elif content == " ":
            # " " doesn't fit line
            self.writer("\n")

        else:
            # text doesn't fit current line
            self._serialize_text_over_lines(content)

        nodes.clear()

    def _serialize_text_over_lines(self, content: str):
        lines: list[str] = []
        nodes = self._unwritten_text_nodes

        if self._line_offset == 0:
            # just a side note: this branch would also be interesting if
            # len(content) > self._width  # noqa: E800
            # and self._whitespace_is_legit_before_node(nodes[0])
            # and one would know that the line starts with text content
            #
            # so for now that's why text might start after a closing tag of an
            # element that spans multiple lines on their last one
            # (i.e. this prefers: "the <hi>A</hi> letter…" over the "A" on a
            # separate line which the next branch produces)

            if self._whitespace_is_legit_before_node(nodes[0]):
                lines.append("")
            lines.extend(self._wrap_text(content.lstrip(), self._width))

        else:
            if content.startswith(" "):
                filling = " " + next(
                    self._wrap_text(content[1:], self._available_space - 1)
                )
            else:
                filling = next(self._wrap_text(content, self._available_space))

            if not (
                len(filling) > self._available_space
                and self._whitespace_is_legit_before_node(nodes[0])
            ):
                self.writer(filling)
                content = content[len(filling) + 1 :]
                if not content:
                    return

            lines.append("")
            lines.extend(self._wrap_text(content, self._width))

        if (
            lines[-1].endswith(" ")
            and self._whitespace_is_legit_after_node(nodes[-1])
            and (following_sibling := nodes[-1].fetch_following_sibling()) is not None
            and not self._required_space(
                following_sibling, self._width - len(lines[-1])
            )
        ):
            lines.append("")

        self._consolidate_text_lines(lines)

        prefix = self._level * self.indentation
        for line in lines[:-1]:
            if line == "":
                self.writer("\n")
            else:
                self.writer(f"{prefix}{line}\n")
        if lines[-1] != "":
            self.writer(f"{prefix}{lines[-1]}")

    def _consolidate_text_lines(self, lines: list[str]):
        last_node = self._unwritten_text_nodes[-1]
        assert last_node.parent is not None
        if (
            lines[0] == ""
            and last_node is last_node.parent.last_child
            and self._whitespace_is_legit_after_node(last_node)
        ):
            lines.append("")
        if self._line_offset == 0 and lines[0] == "":
            lines.pop(0)
        if len(lines) >= 2 and lines[-1] == "":
            lines[-2] = lines[-2].rstrip()

    @staticmethod
    def _wrap_text(text: str, width: int) -> Iterator[str]:
        while len(text) > width:

            if (index := text.rfind(" ", 0, width + 1)) > -1 or (
                index := text.find(" ", width)
            ) > 0:
                yield text[:index]
                text = text[index + 1 :]
            else:
                yield text
                return

        if text:
            yield text


class FormatOptions(NamedTuple):
    """
    Instances of this class can be used to define serialization formatting that is
    not so hard to interpret for instances of Homo sapiens s., but more costly to
    compute.

    When it's employed whitespace contents will be collapsed and trimmed, newlines will
    be inserted to improve readability, but only where further whitespace reduction
    would drop it again.

    The serialization respects when a tag node bears the ``xml:space`` attribute with
    the value ``preserve``. But if any descendent of such annotated node signals to
    allow whitespace alterations again that has no effect. Such attributes with invalid
    values are ignored.
    """

    align_attributes: bool = False
    """
    Determines whether attributes' names and values line up sharply around vertically
    aligned equal signs.
    """
    indentation: str = "\t"
    """ This string prefixes descending nodes' contents one time per depth level. """
    width: int = 0
    """
    A positive value indicates that text nodes shall get wrapped at this character
    position. Indentations are not considered as part of text. This parameter is
    purposed to define reasonable widths for text displays that could be scrolled
    horizontally.
    """


class DefaultStringOptions:
    """
    This object's class variables are used to configure the serialization parameters
    that are applied when nodes are coerced to :class:`str` objects. Hence it also
    applies when node objects are fed to the :func:`print` function and in other cases
    where objects are implicitly cast to strings.

    .. attention::

        Use this once to define behaviour on *application level*. For thread-safe
        serializations of nodes with diverging parameters use
        :meth:`NodeBase.serialize`! Think thrice whether you want to use this facility
        in a library.
    """

    namespaces: ClassWar[None | NamespaceDeclarations] = None
    """
    A mapping of prefixes to namespaces. These are overriding possible declarations from
    a parsed serialisat that the document instance stems from. Any other prefixes for
    undeclared namespaces are enumerated with the prefix ``ns``.
    """
    newline: ClassWar[None | str] = None
    """
    See :class:`io.TextIOWrapper` for a detailed explanation of the parameter with the
    same name.
    """
    format_options: ClassWar[None | FormatOptions] = None
    """
    An instance of :class:`FormatOptions` can be provided to configure formatting.
    """

    @classmethod
    def _get_serializer(cls) -> Serializer:
        return _get_serializer(
            _StringWriter(newline=cls.newline),
            format_options=cls.format_options,
            namespaces=cls.namespaces,
        )

    @classmethod
    def reset_defaults(cls):
        """Restores the factory settings."""
        cls.format_options = None
        cls.namespaces = None
        cls.newline = None


class _SerializationWriter(ABC):
    __slots__ = ("buffer",)

    def __init__(self, buffer: TextIO):
        self.buffer = buffer

    def __call__(self, data: str):
        self.buffer.write(data)

    @property
    def result(self):
        if isinstance(self.buffer, StringIO):
            return self.buffer.getvalue()
        raise TypeError("Underlying buffer must be an instance of `io.StingIO`")


class _LengthTrackingWriter(_SerializationWriter):
    __slots__ = ("offset", "preserve_space")

    def __init__(self, buffer: TextIO):
        super().__init__(buffer)
        self.offset = 0
        self.preserve_space = False

    def __call__(self, data: str):
        if not self.preserve_space and self.offset == 0:
            data = data.lstrip("\n")

        if not data:
            return

        if data[-1] == "\n":
            self.offset = 0
        else:
            if (index := data.rfind("\n")) == -1:
                self.offset += len(data)
            else:
                self.offset = len(data) - (index + 1)
        super().__call__(data)


class _StringWriter(_SerializationWriter):
    def __init__(self, newline: Optional[str] = None):
        super().__init__(StringIO(newline=newline))


class _TextBufferWriter(_SerializationWriter):
    def __init__(
        self,
        buffer: TextIOWrapper,
        encoding: str = "utf-8",
        newline: Optional[str] = None,
    ):
        buffer.reconfigure(encoding=encoding, newline=newline)
        super().__init__(buffer)


#


__all__ = (
    Attribute.__name__,
    CommentNode.__name__,
    DefaultStringOptions.__name__,
    FormatOptions.__name__,
    NodeBase.__name__,
    ProcessingInstructionNode.__name__,
    QueryResults.__name__,
    Siblings.__name__,
    TagAttributes.__name__,
    TagNode.__name__,
    TextNode.__name__,
    altered_default_filters.__name__,
    any_of.__name__,
    is_comment_node.__name__,
    is_processing_instruction_node.__name__,
    is_root_node.__name__,
    is_tag_node.__name__,
    is_text_node.__name__,
    not_.__name__,
    new_comment_node.__name__,
    new_processing_instruction_node.__name__,
    new_tag_node.__name__,
)
