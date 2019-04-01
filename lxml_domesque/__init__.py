from pathlib import Path
from itertools import chain
from typing import Any, Dict, Iterable, List, Optional
from typing import IO as IOType

from lxml import etree

from lxml_domesque import utils
from lxml_domesque.caches import roots_of_documents
from lxml_domesque.exceptions import InvalidOperation
from lxml_domesque.loaders import configured_loaders, tag_node_loader
from lxml_domesque.nodes import (
    any_of,
    _get_or_create_element_wrapper,
    is_tag_node,
    is_text_node,
    not_,
    new_tag_node,
    NodeBase,
    TagNode,
    TextNode,
)
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

    def __init__(self, source: Any, parser: etree.XMLParser = DEFAULT_PARSER):
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

        self.__set_root(_get_or_create_element_wrapper(loaded_tree.getroot(), cache))

    def __contains__(self, node: NodeBase) -> bool:
        """ Tests whether a node is part of a document instance. """
        return node.document is self

    def __str__(self):
        clone = self.clone()
        clone.merge_text_nodes()
        return etree.tounicode(clone.root._etree_obj.getroottree())

    def cleanup_namespaces(
        self,
        namespaces: Optional["etree._NSMap"] = None,
        retain_prefixes: Optional[Iterable[str]] = None,
    ):
        etree.cleanup_namespaces(
            self.root._etree_obj, top_nsmap=namespaces, keep_ns_prefixes=retain_prefixes
        )

    def clone(self) -> "Document":
        return self.__class__(
            self.root, parser=self.root._etree_obj.getroottree().parser
        )

    def css_select(self, expression: str) -> List["TagNode"]:
        return self.root.css_select(expression)

    def merge_text_nodes(self):
        self.root.merge_text_nodes()

    @property
    def namespaces(self) -> Dict[str, str]:
        return self.root.namespaces

    def new_tag_node(
        self,
        local_name: str,
        attributes: Optional[Dict[str, str]] = None,
        namespace: Optional[str] = None,
    ) -> "TagNode":
        return self.root.new_tag_node(
            local_name=local_name, attributes=attributes, namespace=namespace
        )

    @property
    def root(self) -> "TagNode":
        """ The root node of a document instance. """
        return roots_of_documents[self]

    @root.setter
    def root(self, root: "TagNode"):
        if not all(
            x is None for x in (root.parent, root.previous_node(), root.next_node())
        ):
            raise InvalidOperation(
                "Only a detached node can be set as root. Use :meth:`TagNode.clone` or "
                ":meth:`TagNode.detach` on the designated root node."
            )

        utils.copy_heading_pis(self.root._etree_obj, root._etree_obj)
        self.__set_root(root)

    def __set_root(self, root: TagNode):
        self.__wrapper_cache = root._cache
        roots_of_documents[self] = root

    def save(self, path: Path, pretty=False):
        with path.open("bw") as file:
            self.write(file, pretty=pretty)

    def write(self, buffer: IOType, pretty: bool = False):
        self.root.merge_text_nodes()
        self.cleanup_namespaces()
        self.root._etree_obj.getroottree().write(
            file=buffer, encoding="utf-8", pretty_print=pretty, xml_declaration=True
        )

    def xpath(self, expression: str) -> List["TagNode"]:
        """ Returns the results of :meth:`TagNode.xpath` call on the instances'
            :attr:`Document.root`.

            :param expression: An XPath 1.0 location path.
        """

        return self.root.xpath(expression)

    def xslt(self, transformation: etree.XSLT) -> "Document":
        result = transformation(self.root._etree_obj.getroottree())
        return Document(result.getroot())


__all__ = (
    Document.__name__,
    InvalidOperation.__name__,
    TagNode.__name__,
    TextNode.__name__,
    any_of.__name__,
    is_tag_node.__name__,
    is_text_node.__name__,
    not_.__name__,
    new_tag_node.__name__,
)
