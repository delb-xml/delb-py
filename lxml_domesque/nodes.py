from abc import abstractmethod, ABC
from copy import copy
from random import randrange
from typing import (
    TYPE_CHECKING,
    cast,
    overload,
    Any,
    Dict,
    Iterable,
    List,
    Optional,
    Sequence,
    Tuple,
    Union,
)

from lxml import etree

from lxml_domesque.caches import roots_of_documents
from lxml_domesque.exceptions import InvalidCodePath, InvalidOperation
from lxml_domesque.typing import _WrapperCache, Filter
from lxml_domesque.utils import random_unused_prefix
from lxml_domesque.xpath import LocationPath

if TYPE_CHECKING:
    from lxml_domesque import Document  # noqa: F401


Comment = etree.Comment
_Element = etree._Element
ElementAttributes = etree._Attrib
PI = etree.PI
QName = etree.QName


DETACHED, DATA, TAIL, APPENDED = 0, 1, 2, 3


def _get_or_create_element_wrapper(
    element: _Element, cache: _WrapperCache
) -> "TagNode":
    result = cache.get(id(element))
    if result is None:
        result = TagNode(element, cache)
        cache[id(element)] = result
    return result


def _prune_wrapper_cache(node: "TagNode"):
    if node.parent is None:
        root = node
    else:
        assert node.document is not None
        root = node.document.root
    cache = root._cache
    for key in set(cache) - {id(x) for x in root._etree_obj.iter()}:
        cache.pop(key)


class NodeBase(ABC):
    # the method is here to trick mypy
    def __init__(self, cache: _WrapperCache):
        self._cache = cache

    def add_next(self, *node: Any, clone: bool = False):
        if node:
            this, queue = self._prepare_new_relative(node, clone)
            self._add_next_node(this)
            if queue:
                this.add_next(*queue, clone=clone)

    @abstractmethod
    def _add_next_node(self, node: "NodeBase"):
        pass

    def add_previous(self, *node: Any, clone: bool = False):
        if node:
            this, queue = self._prepare_new_relative(node, clone)
            self._add_previous_node(this)
            if queue:
                this.add_previous(*queue, clone=clone)

    @abstractmethod
    def _add_previous_node(self, node: "NodeBase"):
        pass

    def ancestors(self, *filter: Filter) -> Iterable["TagNode"]:
        """ Yields the ancestor nodes from bottom to top. """
        parent = self.parent
        if parent:
            if all(f(parent) for f in filter):
                yield parent
            yield from parent.ancestors(*filter)

    @abstractmethod
    def clone(self, deep: bool = False) -> "NodeBase":
        pass

    @abstractmethod
    def detach(self) -> "NodeBase":
        pass

    @property
    @abstractmethod
    def document(self) -> Optional["Document"]:
        pass

    @property
    def index(self) -> Optional[int]:
        for index, node in enumerate(self.parent.child_nodes(recurse=False)):
            if node is self:
                return index
        raise InvalidCodePath

    @abstractmethod
    def new_tag_node(
        self,
        local_name: str,
        attributes: Optional[Dict[str, str]] = None,
        namespace: Optional[str] = None,
    ) -> "TagNode":
        pass

    def _new_tag_node_from(
        self,
        context: _Element,
        local_name: str,
        attributes: Optional[Dict[str, str]],
        namespace: Optional[str],
    ) -> "TagNode":
        # TODO docs: hint on etree.register_namespace

        tag: QName

        context_namespace = QName(context).namespace
        nsmap = context.nsmap

        if namespace:
            tag = QName(namespace, local_name)

        elif context_namespace:
            tag = QName(context_namespace, local_name)

        else:
            tag = QName(local_name)

        return _get_or_create_element_wrapper(
            context.makeelement(tag, attrib=attributes, nsmap=nsmap), self._cache
        )

    @abstractmethod
    def next_node(self, *filter: Filter) -> Optional["NodeBase"]:
        pass

    @abstractmethod
    def next_node_in_stream(self, name: Optional[str]) -> Optional["NodeBase"]:
        """ Returns the next node in stream order that matches the given
            name. """
        pass

    @property
    @abstractmethod
    def parent(self):
        pass

    def _prepare_new_relative(
        self, nodes: Tuple[Any, ...], clone: bool
    ) -> Tuple["NodeBase", List[Any]]:
        this, *queue = nodes
        if not isinstance(this, NodeBase):
            this = TextNode(str(this))
        elif clone:
            this = this.clone(deep=True)
        else:
            assert isinstance(this, NodeBase)

        if not all(
            x is None for x in (this.parent, this.next_node(), this.previous_node())
        ):
            raise InvalidOperation(
                "A node that shall be added to a tree must have neither a parent nor "
                "any sibling node. Use :meth:`NodeBase.detach` or a `clone` argument "
                "to move a node within or between trees."
            )

        self._cache.update(this._cache)
        this._cache = self._cache

        return this, queue

    @abstractmethod
    def previous_node(self, *filter: Filter) -> Optional["NodeBase"]:
        pass

    @abstractmethod
    def previous_node_in_stream(self, name: Optional[str]) -> Optional["TagNode"]:
        """ Returns the previous node in stream order that matches the given
            name. """
        pass

    def replace_with(self, node: "NodeBase", clone: bool = False) -> "NodeBase":
        what_a_silly_fuzz = randrange(0, 4)  # FUN FUN FUN

        if self.parent is None:
            raise InvalidOperation(
                "Cannot replace a root node of a tree. Maybe you want to set the "
                "`root` property of a Document instance?"
            )

        if what_a_silly_fuzz == 0:
            # TODO use this variant only when all code paths seem implemented
            self.add_next(node, clone=clone)
            return self.detach()
        elif what_a_silly_fuzz == 1:
            self.add_previous(node, clone=clone)
            return self.detach()

        parent, index = self.parent, self.index
        assert parent is not None

        if what_a_silly_fuzz == 2:
            parent.insert_child(index, node, clone=clone)
            return self.detach()
        if what_a_silly_fuzz == 3:
            self.detach()
            parent.insert_child(index, node, clone=clone)
            return self

        raise InvalidCodePath


class TagNode(NodeBase):
    # TODO __slots__

    def __init__(self, etree_element: _Element, cache: _WrapperCache):
        # TODO alternate signature
        super().__init__(cache=cache)
        self._etree_obj = etree_element
        self._data_node = TextNode(etree_element, position=DATA, cache=cache)
        self._tail_node = TextNode(etree_element, position=TAIL, cache=cache)

    def __contains__(self, item: Union[str, NodeBase]) -> bool:
        # TODO move docs
        """ Tests whether the node has an attribute with given string or
            a given node is a within its child nodes. """
        if isinstance(item, str):
            return item in self.attributes
        elif isinstance(item, NodeBase):
            for child in self.child_nodes(recurse=False):
                if child is item:
                    return True
            return False
        else:
            raise TypeError

    def __copy__(self) -> "TagNode":
        return self.clone(deep=False)

    def __deepcopy__(self, memodict=None):
        return self.clone(deep=True)

    def __eq__(self, other: Any) -> bool:
        # TODO docs
        if not isinstance(other, TagNode):
            raise TypeError

        return (self.qualified_name == other.qualified_name) and (
            set(self.attributes.items()) == set(other.attributes.items())
        )

    # TODO remove flake8 exception soonish; the issue is fixed in pyflakes
    @overload
    def __getitem__(self, item: str) -> str:
        ...

    @overload  # noqa: F811
    def __getitem__(self, item: int) -> NodeBase:
        ...

    def __getitem__(self, item):  # noqa: F811
        # TODO docs
        # TODO support reverse index lookup and slices

        if isinstance(item, str):
            return self._etree_obj.attrib[item]

        elif isinstance(item, int):
            if item < 0:
                raise ValueError("An index must be a non-negative number.")

            index = -1
            for child_node in self.child_nodes():
                index += 1
                if index == item:
                    return child_node

            raise IndexError

        raise TypeError

    def __len__(self) -> int:
        # TODO docs
        return len([x for x in self.child_nodes(recurse=False)])

    def __str__(self) -> str:
        attributes = " ".join(f"{k}={v}" for k, v in self._etree_obj.attrib.items())
        result = f"<{self.qualified_name}"
        if attributes:
            result += " " + attributes
        return result + ">"

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__}('{self.qualified_name}', "
            f" {self.attributes}) [{hex(id(self))}]>"
        )

    def __add_first_child(self, node: NodeBase):
        assert not len(self)
        if isinstance(node, TagNode):
            self._etree_obj.append(node._etree_obj)
        elif isinstance(node, TextNode):
            node._bind_to_data(self)
        else:
            raise InvalidCodePath

    def add_next(self, *node: Any, clone: bool = False):
        if self.parent is None:
            raise InvalidOperation("Can't add a sibling to a root node.")

        super().add_next(*node, clone=clone)

    def _add_next_node(self, node: "NodeBase"):
        if isinstance(node, TagNode):
            my_old_tail = self._tail_node

            if self._tail_node._exists:
                my_old_tail._bind_to_tail(node)
                self._etree_obj.tail = None
                self._etree_obj.addnext(node._etree_obj)
                self._tail_node = TextNode(self._etree_obj, TAIL, self._cache)

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

        else:
            raise TypeError

    def add_previous(self, *node: Any, clone: bool = False):
        if self.parent is None:
            raise InvalidOperation("Can't add a sibling to a root node.")

        super().add_previous(*node, clone=clone)

    def _add_previous_node(self, node: NodeBase):
        previous = self.previous_node()

        if previous is None:

            if isinstance(node, TagNode):
                self._etree_obj.addprevious(node._etree_obj)

            else:
                assert isinstance(node, TextNode)
                parent = self.parent
                assert parent is not None
                if parent._data_node._exists:
                    last_text_canidate = parent._data_node
                    while last_text_canidate._appended_text_node is not None:
                        last_text_canidate = last_text_canidate._appended_text_node
                    last_text_canidate._add_next_node(node)
                else:
                    node._bind_to_data(parent)

        else:
            previous._add_next_node(node)

    def append_child(self, *node: Any, clone: bool = False):
        if not node:
            return

        queue: Sequence[Any]

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
        return self._etree_obj.attrib

    def child_nodes(self, *filter: Filter, recurse: bool = False) -> Iterable[NodeBase]:

        current_node: Optional[NodeBase]

        assert isinstance(self._data_node, TextNode)
        if self._data_node._exists:
            current_node = self._data_node
        elif len(self._etree_obj):
            current_node = _get_or_create_element_wrapper(
                self._etree_obj[0], self._cache
            )
        else:
            current_node = None

        while current_node is not None:

            if all(f(current_node) for f in filter):
                yield current_node

            if recurse and isinstance(current_node, TagNode):
                yield from current_node.child_nodes(*filter, recurse=True)

            current_node = current_node.next_node()

    def clone(self, deep: bool = False) -> "TagNode":
        # a faster implementation may be to not clear a cloned element's children and
        # to clone appended text nodes afterwards

        etree_clone = copy(self._etree_obj)
        etree_clone.text = etree_clone.tail = None
        del etree_clone[:]  # remove all subelements
        result = _get_or_create_element_wrapper(etree_clone, {})
        assert not len(result)

        if deep:
            for child_node in (
                x.clone(deep=True) for x in self.child_nodes(recurse=False)
            ):
                assert isinstance(child_node, NodeBase)
                assert child_node.parent is None
                if isinstance(child_node, TagNode):
                    assert child_node._etree_obj.tail is None
                elif isinstance(child_node, TextNode):
                    assert child_node._position is DETACHED
                else:
                    raise InvalidCodePath

                result.append_child(child_node)
                assert child_node in result

        return result

    def css_select(self, expression: str) -> Iterable["TagNode"]:
        raise NotImplementedError

    def detach(self) -> "TagNode":
        parent = self.parent

        if parent is None:
            return self

        if self._tail_node._exists:
            self._tail_node._bind_to_data(parent)

        etree_obj = self._etree_obj
        cast(_Element, etree_obj.getparent()).remove(etree_obj)

        self._cache = cache = copy(self._cache)
        for child_node in self.child_nodes(recurse=True):
            child_node._cache = cache

        _prune_wrapper_cache(parent)
        _prune_wrapper_cache(self)

        return self

    @property
    def document(self) -> Optional["Document"]:
        if self.parent is None:
            self_root = self
        else:
            self_root = next(self.ancestors(lambda x: x.parent is None))  # type: ignore
        for document, root in roots_of_documents.items():
            if root is self_root:
                return document
        return None

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
    def index(self) -> Optional[int]:
        if self.parent is None:
            return None  # TODO meditate over 0 as alternative
        return super().index

    def insert_child(self, index: int, *node: NodeBase, clone: bool = False):
        if index < 0:
            raise ValueError

        if index > len(self):
            raise InvalidOperation("The given index is beyond the target's size.")

        this, *queue = node

        if index == 0:
            if len(self):
                self[0].add_previous(this, clone=clone)
                if isinstance(this, TagNode):
                    assert self[1].previous_node() is this
                    assert this.next_node() is self[1]
            else:
                self.__add_first_child(this)

        else:
            self[index - 1].add_next(this, clone=False)

        if queue:
            this.add_next(*queue, clone=clone)

    @property
    def last_child(self) -> Optional[NodeBase]:
        result = None
        for result in self.child_nodes(recurse=False):
            pass
        return result

    @property
    def local_name(self) -> str:
        return cast(str, QName(self._etree_obj).localname)

    @local_name.setter
    def local_name(self, value: str):
        namespace = self.namespace
        if namespace:
            self._etree_obj.tag = QName(self.namespace, value)
        else:
            self._etree_obj.tag = value

    @property
    def location_path(self):
        raise NotImplementedError

    def merge_text_nodes(self):
        for node in self.child_nodes(is_text_node, recurse=True):
            node._merge_appended_text_nodes()

    @property
    def namespace(self) -> str:
        return cast(str, QName(self._etree_obj).namespace)

    @namespace.setter
    def namespace(self, value: str) -> None:
        self._etree_obj.tag = QName(value, self.local_name)

    @property
    def namespaces(self) -> Dict[str, str]:
        return cast(Dict[str, str], self._etree_obj.nsmap)

    def next_node(self, *filter: Filter) -> Optional["NodeBase"]:

        candidate: NodeBase

        if self._tail_node._exists:
            candidate = self._tail_node
        else:
            next_etree_obj = self._etree_obj.getnext()

            # TODO handle Comments' and PIs' tails properly
            if next_etree_obj is not None and next_etree_obj.tag in (PI, Comment):
                while True:
                    next_etree_obj = next_etree_obj.getnext()
                    if next_etree_obj is None or next_etree_obj.tag not in (
                        PI,
                        Comment,
                    ):
                        break

            if next_etree_obj is None:
                return None
            candidate = _get_or_create_element_wrapper(next_etree_obj, self._cache)

        if all(f(candidate) for f in filter):
            return candidate
        else:
            return candidate.next_node(*filter)

    def next_node_in_stream(self, name: Optional[str]) -> Optional["NodeBase"]:
        raise NotImplementedError

    def new_tag_node(
        self,
        local_name: str,
        attributes: Optional[Dict[str, str]] = None,
        namespace: Optional[str] = None,
    ) -> "TagNode":
        return self._new_tag_node_from(
            self._etree_obj, local_name, attributes, namespace
        )

    @property
    def parent(self) -> Optional["TagNode"]:
        etree_parent = self._etree_obj.getparent()
        if etree_parent is None:
            return None
        return _get_or_create_element_wrapper(etree_parent, self._cache)

    @property
    def prefix(self) -> Optional[str]:
        target = QName(self._etree_obj).namespace
        assert isinstance(target, str)
        for prefix, namespace in self._etree_obj.nsmap.items():
            assert isinstance(prefix, str) or prefix is None
            assert isinstance(namespace, str)
            if namespace == target:
                return prefix
        raise InvalidCodePath

    @prefix.setter
    def prefix(self, prefix: str):
        raise NotImplementedError

    def prepend_child(self, *node: NodeBase, clone: bool = False) -> None:
        self.insert_child(0, *node, clone=clone)

    def previous_node(self, *filter: Filter) -> Optional["NodeBase"]:

        candidate: Optional[NodeBase]

        previous_etree_obj = self._etree_obj.getprevious()

        # TODO handle Comments' and PIs' tails properly
        if previous_etree_obj is not None and previous_etree_obj.tag in (PI, Comment):
            while True:
                previous_etree_obj = previous_etree_obj.getprevious()
                if previous_etree_obj is None or previous_etree_obj.tag not in (
                    PI,
                    Comment,
                ):
                    break

        if previous_etree_obj is None:
            return None

        wrapper_of_previous = _get_or_create_element_wrapper(
            previous_etree_obj, self._cache
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

        if all(f(candidate) for f in filter):
            return candidate
        else:
            return candidate.previous_node(*filter)

    def previous_node_in_stream(self, name: Optional[str]) -> Optional["TagNode"]:
        """ Returns the previous node in stream order that matches the given
            name. """
        raise NotImplementedError

    @property
    def qualified_name(self) -> str:
        return cast(str, QName(self._etree_obj).text)

    def xpath(self, expression: str) -> Iterable["TagNode"]:
        """ Yields all :class:`TagNode` instances that match the evaluation of an XPath
            expression.

            Mind to start any the expression with a ``.`` when the node you call it on
            is supposed to be the initial context node in the path evaluation.

            As this API is for a real programming language, the full XPath
            specification is not intended to be supported. For example, instead of
            querying attributes with an XPath expression, one must use a comprehension
            like:

            >>> [ x.attributes["target"] for x in root.xpath(".//foo")
            ...   if "target" in x.attributes ]

            Instead of:

            >>> root.xpath(".//foo/@target")

            Having that said, implementing retrieval of attributes may actually happen
            if there are convincing user stories. But other things like addressing
            processing instructions and higher level operations are out of scope.

            This method includes a workaround for a bug in XPath 1.0 that concerns
            its lack of default namespace support. It is extensively described in this
            lxml issue: https://github.com/lxml/lxml/pull/236

            :param expression: An XPath 1.0 location path.
        """

        location_path = LocationPath(expression)
        # TODO prepend self::node() if missing?

        last_step = location_path.location_steps[-1]

        if last_step.axis == "attribute":
            raise InvalidOperation(
                "XPath expressions that point to attributes are not supported. "
                "You are advised to use a Python comprehension expression, e.g.: "
                "[x['target'] for x in node.xpath('.//foo') if 'target' in "
                "x.attributes]"
            )
        if last_step.node_test.type == "type_test":
            raise InvalidOperation(
                "Other node tests than names tests are not supported for now. "
                "If you require to retrieve other nodes than tag nodes, please open "
                "an issue with a description of your use-case."
            )

        etree_obj = self._etree_obj
        namespaces = etree_obj.nsmap

        if None in namespaces:
            prefix = random_unused_prefix(namespaces)
            namespaces = {  # type: ignore
                **namespaces,  # type: ignore
                prefix: namespaces[None],
            }
            namespaces.pop(None)

            for location_step in location_path.location_steps:
                node_test = location_step.node_test
                if node_test.type != "name_test":
                    continue
                if ":" not in node_test.data:
                    node_test.data = prefix + ":" + node_test.data

        for element in etree_obj.xpath(  # type: ignore
            str(location_path), namespaces=namespaces
        ):
            yield _get_or_create_element_wrapper(element, self._cache)


class TextNode(NodeBase):
    """ This class also proxies all (?) methods that :class:`py:str`
        objects provide, including dunder-methods. """

    def __init__(
        self,
        reference_or_text: Union[_Element, str, "TextNode"],
        position: int = DETACHED,
        cache: Optional[_WrapperCache] = None,
    ):
        # TODO __slots__
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

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, TextNode):
            return self.content == other.content
        elif isinstance(other, str):
            return self.content == other
        raise TypeError

    def __repr__(self):
        if self._exists:
            return (
                f"<{self.__class__.__name__}(text='{self.content}', "
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

        elif isinstance(node, TagNode):
            self._add_next_tag_node(node)

    def _add_next_tag_node(self, node: TagNode):

        if self._position is DATA:
            assert isinstance(self._bound_to, _Element)
            self._bound_to.insert(0, node._etree_obj)

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
                raise NotImplementedError

        elif self._position is APPENDED:

            if self._appended_text_node is None:
                head = self._tail_sequence_head
                if head._position is DATA:
                    head._bound_to.insert(0, node._etree_obj)
                elif head._position is TAIL:
                    head_anchor = head._bound_to
                    head_content = head.content

                    head_anchor.addnext(node._etree_obj)

                    head_anchor.tail = head_content
                    node._etree_obj.tail = None

                else:
                    raise InvalidCodePath

            else:
                raise NotImplementedError

        elif self._position is DETACHED:
            raise InvalidCodePath

    def _add_previous_node(self, node: NodeBase):
        if isinstance(node, TextNode):
            self._prepend_text_node(node)

        elif isinstance(node, TagNode):

            if self._position is DATA:

                content = self.content
                current_bound = self._bound_to
                assert isinstance(current_bound, _Element)
                current_bound.insert(0, node._etree_obj)

                _get_or_create_element_wrapper(
                    current_bound, self._cache
                )._data_node = TextNode(current_bound, DATA, self._cache)
                self._bind_to_tail(node)
                current_bound.text = None
                self.content = content

            elif self._position is TAIL:

                assert isinstance(self._bound_to, _Element)
                _get_or_create_element_wrapper(
                    self._bound_to, self._cache
                )._add_next_node(node)

            elif self._position is APPENDED:
                raise NotImplementedError

            else:
                raise InvalidCodePath

    def _bind_to_data(self, target: TagNode):
        target._etree_obj.text = self.content
        target._data_node = self
        self._bound_to = target._etree_obj
        self._position = DATA
        self.__content = None
        assert isinstance(self.content, str)

    def _bind_to_tail(self, target: TagNode):
        assert isinstance(target, TagNode)
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
    def content(self) -> Optional[str]:
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
            raise InvalidCodePath

    @content.setter
    def content(self, text: Any):
        if not isinstance(text, str):
            text = str(text)

        if self._position is DATA:
            assert isinstance(self._bound_to, _Element)
            self._bound_to.text = text or None

        elif self._position is TAIL:
            assert isinstance(self._bound_to, _Element)
            self._bound_to.tail = text or None

        elif self._position in (APPENDED, DETACHED):
            assert self._bound_to is None or isinstance(self._bound_to, TextNode)
            self.__content = text

    def detach(self) -> "TextNode":

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
                    current_parent._etree_obj, DATA, current_parent._cache
                )
                assert self not in current_parent
                self._bound_to.text = None
                assert not current_parent._data_node._exists

        elif self._position is TAIL:

            current_bound = self._bound_to
            assert isinstance(current_bound, _Element)
            current_previous = _get_or_create_element_wrapper(
                current_bound, self._cache
            )

            if text_sibling:
                text_sibling._bind_to_tail(current_previous)
            else:
                current_previous._tail_node = TextNode(
                    current_previous._etree_obj, TAIL, current_previous._cache
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
            raise InvalidCodePath

        self._bound_to = None
        self._cache = {}
        self._position = DETACHED
        self.content = content

        assert self.parent is None
        assert self.next_node() is None

        return self

    @property
    def document(self) -> Optional["Document"]:
        parent = self.parent
        if parent is None:
            return None
        return parent.document

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

    def new_tag_node(
        self,
        local_name: str,
        attributes: Optional[Dict[str, str]] = None,
        namespace: Optional[str] = None,
    ) -> "TagNode":
        raise NotImplementedError

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
                    self._bound_to[0], self._cache
                )
            else:
                return None

        elif self._position is TAIL:
            candidate = self.__next_candidate_of_tail()

        elif self._position is APPENDED:  # and last in tail sequence
            candidate = self.__next_candidate_of_last_appended()

        if candidate is None:
            return None

        if all(f(candidate) for f in filter):
            if isinstance(candidate, TextNode):
                assert candidate._exists
            return candidate
        else:
            # FIXME?
            raise RuntimeError(  # pragma: no cover
                "I'm here to inform you that an expected code path has actually been "
                "reached."
            )
            # eg in test_nodes::test_siblings_filter
            return candidate.next_node(*filter)  # pragma: no cover

    def __next_candidate_of_last_appended(self) -> Optional[NodeBase]:
        head = self._tail_sequence_head
        if head._position is DATA:
            if len(head.parent._etree_obj):
                return _get_or_create_element_wrapper(
                    head.parent._etree_obj[0], self._cache
                )
            else:
                return None
        elif head._position is TAIL:
            next_etree_tag = head._bound_to.getnext()
            if next_etree_tag is None:
                return None
            else:
                return _get_or_create_element_wrapper(next_etree_tag, self._cache)

        raise InvalidCodePath

    def __next_candidate_of_tail(self) -> Optional[NodeBase]:
        assert isinstance(self._bound_to, _Element)
        next_etree_node = self._bound_to.getnext()
        if next_etree_node is None:
            return None
        return _get_or_create_element_wrapper(next_etree_node, self._cache)

    def next_node_in_stream(self, name: Optional[str]) -> Optional["TagNode"]:
        """ Returns the next node in stream order that matches the given
            name. """
        raise NotImplementedError

    @property
    def parent(self) -> Optional[TagNode]:
        if self._position is DATA:
            assert isinstance(self._bound_to, _Element)
            return _get_or_create_element_wrapper(self._bound_to, self._cache)

        elif self._position is TAIL:
            assert isinstance(self._bound_to, _Element)
            return _get_or_create_element_wrapper(self._bound_to, self._cache).parent

        elif self._position is APPENDED:
            assert isinstance(self._bound_to, TextNode)
            return self._tail_sequence_head.parent

        elif self._position is DETACHED:
            assert self._bound_to is None
            return None

        raise InvalidCodePath

    def _prepend_text_node(self, node: "TextNode"):
        if self._position is DATA:

            assert isinstance(self._bound_to, _Element)
            sibling = _get_or_create_element_wrapper(self._bound_to, self._cache)
            content = self.content
            node._bind_to_data(sibling)
            node._insert_text_node_as_next_appended(self)
            self.content = content

        elif self._position is TAIL:

            assert isinstance(self._bound_to, _Element)
            sibling = _get_or_create_element_wrapper(self._bound_to, self._cache)
            content = self.content
            node._bind_to_tail(sibling)
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
            raise InvalidCodePath

    def previous_node(self, *filter: Filter) -> Optional["NodeBase"]:
        candidate: Optional[NodeBase]

        if self._position in (DATA, DETACHED):
            return None
        elif self._position is TAIL:
            assert isinstance(self._bound_to, _Element)
            candidate = _get_or_create_element_wrapper(self._bound_to, self._cache)
        elif self._position is APPENDED:
            assert isinstance(self._bound_to, TextNode)
            candidate = self._bound_to
        else:
            raise InvalidCodePath

        if candidate is None:
            return None

        if all(f(candidate) for f in filter):
            return candidate
        else:
            return candidate.previous_node(*filter)

    def previous_node_in_stream(self, name: Optional[str]) -> Optional["TagNode"]:
        """ Returns the previous node in stream order that matches the given
            name. """
        raise NotImplementedError

    @property
    def _tail_sequence_head(self):
        if self._position in (DATA, TAIL):
            return self
        elif self._position is APPENDED:
            return self._bound_to._tail_sequence_head
        else:
            raise InvalidCodePath


# contributed filters and filter wrappers


def any_of(filters: Iterable[Filter]) -> Filter:
    def wrapper(node: NodeBase) -> bool:
        return any(x(node) for x in filters)

    return wrapper


def is_tag_node(node: NodeBase) -> bool:
    return isinstance(node, TagNode)


def is_text_node(node: NodeBase) -> bool:
    return isinstance(node, TextNode)


def not_(filter: Filter) -> Filter:
    def wrapper(node: NodeBase) -> bool:
        return not filter(node)

    return wrapper


__all__ = (
    TagNode.__name__,
    TextNode.__name__,
    any_of.__name__,
    is_tag_node.__name__,
    is_text_node.__name__,
    not_.__name__,
)
