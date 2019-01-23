from abc import abstractmethod, ABC
from copy import copy
from pathlib import Path
from typing import (
    cast,
    overload,
    Any,
    Callable,
    Dict,
    Iterable,
    Optional,
    Sequence,
    Union,
)
from typing import IO as IOType

from lxml import etree

from lxml_domesque import utils
from lxml_domesque.loaders import configured_loaders


# types

Filter = Callable[["NodeBase"], bool]
_WrapperCache = Dict[int, "TagNode"]


# constants

DETACHED, DATA, TAIL, APPENDED = 0, 1, 2, 3
# care has to be taken:
# https://wiki.tei-c.org/index.php/XML_Whitespace#Recommendations
# https://wiki.tei-c.org/index.php/XML_Whitespace#Default_Whitespace_Processing
# https://lxml.de/FAQ.html#why-doesn-t-the-pretty-print-option-reformat-my-xml-output
DEFAULT_PARSER = etree.XMLParser(remove_blank_text=True)


# api


class Document:
    """ This class represents an XML document.
        TODO
    """

    def __init__(
        self,
        source: Union[str, Path, IOType, "TagNode", etree._ElementTree, etree._Element],
        parser: etree.XMLParser = DEFAULT_PARSER,
    ):
        # TODO __slots__
        # instance properties
        self.__wrapper_cache: Dict[int, "TagNode"] = {}
        self._etree_obj: etree._ElementTree

        # as practicality beats purity, for now
        if isinstance(source, TagNode):
            self._etree_obj = etree.ElementTree(parser=parser)
            self.root = source.clone(deep=True)
            utils.copy_heading_pis(source._etree_obj, self.root._etree_obj)
            return

        # document loading
        loaded_tree: Optional[etree._ElementTree] = None
        for loader in configured_loaders:
            loaded_tree = loader(source, parser)
            if loaded_tree:
                break
        if loaded_tree is None:
            raise ValueError(
                f"Couldn't load {source!r} with these currently configured loaders: "
                + ", ".join(x.__name__ for x in configured_loaders)
            )
        self._etree_obj = loaded_tree

    def __contains__(self, node: "NodeBase") -> bool:
        """ Tests whether a node is part of a document instance. """
        raise NotImplementedError

    def __str__(self):
        clone = self.clone()
        clone.merge_text_nodes()
        return etree.tounicode(clone._etree_obj)

    def clone(self) -> "Document":
        return self.__class__(self.root, parser=self._etree_obj.parser)

    def css_select(self, expression: str) -> Iterable["TagNode"]:
        raise NotImplementedError

    def merge_text_nodes(self):
        self.root.merge_text_nodes()

    @property
    def namespaces(self) -> "etree._NSMap":
        return self._etree_obj.getroot().nsmap

    def new_tag_node(
        self,
        local_name: str,
        attributes: Optional[Dict[str, str]] = None,
        prefix: Optional[str] = None,
        namespace: Optional[str] = None,
    ) -> "TagNode":
        raise NotImplementedError

    def new_text_node(self, content: str = "") -> "TextNode":
        # also implemented in NodeBase
        return TextNode(content, position=DETACHED, cache=self.__wrapper_cache)

    def _prune_cache(self):
        cache = self.__wrapper_cache
        for key in set(cache) - {id(x) for x in self.root._etree_obj.iter()}:
            cache.pop(key)

    @property
    def root(self) -> "TagNode":
        return TagNode(self._etree_obj.getroot(), self.__wrapper_cache)

    @root.setter
    def root(self, root: "TagNode"):
        old_etree_root = self._etree_obj.getroot()
        new_etree_root = root._etree_obj

        assert new_etree_root.getprevious() is None

        new_etree_root.tail = None
        if old_etree_root is not None:
            utils.copy_heading_pis(self._etree_obj.getroot(), new_etree_root)

        self._etree_obj._setroot(new_etree_root)
        self.__wrapper_cache = root._cache

    def save(self, path: Path, pretty=False):
        self._etree_obj.write(
            str(path.resolve()),
            encoding="utf-8",
            pretty_print=pretty,
            xml_declaration=True,
        )

    def write(self, buffer: IOType):
        raise NotImplementedError

    def xpath(self, expression: str) -> Iterable["TagNode"]:
        """ This method includes a workaround for a bug in XPath 1.0 that
            concerns default namespaces. It is extensively described in
            `this lxml issue`_.

            .. this lxml issue: https://github.com/lxml/lxml/pull/236 """
        raise NotImplementedError

    def xslt(self, transformation: etree.XSLT) -> "Document":
        # TODO cache xslt object and use it directly
        result = self._etree_obj.xslt(transformation)
        return Document(result.getroot())


class NodeBase(ABC):
    def __init__(self, cache: _WrapperCache):
        self._cache = cache

    def add_next(self, *node: Any, clone: bool = False):
        if not node:
            return

        head, *tail = node
        if not isinstance(head, NodeBase):
            head = TextNode(str(head))
        elif clone:
            head = head.clone(deep=True, __cache__=self._cache)

        # TODO? head.detach()
        assert head.parent is None
        assert head.next_node() is None
        # assert head.previous_node() is None

        self._add_next_node(head)
        if tail:
            head.add_next(*tail, clone=clone)

    @abstractmethod
    def _add_next_node(self, node: "NodeBase"):
        pass

    @abstractmethod
    def add_previous(self, *node: Union["NodeBase", str], clone: bool = False) -> None:
        raise NotImplementedError

    @abstractmethod
    def ancestors(self, *filter: Filter) -> Iterable["TagNode"]:
        """ Yields the ancestor nodes from bottom to top. """
        raise NotImplementedError

    @abstractmethod
    def clone(self, deep: bool = False, __cache__: _WrapperCache = None) -> "NodeBase":
        pass

    @abstractmethod
    def detach(self) -> "NodeBase":
        pass

    @property
    @abstractmethod
    def document(self) -> Optional[Document]:
        # TODO wasn't there a bug where a node may return a root though it has been
        #      detached from a tree?
        raise NotImplementedError

    @property
    @abstractmethod
    def index(self) -> int:
        pass

    def new_tag_node(
        self,
        local_name: str,
        attributes: Optional[Dict[str, str]] = None,
        prefix: Optional[str] = None,
        namespace: Optional[str] = None,
    ) -> "TagNode":
        raise NotImplementedError

    def new_text_node(self, content: str = "") -> "TextNode":
        # also implemented in Document
        return TextNode(content, position=DETACHED)

    @abstractmethod
    def next_node(self, *filter: Filter) -> Optional["NodeBase"]:
        raise NotImplementedError

    @abstractmethod
    def next_node_in_stream(self, name: Optional[str]) -> Optional["NodeBase"]:
        """ Returns the next node in stream order that matches the given
            name. """
        raise NotImplementedError

    @property
    @abstractmethod
    def parent(self):
        pass

    @abstractmethod
    def previous_node(self, *filter: Filter) -> Optional["NodeBase"]:
        raise NotImplementedError

    @abstractmethod
    def previous_node_in_stream(self, name: Optional[str]) -> Optional["TagNode"]:
        """ Returns the previous node in stream order that matches the given
            name. """
        raise NotImplementedError


class TagNode(NodeBase):
    # TODO __slots__

    def __new__(
        cls, etree_element: etree._Element, cache: Optional[_WrapperCache] = None
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
    def __init__(self, etree_element: etree._Element, _):
        self._etree_obj: etree._Element
        self._data_node: TextNode
        self._tail_node: TextNode
        self._cache: _WrapperCache

    def __contains__(self, item: Union[str, NodeBase]) -> bool:
        """ Tests whether the node has an attribute with given string or
            a given node is a descendant. """
        raise NotImplementedError

    def __copy__(self) -> "TagNode":
        return self.clone(deep=False)

    def __deepcopy__(self, memodict=None):
        return self.clone(deep=True)

    def __eq__(self, other: Any) -> bool:
        raise NotImplementedError

    # TODO remove flake8 exception soon; the issue is fixed in pyflakes
    @overload
    def __getitem__(self, item: str) -> str:
        ...

    @overload  # noqa: F811
    def __getitem__(self, item: int) -> NodeBase:
        ...

    def __getitem__(self, item):  # noqa: F811

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
            raise RuntimeError

    def add_next(self, *node: Any, clone: bool = False):
        if self.parent is None:
            # TODO proper Exception
            raise RuntimeError

        super().add_next(*node, clone=clone)

    def _add_next_node(self, node: "NodeBase"):
        if isinstance(node, TagNode):
            raise NotImplementedError

        elif isinstance(node, TextNode):
            assert node._position is DETACHED
            assert node._appended_text_node is None

            if self._tail_node._exists:
                raise NotImplementedError
            else:
                node._bind_to_tail(self)

        else:
            raise TypeError

    def add_previous(self, *node: Union["NodeBase", str], clone: bool = False):
        raise NotImplementedError

    def ancestors(self, *filter: Filter):
        raise NotImplementedError

    def append_child(self, *node: Any, clone: bool = False):
        last_child = self.last_child

        tail: Sequence[Any]

        if last_child is None:
            head, *tail = node

            if not isinstance(head, NodeBase):
                last_child = TextNode(str(head))
            elif clone:
                last_child = head.clone(deep=True)
            else:
                last_child = head

            self.__add_first_child(last_child)

        else:
            tail = node

        last_child.add_next(*tail, clone=clone)

    @property
    def attributes(self) -> etree._Attrib:
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
                yield from current_node.child_nodes(*filter, recurse=recurse)

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
                    raise AssertionError

                result.append_child(child_node)

        return result

    def css_select(self, expression: str) -> Iterable["TagNode"]:
        raise NotImplementedError

    def detach(self) -> "TagNode":
        raise NotImplementedError

    @property
    def document(self) -> Optional[Document]:
        raise NotImplementedError

    @property
    def first_child(self) -> Optional[NodeBase]:
        for result in self.child_nodes(recurse=False):
            return result
        return None

    @property
    def full_text(self) -> str:
        return "".join(
            cast(TextNode, x).content
            for x in self.child_nodes(is_text_node, recurse=True)
        )

    @property
    def index(self):
        raise NotImplementedError

    def insert_child(self, *node: NodeBase, index: int = 0) -> None:
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
        return cast(str, etree.QName(self._etree_obj).localname)

    @local_name.setter
    def local_name(self, value: str) -> None:
        self._etree_obj.tag = etree.QName(self.namespace, value)

    def merge_text_nodes(self):
        for node in self.child_nodes(is_text_node, recurse=True):
            node._merge_appended_text_nodes()

    @property
    def namespace(self) -> str:
        return cast(str, etree.QName(self._etree_obj).namespace)

    @namespace.setter
    def namespace(self, value: str) -> None:
        self._etree_obj.tag = etree.QName(value, self.local_name)

    @property
    def namespaces(self) -> Dict[str, str]:
        return cast(Dict[str, str], self._etree_obj.nsmap)

    def next_node(self, *filter: Filter) -> Optional["NodeBase"]:

        candidate: NodeBase

        if self._tail_node._exists:
            candidate = self._tail_node
        else:
            next_etree_obj = self._etree_obj.getnext()
            if next_etree_obj is None:
                return None
            candidate = TagNode(next_etree_obj, self._cache)

        if all(f(candidate) for f in filter):
            return candidate
        else:
            return candidate.next_node(*filter)

    def next_node_in_stream(self, name: Optional[str]) -> Optional["NodeBase"]:
        raise NotImplementedError

    @property
    def parent(self) -> Optional["TagNode"]:
        etree_parent = self._etree_obj.getparent()
        if etree_parent is None:
            return None
        return TagNode(etree_parent, self._cache)

    @property
    def prefix(self) -> Optional[str]:
        # mypy 0.650 throws weird errors here
        target = etree.QName(self._etree_obj).namespace
        assert isinstance(target, str)
        for prefix, namespace in self._etree_obj.nsmap:  # type: ignore
            assert isinstance(prefix, str) or prefix is None
            assert isinstance(namespace, str)
            if namespace == target:
                return prefix
        raise RuntimeError("Reached unreachable code.")

    def prepend_child(self, *node: NodeBase) -> None:
        self.insert_child(*node, index=0)

    def previous_node(self, *filter: Filter) -> Optional["NodeBase"]:
        raise NotImplementedError

    def previous_node_in_stream(self, name: Optional[str]) -> Optional["TagNode"]:
        """ Returns the previous node in stream order that matches the given
            name. """
        raise NotImplementedError

    @property
    def qualified_name(self) -> str:
        return cast(str, etree.QName(self._etree_obj).text)

    def replace_with(self, node: NodeBase, clone: bool = False) -> None:
        raise NotImplementedError

    def xpath(self, expression: str) -> Iterable["TagNode"]:
        raise NotImplementedError


class TextNode(NodeBase):
    """ This class also proxies all (?) methods that :class:`py:str`
        objects provide, including dunder-methods. """

    def __init__(
        self,
        reference_or_text: Union[etree._Element, str, "TextNode"],
        position: int = DETACHED,
        cache: Optional[_WrapperCache] = None,
    ):
        # TODO __slots__
        self._appended_text_node: Optional[TextNode] = None
        self._bound_to: Union[None, etree._Element, TextNode]
        self._cache = cache or {}  # REMOVE?!
        self.__content: Optional[str]
        self._position: int = position

        if position is DETACHED:
            self._appended_text_node = None
            self._bound_to = None
            self.__content = cast(str, reference_or_text)

        elif position in (DATA, TAIL):
            assert isinstance(reference_or_text, etree._Element)
            self._bound_to = reference_or_text  # TODO rather bind to the wrapper?
            self.__content = None

        else:
            raise ValueError

    def __repr__(self):
        return (
            f"<{self.__class__.__name__}(text='{self.content}', "
            f"pos={self._position}) [{hex(id(self))}]>"
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
                text_sibling = self._appended_text_node

                self._appended_text_node = None
                cast(etree._Element, self._bound_to).addnext(node._etree_obj)

                assert node._etree_obj.tail is None

                if text_sibling is not None:
                    node._etree_obj.tail = text_sibling.content
                    node._tail_node._appended_text_node = (
                        text_sibling._appended_text_node
                    )

            elif self._position is APPENDED:
                raise NotImplementedError

            elif self._position is DETACHED:
                raise RuntimeError

    def add_previous(self, *node: Union["NodeBase", str], clone: bool = False) -> None:
        raise NotImplementedError

    def ancestors(self, *filter: Filter) -> Iterable["TagNode"]:
        """ Yields the ancestor nodes from bottom to top. """
        raise NotImplementedError

    def _append_text_node(self, node: "TextNode"):
        # TODO leverage that both objects are gc-safe due to the mutual binding?
        #      and hence discard TextNode._cache
        assert node.parent is None
        old = self._appended_text_node
        node._bound_to = self
        node._position = APPENDED
        self._appended_text_node = node
        if old:
            node._append_text_node(old)

    def _bind_to_data(self, target: TagNode):
        target._etree_obj.text = self.content
        target._data_node = self
        self._bound_to = target._etree_obj
        self._position = DATA
        self._cache = target._cache

    def _bind_to_tail(self, target: TagNode):
        assert isinstance(target, TagNode)

        target._etree_obj.tail = self.content
        target._tail_node = self

        self._bound_to = target._etree_obj
        self._position = TAIL
        self._cache = target._cache
        self.__content = None

    def clone(self, deep: bool = False, __cache__: _WrapperCache = None) -> "NodeBase":
        return self.__class__(self.content, cache=__cache__)

    @property
    def content(self) -> str:
        if self._position is DATA:
            assert isinstance(self._bound_to, etree._Element)
            return cast(str, cast(etree._Element, self._bound_to).text) or ""

        elif self._position is TAIL:
            assert isinstance(self._bound_to, etree._Element)
            return cast(str, cast(etree._Element, self._bound_to).tail) or ""

        elif self._position in (APPENDED, DETACHED):
            assert self._bound_to is None or isinstance(self._bound_to, TextNode)
            return cast(str, self.__content)

        else:
            raise RuntimeError

    @content.setter
    def content(self, text: Any):
        if not isinstance(text, str):
            text = str(text)

        if self._position is DATA:
            assert isinstance(self._bound_to, etree._Element)
            cast(etree._Element, self._bound_to).text = text or None

        elif self._position is TAIL:
            assert isinstance(self._bound_to, etree._Element)
            cast(etree._Element, self._bound_to).tail = text or None

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

            cast(TextNode, self._bound_to)._appended_text_node = text_sibling
            if text_sibling:
                text_sibling._bound_to = self._bound_to
            self._bound_to = None

            self._position = DETACHED
        else:
            raise ValueError

        return self

    @property
    def document(self) -> Optional[Document]:
        # TODO wasn't there a bug where a node may return a root though it has been
        #      detached from a tree?
        raise NotImplementedError

    @property
    def _exists(self) -> bool:
        if self._position is DATA:
            assert isinstance(self._bound_to, etree._Element)
            return cast(etree._Element, self._bound_to).text is not None
        elif self._position is TAIL:
            assert isinstance(self._bound_to, etree._Element)
            return cast(etree._Element, self._bound_to).tail is not None
        else:
            return True

    @property
    def index(self) -> int:
        raise NotImplementedError

    def _merge_appended_text_nodes(self):
        sibling = self._appended_text_node
        if sibling is None:
            return

        current_node, appendix = sibling, ""
        while current_node is not None:
            appendix += current_node.content
            current_node = current_node._appended_text_node

        self.content += appendix
        self._appended_text_node = None
        sibling._bound_to = None

    def new_tag_node(
        self,
        local_name: str,
        attributes: Optional[Dict[str, str]] = None,
        prefix: Optional[str] = None,
        namespace: Optional[str] = None,
    ) -> "TagNode":
        raise NotImplementedError

    def new_text_node(self, content: str = "") -> "TextNode":
        # also implemented in NodeBase
        return TextNode(content, position=DETACHED)

    def next_node(self, *filter: Filter) -> Optional["NodeBase"]:
        if self._position is DETACHED:
            return None

        candidate: Optional[NodeBase]

        if self._appended_text_node:
            candidate = self._appended_text_node

        elif self._position is DATA:

            assert isinstance(self._bound_to, etree._Element)
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

        raise RuntimeError

    def __next_candidate_of_tail(self) -> Optional[NodeBase]:
        next_etree_node = cast(etree._Element, self._bound_to).getnext()
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
            assert isinstance(self._bound_to, etree._Element)
            return TagNode(cast(etree._Element, self._bound_to), self._cache)

        elif self._position is TAIL:
            return TagNode(cast(etree._Element, self._bound_to), self._cache).parent

        elif self._position is APPENDED:
            assert isinstance(self._bound_to, TextNode)
            return cast(TextNode, self._bound_to).parent

        elif self._position is DETACHED:
            assert self._bound_to is None
            return None

        raise RuntimeError

    def previous_node(self, *filter: Filter) -> Optional["NodeBase"]:
        raise NotImplementedError

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
            raise RuntimeError


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
    Document.__name__,
    TagNode.__name__,
    TextNode.__name__,
    any_of.__name__,
    is_tag_node.__name__,
    is_text_node.__name__,
    not_.__name__,
)
