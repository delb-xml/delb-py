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

if TYPE_CHECKING:
    from lxml_domesque import Document  # noqa: F401


Comment = etree.Comment
_Element = etree._Element
ElementAttributes = etree._Attrib
PI = etree.PI
QName = etree.QName


DETACHED, DATA, TAIL, APPENDED = 0, 1, 2, 3


class NodeBase(ABC):
    # the method is here to trick mypy
    def __init__(self, cache: _WrapperCache):  # pragma: no cover
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
    def clone(self, deep: bool = False, __cache__: _WrapperCache = None) -> "NodeBase":
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

        return TagNode(
            context.makeelement(tag, attrib=attributes, nsmap=nsmap), self._cache
        )

    def new_text_node(self, content: str = "") -> "TextNode":
        # also implemented in Document
        return TextNode(content, position=DETACHED)

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
            this = this.clone(deep=True, __cache__=self._cache)
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
            parent.insert_child(node, index=index, clone=clone)
            return self.detach()
        if what_a_silly_fuzz == 3:
            self.detach()
            parent.insert_child(node, index=index, clone=clone)
            return self

        raise InvalidCodePath


class TagNode(NodeBase):
    # TODO __slots__

    def __new__(
        cls, etree_element: _Element, cache: Optional[_WrapperCache] = None
    ) -> "TagNode":
        if cache is None:
            obj, cache = None, {}
        else:
            obj = cache.get(id(etree_element))

        if obj is None:
            cache[id(etree_element)] = obj = object.__new__(cls)

            # __init__
            obj._etree_obj = etree_element  # type: ignore
            obj._data_node = TextNode(
                etree_element, position=DATA, cache=cache
            )  # type: ignore
            obj._tail_node = TextNode(
                etree_element, position=TAIL, cache=cache
            )  # type: ignore
            obj._cache = cache

        return obj  # type: ignore

    # this only serves to declare properties' types
    def __init__(self, etree_element: _Element, _):
        self._etree_obj: _Element
        self._data_node: TextNode
        self._tail_node: TextNode
        self._cache: _WrapperCache

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
            self._cache.update(node._cache)
            node._cache = self._cache
            # cache
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
            if self._tail_node._exists:
                raise NotImplementedError
            else:
                self._etree_obj.addnext(node._etree_obj)

        elif isinstance(node, TextNode):
            assert node._position is DETACHED
            assert node._appended_text_node is None

            if self._tail_node._exists:
                raise NotImplementedError
            else:
                node._bind_to_tail(self)

        else:
            raise TypeError

    def add_previous(self, *node: Any, clone: bool = False):
        if self.parent is None:
            raise InvalidOperation("Can't add a sibling to a root node.")

        super().add_previous(*node, clone=clone)

    def _add_previous_node(self, node: NodeBase):
        if isinstance(node, TagNode):
            previous = self.previous_node()

            if previous is None:
                self._etree_obj.addprevious(node._etree_obj)

            elif isinstance(previous, TagNode):
                raise NotImplementedError

            else:  # isinstance(node, TextNode)
                raise NotImplementedError

        elif isinstance(node, TextNode):
            raise NotImplementedError

        else:
            raise InvalidCodePath

    def append_child(self, *node: Any, clone: bool = False):
        last_child = self.last_child

        queue: Sequence[Any]

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
            current_node = TagNode(self._etree_obj[0], self._cache)
        else:
            current_node = None

        while current_node is not None:

            if all(f(current_node) for f in filter):
                yield current_node

            if recurse and isinstance(current_node, TagNode):
                yield from current_node.child_nodes(*filter, recurse=True)

            current_node = current_node.next_node()

    def clone(self, deep: bool = False, __cache__: _WrapperCache = None) -> "TagNode":
        # a faster implementation may be to not clear a cloned element's children and
        # to clone appended text nodes afterwards

        cache = __cache__ or {}

        etree_clone = copy(self._etree_obj)
        etree_clone.text = etree_clone.tail = None
        del etree_clone[:]  # remove all subelements
        result = self.__class__(etree_clone, cache)
        assert not len(result)

        if deep:
            for child_node in (
                x.clone(deep=True, __cache__=cache)
                for x in self.child_nodes(recurse=False)
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

        return result

    def css_select(self, expression: str) -> Iterable["TagNode"]:
        raise NotImplementedError

    def detach(self) -> "TagNode":
        if self.parent is None:
            return self

        if self._tail_node._exists:
            raise NotImplementedError
        else:
            etree_obj = self._etree_obj
            cast(_Element, etree_obj.getparent()).remove(etree_obj)

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

    def insert_child(
        self, *node: NodeBase, index: int = 0, clone: bool = False
    ) -> None:
        # TODO merge caches if applicable
        raise NotImplementedError

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
                    next_etree_obj = next_etree_obj.getprevious()
                    if next_etree_obj is None or next_etree_obj.tag not in (
                        PI,
                        Comment,
                    ):
                        break

            if next_etree_obj is None:
                return None
            candidate = TagNode(next_etree_obj, self._cache)

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
        return TagNode(etree_parent, self._cache)

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

    def prepend_child(self, *node: NodeBase) -> None:
        self.insert_child(*node, index=0)

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

        wrapper_of_previous = TagNode(previous_etree_obj, self._cache)

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
        raise NotImplementedError


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
        self._bound_to: Union[None, _Element, TextNode]
        self.__content: Optional[str]

        self._appended_text_node: Optional[TextNode] = None
        self._cache = cache or {}
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
            self._append_text_node(node)

        elif isinstance(node, TagNode):

            if self._position is DATA:
                raise NotImplementedError

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
                raise NotImplementedError

            elif self._position is DETACHED:
                raise InvalidCodePath

    def _add_previous_node(self, node: NodeBase):
        if isinstance(node, TextNode):
            self._prepend_text_node(node)

        elif isinstance(node, TagNode):

            if self._position is DATA:
                raise NotImplementedError

            elif self._position is TAIL:
                raise NotImplementedError

            elif self._position is APPENDED:
                raise NotImplementedError

            else:
                raise InvalidCodePath

    def _append_text_node(self, node: "TextNode"):
        old = self._appended_text_node
        content = node.content
        node._bound_to = self
        node._cache = self._cache
        node._position = APPENDED
        node.content = content
        self._appended_text_node = node
        if old:
            assert old._position is APPENDED, old
            node._append_text_node(old)

        assert isinstance(self.content, str)
        assert isinstance(node.content, str)

    def _bind_to_data(self, target: TagNode):
        target._etree_obj.text = self.content
        target._data_node = self
        self._bound_to = target._etree_obj
        self._position = DATA
        self._cache = target._cache
        self.__content = None
        assert isinstance(self.content, str)

    def _bind_to_tail(self, target: TagNode):
        assert isinstance(target, TagNode)
        target._etree_obj.tail = self.content
        target._tail_node = self
        self._bound_to = target._etree_obj
        self._position = TAIL
        self._cache = target._cache
        self.__content = None
        assert isinstance(self.content, str)

    def clone(self, deep: bool = False, __cache__: _WrapperCache = None) -> "NodeBase":
        assert self.content is not None
        return self.__class__(self.content, cache=__cache__)

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
        elif self._position is DATA:
            raise NotImplementedError
        elif self._position is TAIL:
            raise NotImplementedError
        elif self._position is APPENDED:
            text_sibling = self._appended_text_node

            assert isinstance(self._bound_to, TextNode)
            self._bound_to._appended_text_node = text_sibling
            if text_sibling:
                text_sibling._bound_to = self._bound_to
            self._bound_to = self._appended_text_node = None

            self._position = DETACHED
        else:
            raise InvalidCodePath

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
                candidate = TagNode(self._bound_to[0], self._cache)
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
            return candidate.next_node(*filter)

    def __next_candidate_of_last_appended(self) -> Optional[NodeBase]:
        head = self._tail_sequence_head
        if head._position is DATA:
            if len(head.parent._etree_obj):
                return TagNode(head.parent._etree_obj[0], self._cache)
            else:
                return None
        elif head._position is TAIL:
            next_etree_tag = head._bound_to.getnext()
            if next_etree_tag is None:
                return None
            else:
                return TagNode(next_etree_tag, self._cache)

        raise InvalidCodePath

    def __next_candidate_of_tail(self) -> Optional[NodeBase]:
        assert isinstance(self._bound_to, _Element)
        next_etree_node = self._bound_to.getnext()
        if next_etree_node is None:
            return None
        return TagNode(next_etree_node, self._cache)

    def next_node_in_stream(self, name: Optional[str]) -> Optional["TagNode"]:
        """ Returns the next node in stream order that matches the given
            name. """
        raise NotImplementedError

    @property
    def parent(self) -> Optional[TagNode]:
        if self._position is DATA:
            assert isinstance(self._bound_to, _Element)
            return TagNode(self._bound_to, self._cache)

        elif self._position is TAIL:
            assert isinstance(self._bound_to, _Element)
            return TagNode(self._bound_to, self._cache).parent

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
            sibling = TagNode(self._bound_to, self._cache)
            content = self.content
            node._bind_to_data(sibling)
            node._append_text_node(self)
            self.content = content

        elif self._position is TAIL:

            assert isinstance(self._bound_to, _Element)
            sibling = TagNode(self._bound_to, self._cache)
            content = self.content
            node._bind_to_tail(sibling)
            node._append_text_node(self)
            self.content = content

        elif self._position is APPENDED:

            assert node._appended_text_node is None
            previous = self._bound_to
            assert isinstance(previous, TextNode)
            previous._appended_text_node = None
            previous._append_text_node(node)
            node._append_text_node(self)

        else:
            raise InvalidCodePath

    def previous_node(self, *filter: Filter) -> Optional["NodeBase"]:
        candidate: Optional[NodeBase]

        if self._position in (DATA, DETACHED):
            return None
        elif self._position is TAIL:
            assert isinstance(self._bound_to, _Element)
            candidate = TagNode(self._bound_to, self._cache)
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
