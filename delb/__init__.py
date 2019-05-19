# Copyright (C) 2019  Frank Sachsenheim
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

from collections.abc import Iterator, Sequence
from pathlib import Path
from itertools import chain
from typing import Any, Dict, Iterable, List, Optional
from typing import IO as IOType

from lxml import etree

from delb import utils
from delb.exceptions import InvalidOperation
from delb.loaders import configured_loaders, tag_node_loader
from delb.nodes import (
    altered_default_filters,
    any_of,
    _get_or_create_element_wrapper,
    is_comment_node,
    is_processing_instruction_node,
    is_root_node,
    is_tag_node,
    _is_tag_or_text_node,
    is_text_node,
    not_,
    new_comment_node,
    new_processing_instruction_node,
    new_tag_node,
    tag,
    CommentNode,
    NodeBase,
    ProcessingInstructionNode,
    TagNode,
    TextNode,
)
from delb.typing import _WrapperCache


# constants

# care has to be taken:
# https://wiki.tei-c.org/index.php/XML_Whitespace#Recommendations
# https://wiki.tei-c.org/index.php/XML_Whitespace#Default_Whitespace_Processing
# https://lxml.de/FAQ.html#why-doesn-t-the-pretty-print-option-reformat-my-xml-output
DEFAULT_PARSER = etree.XMLParser(remove_blank_text=True)


# api


def first(iterable: Iterable) -> Optional["NodeBase"]:
    """
    Returns the first item of the given iterable.
    Note that the first item is consumed when the iterable is an :term:`iterator`.
    """
    if isinstance(iterable, Iterator):
        try:
            return next(iterable)
        except StopIteration:
            return None
    elif isinstance(iterable, Sequence):
        return iterable[0] if len(iterable) else None
    else:
        raise TypeError


def register_namespace(prefix: str, namespace: str):
    """
    Registers a namespace prefix that newly created :class:`TagNode` instances in that
    namespace will use in serializations.

    The registry is global, and any existing mapping for either the given prefix or the
    namespace URI will be removed. It has however no effect on the serialization of
    existing nodes, see :meth:`Document.cleanup_namespace` for that.

    :param prefix: The prefix to register.
    :param namespace: The targeted namespace.
    """
    etree.register_namespace(prefix, namespace)


class Document:
    """
    This class is the entrypoint to obtain a representation of an XML encoded text
    document. For instantiation, any object can be passed. There must be a loader
    present in the :obj:`loaders.configured_loaders` list that is capable to return a
    parsed tree from that object. See :ref:`document-loaders` for the default loaders
    that come with this package. Have a look at the :mod:`loaders` module to figure out
    how to implement and configure other loaders.

    Nodes can be tested for membership in a document:

    >>> document = Document("<root>text</root>")
    >>> text_node = document.root[0]
    >>> text_node in document
    True
    >>> text_node.clone() in document
    False

    The string coercion of a document yields an XML encoded stream, but unlike
    :meth:`Document.save` and :meth:`Document.write` without an XML declaration:

    >>> document = Document("<root/>")
    >>> str(document)
    '<root/>'

    :param source: Anything that the configured loaders can make sense of to return a
                   parsed document tree.
    :param parser: An optional :class:`lxml.etree.XMLParser` instance that is used to
                   parse a document stream.
    """

    __slots__ = ("__root_node__",)

    def __init__(self, source: Any, parser: etree.XMLParser = DEFAULT_PARSER):
        loaded_tree: Optional[etree._ElementTree] = None
        wrapper_cache: Optional[_WrapperCache] = None
        for loader in chain((tag_node_loader,), configured_loaders):
            loaded_tree, wrapper_cache = loader(source, parser)
            if loaded_tree:
                break

        if loaded_tree is None or not isinstance(wrapper_cache, dict):
            raise ValueError(
                f"Couldn't load {source!r} with these currently configured loaders: "
                + ", ".join(x.__name__ for x in configured_loaders)
            )

        self.root = _get_or_create_element_wrapper(loaded_tree.getroot(), wrapper_cache)

    def __contains__(self, node: NodeBase) -> bool:
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
        """
        Consolidates the namespace declarations in a document by removing unused and
        redundant ones.

        There are currently some caveats due to lxml's implementations:
          - prefixes cannot be set for the default namespace
          - a namespace cannot be declared as default after a node's creation (where a
            namespace was specified that had been registered for a prefix with
            :func:`register_namespace`)
          - there's no way to unregister a prefix for a namespace
          - if there are other namespaces used as default namespaces (where a namespace
            was specified that had *not* been registered for a prefix) in the
            descendants of the root, their declarations are lost when this method is
            used

        To ensure clean serializations, one should:
          - register prefixes for all except the default namespace at the start of an
            application
          - use only one default namespace within a document

        :param namespaces: An optional :term:`mapping` of prefixes (keys) to namespaces
                           (values) that will be declared at the root element.
        :param retain_prefixes: An optional iterable that contains prefixes whose
                                declarations shall be kept despite not being used.
        """
        etree.cleanup_namespaces(
            self.root._etree_obj.getroottree(),
            top_nsmap=namespaces,
            keep_ns_prefixes=retain_prefixes,
        )

    def clone(self) -> "Document":
        """
        :return: Another instance w/ the duplicated contents.
        """
        return self.__class__(
            self.root, parser=self.root._etree_obj.getroottree().parser
        )

    def css_select(self, expression: str) -> List["TagNode"]:
        """
        This method proxies to the :meth:`TagNode.css_select` method of the document's
        root node.
        """
        return self.root.css_select(expression)

    def merge_text_nodes(self):
        """
        This method proxies to the :meth:`TagNode.merge_text_nodes` method of the
        document's root node.
        """
        self.root.merge_text_nodes()

    @property
    def namespaces(self) -> Dict[str, str]:
        """
        The namespace mapping of the document's root node.
        """
        return self.root.namespaces

    def new_tag_node(
        self,
        local_name: str,
        attributes: Optional[Dict[str, str]] = None,
        namespace: Optional[str] = None,
    ) -> "TagNode":
        """
        This method proxies to the :meth:`TagNode.new_tag_node` method of the
        document's root node.
        """
        return self.root.new_tag_node(
            local_name=local_name, attributes=attributes, namespace=namespace
        )

    @property
    def root(self) -> "TagNode":
        """ The root node of a document tree. """
        return getattr(self, "__root_node__")

    @root.setter
    def root(self, node: "TagNode"):
        if not isinstance(node, TagNode):
            raise TypeError("The document root node must be of 'TagNode' type.")

        with altered_default_filters(_is_tag_or_text_node):
            if not all(
                x is None for x in (node.parent, node.previous_node(), node.next_node())
            ):
                raise InvalidOperation(
                    "Only a detached node can be set as root. Use "
                    ":meth:`TagNode.clone` or :meth:`TagNode.detach` on the "
                    "designated root node."
                )

        current_root = getattr(self, "__root_node__", None)
        if current_root is not None:
            utils.copy_root_siblings(current_root._etree_obj, node._etree_obj)
            delattr(current_root, "__document__")

        setattr(node, "__document__", self)
        setattr(self, "__root_node__", node)

    def save(self, path: Path, pretty: bool = False, **cleanup_namespaces_args):
        """
        :param path: The path where the document shall be saved.
        :param pretty: Adds indentation for human consumers when ``True``.
        :param cleanup_namespaces_args: Arguments that are a passed to
                                        :meth:`Document.cleanup_namespaces` before
                                        saving.
        """
        with path.open("bw") as file:
            self.write(file, pretty=pretty, **cleanup_namespaces_args)

    def write(self, buffer: IOType, pretty: bool = False, **cleanup_namespaces_args):
        """
        :param buffer: An :term:`file-like object` that the document is written to.
        :param pretty: Adds indentation for human consumers when ``True``.
        :param cleanup_namespaces_args: Arguments that are a passed to
                                        :meth:`Document.cleanup_namespaces` before
                                        writing.
        """
        self.root.merge_text_nodes()
        self.cleanup_namespaces(**cleanup_namespaces_args)
        self.root._etree_obj.getroottree().write(
            file=buffer, encoding="utf-8", pretty_print=pretty, xml_declaration=True
        )

    def xpath(self, expression: str) -> List["TagNode"]:
        """
        This method proxies to the :meth:`TagNode.xpath` method of the document's root
        node.
        """

        return self.root.xpath(expression)

    def xslt(self, transformation: etree.XSLT) -> "Document":
        """
        :param transformation: A :class:`lxml.etree.XSLT` instance that shall be
                               applied to the document.
        :return: A new instance with the transformation's result.
        """
        result = transformation(self.root._etree_obj.getroottree())
        return Document(result.getroot())


__all__ = (
    CommentNode.__name__,
    Document.__name__,
    InvalidOperation.__name__,
    ProcessingInstructionNode.__name__,
    TagNode.__name__,
    TextNode.__name__,
    altered_default_filters.__name__,
    any_of.__name__,
    first.__name__,
    is_comment_node.__name__,
    is_processing_instruction_node.__name__,
    is_root_node.__name__,
    is_tag_node.__name__,
    is_text_node.__name__,
    not_.__name__,
    new_comment_node.__name__,
    new_tag_node.__name__,
    new_processing_instruction_node.__name__,
    register_namespace.__name__,
    tag.__name__,
)
