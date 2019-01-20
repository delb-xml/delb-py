from abc import abstractmethod, ABC
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Optional, Union
from typing import IO as IOType

from lxml import etree

from lxml_domesque.loaders import configured_loaders


# types

_DictAnyStr = Union[Dict[str, str], Dict[bytes, bytes]]
Filter = Callable[["NodeBase"], bool]


# constants

# care has to be taken:
# https://wiki.tei-c.org/index.php/XML_Whitespace#Recommendations
# https://wiki.tei-c.org/index.php/XML_Whitespace#Default_Whitespace_Processing
# https://lxml.de/FAQ.html#why-doesn-t-the-pretty-print-option-reformat-my-xml-output
DEFAULT_PARSER = etree.XMLParser(remove_blank_text=True)


# api


class Document:
    """ This class represents a complete XML document.
        TODO
    """

    def __init__(
        self,
        source: Union[str, Path, IOType, "TagNode", etree._ElementTree, etree._Element],
        parser: etree.XMLParser = DEFAULT_PARSER,
    ):
        # instance properties' types
        self._etree_obj: etree._ElementTree

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
        raise NotImplementedError

    def clone(self) -> "Document":
        return self.__class__(self.root.clone(deep=True))

    @property
    def root(self) -> "TagNode":
        return TagNode(self._etree_obj.getroot())

    def css_select(self, expression: str) -> Iterable["TagNode"]:
        raise NotImplementedError

    def merge_text_nodes(self):
        raise NotImplementedError

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
        return TextNode(content, position=DETATCHED)

    def save(self, path: Path, pretty=False):
        self._etree_obj.write(
            str(path.resolve()), encoding="utf-8", pretty_print=pretty
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
    @abstractmethod
    def add_next(self, *node: Union["NodeBase", str], clone: bool = False) -> None:
        raise NotImplementedError

    @abstractmethod
    def add_previous(self, *node: Union["NodeBase", str], clone: bool = False) -> None:
        raise NotImplementedError

    @abstractmethod
    def ancestors(self, *filter: Filter) -> Iterable["TagNode"]:
        """ Yields the ancestor nodes from bottom to top. """
        raise NotImplementedError

    @abstractmethod
    def clone(self, deep: bool = False) -> "NodeBase":
        raise NotImplementedError

    @property
    @abstractmethod
    def document(self) -> Optional[Document]:
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
        # also implemented in NodeBase
        return TextNode(content, position=DETATCHED)

    @abstractmethod
    def next_node(self, *filter: Filter) -> Optional["NodeBase"]:
        raise NotImplementedError

    @abstractmethod
    def next_node_in_stream(self, name: Optional[str]) -> Optional["NodeBase"]:
        """ Returns the next node in stream order that matches the given
            name. """
        raise NotImplementedError

    @abstractmethod
    def previous_node(self, *filter: Filter) -> Optional["NodeBase"]:
        raise NotImplementedError

    @abstractmethod
    def previous_node_in_stream(self, name: Optional[str]) -> Optional["TagNode"]:
        """ Returns the previous node in stream order that matches the given
            name. """
        raise NotImplementedError

    @abstractmethod
    def remove(self) -> None:
        raise NotImplementedError


class TagNode(NodeBase):
    def __init__(self):
        self._etree_obj: etree._Element

    def __contains__(self, item: Union[str, NodeBase]) -> bool:
        """ Tests whether the node has an attribute with given string or
            a given node is a descendant. """
        raise NotImplementedError

    def __eq__(self, other: Any) -> bool:
        raise NotImplementedError

    def __getitem__(self, item: str) -> str:
        return self._etree_obj.attrib[item]

    def __len__(self) -> int:
    def add_next(self, *node: Union["NodeBase", str], clone: bool = False):
        raise NotImplementedError

    def add_previous(self, *node: Union["NodeBase", str], clone: bool = False):
        raise NotImplementedError

    def ancestors(self, *filter: Filter):
        raise NotImplementedError

    def append_child(self, *node: NodeBase) -> None:
        raise NotImplementedError

    @property
    def attributes(self) -> etree._Attrib:
        return self._etree_obj.attrib

    def child_nodes(self, *filter: Filter, recurse: bool = False) -> Iterable[NodeBase]:
        raise NotImplementedError

    def clone(self, deep: bool = False) -> "TagNode":
        raise NotImplementedError

    def css_select(self, expression: str) -> Iterable["TagNode"]:
        raise NotImplementedError

    @property
    def first_child(self) -> NodeBase:
        raise NotImplementedError

    @property
    def full_text(self) -> str:
        return "".join(
            cast(TextNode, x).content
            for x in self.child_nodes(is_text_node, recurse=True)
        )

    @property
    def fully_qualified_name(self) -> str:
        return cast(str, etree.QName(self._etree_obj).text)

    @property
    def index(self):
        raise NotImplementedError

    def insert_child(self, *node: NodeBase, index: int = 0) -> None:
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
        raise NotImplementedError

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
        raise NotImplementedError

    def next_node_in_stream(self, name: Optional[str]) -> Optional["NodeBase"]:
        raise NotImplementedError

    @property
    def parent(self) -> Optional["TagNode"]:
        etree_parent = self._etree_obj.getparent()
        if etree_parent is None:
            return None
        return TagNode(etree_parent)

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

    def remove(self) -> None:
        raise NotImplementedError

    def replace_with(self, node: NodeBase, clone: bool = False) -> None:
        raise NotImplementedError

    def xpath(self, expression: str) -> Iterable["TagNode"]:
        raise NotImplementedError


class TextNode(NodeBase):
    """ This class also proxies all (?) methods that :class:`py:str`
        objects provide, including dunder-methods. """

    def add_next(self, *node: Union["NodeBase", str], clone: bool = False) -> None:
        raise NotImplementedError

    def add_previous(self, *node: Union["NodeBase", str], clone: bool = False) -> None:
        raise NotImplementedError

    def ancestors(self, *filter: Filter) -> Iterable["TagNode"]:
        """ Yields the ancestor nodes from bottom to top. """
        raise NotImplementedError

    def clone(self, deep: bool = False) -> "NodeBase":
        raise NotImplementedError

    @property
    def content(self) -> str:
        raise NotImplementedError

    @property
    def parent(self) -> TagNode:
        raise NotImplementedError


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
