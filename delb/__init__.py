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

from abc import ABC, abstractmethod
from collections.abc import MutableSequence
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, Iterable, Iterator, Optional, Tuple, Type, Union
from typing import IO as IOType

from lxml import etree

from _delb.exceptions import FailedDocumentLoading, InvalidOperation
from _delb.plugins import (
    core_loaders,
    DocumentMixinHooks,
    plugin_manager as _plugin_manager,
)
from _delb.nodes import (
    _get_or_create_element_wrapper,
    _is_tag_or_text_node,
    altered_default_filters,
    any_of,
    is_comment_node,
    is_processing_instruction_node,
    is_root_node,
    is_tag_node,
    is_text_node,
    not_,
    new_comment_node,
    new_processing_instruction_node,
    new_tag_node,
    tag,
    CommentNode,
    NodeBase,
    ProcessingInstructionNode,
    QueryResults,
    TagNode,
    TextNode,
)
from _delb.typing import Loader
from _delb.utils import (
    DEFAULT_PARSER,
    _collect_subclasses,
    _copy_root_siblings,
    first,
    get_traverser,
    last,
    register_namespace,
)


# plugin loading


_plugin_manager.load_plugins()


# api


class _RootSiblingsContainer(ABC, MutableSequence):
    def __init__(self, document: "Document"):
        self._document = document

    def __delitem__(self, index):
        # https://stackoverflow.com/q/54562097/
        raise InvalidOperation(
            "The thing is, lxml doesn't provide an interface to remove siblings of the "
            "root node."
        )

    def __getitem__(self, index):
        # TODO? slices

        if index < 0:
            index = len(self) + index

        if len(self) <= index:
            raise IndexError

        if index == 0:
            return self._get_first()

        with altered_default_filters():
            for i, result in enumerate(self._get_first().iterate_next_nodes(), start=1):
                if i == index:
                    return result

    def __setitem__(self, index, node):
        # https://stackoverflow.com/q/54562097/
        raise InvalidOperation(
            "The thing is, lxml doesn't provide an interface to remove siblings of the "
            "root node."
        )

    def __len__(self):
        index = -1
        for index, _ in enumerate(self._iter_all()):
            pass
        return index + 1

    def insert(self, index, node):
        length = len(self)

        if index == 0 and not length:
            self._add_first(node)
        elif index == length:
            self[-1].add_next(node)
        else:
            self[index].add_previous(node)

    def prepend(self, node):
        self.insert(0, node)

    @abstractmethod
    def _add_first(self, node: NodeBase):
        pass

    @abstractmethod
    def _get_first(self) -> Optional[NodeBase]:
        pass

    @abstractmethod
    def _iter_all(self) -> Iterator["NodeBase"]:
        pass


class _HeadNodes(_RootSiblingsContainer):
    def _add_first(self, node):
        self._document.root.add_previous(node)

    def _get_first(self):
        return last(self._iter_all())

    def _iter_all(self):
        with altered_default_filters():
            yield from self._document.root.iterate_previous_nodes()


class _TailNodes(_RootSiblingsContainer):
    def _add_first(self, node):
        self._document.root.add_next(node)

    def _get_first(self):
        return first(self._iter_all())

    def _iter_all(self):
        with altered_default_filters():
            yield from self._document.root.iterate_next_nodes()


class DocumentMeta(type):
    def __new__(mcs, name, base_classes, namespace):
        extension_classes = tuple(_plugin_manager.plugins.document_extensions)

        if not base_classes:  # Document class is being constructed
            extension_docs = sorted(
                (x.__name__, x.__doc__) for x in extension_classes if x.__doc__
            )
            if extension_docs:
                namespace["__doc__"] += "\n\n" + "\n\n".join(
                    (f"{x[0]}:\n\n{x[1]}" for x in extension_docs)
                )

        base_classes += extension_classes + (DocumentMixinHooks,)

        namespace["_loaders"] = (
            core_loaders.tag_node_loader,
            *_plugin_manager.plugins.loaders,
        )

        return super().__new__(mcs, name, base_classes, namespace)


class Document(metaclass=DocumentMeta):
    """
    This class is the entrypoint to obtain a representation of an XML encoded text
    document. For instantiation any object can be passed. A suitable loader must be
    available for the given source. See :ref:`document-loaders` for the default loaders
    that come with this package. Plugins are capable to alter the available loaders,
    see :doc:`extending`.

    Nodes can be tested for membership in a document:

    >>> document = Document("<root>text</root>")
    >>> text_node = document.root[0]
    >>> text_node in document
    True
    >>> text_node.clone() in document
    False

    The string coercion of a document yields an XML encoded stream, but unlike
    :meth:`Document.save` and :meth:`Document.write`, without an XML declaration:

    >>> document = Document("<root/>")
    >>> str(document)
    '<root/>'

    :param source: Anything that the configured loaders can make sense of to return a
                   parsed document tree.
    :param collapse_whitespace: :meth:`Collapses the content's whitespace
                                <delb.Document.collapse_whitespace>` after loading the
                                document.
    :param parser: An optional :class:`lxml.etree.XMLParser` instance that is used to
                   parse a document stream.
    :param klass: Explicitly define the initilized class. This can be useful for
                  applications that have :ref:`default document subclasses
                  <extending-subclasses>` in use.
    :param config: Additional keyword arguments for the configuration of extension
                   classes.
    """

    _loaders: Tuple[Loader, ...]
    __slots__ = ("__root_node__", "head_nodes", "source_url", "tail_nodes")

    def __new__(
        cls,
        source,
        collapse_whitespace=False,
        parser=DEFAULT_PARSER,
        klass=None,
        **config,
    ):
        config = cls.__process_config(collapse_whitespace, parser, config)
        root = cls.__load_source(source, config)

        if klass is None:
            subclasses = list()
            _collect_subclasses(cls, subclasses)

            for subclass in subclasses:
                if hasattr(subclass, "__class_test__") and subclass.__class_test__(
                    root, config
                ):
                    klass = subclass
                    break
            else:
                klass = cls

        assert issubclass(klass, Document)
        instance = super().__new__(klass)
        instance.config = config
        instance.root = root
        return instance

    def __init__(
        self,
        source: Any,
        collapse_whitespace: bool = False,
        parser: etree.XMLParser = DEFAULT_PARSER,
        klass: Optional[Type["Document"]] = None,
        **config,
    ):
        self.config: SimpleNamespace
        """
        Beside the used ``parser`` and ``collapsed_whitespace`` option, this property
        contains the namespaced data that extension classes and loaders may have stored.
        """
        if collapse_whitespace:
            self.collapse_whitespace()

        self.source_url: Optional[str] = self.config.__dict__.pop("source_url", None)
        """
        The source URL where a loader obtained the document's contents or ``None``.
        """
        self.head_nodes = _HeadNodes(self)
        """
        A list-like accessor to the nodes that precede the document's root node.
        Note that nodes can't be removed or replaced.
        """
        self.tail_nodes = _TailNodes(self)
        """
        A list-like accessor to the nodes that follow the document's root node.
        Note that nodes can't be removed or replaced.
        """

    @classmethod
    def __process_config(cls, collapse_whitespace, parser, kwargs) -> SimpleNamespace:
        config = SimpleNamespace(collapse_whitespace=collapse_whitespace, parser=parser)
        cls._init_config(config, kwargs)  # type: ignore
        return config

    @classmethod
    def __load_source(cls, source: Any, config: SimpleNamespace) -> TagNode:
        loader_excuses: Dict[Loader, Union[str, Exception]] = {}

        for loader in cls._loaders:
            try:
                loader_result = loader(source, config)
            except Exception as e:
                loader_excuses[loader] = e
            else:
                if isinstance(loader_result, tuple):
                    loaded_tree, wrapper_cache = loader_result
                    break
                else:
                    loader_excuses[loader] = loader_result
        else:
            raise FailedDocumentLoading(source, loader_excuses)

        assert isinstance(loaded_tree, etree._ElementTree)
        assert isinstance(wrapper_cache, dict)

        root = _get_or_create_element_wrapper(loaded_tree.getroot(), wrapper_cache)
        assert isinstance(root, TagNode)

        return root

    def __contains__(self, node: NodeBase) -> bool:
        return node.document is self

    def __str__(self):
        cloned_root = self.root.clone(deep=True)
        cloned_root.merge_text_nodes()
        _copy_root_siblings(self.root._etree_obj, cloned_root._etree_obj)
        return etree.tounicode(cloned_root._etree_obj.getroottree())

    def cleanup_namespaces(
        self,
        namespaces: Optional["etree._NSMap"] = None,
        retain_prefixes: Optional[Iterable[str]] = None,
    ):
        """
        Consolidates the namespace declarations in the document by removing unused and
        redundant ones.

        There are currently some caveats due to lxml/libxml2's implementations:
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
          - register prefixes for all namespaces except the default one at the start of
            an application
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
        :return: Another instance with the duplicated contents.
        """
        result = Document(self.root, klass=self.__class__)
        # lxml.etree.XMLParser instances aren't pickable / copyable
        parser = self.config.__dict__.pop("parser")
        result.config = deepcopy(self.config)
        self.config.parser = result.config.parser = parser
        return result

    def collapse_whitespace(self):
        """
        Collapses whitespace as described here:
        https://wiki.tei-c.org/index.php/XML_Whitespace#Recommendations

        Implicitly merges all neighbouring text nodes.
        """
        self.merge_text_nodes()
        with altered_default_filters():
            self.root._collapse_whitespace()

    def css_select(self, expression: str) -> QueryResults:
        """
        This method proxies to the :meth:`TagNode.css_select` method of the document's
        :attr:`root <Document.root>` node.
        """
        return self.root.css_select(expression)

    def merge_text_nodes(self):
        """
        This method proxies to the :meth:`TagNode.merge_text_nodes` method of the
        document's :attr:`root <Document.root>` node.
        """
        self.root.merge_text_nodes()

    @property
    def namespaces(self) -> Dict[str, str]:
        """
        The namespace mapping of the document's :attr:`root <Document.root>` node.
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
        """The root node of a document tree."""
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
            _copy_root_siblings(current_root._etree_obj, node._etree_obj)
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
        :param buffer: A :term:`file-like object` that the document is written to.
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

    def xpath(self, expression: str) -> QueryResults:
        """
        This method proxies to the :meth:`TagNode.xpath` method of the document's
        :attr:`root <Document.root>` node.
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
    ProcessingInstructionNode.__name__,
    QueryResults.__name__,
    TagNode.__name__,
    TextNode.__name__,
    altered_default_filters.__name__,
    any_of.__name__,
    first.__name__,
    get_traverser.__name__,
    is_comment_node.__name__,
    is_processing_instruction_node.__name__,
    is_root_node.__name__,
    is_tag_node.__name__,
    is_text_node.__name__,
    last.__name__,
    not_.__name__,
    new_comment_node.__name__,
    new_tag_node.__name__,
    new_processing_instruction_node.__name__,
    register_namespace.__name__,
    tag.__name__,
)
