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

from abc import ABC, abstractmethod
from collections.abc import Iterator, MutableSequence, Sequence
from copy import deepcopy
from io import TextIOWrapper
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, BinaryIO, Optional
from warnings import warn

from lxml import etree

from _delb.exceptions import FailedDocumentLoading, InvalidOperation
from _delb.plugins import (
    core_loaders,
    plugin_manager as _plugin_manager,
    DocumentMixinBase,
)
from _delb.names import Namespaces
from _delb.nodes import (
    _is_tag_or_text_node,
    _wrapper_cache,
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
    DefaultStringOptions,
    NodeBase,
    ProcessingInstructionNode,
    TagNode,
    TextBufferSerializer,
    TextNode,
)
from _delb.parser import ParserOptions
from _delb.utils import (
    _copy_root_siblings,
    first,
    get_traverser,
    last,
)
from _delb.xpath import QueryResults
from delb.utils import compare_trees

if TYPE_CHECKING:
    from pathlib import Path

    from _delb.typing import Loader, NamespaceDeclarations

# plugin loading


_plugin_manager.load_plugins()


# api


class _RootSiblingsContainer(ABC, MutableSequence):
    __slots__ = ("_document",)

    def __init__(self, document: Document):
        self._document = document

    def __delitem__(self, index):
        # https://stackoverflow.com/q/54562097/
        raise InvalidOperation(
            "The thing is, lxml doesn't provide an interface to remove siblings of the "
            "root node."
        )

    def __eq__(self, other):
        return (
            isinstance(other, Sequence)
            and len(self) == len(other)
            and all(a == b for a, b in zip(iter(self), iter(other)))
        )

    def __getitem__(self, index):
        # TODO? slices

        if index < 0:
            index = len(self) + index

        if len(self) <= index:
            raise IndexError("Node index out of range.")

        if index == 0:
            return self._get_first()

        with altered_default_filters():
            for i, result in enumerate(
                self._get_first().iterate_following_siblings(), start=1
            ):
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
            self[-1].add_following_siblings(node)
        else:
            self[index].add_preceding_siblings(node)

    def prepend(self, node):
        self.insert(0, node)

    @abstractmethod
    def _add_first(self, node: NodeBase):
        pass

    @abstractmethod
    def _get_first(self) -> Optional[NodeBase]:
        pass

    @abstractmethod
    def _iter_all(self) -> Iterator[NodeBase]:
        pass


class _HeadNodes(_RootSiblingsContainer):
    def _add_first(self, node):
        self._document.root.add_preceding_siblings(node)

    def _get_first(self):
        return last(self._iter_all())

    def _iter_all(self):
        with altered_default_filters():
            yield from self._document.root.iterate_preceding_siblings()


class _TailNodes(_RootSiblingsContainer):
    def _add_first(self, node):
        self._document.root.add_following_siblings(node)

    def _get_first(self):
        return first(self._iter_all())

    def _iter_all(self):
        with altered_default_filters():
            yield from self._document.root.iterate_following_siblings()


class DocumentMeta(type):
    def __new__(mcls, name, base_classes, namespace):  # noqa: N804
        extension_classes = tuple(_plugin_manager.document_mixins)

        if not base_classes:  # Document class is being constructed
            extension_docs = sorted(
                (x.__name__, x.__doc__) for x in extension_classes if x.__doc__
            )
            if extension_docs:
                namespace["__doc__"] += "\n\n" + "\n\n".join(
                    (f"{x[0]}:\n\n{x[1]}" for x in extension_docs)
                )

        # adding DocumentMixinBase unconditionally would lead to the registration of
        # the bare Document class as mixin extension
        if extension_classes:
            base_classes += extension_classes + (DocumentMixinBase,)

        namespace["_loaders"] = (
            core_loaders.tag_node_loader,
            *_plugin_manager.loaders,
        )

        return super().__new__(mcls, name, base_classes, namespace)


class Document(metaclass=DocumentMeta):
    """
    This class is the entrypoint to obtain a representation of an XML encoded text
    document.

    :param source: Anything that the configured loaders can make sense of to return a
                   parsed document tree.
    :param parser_options: A :class:`delb.ParserOptions` instance to configure the used
                           parser.
    :param klass: Explicitly define the initialized class. This can be useful for
                  applications that have :ref:`default document subclasses
                  <document-subclasses>` in use.
    :param config: Additional keyword arguments for the configuration of extension
                   classes.

    For instantiation any object can be passed. A suitable loader must be available for
    the given source. See :ref:`document-loaders` for the default loaders that come with
    this package. Plugins are capable to alter the available loaders, see
    :doc:`/api/extending`.

    Nodes can be tested for membership in a document:

    >>> document = Document("<root>text</root>")
    >>> text_node = document.root[0]
    >>> text_node in document
    True
    >>> text_node.clone() in document
    False

    The string coercion of a document yields an XML encoded stream as string. Its
    appearance can be configured via :class:`DefaultStringOptions`.

    >>> document = Document("<root/>")
    >>> str(document)
    '<?xml version="1.0" encoding="UTF-8"?><root/>'
    """

    _loaders: tuple[Loader, ...]
    __slots__ = ("__root_node__", "config", "head_nodes", "source_url", "tail_nodes")

    def __new__(
        cls,
        source,
        parser_options=None,
        klass=None,
        **config_options,
    ):
        config = SimpleNamespace()
        if DocumentMixinBase in cls.__mro__:
            cls._init_config(config, config_options)

        config.parser_options = parser_options or ParserOptions()
        root = cls.__load_source(source, config)

        if klass is None:
            for subclass in _plugin_manager.document_subclasses:
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
        parser: Optional[etree.XMLParser] = None,
        parser_options: Optional[ParserOptions] = None,
        klass: Optional[type[Document]] = None,
        **config,
    ):
        self.config: SimpleNamespace
        """
        Beside the ``parser_options``, this property contains the namespaced data that
        extension classes and loaders may have stored.
        """
        self.source_url: Optional[str] = self.config.__dict__.pop("source_url", None)
        """
        The source URL where a loader obtained the document's contents or
        :obj:`None`.
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

    def __init_subclass__(cls):
        assert cls not in _plugin_manager.document_mixins
        _plugin_manager.document_subclasses.insert(0, cls)

    @classmethod
    def __load_source(cls, source: Any, config: SimpleNamespace) -> TagNode:
        loader_excuses: dict[Loader, str | Exception] = {}

        for loader in cls._loaders:
            try:
                loader_result = loader(source, config)
            except Exception as e:
                loader_excuses[loader] = e
            else:
                if isinstance(loader_result, etree._ElementTree):
                    loaded_tree = loader_result
                    break
                else:
                    assert isinstance(loader_result, str)
                    loader_excuses[loader] = loader_result
        else:
            raise FailedDocumentLoading(source, loader_excuses)

        assert isinstance(loaded_tree, etree._ElementTree)

        root = _wrapper_cache(loaded_tree.getroot())
        assert isinstance(root, TagNode)

        if config.parser_options.reduce_whitespace:
            with altered_default_filters():
                root._reduce_whitespace()

        return root

    def __contains__(self, node: NodeBase) -> bool:
        return node.document is self

    def __str__(self) -> str:
        with DefaultStringOptions._get_serializer() as serializer:
            self.__serialize(
                serializer=serializer,
                encoding="utf-8",
                indentation=serializer.indentation,
            )
            return serializer.result

    def clone(self) -> Document:
        """
        Clones the document with its contents.

        :return: A new document instance.
        """
        result = Document(self.root, klass=self.__class__)
        # lxml.etree.XMLParser instances aren't pickable / copyable
        parser = self.config.parser_options._make_parser()
        result.config = deepcopy(self.config)
        self.config.parser = result.config.parser = parser
        return result

    def collapse_whitespace(self):
        warn("This method was renamed to `reduce_whitespace`.", DeprecationWarning)
        self.reduce_whitespace()

    def css_select(
        self, expression: str, namespaces: Optional[NamespaceDeclarations] = None
    ) -> QueryResults:
        """
        This method proxies to the :meth:`TagNode.css_select` method of the document's
        :attr:`root <Document.root>` node.
        """
        return self.root.css_select(expression, namespaces=namespaces)

    def merge_text_nodes(self):
        """
        This method proxies to the :meth:`TagNode.merge_text_nodes` method of the
        document's :attr:`root <Document.root>` node.
        """
        self.root.merge_text_nodes()

    @property
    def namespaces(self) -> Namespaces:
        """
        The namespace mapping of the document's :attr:`root <Document.root>` node.
        """
        return self.root.namespaces

    def new_tag_node(
        self,
        local_name: str,
        attributes: Optional[dict[str, str]] = None,
        namespace: Optional[str] = None,
    ) -> TagNode:
        """
        This method proxies to the :meth:`TagNode.new_tag_node` method of the
        document's root node.
        """
        return self.root.new_tag_node(
            local_name=local_name, attributes=attributes, namespace=namespace
        )

    def reduce_whitespace(self):
        """
        Collapses and trims whitespace as described in these `TEI recommendation`_.
        Text in (sub-)trees with structured data should be trimmed further in
        subsequent processing.
        Implicitly merges all neighbouring text nodes.

        .. _TEI recommendation: https://wiki.tei-c.org/index.php/XML_Whitespace
        """
        self.merge_text_nodes()
        with altered_default_filters():
            self.root._reduce_whitespace()

    @property
    def root(self) -> TagNode:
        """The root node of a document's *content* tree."""
        return self.__root_node__

    @root.setter
    def root(self, node: TagNode):
        if not isinstance(node, TagNode):
            raise TypeError("The document root node must be of 'TagNode' type.")

        with altered_default_filters(_is_tag_or_text_node):
            if not all(
                x is None
                for x in (
                    node.parent,
                    node.fetch_preceding_sibling(),
                    node.fetch_following_sibling(),
                )
            ):
                raise ValueError(
                    "Only a detached node can be set as root. Use "
                    ":meth:`TagNode.clone` or :meth:`TagNode.detach` on the "
                    "designated root node."
                )

        current_root = getattr(self, "__root_node__", None)
        if current_root is not None:
            _copy_root_siblings(current_root._etree_obj, node._etree_obj)
            current_root.__document__ = None

        self.__root_node__ = node
        node.__document__ = self

    def save(
        self,
        path: Path,
        pretty: Optional[bool] = None,
        *,
        encoding: str = "utf-8",
        align_attributes: bool = False,
        indentation: str = "",
        namespaces: Optional[NamespaceDeclarations] = None,
        newline: None | str = None,
        text_width: int = 0,
    ):
        """
        Saves the serialized document contents to a file.

        :param path: The filesystem path to the target file.
        :param pretty: *Deprecated.* Adds indentation for human consumers when
                       :obj:`True`.
        :param encoding: The desired text encoding.
        :param align_attributes: Determines whether attributes' names and values line up
                                 sharply around vertically aligned equal signs.
        :param indentation: This string prefixes descending nodes' contents one time per
                            depth level. A non-empty string implies line-breaks between
                            nodes as well.
        :param namespaces: A mapping of prefixes to namespaces. These are overriding
                           possible declarations from a parsed serialisat that the
                           document instance stems from. Prefixes for undeclared
                           namespaces are enumerated with the prefix ``ns``.
        :param newline: See :class:`io.TextIOWrapper` for a detailed explanation of the
                        parameter with the same name.
        :param text_width: A positive value indicates that text nodes shall get wrapped
                           at this character position.
                           Indentations are not considered as part of text. This
                           parameter's purposed to define reasonable widths for text
                           displays that can be scrolled horizontally.
        """
        with path.open("bw") as file:
            self.write(
                buffer=file,
                pretty=pretty,
                encoding=encoding,
                align_attributes=align_attributes,
                indentation=indentation,
                namespaces=namespaces,
                newline=newline,
                text_width=text_width,
            )

    def __serialize(self, serializer, encoding, indentation):
        declaration = f'<?xml version="1.0" encoding="{encoding.upper()}"?>'
        if indentation:
            declaration += "\n"
        serializer.buffer.write(declaration)
        for node in self.head_nodes:
            serializer.serialize_node(node)
        with altered_default_filters():
            serializer.serialize_root(self.root)
        if self.tail_nodes:
            if indentation:
                serializer.buffer.write("\n")
            for node in self.tail_nodes:
                serializer.serialize_node(node)

    def write(
        self,
        buffer: BinaryIO,
        pretty: Optional[bool] = None,
        *,
        encoding: str = "utf-8",
        align_attributes: bool = False,
        indentation: str = "",
        namespaces: Optional[NamespaceDeclarations] = None,
        newline: None | str,
        text_width: int = 0,
    ):
        """
        Writes the serialized document contents to a :term:`file-like object`.

        :param buffer: A :term:`file-like object` that the document is written to.
        :param pretty: *Deprecated.* Adds indentation for human consumers when
                       :obj:`True`.
        :param encoding: The desired text encoding.
        :param align_attributes: Determines whether attributes' names and values line up
                                 sharply around vertically aligned equal signs.
        :param indentation: This string prefixes descending nodes' contents one time per
                            depth level. A non-empty string implies line-breaks between
                            nodes as well.
        :param namespaces: A mapping of prefixes to namespaces. These are overriding
                           possible declarations from a parsed serialisat that the
                           document instance stems from. Prefixes for undeclared
                           namespaces are enumerated with the prefix ``ns``.
        :param newline: See :class:`io.TextIOWrapper` for a detailed explanation of the
                        parameter with the same name.
        :param text_width: A positive value indicates that text nodes shall get wrapped
                           at this character position.
                           Indentations are not considered as part of text. This
                           parameter's purposed to define reasonable widths for text
                           displays that can be scrolled horizontally.
        """
        if pretty is not None:
            warn(
                "The `pretty` argument is deprecated, for the legacy behaviour provide "
                "`indentation` as two spaces instead."
            )
            align_attributes = False
            indentation = "  " if pretty else ""
            text_width = 0

        with TextBufferSerializer(
            buffer=TextIOWrapper(buffer),
            encoding=encoding,
            align_attributes=align_attributes,
            indentation=indentation,
            namespaces=namespaces,
            newline=newline,
            text_width=text_width,
        ) as serializer:
            self.__serialize(
                serializer=serializer, encoding=encoding, indentation=indentation
            )

    def xpath(
        self, expression: str, namespaces: Optional[NamespaceDeclarations] = None
    ) -> QueryResults:
        """
        This method proxies to the :meth:`TagNode.xpath` method of the document's
        :attr:`root <Document.root>` node.
        """

        return self.root.xpath(expression=expression, namespaces=namespaces)


__all__ = (
    CommentNode.__name__,
    DefaultStringOptions.__name__,
    Document.__name__,
    Namespaces.__name__,
    ParserOptions.__name__,
    ProcessingInstructionNode.__name__,
    QueryResults.__name__,
    TagNode.__name__,
    TextNode.__name__,
    altered_default_filters.__name__,
    any_of.__name__,
    compare_trees.__name__,
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
    tag.__name__,
)
