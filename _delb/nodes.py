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

import sys
from abc import abstractmethod, ABC
from collections import deque
from contextlib import contextmanager
from copy import copy
from functools import wraps
from itertools import chain
from typing import (
    TYPE_CHECKING,
    cast,
    overload,
    Any,
    AnyStr,
    Callable,
    Deque,
    Dict,
    Iterator,
    List,
    Mapping,
    NamedTuple,
    Optional,
    Sequence,
    Set,
    Tuple,
    Union,
)

from lxml import etree

from _delb.exceptions import InvalidCodePath, InvalidOperation
from _delb.typing import ElementAttributes, Filter, NodeSource, _WrapperCache
from _delb.utils import (
    DEFAULT_PARSER,
    _crunch_whitespace,
    _css_to_xpath,
    last,
    _random_unused_prefix,
)
from _delb.xpath import XPathExpression

if TYPE_CHECKING:
    from delb import Document  # noqa: F401


# shortcuts


Comment = etree.Comment
_Element = etree._Element
PI = etree.PI
QName = etree.QName


# constants


DETACHED, DATA, TAIL, APPENDED = 0, 1, 2, 3
STRINGMETHODS = {
    name
    for name, obj in vars(str).items()
    if not name.startswith("_") and callable(obj)
}
XML_ATT_ID = "{http://www.w3.org/XML/1998/namespace}id"
XML_ATT_SPACE = "{http://www.w3.org/XML/1998/namespace}space"


# functions


def _get_or_create_element_wrapper(
    element: _Element, cache: _WrapperCache
) -> "_ElementWrappingNode":
    result = cache.get(id(element))
    if result is None:
        tag = element.tag
        if tag is Comment:
            result = CommentNode(element, cache)
        elif tag is PI:
            result = ProcessingInstructionNode(element, cache)
        else:
            result = TagNode(element, cache)
        cache[id(element)] = result
    return result


def new_comment_node(content: str) -> "CommentNode":
    """
    Creates a new :class:`CommentNode`.

    :param content: The comment's content a.k.a. as text.
    :return: The newly created comment node.
    """
    result = _get_or_create_element_wrapper(etree.Comment(content), {})
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
    result = _get_or_create_element_wrapper(etree.PI(target, content), {})
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

    result = _get_or_create_element_wrapper(
        etree.Element(QName(namespace, local_name).text, attrib=attributes), {}
    )
    assert isinstance(result, TagNode)

    for child in children:
        if isinstance(child, (str, NodeBase, _TagDefinition)):
            result.append_child(child)
        else:
            raise TypeError

    return result


def _prune_wrapper_cache(node: "_ElementWrappingNode"):
    if node.parent is None:
        root = node
    else:
        with altered_default_filters():
            root = cast(TagNode, last(node.ancestors()))

    cache = root._wrapper_cache
    for key in set(cache) - {id(x) for x in root._etree_obj.iter()}:
        cache.pop(key)


# wrapper


def _yield_with_altered_recursion_limit(func: Callable) -> Callable:
    def count_nodes(node) -> int:
        result = 0
        with altered_default_filters():
            for _ in node.document.root.child_nodes(recurse=True):
                result += 1
        return result

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        recursion_limit = sys.getrecursionlimit()
        sys.setrecursionlimit(max(int(count_nodes(self) * 1.1), recursion_limit))
        yield from func(self, *args, **kwargs)
        sys.setrecursionlimit(recursion_limit)

    return wrapper


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
def tag(local_name: str):
    ...


@overload
def tag(local_name: str, attributes: Mapping[str, str]):
    ...


@overload
def tag(local_name: str, child: NodeSource):
    ...


@overload
def tag(local_name: str, children: Sequence[NodeSource]):
    ...


@overload
def tag(local_name: str, attributes: Mapping[str, str], child: NodeSource):
    ...


@overload
def tag(local_name: str, attributes: Mapping[str, str], children: Sequence[NodeSource]):
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
    >>> root.append_child(tag("addendum"))
    >>> str(root)[-26:]
    '</items><addendum/></root>'
    """

    if len(args) == 1:
        return _TagDefinition(local_name=args[0])

    if len(args) == 2:
        second_arg = args[1]
        if isinstance(second_arg, (Mapping, etree._Attrib)):
            return _TagDefinition(local_name=args[0], attributes=dict(second_arg))
        if isinstance(second_arg, (str, NodeBase, _TagDefinition)):
            return _TagDefinition(local_name=args[0], children=(second_arg,))
        if isinstance(second_arg, Sequence):
            if not all(
                isinstance(x, (str, NodeBase, _TagDefinition)) for x in second_arg
            ):
                raise TypeError
            return _TagDefinition(local_name=args[0], children=tuple(second_arg))

    if len(args) == 3:
        third_arg = args[2]
        if isinstance(third_arg, (str, NodeBase, _TagDefinition)):
            return _TagDefinition(
                local_name=args[0], attributes=args[1], children=(third_arg,)
            )
        if isinstance(third_arg, Sequence):
            if not all(
                isinstance(x, (str, NodeBase, _TagDefinition)) for x in third_arg
            ):
                raise TypeError
            return _TagDefinition(
                local_name=args[0], attributes=args[1], children=tuple(third_arg)
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
    ...     print([x.content for x in root.child_nodes()])
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


# nodes


class NodeBase(ABC):
    __slots__ = ("_wrapper_cache",)

    def __init__(self, wrapper_cache: _WrapperCache):
        self._wrapper_cache = wrapper_cache

    def add_next(self, *node: NodeSource, clone: bool = False):
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
            self._add_next_node(this)
            if queue:
                this.add_next(*queue, clone=clone)

    @abstractmethod
    def _add_next_node(self, node: "NodeBase"):
        pass

    def add_previous(self, *node: NodeSource, clone: bool = False):
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
            self._add_previous_node(this)
            if queue:
                this.add_previous(*queue, clone=clone)

    @abstractmethod
    def _add_previous_node(self, node: "NodeBase"):
        pass

    def ancestors(self, *filter: Filter) -> Iterator["TagNode"]:
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
            yield from parent.ancestors(*filter)

    @abstractmethod
    def child_nodes(
        self, *filter: Filter, recurse: bool = False
    ) -> Iterator["NodeBase"]:
        """
        :param filter: Any number of :term:`filter` s that a node must match to be
                       yielded.
        :param recurse: Also returns the children's children and so on in document order
                        if ``True``.
        :return: A :term:`generator iterator` that yields the child nodes of the node.

        :meta category: iter-relatives
        """
        pass

    @abstractmethod
    def clone(self, deep: bool = False) -> "NodeBase":
        """
        :param deep: Clones the whole subtree if ``True``.
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
        Removes the node, including its descendants, from its tree.

        :param retain_child_nodes: Keeps the child nodes in the tree if ``True``.
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

        for index, node in enumerate(parent.child_nodes(recurse=False)):
            if node is self:
                break

        return index

    def iterate_next_nodes(self, *filter: Filter) -> Iterator["NodeBase"]:
        """
        :param filter: Any number of :term:`filter` s that a node must match to be
               yielded.
        :return: A :term:`generator iterator` that yields the siblings to the node's
                 right.

        :meta category: iter-relatives
        """
        next_node = self.next_node(*filter)
        while next_node is not None:
            yield next_node
            next_node = next_node.next_node(*filter)

    @_yield_with_altered_recursion_limit
    def iterate_next_nodes_in_stream(self, *filter: Filter) -> Iterator["NodeBase"]:
        """
        :param filter: Any number of :term:`filter` s that a node must match to be
               yielded.
        :return: A :term:`generator iterator` that yields the following nodes in
                 document order.

        :meta category: iter-relatives
        """
        for node in self._iterate_next_nodes_in_stream():
            if all(f(node) for f in chain(default_filters[-1], filter)):
                yield node

    @altered_default_filters()
    def _iterate_next_nodes_in_stream(self) -> Iterator["NodeBase"]:
        def next_sibling_of_an_ancestor(
            node: NodeBase,
        ) -> Optional[_ElementWrappingNode]:
            parent = node.parent
            if parent is None:
                return None
            parents_next = parent.next_node()
            if parents_next is None:
                return next_sibling_of_an_ancestor(parent)
            return parents_next

        next_node = self.first_child
        if next_node is None:
            next_node = self.next_node()

        if next_node is None:
            next_node = next_sibling_of_an_ancestor(self)

        if next_node is None:
            return

        yield next_node
        yield from next_node._iterate_next_nodes_in_stream()

    def iterate_previous_nodes(self, *filter: Filter) -> Iterator["NodeBase"]:
        """
        :param filter: Any number of :term:`filter` s that a node must match to be
               yielded.
        :return: A :term:`generator iterator` that yields the siblings to the node's
                 left.

        :meta category: iter-relatives
        """
        previous_node = self.previous_node(*filter)
        while previous_node is not None:
            yield previous_node
            previous_node = previous_node.previous_node(*filter)

    @_yield_with_altered_recursion_limit
    def iterate_previous_nodes_in_stream(self, *filter: Filter) -> Iterator["NodeBase"]:
        """
        :param filter: Any number of :term:`filter` s that a node must match to be
               yielded.
        :return: A :term:`generator iterator` that yields the previous nodes in document
                 order.

        :meta category: iter-relatives
        """
        for node in self._iterate_previous_nodes_in_stream():
            if all(f(node) for f in filter):
                yield node

    @altered_default_filters()
    def _iterate_previous_nodes_in_stream(self) -> Iterator["NodeBase"]:
        def iter_children(node: NodeBase) -> Iterator[NodeBase]:
            for child_node in reversed(tuple(node.child_nodes(recurse=False))):
                yield from iter_children(child_node)
                yield child_node

        previous_node = self.previous_node()

        if previous_node is None:
            parent = self.parent
            if parent is None:
                return
            yield parent
            yield from parent._iterate_previous_nodes_in_stream()

        else:
            yield from iter_children(previous_node)
            yield previous_node
            yield from previous_node._iterate_previous_nodes_in_stream()

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

    # REMOVE?
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

        result = _get_or_create_element_wrapper(
            context.makeelement(tag.text, attrib=attributes, nsmap=context.nsmap),
            self._wrapper_cache,
        )
        assert isinstance(result, TagNode)

        for child in children:
            if isinstance(child, (str, NodeBase, _TagDefinition)):
                result.append_child(child)
            else:
                raise TypeError

        return result

    def _new_tag_node_from_definition(self, definition: _TagDefinition) -> "TagNode":
        return self.parent._new_tag_node_from_definition(definition)

    @abstractmethod
    def next_node(self, *filter: Filter) -> Optional["NodeBase"]:
        """
        :param filter: Any number of :term:`filter` s.
        :return: The next sibling to the right that matches all filters or ``None``.

        :meta category: fetch-node
        """
        pass

    def next_node_in_stream(self, *filter: Filter) -> Optional["NodeBase"]:
        """
        :param filter: Any number of :term:`filter` s.
        :return: The next node in document order that matches all filters or ``None``.

        :meta category: fetch-node
        """
        try:
            return next(self.iterate_next_nodes_in_stream(*filter))
        except StopIteration:
            return None

    @property
    @abstractmethod
    def parent(self):
        """
        The node's parent or ``None``.
        """
        pass

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
            raise TypeError

        if not all(
            x is None for x in (this.parent, this.next_node(), this.previous_node())
        ):
            raise InvalidOperation(
                "A node that shall be added to a tree must have neither a parent nor "
                "any sibling node. Use :meth:`NodeBase.detach` or a `clone` argument "
                "to move a node within or between trees."
            )

        self._wrapper_cache.update(this._wrapper_cache)
        this._wrapper_cache = self._wrapper_cache

        return this, queue

    @abstractmethod
    def previous_node(self, *filter: Filter) -> Optional["NodeBase"]:
        """
        :param filter: Any number of :term:`filter` s.
        :return: The next sibling to the left that matches all filters or ``None``.

        :meta category: fetch-node
        """
        pass

    def previous_node_in_stream(self, *filter: Filter) -> Optional["NodeBase"]:
        """
        :param filter: Any number of :term:`filter` s.
        :return: The previous node in document order that matches all filters or
                 ``None``.

        :meta category: fetch-node
        """
        try:
            return next(self.iterate_previous_nodes_in_stream(*filter))
        except StopIteration:
            return None

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

        self.add_next(node, clone=clone)
        return self.detach()

    def _validate_sibling_operation(self, node):
        if self.parent is None and not (
            isinstance(node, (CommentNode, ProcessingInstructionNode))
            and (
                isinstance(self, (CommentNode, ProcessingInstructionNode))
                or hasattr(self, "__document__")
            )
        ):
            raise InvalidOperation(
                "Not all node types can be added as siblings to a root node."
            )


class _ChildLessNode(NodeBase):
    """Node types using this mixin also can't be root nodes of a document."""

    first_child = last_child = last_descendant = None

    def child_nodes(self, *filter: Filter, recurse: bool = False) -> Iterator[NodeBase]:
        """
        A :term:`generator iterator` that yields nothing.

        :meta category: iter-relatives
        """
        yield from []

    @property
    def depth(self) -> int:
        return cast(TagNode, self.parent).depth + 1

    @property
    def document(self) -> Optional["Document"]:
        parent = self.parent
        if parent is None:
            return None
        return parent.document

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


class _ElementWrappingNode(NodeBase):
    def __init__(self, etree_element: _Element, cache: _WrapperCache):
        super().__init__(wrapper_cache=cache)
        self._etree_obj = etree_element
        self._tail_node = TextNode(etree_element, position=TAIL, cache=cache)

    def __copy__(self) -> "_ElementWrappingNode":
        return self.clone(deep=False)

    def __deepcopy__(self, memodict=None) -> "_ElementWrappingNode":
        return self.clone(deep=True)

    def _add_next_node(self, node: "NodeBase"):
        if isinstance(node, _ElementWrappingNode):
            my_old_tail = self._tail_node

            if self._tail_node._exists:
                my_old_tail._bind_to_tail(node)
                self._etree_obj.tail = None
                self._etree_obj.addnext(node._etree_obj)
                self._tail_node = TextNode(self._etree_obj, TAIL, self._wrapper_cache)

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

    def _add_previous_node(self, node: NodeBase):
        previous = self.previous_node()

        if previous is None:

            if isinstance(node, _ElementWrappingNode):
                self._etree_obj.addprevious(node._etree_obj)

            else:
                assert isinstance(node, TextNode)
                parent = self.parent
                assert parent is not None
                if parent._data_node._exists:
                    last_text_candidate = parent._data_node
                    while last_text_candidate._appended_text_node is not None:
                        last_text_candidate = last_text_candidate._appended_text_node
                    last_text_candidate._add_next_node(node)
                else:
                    node._bind_to_data(parent)

        else:
            previous._add_next_node(node)

    def clone(self, deep: bool = False) -> "_ElementWrappingNode":
        etree_clone = copy(self._etree_obj)
        etree_clone.tail = None
        return _get_or_create_element_wrapper(etree_clone, self._wrapper_cache)

    @altered_default_filters()
    def detach(self, retain_child_nodes: bool = False) -> "_ElementWrappingNode":
        parent = self.parent

        if parent is None:
            return self

        etree_obj = self._etree_obj
        self._wrapper_cache = cache = copy(self._wrapper_cache)

        if self._tail_node._exists:

            if self.index == 0:
                self._tail_node._bind_to_data(parent)

            else:
                previous_node = self.previous_node()
                if isinstance(previous_node, _ElementWrappingNode):
                    self._tail_node._bind_to_tail(previous_node)
                elif isinstance(previous_node, TextNode):
                    previous_node._insert_text_node_as_next_appended(self._tail_node)
                else:
                    raise InvalidCodePath

            etree_obj.tail = None
            self._tail_node = TextNode(etree_obj, position=TAIL, cache=cache)

        cast(_Element, etree_obj.getparent()).remove(etree_obj)

        for child_node in self.child_nodes(recurse=True):
            child_node._wrapper_cache = cache

        _prune_wrapper_cache(parent)
        _prune_wrapper_cache(self)

        return self

    @property
    def full_text(self) -> str:
        return ""

    def next_node(self, *filter: Filter) -> Optional["NodeBase"]:

        candidate: NodeBase

        if self._tail_node._exists:
            candidate = self._tail_node
        else:
            next_etree_obj = self._etree_obj.getnext()

            if next_etree_obj is None:
                return None
            candidate = _get_or_create_element_wrapper(
                next_etree_obj, self._wrapper_cache
            )

        if all(f(candidate) for f in chain(default_filters[-1], filter)):
            return candidate
        else:
            return candidate.next_node(*filter)

    @property
    def parent(self) -> Optional["TagNode"]:
        etree_parent = self._etree_obj.getparent()
        if etree_parent is None:
            return None
        result = _get_or_create_element_wrapper(etree_parent, self._wrapper_cache)
        assert isinstance(result, TagNode)
        return result

    def previous_node(self, *filter: Filter) -> Optional["NodeBase"]:

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
            wrapper_of_previous = _get_or_create_element_wrapper(
                previous_etree_obj, self._wrapper_cache
            )

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
            return candidate.previous_node(*filter)


class CommentNode(_ChildLessNode, _ElementWrappingNode, NodeBase):
    """
    The instances of this class represent comment nodes of a tree.

    To instantiate new nodes use :func:`new_comment_node`.
    """

    __slots__ = ("_etree_obj", "_tail_node")

    def __eq__(self, other) -> bool:
        return isinstance(other, CommentNode) and self.content == other.content

    def __str__(self) -> str:
        return str(self._etree_obj)

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

    __slots__ = ("_etree_obj", "_tail_node")

    def __eq__(self, other) -> bool:
        return (
            isinstance(other, ProcessingInstructionNode)
            and self.target == other.target
            and self.content == other.content
        )

    def __str__(self) -> str:
        return str(self._etree_obj)

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

    __slots__ = ("_data_node", "__document__", "_etree_obj", "_tail_node")

    def __init__(self, etree_element: _Element, cache: _WrapperCache):
        super().__init__(etree_element, cache)
        self._data_node = TextNode(etree_element, position=DATA, cache=cache)

    def __contains__(self, item: Union[str, NodeBase]) -> bool:
        if isinstance(item, str):
            return item in self.attributes
        elif isinstance(item, NodeBase):
            for child in self.child_nodes(recurse=False):
                if child is item:
                    return True
            return False
        else:
            raise TypeError

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, TagNode):
            return False

        return (self.qualified_name == other.qualified_name) and (
            set(self.attributes.items()) == set(other.attributes.items())
        )

    # TODO remove flake8 exception soonish; the issue is fixed in pyflakes
    @overload
    def __getitem__(self, item: str) -> str:
        ...

    @overload
    def __getitem__(self, item: int) -> NodeBase:  # noqa: F811
        ...

    @overload
    def __getitem__(self, item: slice) -> List[NodeBase]:  # noqa: F811
        ...

    def __getitem__(self, item):  # noqa: F811
        if isinstance(item, str):
            return self._etree_obj.attrib[item]

        elif isinstance(item, int):
            if item < 0:
                item = len(self) + item

            index = 0
            for child_node in self.child_nodes(recurse=False):
                if index == item:
                    return child_node
                index += 1

            raise IndexError

        elif isinstance(item, slice):
            return list(self.child_nodes(recurse=False))[item]

        raise TypeError

    def __hash__(self) -> int:
        return hash(self._etree_obj)

    def __len__(self) -> int:
        i = 0
        for _ in self.child_nodes(recurse=False):
            i += 1
        return i

    def __str__(self) -> str:
        clone = self.clone(deep=True)
        clone.merge_text_nodes()
        return etree.tounicode(clone._etree_obj)

    def __repr__(self) -> str:
        return (
            f'<{self.__class__.__name__}("{self.qualified_name}", '
            f"{self.attributes}, {self.location_path}) [{hex(id(self))}]>"
        )

    def __add_first_child(self, node: NodeBase):
        assert not len(self)
        if isinstance(node, _ElementWrappingNode):
            self._etree_obj.append(node._etree_obj)
        elif isinstance(node, TextNode):
            node._bind_to_data(self)

    def append_child(self, *node: NodeSource, clone: bool = False):
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
            last_child.add_next(*queue, clone=clone)

    @property
    def attributes(self) -> ElementAttributes:
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
        >>> node.attributes.update({"bar": "2", "zong": "2"})
        >>> print(node)
        <node foo="1" peng="1" bar="2" zong="2"/>
        """
        return self._etree_obj.attrib

    def child_nodes(self, *filter: Filter, recurse: bool = False) -> Iterator[NodeBase]:

        current_node: Optional[NodeBase]

        assert isinstance(self._data_node, TextNode)
        if self._data_node._exists:
            current_node = self._data_node
        elif len(self._etree_obj):
            current_node = _get_or_create_element_wrapper(
                self._etree_obj[0], self._wrapper_cache
            )
        else:
            current_node = None

        while current_node is not None:

            assert isinstance(default_filters[-1], tuple), default_filters[-1]

            if all(f(current_node) for f in chain(default_filters[-1], filter)):
                yield current_node

            if recurse and isinstance(current_node, TagNode):
                yield from current_node.child_nodes(*filter, recurse=True)

            current_node = current_node.next_node()

    @altered_default_filters()
    def clone(self, deep: bool = False) -> "TagNode":
        # a faster implementation may be to not clear a cloned element's children and
        # to clone appended text nodes afterwards

        etree_clone = copy(self._etree_obj)
        etree_clone.text = etree_clone.tail = None
        del etree_clone[:]  # remove all subelements
        result = _get_or_create_element_wrapper(etree_clone, {})
        assert isinstance(result, TagNode)
        assert not len(result)

        if deep:
            for child_node in (
                x.clone(deep=True) for x in self.child_nodes(recurse=False)
            ):
                assert isinstance(child_node, NodeBase)
                assert child_node.parent is None
                if isinstance(child_node, _ElementWrappingNode):
                    assert child_node._etree_obj.tail is None
                elif isinstance(child_node, TextNode):
                    assert child_node._position is DETACHED

                result.append_child(child_node)
                assert child_node in result

        return result

    def _collapse_whitespace(self, normalize_space: str = "default"):
        normalize_space = cast(str, self.attributes.get(XML_ATT_SPACE, normalize_space))

        if normalize_space == "default":
            for child_node in self.child_nodes():
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

        for child_node in self.child_nodes(is_tag_node, recurse=False):
            cast(TagNode, child_node)._collapse_whitespace(normalize_space)

    def css_select(self, expression: str) -> "QueryResults":
        """
        Namespace prefixes are delimited with a ``|`` before a name test, for example
        ``div svg|metadata`` selects all descendants of ``div`` named nodes that belong
        to the default namespace or have no namespace and whose name is ``metadata``
        and have a namespace that is mapped to the ``svg`` prefix.

        :param expression: A CSS selector expression.
        :return: A list of matching :term:`tag node` s.

        :meta category: query-nodes
        """
        return self.xpath(_css_to_xpath(expression))

    @property
    def depth(self) -> int:
        return self.location_path.count("/")

    @altered_default_filters()
    def detach(self, retain_child_nodes: bool = False) -> "_ElementWrappingNode":
        parent = self.parent
        index = self.index

        if parent is None and getattr(self, "__document__", None):
            raise InvalidOperation("The root node of a document cannot be detached.")

        if retain_child_nodes and parent is None:
            raise InvalidOperation(
                "Child nodes can't be retained when the node to detach has no parent "
                "node."
            )

        result = super().detach()

        if retain_child_nodes:
            child_nodes = tuple(self.child_nodes())
            for node in child_nodes:
                node.detach()

            if child_nodes:
                assert isinstance(parent, TagNode)
                assert isinstance(index, int)
                parent.insert_child(index, *child_nodes)

        return result

    @property
    def document(self) -> Optional["Document"]:
        if self.parent is None:
            root_node = self
        else:
            root_node = cast(TagNode, last(self.ancestors()))
        return getattr(root_node, "__document__", None)

    @property
    def first_child(self) -> Optional[NodeBase]:
        for result in self.child_nodes(recurse=False):
            return result
        return None

    @property
    def full_text(self) -> str:
        return "".join(
            x.content  # type: ignore
            for x in self.child_nodes(is_text_node, recurse=True)
        )

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
            root = cast(TagNode, last(self.ancestors())) or self
            if root.css_select(f'*[xml|id="{value}"]'):
                raise InvalidOperation(
                    "An id with that value is already assigned in the tree."
                )
            self.attributes[XML_ATT_ID] = value
        else:
            raise TypeError("Value must be None or a string.")

    @property
    def index(self) -> Optional[int]:
        if self.parent is None:
            return None
        return super().index

    def insert_child(self, index: int, *node: NodeSource, clone: bool = False):
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
            raise ValueError

        children_count = len(self)

        if index > children_count:
            raise IndexError("The given index is beyond the target's size.")

        this, *queue = node

        if index == 0:
            if children_count:
                self[0].add_previous(this, clone=clone)
                if not (
                    clone
                    or isinstance(node[0], (str, _TagDefinition))
                    or isinstance(self[1], TextNode)
                ):
                    assert self[0] is this
                    assert self[1].previous_node() is this, self[1].previous_node()
                    assert isinstance(this, NodeBase)
                    assert this.next_node() is self[1]
            else:
                self.__add_first_child(
                    self._prepare_new_relative((this,), clone=clone)[0]
                )

        else:
            self[index - 1].add_next(this, clone=clone)

        if queue:
            self[index].add_next(*queue, clone=clone)

    @property
    def last_child(self) -> Optional[NodeBase]:
        result = None
        for result in self.child_nodes(recurse=False):
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
        steps = []

        node = self
        with altered_default_filters(is_tag_node):
            while node.parent is not None:
                index = node.index
                assert isinstance(index, int)
                steps.append(index + 1)
                node = node.parent

        return "." + "".join(f"/*[{i}]" for i in reversed(steps))

    @altered_default_filters()
    def merge_text_nodes(self):
        """
        Merges all consecutive text nodes in the subtree into one.
        """
        for node in self.child_nodes(is_text_node, recurse=True):
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

    @property
    def namespaces(self) -> Dict[str, str]:
        """
        The prefix to namespace :term:`mapping` of the node.
        """
        return cast(Dict[str, str], self._etree_obj.nsmap)

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
            self._etree_obj,
            definition.local_name,
            definition.attributes,
            self.namespace,
            definition.children,
        )

    @staticmethod
    def parse(
        text: AnyStr,
        parser: etree.XMLParser = DEFAULT_PARSER,
        collapse_whitespace: bool = False,
    ) -> "TagNode":
        """
        Parses the given string or bytes sequence into a new tree.

        :param text: A serialized XML tree.
        :param parser: The XML parser to use.
        :param collapse_whitespace: :meth:`Collapses the content's whitespace
                                    <delb.Document.collapse_whitespace>`.
        """
        result = _get_or_create_element_wrapper(
            etree.fromstring(text, parser=parser), {}
        )
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

    def prepend_child(self, *node: NodeBase, clone: bool = False) -> None:
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
        self.insert_child(0, *node, clone=clone)

    @property
    def qualified_name(self) -> str:
        """
        The node's qualified name.
        """
        return cast(str, self._etree_obj.tag)

    def xpath(self, expression: str) -> "QueryResults":
        """
        Returns all :term:`tag node` s that match the evaluation of an XPath expression.

        Mind to start any the expression with a ``.`` when the node you call it on is
        supposed to be the initial context node in the path evaluation.

        As this API is for a real programming language, the full XPath specification is
        not intended to be supported. For example, instead of querying attributes with
        an XPath expression, one must use a comprehension like:

        >>> [ x.attributes["target"] for x in root.xpath(".//foo")
        ...   if "target" in x.attributes ]  # doctest: +SKIP

        Instead of:

        >>> root.xpath(".//foo/@target")  # doctest: +SKIP

        Having that said, implementing retrieval of attributes may actually happen if
        there are convincing user stories. But other things like addressing processing
        instructions and higher level operations are out of scope.

        This method includes a workaround for a bug in XPath 1.0 that concerns its lack
        of default namespace support. It is extensively described in this lxml issue:
        https://github.com/lxml/lxml/pull/236

        :param expression: An XPath 1.0 location path.

        :meta category: query-nodes
        """

        etree_obj = self._etree_obj
        namespaces = etree_obj.nsmap
        compat_namespaces: etree._DictAnyStr
        xpath_expression = XPathExpression(expression)

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
            # TODO prepend self::node() if missing?

            last_step = location_path.location_steps[-1]

            if last_step.axis == "attribute":
                raise InvalidOperation(
                    "XPath expressions that point to attributes are not supported."
                )
            if last_step.node_test.type == "type_test":
                raise InvalidOperation(
                    "Other node tests than names tests are not supported for now. "
                    "If you require to retrieve other nodes than tag nodes, please "
                    "open an issue with a description of your use-case."
                )

            if has_default_namespace:
                for location_step in location_path.location_steps:
                    node_test = location_step.node_test
                    if node_test.type != "name_test":
                        continue
                    if ":" not in node_test.data:
                        node_test.data = prefix + ":" + node_test.data

        cache = self._wrapper_cache
        _results = etree_obj.xpath(str(xpath_expression), namespaces=compat_namespaces)
        if not (
            isinstance(_results, list)
            and all(isinstance(x, _Element) for x in _results)
        ):
            raise InvalidOperation(
                "Only XPath expressions that target tag nodes are supported."
            )
        return QueryResults(
            (
                _get_or_create_element_wrapper(cast(_Element, element), cache)
                for element in _results
            )
        )


class TextNode(_ChildLessNode, NodeBase):
    """
    TextNodes contain the textual data of a document.

    Instances expose all methods of :class:`str`:

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
        cache: Optional[_WrapperCache] = None,
    ):
        if cache is None:
            cache = {}
        super().__init__(cache)

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

    def __contains__(self, item) -> bool:
        return item in self.content

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, TextNode):
            return self.content == other.content
        elif isinstance(other, str):
            return self.content == other
        return False

    def __getattr__(self, item: str) -> Any:
        if item in STRINGMETHODS:
            return getattr(self.content, item)
        raise AttributeError(
            f"type object '{self.__class__.__name__}' has no " f"attribute '{item}'"
        )

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

    def __str__(self):
        return self.content

    def _add_next_node(self, node: NodeBase):
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
                head._bound_to.insert(0, node._etree_obj)
            elif head._position is TAIL:
                head_anchor = head._bound_to
                head_content = head.content

                head_anchor.addnext(node._etree_obj)

                head_anchor.tail = head_content
                node._etree_obj.tail = None

            if appended_text_node is not None:
                appended_text_node._bind_to_tail(node)

    def _add_previous_node(self, node: NodeBase):
        if isinstance(node, TextNode):
            self._prepend_text_node(node)

        elif isinstance(node, _ElementWrappingNode):

            if self._position is DATA:

                content = self.content
                current_bound = self._bound_to
                assert isinstance(current_bound, _Element)
                current_bound.insert(0, node._etree_obj)

                current_bound_wrapper = _get_or_create_element_wrapper(
                    current_bound, self._wrapper_cache
                )
                assert isinstance(current_bound_wrapper, TagNode)
                current_bound_wrapper._data_node = TextNode(
                    current_bound, DATA, self._wrapper_cache
                )
                self._bind_to_tail(node)
                current_bound.text = None
                self.content = content

            elif self._position is TAIL:

                assert isinstance(self._bound_to, _Element)
                _get_or_create_element_wrapper(
                    self._bound_to, self._wrapper_cache
                )._add_next_node(node)

            elif self._position is APPENDED:
                assert isinstance(self._bound_to, TextNode)
                self._bound_to._add_next_node(node)

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

    def clone(self, deep: bool = False) -> "NodeBase":
        assert self.content is not None
        return self.__class__(self.content, cache={})

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

                current_parent._data_node = TextNode(
                    current_parent._etree_obj, DATA, current_parent._wrapper_cache
                )
                assert self not in current_parent
                self._bound_to.text = None
                assert not current_parent._data_node._exists

        elif self._position is TAIL:

            current_bound = self._bound_to
            assert isinstance(current_bound, _Element)
            current_previous = _get_or_create_element_wrapper(
                current_bound, self._wrapper_cache
            )

            if text_sibling:
                text_sibling._bind_to_tail(current_previous)
            else:
                current_previous._tail_node = TextNode(
                    current_previous._etree_obj, TAIL, current_previous._wrapper_cache
                )
                current_bound.tail = None
                assert not current_previous._tail_node._exists

        elif self._position is APPENDED:

            assert isinstance(self._bound_to, TextNode)
            self._bound_to._appended_text_node = text_sibling
            if text_sibling:
                text_sibling._bound_to = self._bound_to
            self._appended_text_node = None

        else:
            raise ValueError(
                f"A TextNode._position must not be set to {self._position}"
            )

        self._bound_to = None
        self._wrapper_cache = {}
        self._position = DETACHED
        self.content = content

        assert self.parent is None
        assert self.next_node() is None

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

    def next_node(self, *filter: Filter) -> Optional["NodeBase"]:
        if self._position is DETACHED:
            return None

        candidate: Optional[NodeBase]

        if self._appended_text_node:
            candidate = self._appended_text_node

        elif self._position is DATA:

            assert isinstance(self._bound_to, _Element)
            if len(self._bound_to):
                candidate = _get_or_create_element_wrapper(
                    self._bound_to[0], self._wrapper_cache
                )
            else:
                return None

        elif self._position is TAIL:
            candidate = self.__next_candidate_of_tail()

        elif self._position is APPENDED:  # and last in tail sequence
            candidate = self.__next_candidate_of_last_appended()

        if candidate is None:
            return None

        if all(f(candidate) for f in chain(default_filters[-1], filter)):
            if isinstance(candidate, TextNode):
                assert candidate._exists
            return candidate
        else:
            return candidate.next_node(*filter)

    def __next_candidate_of_last_appended(self) -> Optional[NodeBase]:
        head = self._tail_sequence_head
        if head._position is DATA:
            if len(head.parent._etree_obj):
                return _get_or_create_element_wrapper(
                    head.parent._etree_obj[0], self._wrapper_cache
                )
            else:
                return None
        elif head._position is TAIL:
            next_etree_tag = head._bound_to.getnext()
            if next_etree_tag is None:
                return None
            else:
                return _get_or_create_element_wrapper(
                    next_etree_tag, self._wrapper_cache
                )

        raise InvalidCodePath

    def __next_candidate_of_tail(self) -> Optional[NodeBase]:
        assert isinstance(self._bound_to, _Element)
        next_etree_node = self._bound_to.getnext()
        if next_etree_node is None:
            return None
        return _get_or_create_element_wrapper(next_etree_node, self._wrapper_cache)

    @property
    def parent(self) -> Optional[TagNode]:
        if self._position is DATA:
            assert isinstance(self._bound_to, _Element)
            result = _get_or_create_element_wrapper(self._bound_to, self._wrapper_cache)
            assert isinstance(result, TagNode)
            return result

        elif self._position is TAIL:
            assert isinstance(self._bound_to, _Element)
            return _get_or_create_element_wrapper(
                self._bound_to, self._wrapper_cache
            ).parent

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
            parent = _get_or_create_element_wrapper(self._bound_to, self._wrapper_cache)
            assert isinstance(parent, TagNode)
            content = self.content
            node._bind_to_data(parent)
            node._insert_text_node_as_next_appended(self)
            self.content = content

        elif self._position is TAIL:

            assert isinstance(self._bound_to, _Element)
            left_sibling = _get_or_create_element_wrapper(
                self._bound_to, self._wrapper_cache
            )
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

    def previous_node(self, *filter: Filter) -> Optional["NodeBase"]:
        candidate: Optional[NodeBase]

        if self._position in (DATA, DETACHED):
            return None
        elif self._position is TAIL:
            assert isinstance(self._bound_to, _Element)
            candidate = _get_or_create_element_wrapper(
                self._bound_to, self._wrapper_cache
            )
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
            return candidate.previous_node(*filter)

    @property
    def _tail_sequence_head(self):
        if self._position in (DATA, TAIL):
            return self
        elif self._position is APPENDED:
            return self._bound_to._tail_sequence_head
        else:
            raise InvalidCodePath


# query results container


class QueryResults(Sequence[TagNode]):
    """
    A sequence with the results of a CSS or XPath query with some helpers for readable
    Python expressions.
    """

    def __init__(self, results: Iterator[_ElementWrappingNode]):
        self.__items = cast(Tuple[TagNode], tuple(results))

    def __getitem__(self, item):
        return self.__items[item]

    def __len__(self) -> int:
        return len(self.__items)

    def __repr__(self):
        return str([repr(x) for x in self.__items])

    def as_list(self) -> List[TagNode]:
        """The contained nodes as a new :class:`list`."""
        return list(self.__items)

    def as_set(self) -> Set[TagNode]:
        """The contained nodes as a new :class:`set`."""
        return set(self.__items)

    @property
    def as_tuple(self) -> Tuple[TagNode, ...]:
        """The contained nodes in a :class:`tuple`."""
        return self.__items

    def filtered_by(self, *filters: Filter) -> "QueryResults":
        """
        Returns another :class:`QueryResults` instance that contains all nodes filtered
        by the provided :term:`filter` s.
        """
        items = self.__items
        for filter in filters:
            items = (x for x in items if filter(x))  # type: ignore
        return self.__class__(items)  # type: ignore

    @property
    def first(self) -> Optional[TagNode]:
        """The first node from the results or ``None`` if there are none."""
        if len(self.__items):
            return self.__items[0]
        else:
            return None

    @property
    def last(self) -> Optional[TagNode]:
        """The last node from the results or ``None`` if there are none."""
        if len(self.__items):
            return self.__items[-1]
        else:
            return None

    @property
    def size(self) -> int:
        """The amount of contained nodes."""
        return len(self.__items)


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


def not_(filter: Filter) -> Filter:
    """
    A node filter wrapper that matches when the given filter is not matching,
    like a boolean ``not``.
    """

    def not_wrapper(node: NodeBase) -> bool:
        return not filter(node)

    return not_wrapper


#


__all__ = (
    CommentNode.__name__,
    NodeBase.__name__,
    ProcessingInstructionNode.__name__,
    QueryResults.__name__,
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
