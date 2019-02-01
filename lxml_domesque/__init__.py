from pathlib import Path
from itertools import chain
from typing import Dict, Iterable, Optional, Union
from typing import IO as IOType

from lxml import etree

from lxml_domesque import utils
from lxml_domesque.loaders import configured_loaders, tag_node_loader
from lxml_domesque.nodes import any_of, is_tag_node, is_text_node, not_
from lxml_domesque.nodes import DETACHED, NodeBase, TagNode, TextNode
from lxml_domesque.typing import _WrapperCache


# constants

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

        # document loading
        loaded_tree: Optional[etree._ElementTree] = None
        cache: Optional[_WrapperCache] = None
        for loader in chain((tag_node_loader,), configured_loaders):
            loaded_tree, cache = loader(source, parser)
            if loaded_tree:
                break

        if loaded_tree is None or not isinstance(cache, dict):
            raise ValueError(
                f"Couldn't load {source!r} with these currently configured loaders: "
                + ", ".join(x.__name__ for x in configured_loaders)
            )

        # instance properties
        self._etree_obj: etree._ElementTree = loaded_tree
        self.__wrapper_cache: _WrapperCache = cache

    def __contains__(self, node: NodeBase) -> bool:
        """ Tests whether a node is part of a document instance. """
        raise NotImplementedError

    def __str__(self):
        clone = self.clone()
        clone.merge_text_nodes()
        return etree.tounicode(clone._etree_obj)

    def cleanup_namespaces(self, namespaces: "etree._NSMap"):
        raise NotImplementedError

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
        return self.root.new_tag_node(
            local_name=local_name, attributes=attributes, namespace=namespace
        )

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


__all__ = (
    Document.__name__,
    TagNode.__name__,
    TextNode.__name__,
    any_of.__name__,
    is_tag_node.__name__,
    is_text_node.__name__,
    not_.__name__,
)
