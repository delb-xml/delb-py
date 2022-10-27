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

import gc
from abc import abstractmethod, ABC
from collections import deque
from collections.abc import MutableMapping
from contextlib import contextmanager
from copy import copy, deepcopy
from warnings import warn
from itertools import chain
from sys import getrefcount
from typing import (
    TYPE_CHECKING,
    cast,
    overload,
    Any,
    AnyStr,
    Deque,
    Dict,
    Iterable,
    Iterator,
    List,
    Mapping,
    NamedTuple,
    Optional,
    Sequence,
    Tuple,
    Union,
)

from lxml import etree

from _delb.exceptions import AmbiguousTreeError, InvalidCodePath, InvalidOperation
from _delb.names import (
    XML_ATT_ID,
    XML_ATT_SPACE,
    deconstruct_clark_notation,
    Namespaces,
)
from _delb.parser import ParserOptions, _compat_get_parser
from _delb.typing import Filter, NodeSource
from _delb.utils import (
    _StringMixin,
    _better_call,
    _better_yield,
    _crunch_whitespace,
    last,
    _random_unused_prefix,
)
from _delb.xpath import (
    LegacyXPathExpression,
    QueryResults,
    _css_to_xpath,
)
from _delb.xpath import evaluate as evaluate_xpath, parse as parse_xpath
from _delb.xpath.ast import NameMatchTest, XPathExpression

if TYPE_CHECKING:
    from delb import Document  # noqa: F401


# shortcuts


Comment = etree.Comment
_Element = etree._Element
PI = etree.PI
QName = etree.QName


# constants


DETACHED, DATA, TAIL, APPENDED = 0, 1, 2, 3


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
            # assert getrefcount(result) == 3, getrefcount(result)
        return result

    def __enter__(self):
        self.locks += 1
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.locks -= 1
        return False

    def __gc_callback__(self, phase: str, info: Dict):  # noqa: C901
        """
        This is the verbose implementation, please verify changes with this one:

        .. code-block:

            def __gc_callback__(self, phase: str, info: Dict):
                if phase != "stop" or self.locks:
                    return

                for element, node in tuple(self.wrappers.items()):
                    node_user_references = (
                        getrefcount(node)
                        - 1  # `getrefcount`
                        - 1  # `self.wrappers`
                        - 1  # the iterated tuple
                        - 1  # `node`
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
            if getrefcount(node) > 4 + (
                getattr(node, "__document__", None) is not None
                and (getrefcount(node.__document__)) == 4
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


def new_comment_node(content: str) -> "CommentNode":
    """
    Creates a new :class:`CommentNode`.

    :param content: The comment's content a.k.a. as text.
    :return: The newly created comment node.
    """
    result = _wrapper_cache(etree.Comment(content))
    assert isinstance(result, CommentNode)
    return result


def new_processing_instruction_node(
    target: str, content: str
) -> "ProcessingInstructionNode":
    """
    Creates a new :class:`ProcessingInstructionNode`.

    :param target: The processing instruction's target name.
    :param content: The processing instruction's text.
    :return: The newly created processing instruction node.
    """
    result = _wrapper_cache(etree.PI(target, content))
    assert isinstance(result, ProcessingInstructionNode)
    return result


def new_tag_node(
    local_name: str,
    attributes: Optional[Dict[str, str]] = None,
    namespace: Optional[str] = None,
    children: Sequence[NodeSource] = (),
) -> "TagNode":
    """
    Creates a new :class:`TagNode` instance outside any context. It is preferable to
    use :meth:`new_tag_node`, on instances of documents and nodes where the instance is
    the creation context.

    :param local_name: The tag name.
    :param attributes: Optional attributes that are assigned to the new node.
    :param namespace: An optional tag namespace.
    :param children: An optional sequence of objects that will be appended as child
                     nodes. This can be existing nodes, strings that will be inserted
                     as text nodes and in-place definitions of :class:`TagNode`
                     instances from :func:`tag`. The latter will be assigned to the
                     same namespace.
    :return: The newly created tag node.
    """

    result = _wrapper_cache(
        etree.Element(QName(namespace, local_name).text, attrib=attributes),
    )
    assert isinstance(result, TagNode)

    for child in children:
        if isinstance(child, (str, NodeBase, _TagDefinition)):
            result.append_children(child)
        else:
            raise TypeError(
                "Either node instances, strings or objects from :func:`delb.tag` must "
                "be provided as children argument."
            )

    return result


# abstract tag definitions


class _TagDefinition(NamedTuple):
    """
    Instances of this class describe tag nodes that are constructed from the context
    they are used in (commonly additions to a tree) and the properties that this
    description holds. For the sake of slick code they are not instantiated directly,
    but with the :func:`tag` function.
    """

    local_name: str
    attributes: Optional[Dict[str, str]] = None
    children: Tuple = ()
    # TODO use this notation when it is supported by Python, and only these versions
    #      are supported by delb
    # children: Tuple[Union[str, "_TagDefinition"], ...] = ()


@overload
def tag(local_name: str):  # pragma: no cover
    ...


@overload
def tag(local_name: str, attributes: Mapping[str, str]):  # pragma: no cover
    ...


@overload
def tag(local_name: str, child: NodeSource):  # pragma: no cover
    ...


@overload
def tag(local_name: str, children: Sequence[NodeSource]):  # pragma: no cover
    ...


@overload
def tag(
    local_name: str, attributes: Mapping[str, str], child: NodeSource
):  # pragma: no cover

    ...


@overload
def tag(
    local_name: str, attributes: Mapping[str, str], children: Sequence[NodeSource]
):  # pragma: no cover
    ...


def tag(*args):  # noqa: C901
    """
    This function can be used for in-place creation (or call it templating if you
    want to) of :class:`TagNode` instances as:

    - ``node`` argument to methods that add nodes to a tree
    - items in the ``children`` argument of :func:`new_tag_node` and
      :meth:`NodeBase.new_tag_node`

    The first argument to the function is always the local name of the tag node.
    Optionally, the second argument can be a :term:`mapping` that specifies attributes
    for that node.
    The optional last argument is either a single object that will be appended as child
    node or a sequence of such, these objects can be node instances of any type, strings
    (for derived :class:`TextNode` instances) or other definitions from this function
    (for derived :class:`TagNode` instances).

    The actual nodes that are constructed always inherit the namespace of the context
    node they are created in.

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
    >>> root.append_children(tag("addendum"))
    >>> str(root)[-26:]
    '</items><addendum/></root>'
    """

    def prepare_attributes(attributes: Mapping) -> Dict[str, str]:
        if isinstance(attributes, TagAttributes):
            return attributes.as_dict_with_strings()
        return dict(attributes)

    if len(args) == 1:
        return _TagDefinition(local_name=args[0])

    if len(args) == 2:
        second_arg = args[1]
        if isinstance(second_arg, (Mapping, etree._Attrib)):
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


# default filters


def _is_tag_or_text_node(node: "NodeBase") -> bool:
    return isinstance(node, (TagNode, TextNode))


default_filters: Deque[Tuple[Filter, ...]] = deque()
default_filters.append((_is_tag_or_text_node,))


@contextmanager
def altered_default_filters(*filter: Filter, extend: bool = False):
    """
    This function can be either used as as :term:`context manager` or :term:`decorator`
    to define a set of :obj:`default_filters` for the encapsuled code block or callable.
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

    :param extend: Extends the currently active filters with the given ones instead of
                   replacing them.
    """
    global default_filters

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

    __slots__ = ("_attributes", "_key")

    def __init__(self, attributes: "TagAttributes", key: str):
        self._attributes = attributes
        self._key = key

    def __repr__(self):
        return repr(self.value)

    def _set_new_key(self, namespace, name):
        old_key = self._key

        if namespace is None or self._attributes.namespaces.get(None) == namespace:
            new_key = name
        else:
            new_key = f"{{{namespace}}}{name}"

        if new_key != old_key:
            self._attributes[new_key] = self.value
            del self._attributes[old_key]
            self._key = new_key

    @property
    def local_name(self) -> str:
        """The attribute's local name."""
        return deconstruct_clark_notation(self._key)[1]

    @local_name.setter
    def local_name(self, name: str):
        self._set_new_key(self.namespace, name)

    @property
    def namespace(self) -> Optional[str]:
        """The attribute's namespace"""
        namespace: Union[bytes, str, None]

        if self._key.startswith("{"):
            return deconstruct_clark_notation(self._key)[0]

        namespace, _ = deconstruct_clark_notation(self._key)
        if namespace is None:
            namespace = self._attributes.namespaces.get(None, None)

        if isinstance(namespace, bytes):
            namespace = namespace.decode()

        return namespace

    @namespace.setter
    def namespace(self, namespace: Optional[str]):
        self._set_new_key(namespace, self.local_name)

    @property
    def universal_name(self) -> str:
        """
        The attribute's namespace and local name in `Clark notation`_.

        .. _Clark notation: http://www.jclark.com/xml/xmlns.htm
        """
        namespace = self.namespace
        return f"{{{namespace}}}{self.local_name}" if namespace else self.local_name

    @property
    def value(self) -> str:
        """The attribute's value."""
        value = self._attributes._etree_attrib.get(self._key)
        if value is None:
            raise InvalidOperation("The attribute was removed from its node.")
        return value.decode() if isinstance(value, bytes) else value

    @value.setter
    def value(self, value: str):
        if self._key in self._attributes._etree_attrib:
            self._attributes._etree_attrib[self._key] = value
        else:
            raise InvalidOperation("The attribute was removed from its node.")

    # for utils._StringMixin:
    data = value


class TagAttributes(MutableMapping):
    """A data type to access a :term:`tag node`'s attributes."""

    __slots__ = ("_attributes", "_etree_attrib", "namespaces")

    def __init__(self, node: TagNode):
        self._attributes: Dict[str, Attribute] = {}
        self._etree_attrib: etree._Attrib = node._etree_obj.attrib
        self.namespaces: Namespaces = node.namespaces

    def __contains__(self, item: Any) -> bool:
        return self[item] is not None

    def __delitem__(self, key: Union[str, slice]):
        if isinstance(key, str):
            pass
        elif isinstance(key, slice) and self.namespaces.get(None) != key.start:
            key = f"{{{key.start}}}{key.stop}"
        else:
            raise TypeError(
                "Either an attribute name or a :term:`py:slice` denoting a namespace "
                "and an attribute name must be provided."
            )

        del self._etree_attrib[key]
        self._attributes.pop(key, None)

    def __getitem__(self, item: Union[str, slice]) -> Optional[Attribute]:
        if isinstance(item, str):
            namespace, name = deconstruct_clark_notation(item)
        elif isinstance(item, slice):
            namespace, name = item.start, item.stop
        else:
            raise TypeError(
                "Either an attribute name or a :term:`py:slice` denoting a namespace "
                "and an attribute name must be provided."
            )

        if namespace and not self.namespaces.get(None) == namespace:
            key = f"{{{namespace}}}{name}"
        else:
            key = name

        if key in self._etree_attrib:
            result = self._attributes.get(key)
            if result is None:
                result = Attribute(self, key)
                self._attributes[key] = result
            return result
        else:
            return None

    def __iter__(self) -> Iterator[str]:
        return iter(self._etree_attrib)  # type: ignore

    def __len__(self) -> int:
        return len(self._etree_attrib)

    def __setitem__(self, key: Union[str, slice], value: Union[str, Attribute]):
        if isinstance(key, str):
            pass
        elif isinstance(key, slice):
            key = f"{{{key.start}}}{key.stop}"
        else:
            TypeError(
                "Either an attribute name or a :term:`py:slice` denoting a namespace "
                "and an attribute name must be provided."
            )
        if isinstance(value, Attribute):
            value = value.value
        self._etree_attrib[key] = value
        self._attributes[key] = Attribute(self, key)

    def __str__(self):
        return str(self.as_dict_with_strings())

    __repr__ = __str__

    def as_dict_with_strings(self) -> Dict[str, str]:
        """Returns the attributes as :class:`str` instances in a :class:`dict`."""
        return {str(k): str(v) for k, v in self._etree_attrib.items()}

    def get(self, key, default=None):
        result = self[key]
        return default if result is None else result

    def pop(  # type: ignore
        self, key: str, default: Optional[str] = None
    ) -> Optional[str]:
        if key not in self._etree_attrib:
            return default
        result = str(self._etree_attrib.pop(key, ""))
        self._attributes.pop(key, None)
        return result


# nodes


class NodeBase(ABC):
    __slots__ = ("__weakref__",)

    def add_following_siblings(self, *node: NodeSource, clone: bool = False):
        """
        Adds one or more nodes to the right of the node this method is called on.

        The nodes can be concrete instances of any node type or rather abstract
        descriptions in the form of strings or objects returned from the :func:`tag`
        function that are used to derive :class:`TextNode` respectively :class:`TagNode`
        instances from.

        :param node: The node(s) to be added.
        :param clone: Clones the concrete nodes before adding if ``True``.

        :meta category: add-nodes
        """
        if node:
            this, queue = self._prepare_new_relative(node, clone)
            self._validate_sibling_operation(this)
            self._add_following_sibling(this)
            if queue:
                this.add_following_siblings(*queue, clone=clone)

    @abstractmethod
    def _add_following_sibling(self, node: "NodeBase"):
        pass

    def add_preceding_siblings(self, *node: NodeSource, clone: bool = False):
        """
        Adds one or more nodes to the left of the node this method is called on.

        The nodes can be concrete instances of any node type or rather abstract
        descriptions in the form of strings or objects returned from the :func:`tag`
        function that are used to derive :class:`TextNode` respectively :class:`TagNode`
        instances from.

        :param node: The node(s) to be added.
        :param clone: Clones the concrete nodes before adding if ``True``.

        :meta category: add-nodes
        """
        if node:
            this, queue = self._prepare_new_relative(node, clone)
            self._validate_sibling_operation(this)
            self._add_preceding_sibling(this)
            if queue:
                this.add_preceding_siblings(*queue, clone=clone)

    @abstractmethod
    def _add_preceding_sibling(self, node: "NodeBase"):
        pass

    @abstractmethod
    def clone(self, deep: bool = False, quick_and_unsafe: bool = False) -> "NodeBase":
        """
        :param deep: Clones the whole subtree if ``True``.
        :param quick_and_unsafe: Creates a deep clone in a quicker manner where text
                                 nodes may get lost. It should be safe with trees that
                                 don't contain subsequent text nodes, e.g. freshly
                                 parsed, unaltered documents of after
                                 :meth:`TagNode.merge_text_nodes` has been applied.
        :return: A copy of the node.
        """
        pass

    @property
    @abstractmethod
    def depth(self) -> int:
        """
        The depth (or level) of the node in its tree.
        """
        pass

    @abstractmethod
    def detach(self, retain_child_nodes: bool = False) -> "NodeBase":
        """
        Removes the node from its tree.

        :param retain_child_nodes: Keeps the node's descendants in the originating
                                   tree if ``True``.
        :return: The removed node.

        :meta category: remove-node
        """
        pass

    @property
    @abstractmethod
    def document(self) -> Optional["Document"]:
        """
        The :class:`Document` instances that the node is associated with or ``None``.
        """
        pass

    def fetch_following(self, *filter: Filter) -> Optional["NodeBase"]:
        """
        :param filter: Any number of :term:`filter` s.
        :return: The next node in document order that matches all filters or ``None``.

        :meta category: fetch-node
        """
        try:
            return next(self.iterate_following(*filter))
        except StopIteration:
            return None

    def fetch_following_sibling(self, *filter: Filter) -> Optional["NodeBase"]:
        """
        :param filter: Any number of :term:`filter` s.
        :return: The next sibling to the right that matches all filters or ``None``.

        :meta category: fetch-node
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

    def fetch_preceding(self, *filter: Filter) -> Optional["NodeBase"]:
        """
        :param filter: Any number of :term:`filter` s.
        :return: The previous node in document order that matches all filters or
                 ``None``.

        :meta category: fetch-node
        """
        try:
            return next(self.iterate_preceding(*filter))
        except StopIteration:
            return None

    @abstractmethod
    def fetch_preceding_sibling(self, *filter: Filter) -> Optional["NodeBase"]:
        """
        :param filter: Any number of :term:`filter` s.
        :return: The next sibling to the left that matches all filters or ``None``.

        :meta category: fetch-node
        """
        pass

    @property
    @abstractmethod
    def first_child(self) -> Optional["NodeBase"]:
        """
        The node's first child node.
        """
        pass

    @property
    @abstractmethod
    def full_text(self) -> str:
        """
        The concatenated contents of all text node descendants in document order.
        """
        pass

    @property
    def index(self) -> Optional[int]:
        """
        The node's index within the parent's collection of child nodes or ``None`` when
        the node has no parent.
        """
        parent = self.parent

        if parent is None:
            return None

        for index, node in enumerate(parent.iterate_children()):
            if node is self:
                return index

        raise InvalidCodePath

    def iterate_ancestors(self, *filter: Filter) -> Iterator["TagNode"]:
        """
        :param filter: Any number of :term:`filter` s that a node must match to be
               yielded.
        :return: A :term:`generator iterator` that yields the ancestor nodes from bottom
                 to top.

        :meta category: iter-relatives
        """
        parent = self.parent
        if parent:
            if all(f(parent) for f in filter):
                yield parent
            yield from parent.iterate_ancestors(*filter)

    @abstractmethod
    def iterate_children(
        self, *filter: Filter, recurse: bool = False
    ) -> Iterator["NodeBase"]:
        """
        :param filter: Any number of :term:`filter` s that a node must match to be
                       yielded.
        :param recurse: Deprecated. Use :meth:`NodeBase.iterate_descendants`.
        :return: A :term:`generator iterator` that yields the child nodes of the node.

        :meta category: iter-relatives
        """
        pass

    @abstractmethod
    def iterate_descendants(self, *filter: Filter) -> Iterator["NodeBase"]:
        """
        :param filter: Any number of :term:`filter` s that a node must match to be
                       yielded.
        :return: A :term:`generator iterator` that yields the descending nodes of the
                 node.

        :meta category: iter-relatives
        """
        pass

    def iterate_following(self, *filter: Filter) -> Iterator["NodeBase"]:
        """
        :param filter: Any number of :term:`filter` s that a node must match to be
               yielded.
        :return: A :term:`generator iterator` that yields the following nodes in
                 document order.

        :meta category: iter-relatives
        """
        for node in self._iterate_following():
            if all(f(node) for f in chain(default_filters[-1], filter)):
                yield node

    def _iterate_following(self) -> Iterator["NodeBase"]:
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

    def iterate_following_siblings(self, *filter: Filter) -> Iterator["NodeBase"]:
        """
        :param filter: Any number of :term:`filter` s that a node must match to be
               yielded.
        :return: A :term:`generator iterator` that yields the siblings to the node's
                 right.

        :meta category: iter-relatives
        """
        next_node = self.fetch_following_sibling(*filter)
        while next_node is not None:
            yield next_node
            next_node = next_node.fetch_following_sibling(*filter)

    def iterate_preceding(self, *filter: Filter) -> Iterator["NodeBase"]:
        """
        :param filter: Any number of :term:`filter` s that a node must match to be
               yielded.
        :return: A :term:`generator iterator` that yields the previous nodes in document
                 order.

        :meta category: iter-relatives
        """
        for node in self._iterate_preceding():
            if all(f(node) for f in filter):
                yield node

    @altered_default_filters()
    def _iterate_preceding(self) -> Iterator["NodeBase"]:
        def iter_children(node: NodeBase) -> Iterator[NodeBase]:
            for child_node in reversed(tuple(node.iterate_children())):
                yield from iter_children(child_node)
                yield child_node

        pointer: Optional[NodeBase] = self
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

    def iterate_preceding_siblings(self, *filter: Filter) -> Iterator["NodeBase"]:
        """
        :param filter: Any number of :term:`filter` s that a node must match to be
               yielded.
        :return: A :term:`generator iterator` that yields the siblings to the node's
                 left.

        :meta category: iter-relatives
        """
        previous_node = self.fetch_preceding_sibling(*filter)
        while previous_node is not None:
            yield previous_node
            previous_node = previous_node.fetch_preceding_sibling(*filter)

    @property
    @abstractmethod
    def last_child(self) -> Optional["NodeBase"]:
        """
        The node's last child node.
        """
        pass

    @property
    @abstractmethod
    def last_descendant(self) -> Optional["NodeBase"]:
        """
        The node's last descendant.
        """
        pass

    @property
    @abstractmethod
    def namespaces(self):
        """
        The prefix to namespace :term:`mapping` of the node.
        """
        pass

    @abstractmethod
    def new_tag_node(
        self,
        local_name: str,
        attributes: Optional[Dict[str, str]] = None,
        namespace: Optional[str] = None,
        children: Sequence[NodeSource] = (),
    ) -> "TagNode":
        """
        Creates a new :class:`TagNode` instance in the node's context.

        :param local_name: The tag name.
        :param attributes: Optional attributes that are assigned to the new node.
        :param namespace: An optional tag namespace. If none is provided, the context
                          node's namespace is inherited.
        :param children: An optional sequence of objects that will be appended as child
                         nodes. This can be existing nodes, strings that will be
                         inserted as text nodes and in-place definitions of
                         :class:`TagNode` instances from :func:`tag`. The latter will be
                         assigned to the same namespace.
        :return: The newly created tag node.
        """
        pass

    def _new_tag_node_from(
        self,
        context: _Element,
        local_name: str,
        attributes: Optional[Dict[str, str]],
        namespace: Optional[str],
        children: Sequence[NodeSource],
    ) -> "TagNode":

        tag: QName

        context_namespace = QName(context).namespace

        if namespace:
            tag = QName(namespace, local_name)
        elif context_namespace:
            tag = QName(context_namespace, local_name)
        else:
            tag = QName(local_name)

        result = _wrapper_cache(
            context.makeelement(
                tag.text,
                attrib=attributes,
                # TODO https://github.com/lxml/lxml-stubs/issues/62
                nsmap=context.nsmap,  # type: ignore
            ),
        )
        assert isinstance(result, TagNode)

        if children:
            result.append_children(*children)

        return result

    def _new_tag_node_from_definition(self, definition: _TagDefinition) -> "TagNode":
        return self.parent._new_tag_node_from_definition(definition)

    @property
    @abstractmethod
    def parent(self):
        """
        The node's parent or ``None``.
        """
        pass

    @altered_default_filters()
    def _prepare_new_relative(
        self, nodes: Tuple[NodeSource, ...], clone: bool
    ) -> Tuple["NodeBase", List[NodeSource]]:
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

    def replace_with(self, node: NodeSource, clone: bool = False) -> "NodeBase":
        """
        Removes the node and places the given one in its tree location.

        The node can be a concrete instance of any node type or a rather abstract
        description in the form of a string or an object returned from the :func:`tag`
        function that is used to derive a :class:`TextNode` respectively
        :class:`TagNode` instance from.

        :param node: The replacing node.
        :param clone: A concrete, replacing node is cloned if ``True``.
        :return: The removed node.

        :meta category: remove-node
        """
        if self.parent is None:
            raise InvalidOperation(
                "Cannot replace a root node of a tree. Maybe you want to set the "
                "`root` property of a Document instance?"
            )

        self.add_following_siblings(node, clone=clone)
        return self.detach()

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
        namespaces: Optional[Namespaces] = None,
    ) -> QueryResults:
        """
        See `Queries with XPath & CSS`_ for details on the extent of the XPath
        implementation.

        :param expression: A supported XPath 1.0 expression that contains one or more
                           location paths.
        :param namespaces: A mapping of prefixes that are used in the expression to
                           namespaces. If omitted, the node's definition is used.
        :return: All nodes that match the evaluation of the provided XPath expression.

        :meta category: query-nodes
        """
        return evaluate_xpath(node=self, expression=expression, namespaces=namespaces)

    # deprecated members

    @_better_call(add_following_siblings)
    def add_next(self, *nodes):
        pass

    @_better_call(add_preceding_siblings)
    def add_previous(self, *nodes):
        pass

    @_better_yield(iterate_ancestors)
    def ancestors(self, *filter):
        pass

    @_better_yield(iterate_following_siblings)
    def iterate_next_nodes(self, *filter):
        pass

    @_better_yield(iterate_following)
    def iterate_next_nodes_in_stream(self, *filter):
        pass

    @_better_yield(iterate_preceding_siblings)
    def iterate_previous_nodes(self, *filter):
        pass

    @_better_yield(iterate_preceding)
    def iterate_previous_nodes_in_stream(self, *filter):
        pass

    @_better_call(fetch_following_sibling)
    def next_node(self, *filter):
        pass

    @_better_call(fetch_following)
    def next_node_in_stream(self, *filter):
        pass

    @_better_call(fetch_preceding)
    def previous_node_in_stream(self, *filter):
        pass


class _ChildLessNode(NodeBase):
    """Node types using this mixin also can't be root nodes of a document."""

    __slots__ = ()

    first_child = last_child = last_descendant = None

    @property
    def depth(self) -> int:
        return cast(TagNode, self.parent).depth + 1

    @property
    def document(self) -> Optional["Document"]:
        parent = self.parent
        if parent is None:
            return None
        return parent.document

    def iterate_children(
        self, *filter: Filter, recurse: bool = False
    ) -> Iterator[NodeBase]:
        """
        A :term:`generator iterator` that yields nothing.

        :meta category: iter-relatives
        """
        if recurse:
            warn(
                "The recurse argument is deprecated in favor for the "
                "`iterate_descendants` method.",
                category=DeprecationWarning,
            )

        yield from ()

    def iterate_descendants(self, *filter: Filter) -> Iterator["NodeBase"]:
        yield from ()

    def new_tag_node(
        self,
        local_name: str,
        attributes: Optional[Dict[str, str]] = None,
        namespace: Optional[str] = None,
        children: Sequence[Union[str, NodeBase, "_TagDefinition"]] = (),
    ) -> "TagNode":
        parent = self.parent
        if parent is None:
            return new_tag_node(
                local_name=local_name,
                attributes=attributes,
                namespace=namespace,
                children=children,
            )
        else:
            return parent.new_tag_node(
                local_name=local_name,
                attributes=attributes,
                namespace=namespace,
                children=children,
            )

    # deprecated

    @_better_yield(iterate_children)
    def child_nodes(self, *filter, recurse=False):
        pass


class _ElementWrappingNode(NodeBase):
    __slots__ = ("_etree_obj", "_tail_node")

    def __init__(self, etree_element: _Element):
        self._etree_obj = etree_element
        self._tail_node = TextNode(etree_element, position=TAIL)

    def __copy__(self) -> "_ElementWrappingNode":
        return self.clone(deep=False)

    def __deepcopy__(self, memodict=None) -> "_ElementWrappingNode":
        return self.clone(deep=True)

    def __str__(self) -> str:
        return str(self._etree_obj)

    def _add_following_sibling(self, node: "NodeBase"):
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

    def clone(
        self, deep: bool = False, quick_and_unsafe: bool = False
    ) -> "_ElementWrappingNode":
        etree_clone = copy(self._etree_obj)
        etree_clone.tail = None
        return _wrapper_cache(etree_clone)

    @altered_default_filters()
    def detach(self, retain_child_nodes: bool = False) -> "_ElementWrappingNode":
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

        cast(_Element, etree_obj.getparent()).remove(etree_obj)

        return self

    def _fetch_following_sibling(self) -> Optional[NodeBase]:
        if self._tail_node._exists:
            return self._tail_node

        next_etree_obj = self._etree_obj.getnext()
        if next_etree_obj is None:
            return None
        return _wrapper_cache(next_etree_obj)

    def fetch_preceding_sibling(self, *filter: Filter) -> Optional["NodeBase"]:

        candidate: Optional[NodeBase] = None

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
    def namespaces(self) -> Namespaces:
        return Namespaces(self._etree_obj.nsmap)

    @property
    def parent(self) -> Optional["TagNode"]:
        etree_parent = self._etree_obj.getparent()
        if etree_parent is None:
            return None
        result = _wrapper_cache(etree_parent)
        assert isinstance(result, TagNode)
        return result

    # deprecated

    @_better_call(fetch_preceding_sibling)
    def previous_node(self, *filter):
        pass


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

    @property
    def content(self) -> str:
        """
        The comment's text.
        """
        return cast(str, self._etree_obj.text)

    @content.setter
    def content(self, value: str):
        self._etree_obj.text = value


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

    @property
    def content(self) -> str:
        """
        The processing instruction's text.
        """
        return cast(str, self._etree_obj.text)

    @content.setter
    def content(self, value: str):
        self._etree_obj.text = value

    @property
    def target(self) -> str:
        """
        The processing instruction's target.
        """
        etree_obj = self._etree_obj
        assert isinstance(etree_obj, etree._ProcessingInstruction)
        return cast(str, etree_obj.target)

    @target.setter
    def target(self, value: str):
        etree_obj = self._etree_obj
        assert isinstance(etree_obj, etree._ProcessingInstruction)
        etree_obj.target = value


class TagNode(_ElementWrappingNode, NodeBase):
    """
    The instances of this class represent :term:`tag node` s of a tree, the equivalent
    of DOM's elements.

    To instantiate new nodes use :class:`Document.new_tag_node`,
    :class:`TagNode.new_tag_node`, :class:`TextNode.new_tag_node` or
    :func:`new_tag_node`.

    Some syntactic sugar is baked in:

    Attributes and nodes can be tested for membership in a node.

    >>> root = Document('<root ham="spam"><child/></root>').root
    >>> child = root.first_child
    >>> "ham" in root
    True
    >>> child in root
    True

    Nodes can be copied. Note that this relies on :meth:`TagNode.clone`.

    >>> from copy import copy, deepcopy
    >>> root = Document("<root>Content</root>").root
    >>> print(copy(root))
    <root/>
    >>> print(deepcopy(root))
    <root>Content</root>

    Nodes can be tested for equality regarding their qualified name and attributes.

    >>> root = Document('<root><foo x="0"/><foo x="0"/><bar x="0"/></root>').root
    >>> root[0] == root[1]
    True
    >>> root[0] == root[2]
    False

    Attribute values and child nodes can be obtained with the subscript notation.

    >>> root = Document('<root x="0"><child_1/>child_2<child_3/></root>').root
    >>> root["x"]
    '0'
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
    XML representation of a sub-/tree.
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
        self.__document__: Optional[Document] = None

    def __contains__(self, item: Union[str, NodeBase]) -> bool:
        if isinstance(item, str):
            return item in self.attributes
        elif isinstance(item, NodeBase):
            for child in self.iterate_children():
                if child is item:
                    return True
            return False
        else:
            raise TypeError(
                "Argument must be a string for an attribute name or a node instance."
            )

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, TagNode):
            return False

        return (self.universal_name == other.universal_name) and (
            set(self.attributes.items()) == set(other.attributes.items())
        )

    @overload
    def __getitem__(self, item: str) -> Optional[Attribute]:
        ...

    @overload
    def __getitem__(self, item: int) -> NodeBase:
        ...

    @overload
    def __getitem__(self, item: slice) -> List[NodeBase]:
        ...

    def __getitem__(self, item):
        if isinstance(item, str):
            return self.attributes[item]

        elif isinstance(item, int):
            if item < 0:
                item = len(self) + item

            index = 0
            for child_node in self.iterate_children():
                if index == item:
                    return child_node
                index += 1

            raise IndexError("Node index out of range.")

        elif isinstance(item, slice):
            if all(isinstance(x, str) for x in (item.start, item.stop)):
                return self.attributes[item]
            elif all(
                (isinstance(x, int) or x is None) for x in (item.start, item.stop)
            ):
                return list(self.iterate_children())[item]

        raise TypeError(
            "Argument must be an integer as index for a child node, a string for an "
            "attribute name or a :term:`slice` to denote an attribute's namespace and "
            "name."
        )

    def __len__(self) -> int:
        i = 0
        for _ in self.iterate_children():
            i += 1
        return i

    def __str__(self) -> str:
        clone = self.clone(deep=True)
        clone.merge_text_nodes()
        return etree.tostring(clone._etree_obj, encoding="unicode")

    def __repr__(self) -> str:
        return (
            f'<{self.__class__.__name__}("{self.universal_name}", '
            f"{self.attributes}, {self.location_path}) [{hex(id(self))}]>"
        )

    def __add_first_child(self, node: NodeBase):
        assert not len(self)
        if isinstance(node, _ElementWrappingNode):
            self._etree_obj.append(node._etree_obj)
        elif isinstance(node, TextNode):
            node._bind_to_data(self)

    def append_children(self, *node: NodeSource, clone: bool = False):
        """
        Adds one or more nodes as child nodes after any existing to the child nodes of
        the node this method is called on.

        The nodes can be concrete instances of any node type or rather abstract
        descriptions in the form of strings or objects returned from the :func:`tag`
        function that are used to derive :class:`TextNode` respectively :class:`TagNode`
        instances from.

        :param node: The node(s) to be added.
        :param clone: Clones the concrete nodes before adding if ``True``.

        :meta category: add-nodes
        """
        if not node:
            return

        queue: Sequence[NodeSource]

        last_child = self.last_child

        if last_child is None:
            last_child, queue = self._prepare_new_relative(node, clone=clone)
            self.__add_first_child(last_child)

        else:
            queue = node

        if queue:
            last_child.add_following_siblings(*queue, clone=clone)

    @property
    def attributes(self) -> TagAttributes:
        """
        A :term:`mapping` that can be used to query and alter the node's attributes.

        >>> node = new_tag_node("node", attributes={"foo": "0", "bar": "0"})
        >>> node.attributes
        {'foo': '0', 'bar': '0'}
        >>> node.attributes.pop("bar")
        '0'
        >>> node.attributes["foo"] = "1"
        >>> node.attributes["peng"] = "1"
        >>> print(node)
        <node foo="1" peng="1"/>
        >>> node.attributes.update({"foo": "2", "zong": "2"})
        >>> print(node)
        <node foo="2" peng="1" zong="2"/>

        Namespaced attributes can be accessed by using Python's slice notation. A
        default namespace can be provided optionally, but it's also found without.

        >>> node = new_tag_node("node", {})
        >>> node.attributes["http://namespace":"foo"] = "0"
        >>> print(node)
        <node xmlns:ns0="http://namespace" ns0:foo="0"/>
        >>> node = Document('<node xmlns="default" foo="0"/>').root
        >>> node.attributes["default":"foo"] is node.attributes["foo"]
        True

        Attributes behave like strings, but also expose namespace, local name and
        value for manipulation.

        >>> node = new_tag_node("node")
        >>> node.attributes["foo"] = "0"
        >>> node.attributes["foo"].local_name = "bar"
        >>> node.attributes["bar"].namespace = "http://namespace"
        >>> node.attributes["http://namespace":"bar"].value = "1"
        >>> print(node)
        <node xmlns:ns0="http://namespace" ns0:bar="1"/>

        Unlike with typical Python mappings, requesting a non-existing attribute
        doesn't evoke a :exc:`KeyError`, instead ``None`` is returned.
        """
        return self._attributes

    @altered_default_filters()
    def clone(self, deep: bool = False, quick_and_unsafe: bool = False) -> "TagNode":
        # a faster implementation may be to not clear a cloned element's children and
        # to clone appended text nodes afterwards

        if deep and quick_and_unsafe:
            result = _wrapper_cache(deepcopy(self._etree_obj))
            assert isinstance(result, TagNode)
            result._etree_obj.tail = None
            return result

        etree_clone = copy(self._etree_obj)
        etree_clone.text = etree_clone.tail = None
        del etree_clone[:]  # remove all subelements
        result = _wrapper_cache(etree_clone)
        assert isinstance(result, TagNode)
        assert not len(result)

        if deep:
            for child_node in (x.clone(deep=True) for x in self.iterate_children()):
                assert isinstance(child_node, NodeBase)
                assert child_node.parent is None
                if isinstance(child_node, _ElementWrappingNode):
                    assert child_node._etree_obj.tail is None
                elif isinstance(child_node, TextNode):
                    assert child_node._position is DETACHED

                result.append_children(child_node)

        return result

    def _collapse_whitespace(self, normalize_space: str = "default"):
        with _wrapper_cache:
            normalize_space = cast(
                str, self.attributes.get(XML_ATT_SPACE, normalize_space)
            )

            if normalize_space == "default":
                for child_node in self.iterate_children():
                    if not isinstance(child_node, TextNode):
                        continue

                    crunched = _crunch_whitespace(child_node.content)
                    crunched_stripped = crunched.strip()

                    if (
                        crunched_stripped  # has non-whitespace content
                        and crunched[0] == " "  # begins w/ whitespace
                        and cast(int, child_node.index) > 0  # isn't first child
                    ):
                        child_node.content = f" {crunched_stripped}"
                    elif (
                        crunched[-1] == " "  # ends w/ whitespace
                        and child_node is not self.first_child
                        and child_node is not self.last_child
                    ) or (
                        crunched_stripped  # has non-whitespace content
                        and crunched[-1] == " "  # ends w/ whitespace
                        and child_node is self.first_child
                        and child_node is not self.last_child
                    ):
                        child_node.content = f"{crunched.strip()} "
                    elif len(self) == 1 and crunched == " ":
                        # is only child and contains only whitespace
                        child_node.content = " "
                    else:
                        child_node.content = crunched_stripped
            else:
                assert normalize_space == "preserve"

            for child_node in self.iterate_children(is_tag_node):
                cast(TagNode, child_node)._collapse_whitespace(normalize_space)

    def css_select(
        self, expression: str, namespaces: Optional[Namespaces] = None
    ) -> QueryResults:
        """
        See `Queries with XPath & CSS`_ regarding the extent of the supported grammar.

        Namespace prefixes are delimited with a ``|`` before a name test, for example
        ``div svg|metadata`` selects all descendants of ``div`` named nodes that belong
        to the default namespace or have no namespace and whose name is ``metadata``
        and have a namespace that is mapped to the ``svg`` prefix.

        :param expression: A CSS selector expression.
        :param namespaces: A mapping of prefixes that are used in the expression to
                           namespaces. If omitted, the node's definition is used.
        :return: All nodes that match the evaluation of the provided CSS selector
                 expression.

        :meta category: query-nodes
        """
        return self.xpath(expression=_css_to_xpath(expression), namespaces=namespaces)

    @property
    def depth(self) -> int:
        if self.parent is None:
            return 0
        return self.location_path.count("/")

    @altered_default_filters()
    def detach(self, retain_child_nodes: bool = False) -> "_ElementWrappingNode":
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

        parent_has_default_namespace = parent is not None and None in parent.namespaces

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
                nsmap=parent.namespaces.data,  # type: ignore
            )
            self._attributes._etree_attrib = self._etree_obj.attrib
            self._attributes.namespaces = self.namespaces
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
    def document(self) -> Optional["Document"]:
        if self.parent is None:
            root_node = self
        else:
            root_node = cast(TagNode, last(self.iterate_ancestors()))
        return root_node.__document__

    def fetch_or_create_by_xpath(
        self,
        expression: str,
        namespaces: Union[Namespaces, None, Mapping[Optional[str], str]] = None,
    ) -> "TagNode":
        """
        Fetches a single node that is locatable by the provided XPath expression. If
        the node doesn't exist, the non-existing branch will be created. These rules
        are imperative in your endeavour:

        - All location steps must use the child axis.
        - Each step needs to provide a name test.
        - Attributes must be compared against a literal.
        - Multiple attribute comparisons must be joined with the `and` operator and / or
          more than one predicate expression.
        - The logical validity of multiple attribute comparisons isn't checked. E.g.
          one could provide ``foo[@p="her"][@p="him"]``, but expect an undefined
          behaviour.
        - Other contents in predicate expressions are invalid.

        >>> document = Document("<root/>")
        >>> grandchild = document.root.fetch_or_create_by_xpath(
        ...     "child[@a='b']/grandchild"
        ... )
        >>> grandchild is document.root.fetch_or_create_by_xpath(
        ...     "child[@a='b']/grandchild"
        ... )
        True
        >>> str(document)
        '<root><child a="b"><grandchild/></child></root>'

        :param expression: An XPath expression that can unambiguously locate a
                           descending node in a tree that has any state.
        :param namespaces: An optional mapping of prefixes to namespaces. As default the
                           node's one is used.

        :return: The existing or freshly created node descibed with ``expression``.
        """
        ast = parse_xpath(expression)
        if not ast._is_unambiguously_locatable:
            raise ValueError(
                "The XPath expression doesn't determine a distinct branch."
            )

        if namespaces is None:
            namespaces = self.namespaces
        elif not isinstance(namespaces, Namespaces):
            namespaces = Namespaces(namespaces)

        query_result = self.xpath(expression, namespaces)

        if query_result.size == 1:
            result = query_result.first
            assert isinstance(result, TagNode)
            return result

        if query_result:
            raise AmbiguousTreeError(
                f"The tree already contains {query_result.size} matching branches."
            )

        return self._create_by_xpath(ast, namespaces)

    def _create_by_xpath(
        self,
        ast: XPathExpression,
        namespaces: Namespaces,
    ) -> "TagNode":

        node = self

        for i, step in enumerate(ast.location_paths[0].location_steps):
            candidates = tuple(step.evaluate(node_set=(node,), namespaces=namespaces))

            if len(candidates) == 0:
                node_test = step.node_test
                assert isinstance(node_test, NameMatchTest)
                prefix = node_test.prefix
                if prefix is None:
                    namespace = namespaces.get(None)
                else:
                    namespace = namespaces[prefix]

                new_node = node.new_tag_node(
                    local_name=node_test.local_name,
                    attributes=None,
                    namespace=namespace,
                )

                for prefix, local_name, value in step._derived_attributes:
                    if prefix is None and None not in namespaces:
                        new_node.attributes[local_name] = value
                    else:
                        new_node.attributes[
                            namespaces[prefix] : local_name  # type: ignore
                        ] = value

                node.append_children(new_node)
                node = new_node

            elif len(candidates) == 1:
                node = cast("TagNode", candidates[0])

            else:
                raise AmbiguousTreeError(
                    f"The tree has multiple possible branches at location step {i}."
                )
        return node

    @property
    def first_child(self) -> Optional[NodeBase]:
        for result in self.iterate_children():
            return result
        return None

    @property
    def full_text(self) -> str:
        return "".join(str(x) for x in self.iterate_descendants(is_text_node))

    @property
    def id(self) -> Optional[str]:
        """
        This is a shortcut to retrieve and set the ``id``  attribute in the XML
        namespace. The client code is responsible to pass properly formed id names.
        """
        return cast(str, self.attributes.get(XML_ATT_ID))

    @id.setter
    def id(self, value: Optional[str]):
        if value is None:
            self.attributes.pop(XML_ATT_ID, "")
        elif isinstance(value, str):
            root = cast(TagNode, last(self.iterate_ancestors())) or self
            if root._etree_obj.xpath(f"descendant-or-self::*[@xml:id='{value}']"):
                raise ValueError(
                    "An xml:id-attribute with that value is already assigned in the "
                    "tree."
                )
            self.attributes[XML_ATT_ID] = value
        else:
            raise TypeError("Value must be None or a string.")

    @property
    def index(self) -> Optional[int]:
        if self.parent is None:
            return None
        return super().index

    def insert_children(self, index: int, *node: NodeSource, clone: bool = False):
        """
        Inserts one or more child nodes.

        The nodes can be concrete instances of any node type or rather abstract
        descriptions in the form of strings or objects returned from the :func:`tag`
        function that are used to derive :class:`TextNode` respectively :class:`TagNode`
        instances from.

        :param index: The index at which the first of the given nodes will be inserted,
                      the remaining nodes are added afterwards in the given order.
        :param node: The node(s) to be added.
        :param clone: Clones the concrete nodes before adding if ``True``.

        :meta category: add-nodes
        """
        if index < 0:
            raise ValueError("Index must be zero or a positive integer.")

        children_count = len(self)

        if index > children_count:
            raise IndexError("The given index is beyond the target's size.")

        this, *queue = node

        if index == 0:
            if children_count:
                self[0].add_preceding_siblings(this, clone=clone)
            else:
                self.__add_first_child(
                    self._prepare_new_relative((this,), clone=clone)[0]
                )

        else:
            self[index - 1].add_following_siblings(this, clone=clone)

        if queue:
            self[index].add_following_siblings(*queue, clone=clone)

    def iterate_children(
        self, *filter: Filter, recurse: bool = False
    ) -> Iterator[NodeBase]:
        if recurse:
            warn(
                "The recurse argument is deprecated in favor for the "
                "`iterate_descendants` method.",
                category=DeprecationWarning,
            )
            yield from self.iterate_descendants(*filter)
            return

        all_filters = default_filters[-1] + filter
        candidate: Optional[NodeBase]

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

    def iterate_descendants(self, *filter: Filter) -> Iterator["NodeBase"]:
        all_filters = default_filters[-1] + filter
        with altered_default_filters():
            candidate = self.first_child
            if candidate is None:
                return

            next_candidates: List[Optional[NodeBase]] = []
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
    def last_descendant(self) -> Optional["NodeBase"]:
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
        """
        return cast(str, QName(self._etree_obj).localname)

    @local_name.setter
    def local_name(self, value: str):
        self._etree_obj.tag = QName(self.namespace, value).text

    @property
    def location_path(self) -> str:
        """
        An unambiguous XPath location path that points to this node from its tree root.
        """
        if self.parent is None:
            return "/."

        with altered_default_filters(is_tag_node):
            steps = list(self.iterate_ancestors())
            steps.pop()  # root
            steps.reverse()
            steps.append(self)
            return "".join(f"/*[{n.index+1}]" for n in steps)  # type: ignore

    @altered_default_filters()
    def merge_text_nodes(self):
        """
        Merges all consecutive text nodes in the subtree into one.
        """
        for node in self.iterate_descendants(is_text_node):
            node._merge_appended_text_nodes()

    @property
    def namespace(self) -> Optional[str]:
        """
        The node's namespace. Be aware, that while this property can be set to ``None``,
        serializations will continue to render a previous default namespace declaration
        if the node had such.
        """
        # weirdly QName fails in some cases when called with an etree._Element
        return QName(self._etree_obj.tag).namespace  # type: ignore

    @namespace.setter
    def namespace(self, value: Optional[str]):
        self._etree_obj.tag = QName(value, self.local_name).text

    def new_tag_node(
        self,
        local_name: str,
        attributes: Optional[Dict[str, str]] = None,
        namespace: Optional[str] = None,
        children: Sequence[Union[str, NodeBase, "_TagDefinition"]] = (),
    ) -> "TagNode":
        return self._new_tag_node_from(
            self._etree_obj, local_name, attributes, namespace, children
        )

    def _new_tag_node_from_definition(self, definition: _TagDefinition) -> "TagNode":
        return self._new_tag_node_from(
            context=self._etree_obj,
            local_name=definition.local_name,
            attributes=definition.attributes,
            namespace=self.namespace,
            children=definition.children,
        )

    @staticmethod
    def parse(
        text: AnyStr,
        parser: Optional[etree.XMLParser] = None,
        parser_options: Optional[ParserOptions] = None,
        collapse_whitespace: Optional[bool] = None,
    ) -> "TagNode":
        """
        Parses the given string or bytes sequence into a new tree.

        :param text: A serialized XML tree.
        :param parser: Deprecated.
        :param parser_options: A :class:`delb.ParserOptions` class to configure the used
                               parser.
        :param collapse_whitespace: Deprecated. Use the argument with the same name on
                                    the ``parser_options`` object.
        """
        warn(
            "This method will be replaced by another interface in a future version.",
            category=PendingDeprecationWarning,
        )
        parser, collapse_whitespace = _compat_get_parser(
            parser, parser_options, collapse_whitespace
        )
        result = _wrapper_cache(etree.fromstring(text, parser=parser))
        assert isinstance(result, TagNode)
        if collapse_whitespace:
            result._collapse_whitespace()
        return result

    @property
    def prefix(self) -> Optional[str]:
        """
        The prefix that the node's namespace is currently mapped to.
        """
        target = QName(self._etree_obj).namespace

        if target is None:
            return None

        for prefix, namespace in self._etree_obj.nsmap.items():
            assert isinstance(prefix, str) or prefix is None
            if namespace == target:
                return prefix
        raise InvalidCodePath

    def prepend_children(self, *node: NodeBase, clone: bool = False) -> None:
        """
        Adds one or more nodes as child nodes before any existing to the child nodes of
        the node this method is called on.

        The nodes can be concrete instances of any node type or rather abstract
        descriptions in the form of strings or objects returned from the :func:`tag`
        function that are used to derive :class:`TextNode` respectively :class:`TagNode`
        instances from.

        :param node: The node(s) to be added.
        :param clone: Clones the concrete nodes before adding if ``True``.

        :meta category: add-nodes
        """
        self.insert_children(0, *node, clone=clone)

    @property
    def universal_name(self) -> str:
        """
        The node's qualified name in `Clark notation`_.

        .. _Clark notation: http://www.jclark.com/xml/xmlns.htm
        """
        return cast(str, self._etree_obj.tag)

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

    # REMOVE eventually
    @altered_default_filters()
    def xpath(
        self,
        expression: str,
        namespaces: Optional[Namespaces] = None,
    ) -> QueryResults:
        """
        See `Queries with XPath & CSS`_ for details on the extent of the XPath
        implementation.

        :param expression: A supported XPath 1.0 expression that contains one or more
                           location paths.
        :param namespaces: A mapping of prefixes that are used in the expression to
                           namespaces. If omitted, the node's definition is used.
        :return: All nodes that match the evaluation of the provided XPath expression.

        :meta category: query-nodes
        """
        result = super().xpath(expression=expression, namespaces=namespaces)
        if __debug__ and all(isinstance(n, TagNode) for n in result):
            try:
                etree_result = self._etree_xpath(expression)
            except NotImplementedError:
                # might stem from flaws in LegacyXPathExpression
                pass
            else:
                assert result == etree_result, (
                    "Please report that the native XPath evaluator seems faulty with "
                    f"the expression `{expression}` at "
                    "https://github.com/delb-xml/delb-py/issues"
                )
        return result

    # REMOVE eventually
    def _etree_xpath(self, expression: str) -> QueryResults:
        etree_obj = self._etree_obj
        namespaces = etree_obj.nsmap
        compat_namespaces: etree._DictAnyStr
        xpath_expression = LegacyXPathExpression(expression)

        if None in namespaces:
            has_default_namespace = True
            prefix = _random_unused_prefix(namespaces)
            compat_namespaces = cast(
                "etree._DictAnyStr",
                {
                    **{k: v for k, v in namespaces.items() if k is not None},
                    prefix: namespaces[None],
                },
            )

        else:
            has_default_namespace = False
            prefix = ""
            compat_namespaces = cast("etree._DictAnyStr", namespaces)

        for location_path in xpath_expression.location_paths:
            if has_default_namespace:
                for location_step in location_path.location_steps:
                    node_test = location_step.node_test
                    if node_test.type != "name_test":
                        continue
                    if ":" not in node_test.data:
                        node_test.data = prefix + ":" + node_test.data

        if str(xpath_expression) != expression:
            raise NotImplementedError

        _results = etree_obj.xpath(
            str(xpath_expression),
            namespaces=compat_namespaces,  # type: ignore
        )
        assert isinstance(_results, Iterable)
        return QueryResults(
            (_wrapper_cache(cast(_Element, element)) for element in _results)
        )

    # deprecated

    @_better_call(append_children)
    def append_child(self, *node, clone=False):
        pass

    @_better_yield(iterate_children)
    def child_nodes(self, *filter, recurse=False):
        pass

    @_better_call(insert_children)
    def insert_child(self, *node, clone=False):
        pass

    @_better_call(prepend_children)
    def prepend_child(self, *node, clone=False):
        pass

    @property
    def qualified_name(self):
        """:meta category: deprecated"""
        warn(
            "The property `TagNode.qualified_name` is now named `universal_name`. "
            "The former will be removed in a future release.",
            category=DeprecationWarning,
        )
        return self.universal_name


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

    Attributes that rely to child nodes yield nothing respectively ``None``.
    """

    __slots__ = ("_appended_text_node", "_bound_to", "__content", "_position")

    def __init__(
        self,
        reference_or_text: Union[_Element, str, "TextNode"],
        position: int = DETACHED,
    ):
        self._bound_to: Union[None, _Element, TextNode]
        self.__content: Optional[str]

        self._appended_text_node: Optional[TextNode] = None
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

    def __getitem__(self, item):
        return self.content[item]

    def __repr__(self):
        if self._exists:
            return (
                f'<{self.__class__.__name__}(text="{self}", '
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

    def clone(self, deep: bool = False, quick_and_unsafe: bool = False) -> "NodeBase":
        assert self.content is not None
        return self.__class__(self.content)

    @property
    def content(self) -> str:
        """
        The node's text content.
        """
        if self._position is DATA:
            assert isinstance(self._bound_to, _Element)
            return cast(str, self._bound_to.text)

        elif self._position is TAIL:
            assert isinstance(self._bound_to, _Element)
            return cast(str, self._bound_to.tail)

        elif self._position in (APPENDED, DETACHED):
            assert self._bound_to is None or isinstance(self._bound_to, TextNode)
            return cast(str, self.__content)

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
    data = content  # type: ignore

    @property
    def depth(self) -> int:
        if self._position is DETACHED:
            return 0
        return super().depth

    def detach(self, retain_child_nodes: bool = False) -> "TextNode":

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
        self.content = content

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

    def fetch_preceding_sibling(self, *filter: Filter) -> Optional["NodeBase"]:
        candidate: Optional[NodeBase]

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

    def _insert_text_node_as_next_appended(self, node: "TextNode"):
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

    @property
    def namespaces(self):
        if self.parent:
            return self.parent.namespaces
        else:
            raise InvalidOperation("A lonely text node has no namespace context.")

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

    def _prepend_text_node(self, node: "TextNode"):
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

    # deprecated

    @_better_call(fetch_preceding_sibling)
    def previous_node(self, *filter):
        pass


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


#


__all__ = (
    Attribute.__name__,
    CommentNode.__name__,
    NodeBase.__name__,
    ProcessingInstructionNode.__name__,
    QueryResults.__name__,
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
    tag.__name__,
)
