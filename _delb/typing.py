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

import sys
from abc import ABC, abstractmethod
from collections.abc import Callable, Iterator, Sequence
from typing import (
    TYPE_CHECKING,
    overload,
    Any,
    AnyStr,
    BinaryIO,
    Optional,
    Protocol,
    TypeAlias,
    TypeVar,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping
    from types import SimpleNamespace

    from _delb.nodes import Attribute, Siblings, TagAttributes, _TagDefinition
    from _delb.serializer import FormatOptions
    from _delb.xpath import QueryResults
    from _delb.xpath.ast import EvaluationContext
    from delb import Document


if sys.version_info < (3, 11):  # DROPWITH Python 3.10
    from typing_extensions import Literal, Self
else:
    from typing import Literal, Self


# node types


class XMLNodeType(ABC):
    """
    Defines the interfaces that all node type representations share. All node type
    implementations are a subclass of this one.
    """

    _child_nodes: Siblings
    _parent: None | ParentNodeType

    @abstractmethod
    def __copy__(self): ...

    @abstractmethod
    def __deepcopy__(self, memo): ...

    @abstractmethod
    def __str__(self) -> str: ...

    @abstractmethod
    def add_following_siblings(
        self, *node: NodeSource, clone: bool = False
    ) -> tuple[XMLNodeType, ...]:
        """
        Adds one or more nodes to the right of the node this method is called on.

        :param node: The node(s) to be added.
        :param clone: Clones the concrete nodes before adding if :obj:`True`.
        :return: The concrete nodes that were added.
        :meta category: Methods to add nodes to a tree

        The nodes can be concrete instances of any node type or rather abstract
        descriptions in the form of strings or objects returned from the
        :func:`delb.tag` function that are used to derive :class:`TextNode` respectively
        :class:`TagNode` instances from.
        """

    @abstractmethod
    def add_preceding_siblings(
        self, *node: NodeSource, clone: bool = False
    ) -> tuple[XMLNodeType, ...]:
        """
        Adds one or more nodes to the left of the node this method is called on.

        :param node: The node(s) to be added.
        :param clone: Clones the concrete nodes before adding if :obj:`True`.
        :return: The concrete nodes that were added.
        :meta category: Methods to add nodes to a tree

        The nodes can be concrete instances of any node type or rather abstract
        descriptions in the form of strings or objects returned from the
        :func:`delb.tag` function that are used to derive :class:`TextNode` respectively
        :class:`TagNode` instances from.
        """

    @abstractmethod
    def clone(self, deep: bool = False) -> XMLNodeType:
        """
        Creates a new node of the same type with duplicated contents.

        :param deep: Clones the whole subtree if :obj:`True`.
        :return: A copy of the node.
        """

    @property
    @abstractmethod
    def depth(self) -> int:
        """
        The depth (or level) of the node in its tree.

        :meta category: Node properties
        """

    @abstractmethod
    def detach(self, retain_child_nodes: bool = False) -> XMLNodeType:
        """
        Removes the node from its tree.

        :param retain_child_nodes: Keeps the node's descendants in the originating
                                   tree if :obj:`True`.
        :return: The removed node.
        :meta category: Methods to remove a node
        """

    @property
    @abstractmethod
    def document(self) -> Optional[Document]:
        """
        The :class:`delb.Document` instance that the node is associated with or
        :obj:`None`.

        :meta category: Related document and nodes properties
        """

    @abstractmethod
    def fetch_following(self, *filter: Filter) -> Optional[XMLNodeType]:
        """
        Retrieves the next filter matching node on the following axis.

        :param filter: Any number of :class:`Filter` s.
        :return: The next node in document order that matches all filters or
                 :obj:`None`.
        :meta category: Methods to fetch a relative node
        """

    @abstractmethod
    def _fetch_following(self) -> Optional[XMLNodeType]: ...

    @abstractmethod
    def fetch_following_sibling(self, *filter: Filter) -> Optional[XMLNodeType]:
        """
        Retrieves the next filter matching node on the following-sibling axis.

        :param filter: Any number of :class:`Filter` s.
        :return: The next sibling to the right that matches all filters or
                 :obj:`None`.
        :meta category: Methods to fetch a relative node
        """

    @abstractmethod
    def _fetch_following_sibling(self) -> Optional[XMLNodeType]: ...

    @abstractmethod
    def fetch_preceding(self, *filter: Filter) -> Optional[XMLNodeType]:
        """
        Retrieves the next filter matching node on the preceding axis.

        :param filter: Any number of :class:`Filter` s.
        :return: The previous node in document order that matches all filters or
                 :obj:`None`.
        :meta category: Methods to fetch a relative node
        """

    @abstractmethod
    def _fetch_preceding(self) -> Optional[XMLNodeType]: ...

    @abstractmethod
    def fetch_preceding_sibling(self, *filter: Filter) -> Optional[XMLNodeType]:
        """
        Retrieves the next filter matching node on the preceding-sibling axis.

        :param filter: Any number of :class:`Filter` s.
        :return: The next sibling to the left that matches all filters or
                 :obj:`None`.
        :meta category: Methods to fetch a relative node
        """

    @abstractmethod
    def _fetch_preceding_sibling(self): ...

    @property
    @abstractmethod
    def full_text(self) -> str:
        """
        The concatenated contents of all text node descendants in document order.

        :meta category: Node content properties
        """

    @property
    @abstractmethod
    def index(self) -> Optional[int]:
        """
        The node's index within the parent's collection of child nodes. When this
        property is read the currently set default filters are applied.
        The value :obj:`None` is returned for node without parents and when themself
        are not matching the filters.

        :meta category: Node properties
        """

    @abstractmethod
    def iterate_ancestors(self, *filter: Filter) -> Iterator[ParentNodeType]:
        """
        Iterator over the filter matching nodes on the ancestor axis.

        :param filter: Any number of :class:`Filter` s that a node must match to be
               yielded.
        :return: A :term:`generator iterator` that yields the ancestor nodes from bottom
                 to top.
        :meta category: Methods to iterate over related node
        """

    @abstractmethod
    def _iterate_ancestors(
        self, *, _include_document_node: bool = False
    ) -> Iterator[ParentNodeType]: ...

    @abstractmethod
    def iterate_children(self, *filter: Filter) -> Iterator[XMLNodeType]:
        """
        Iterator over the filter matching nodes on the child axis.

        :param filter: Any number of :class:`Filter` s that a node must match to be
                       yielded.
        :return: A :term:`generator iterator` that yields the child nodes of the node.
        :meta category: Methods to iterate over related node
        """

    @abstractmethod
    def iterate_descendants(self, *filter: Filter) -> Iterator[XMLNodeType]:
        """
        Iterator over the filter matching nodes on the ancestor axis.

        :param filter: Any number of :class:`Filter` s that a node must match to be
                       yielded.
        :return: A :term:`generator iterator` that yields the descending nodes of the
                 node.
        :meta category: Methods to iterate over related node
        """

    @abstractmethod
    def _iterate_descendants(self) -> Iterator[XMLNodeType]: ...

    @abstractmethod
    def iterate_following(
        self, *filter: Filter, include_descendants: bool = True
    ) -> Iterator[XMLNodeType]:
        """
        Iterator over the filter matching nodes on the following axis.

        :param filter: Any number of :class:`Filter` s that a node must match to be
               yielded.
        :param include_descendants: Also yields descendants of the staring node. This
                                    deviates from the XPath definition of the following
                                    axes.
        :return: A :term:`generator iterator` that yields the following nodes in
                 document order.
        :meta category: Methods to iterate over related node
        """

    @abstractmethod
    def _iterate_following(
        self, *, include_descendants: bool = True
    ) -> Iterator[XMLNodeType]: ...

    @abstractmethod
    def iterate_following_siblings(self, *filter: Filter) -> Iterator[XMLNodeType]:
        """
        Iterator over the filter matching nodes on the following-sibling axis.

        :param filter: Any number of :class:`Filter` s that a node must match to be
               yielded.
        :return: A :term:`generator iterator` that yields the siblings to the node's
                 right.
        :meta category: Methods to iterate over related node
        """

    @abstractmethod
    def _iterate_following_siblings(self) -> Iterator[XMLNodeType]: ...

    @abstractmethod
    def iterate_preceding(
        self, *filter: Filter, include_ancestors: bool = True
    ) -> (Iterator)[XMLNodeType]:
        """
        Iterator over the filter matching nodes on the preceding axis.

        :param filter: Any number of :class:`Filter` s that a node must match to be
               yielded.
        :param include_ancestors: Also yields ancestor nodes / tag nodes that were
                                  started earlier in the stream. This deviates from the
                                  XPath definition of the preceding axis.
        :return: A :term:`generator iterator` that yields the previous nodes in document
                 order.
        :meta category: Methods to iterate over related node
        """

    @abstractmethod
    def _iterate_preceding(
        self, *, include_ancestors: bool = True
    ) -> Iterator[XMLNodeType]: ...

    @abstractmethod
    def iterate_preceding_siblings(self, *filter: Filter) -> Iterator[XMLNodeType]:
        """
        Iterator over the filter matching nodes on the preceding-sibling axis.

        :param filter: Any number of :class:`Filter` s that a node must match to be
               yielded.
        :return: A :term:`generator iterator` that yields the siblings to the node's
                 left.
        :meta category: Methods to iterate over related node
        """

    @abstractmethod
    def _iterate_preceding_siblings(self) -> Iterator[XMLNodeType]: ...

    @abstractmethod
    def _iterate_reversed_descendants(self) -> Iterator[XMLNodeType]: ...

    @property
    @abstractmethod
    def parent(self) -> Optional[ParentNodeType]:
        """
        The node's parent or :obj:`None`.

        :meta category: Related document and nodes properties
        """

    @abstractmethod
    def replace_with(self, node: NodeSource, clone: bool = False) -> XMLNodeType:
        """
        Removes the node and places the given one in its tree location.

        The node can be a concrete instance of any node type or a rather abstract
        description in the form of a string or an object returned from the
        :func:`delb.tag` function that is used to derive a :class:`delb.nodes.TextNode`
        respectively :class:`delb.nodes.TagNode` instance from.

        :param node: The replacing node.
        :param clone: A concrete, replacing node is cloned if :obj:`True`.
        :return: The removed node.
        :meta category: Methods to remove a node
        """

    @abstractmethod
    def serialize(
        self,
        *,
        format_options: Optional[FormatOptions] = None,
        namespaces: Optional[NamespaceDeclarations] = None,
        newline: Optional[str] = None,
    ) -> str:
        """
        Returns a string that contains the serialization of the node. See
        :doc:`/api/serialization` for details.

        :param format_options: An instance of :class:`delb.FormatOptions` can be
                               provided to configure formatting.
        :param namespaces: A mapping of prefixes to namespaces.  If not provided the
                           node's namespace will serve as default namespace.  Prefixes
                           for undeclared namespaces are enumerated with the prefix
                           ``ns``.
        :param newline: See :class:`io.TextIOWrapper` for a detailed explanation of the
                        parameter with the same name.
        """

    @abstractmethod
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


class ParentNodeType(XMLNodeType):
    """Defines the interfaces for nodes that can contain further nodes."""

    @abstractmethod
    def __len__(self) -> int: ...

    @abstractmethod
    def append_children(
        self, *node: NodeSource, clone: bool = False
    ) -> tuple[XMLNodeType, ...]:
        """
        Adds one or more nodes as child nodes after any existing to the child nodes of
        the node this method is called on.

        :param node: The node(s) to be added.
        :param clone: Clones the concrete nodes before adding if :obj:`True`.
        :return: The concrete nodes that were appended.
        :meta category: Methods to add nodes to a tree

        The nodes can be concrete instances of any node type or rather abstract
        descriptions in the form of strings or objects returned from the
        :func:`delb.tag` function that are used to derive :class:`delb.nodes.TextNode`
        respectively :class:`delb.nodes.TagNode` instances from.
        """

    @property
    @abstractmethod
    def first_child(self) -> Optional[XMLNodeType]:
        """
        The node's first child node.

        :meta category: Related document and nodes properties
        """

    @abstractmethod
    def insert_children(
        self, index: int, *node: NodeSource, clone: bool = False
    ) -> tuple[XMLNodeType, ...]:
        """
        Inserts one or more child nodes.

        :param index: The index at which the first of the given nodes will be inserted,
                      the remaining nodes are added afterwards in the given order.
        :param node: The node(s) to be added.
        :param clone: Clones the concrete nodes before adding if :obj:`True`.
        :return: The concrete nodes that were inserted.
        :meta category: Methods to add nodes to a tree

        The nodes can be concrete instances of any node type or rather abstract
        descriptions in the form of strings or objects returned from the
        :func:`delb.tag` function that are used to derive :class:`delb.nodes.TextNode`
        respectively :class:`delb.nodes.TagNode` instances from.
        """

    @property
    @abstractmethod
    def last_child(self) -> Optional[XMLNodeType]:
        """
        The node's last child node.

        :meta category: Related document and nodes properties
        """

    @property
    @abstractmethod
    def last_descendant(self) -> Optional[XMLNodeType]:
        """
        The node's last descendant.

        :meta category: Related document and nodes properties
        """

    @abstractmethod
    def merge_text_nodes(self, deep: bool = False):
        """
        Merges all consecutive text nodes in the subtree into one.
        Text nodes without content are dropped.
        """

    @abstractmethod
    def prepend_children(
        self, *node: XMLNodeType, clone: bool = False
    ) -> tuple[XMLNodeType, ...]:
        """
        Adds one or more nodes as child nodes before any existing to the child nodes of
        the node this method is called on.

        :param node: The node(s) to be added.
        :param clone: Clones the concrete nodes before adding if :obj:`True`.
        :return: The concrete nodes that were prepended.
        :meta category: Methods to add nodes to a tree

        The nodes can be concrete instances of any node type or rather abstract
        descriptions in the form of strings or objects returned from the
        :func:`delb.tag` function that are used to derive :class:`delb.nodes.TextNode`
        respectively :class:`delb.nodes.TagNode` instances from.
        """


class CommentNodeType(XMLNodeType):
    """Defines the interfaces for :class:`delb.nodes.CommentNode`."""

    @abstractmethod
    def __eq__(self, other: Any) -> bool: ...

    @property
    @abstractmethod
    def content(self) -> str:
        """
        The comment's text.

        :meta category: Node content properties
        """

    @content.setter
    @abstractmethod
    def content(self, value: str): ...


class _DocumentNodeType(ParentNodeType): ...  # noqa: E701


class ProcessingInstructionNodeType(XMLNodeType):
    """Defines the interfaces for :class:`delb.nodes.ProcessingInstructionNode`."""

    @abstractmethod
    def __eq__(self, other: Any) -> bool: ...

    @property
    @abstractmethod
    def content(self) -> str:
        """
        The processing instruction's text.

        :meta category: Node content properties
        """

    @content.setter
    @abstractmethod
    def content(self, value: str): ...

    @property
    @abstractmethod
    def target(self) -> str:
        """
        The processing instruction's target.

        :meta category: Node content properties
        """

    @target.setter
    @abstractmethod
    def target(self, value: str): ...


class TagNodeType(ParentNodeType):
    """Defines the interfaces for :class:`delb.nodes.TagNodeType`."""

    @abstractmethod
    def __contains__(self, item: AttributeAccessor | XMLNodeType) -> bool: ...

    @overload
    @abstractmethod
    def __getitem__(self, item: int) -> XMLNodeType: ...

    @overload
    @abstractmethod
    def __getitem__(self, item: AttributeAccessor) -> Attribute | None: ...

    @overload
    @abstractmethod
    def __setitem__(self, item: int, value: NodeSource): ...

    @overload
    @abstractmethod
    def __setitem__(self, item: AttributeAccessor, value: str | Attribute): ...

    @property
    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
    def fetch_or_create_by_xpath(
        self,
        expression: str,
        namespaces: Optional[NamespaceDeclarations] = None,
    ) -> TagNodeType:
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

    @abstractmethod
    def _get_normalize_space_directive(
        self, default: Literal["default", "preserve"] = "default"
    ) -> Literal["default", "preserve"]: ...

    @property
    @abstractmethod
    def id(self) -> Optional[str]:
        """
        This is a shortcut to retrieve and set the ``id``  attribute in the XML
        namespace. The client code is responsible to pass properly formed id names.

        :meta category: Node content properties
        """

    @id.setter
    @abstractmethod
    def id(self, value: str | None): ...

    @property
    @abstractmethod
    def location_path(self) -> str:
        """
        An unambiguous XPath location path that points to this node from its tree root.

        :meta category: Node properties
        """

    @property
    @abstractmethod
    def local_name(self) -> str:
        """
        The node's name.

        :meta category: Node properties
        """

    @local_name.setter
    @abstractmethod
    def local_name(self, value: str): ...

    @property
    @abstractmethod
    def namespace(self) -> str:
        """
        The node's namespace. An empty string represents an empty namespace.

        :meta category: Node properties
        """

    @namespace.setter
    @abstractmethod
    def namespace(self, value: str): ...

    @abstractmethod
    def _reduce_whitespace(self): ...

    @property
    @abstractmethod
    def universal_name(self) -> str:
        """
        The node's qualified name in `Clark notation`_.

        :meta category: Node properties

        .. _Clark notation: http://www.jclark.com/xml/xmlns.htm
        """


class TextNodeType(XMLNodeType):
    """Defines the interfaces for :class:`delb.nodes.TextNode`."""

    @abstractmethod
    def __eq__(self, other: Any) -> bool: ...

    @property
    @abstractmethod
    def content(self) -> str:
        """
        The node's text content.

        :meta category: Node content properties
        """

    @content.setter
    @abstractmethod
    def content(self, value: str): ...


# protocols


class BinaryReader(Protocol):
    def close(self): ...

    def read(self, n: int = -1) -> bytes: ...


# aliases


QualifiedName: TypeAlias = tuple[str, str]
AttributeAccessor: TypeAlias = QualifiedName | str
_AttributesData: TypeAlias = dict[QualifiedName, str]

GenericDecorated = TypeVar("GenericDecorated", bound=Callable[..., Any])
SecondOrderDecorator: TypeAlias = "Callable[[GenericDecorated], GenericDecorated]"

Filter: TypeAlias = "Callable[[XMLNodeType], bool]"
NamespaceDeclarations: TypeAlias = "Mapping[str | None, str]"
_NamespaceDeclarations: TypeAlias = "Mapping[str, str]"
NodeSource: TypeAlias = "str | XMLNodeType | _TagDefinition"

InputStream: TypeAlias = AnyStr | BinaryIO
LoaderResult: TypeAlias = "Sequence[XMLNodeType] | str"
Loader: TypeAlias = "Callable[[Any, SimpleNamespace], LoaderResult]"
LoaderConstraint: TypeAlias = "Loader | Iterable[Loader] | None"


XPathFunction: TypeAlias = "Callable[[EvaluationContext, *Any], Any]"


#


__all__ = (
    "AttributeAccessor",
    "_AttributesData",
    "BinaryReader",
    CommentNodeType.__name__,
    _DocumentNodeType.__name__,
    "Filter",
    "GenericDecorated",
    "InputStream",
    "Literal",
    "Loader",
    "LoaderConstraint",
    "LoaderResult",
    "NamespaceDeclarations",
    "NodeSource",
    ParentNodeType.__name__,
    ProcessingInstructionNodeType.__name__,
    "QualifiedName",
    "SecondOrderDecorator",
    "Self",
    TagNodeType.__name__,
    TextNodeType.__name__,
    XMLNodeType.__name__,
    "XPathFunction",
)
