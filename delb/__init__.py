# Copyright (C) 2018-'25  Frank Sachsenheim
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

import warnings
from abc import abstractmethod, ABC
from collections.abc import Iterator, Sequence
from copy import deepcopy
from io import TextIOWrapper
from types import SimpleNamespace
from typing import TYPE_CHECKING, overload, Any, BinaryIO, Final, Optional

from _delb.builder import parse_nodes, parse_tree, tag
from _delb.exceptions import (
    FailedDocumentLoading,
    InvalidOperation,
)
from _delb.plugins import (
    core_loaders,
    plugin_manager as _plugin_manager,
    DocumentMixinBase,
)
from _delb.nodes import (
    CommentNode,
    _DocumentNode,
    ProcessingInstructionNode,
    TagNode,
)
from _delb.parser import ParserOptions
from _delb.serializer import (
    DefaultStringOptions,
    FormatOptions,
    PrettySerializer,
    Serializer,
    _TextBufferWriter,
    _get_serializer,
)

if TYPE_CHECKING:
    from pathlib import Path

    from _delb.typing import (
        CommentNodeType,
        _DocumentNodeType,
        Loader,
        NamespaceDeclarations,
        ProcessingInstructionNodeType,
        TagNodeType,
        XMLNodeType,
    )
    from _delb.xpath import QueryResults


# plugin loading


_plugin_manager.load_plugins()


# api


class _Logue(ABC):
    __slots__ = ("_siblings",)

    def __init__(self, document: _DocumentNodeType):
        self._siblings: Final = document._child_nodes

    @overload
    def __getitem__(self, index: int) -> XMLNodeType:
        pass

    @overload
    def __getitem__(self, index: slice) -> list[XMLNodeType]:
        pass

    def __getitem__(self, index: int | slice) -> XMLNodeType | list[XMLNodeType]:
        return self._siblings_slice[index]

    def __iter__(self) -> Iterator[XMLNodeType]:
        return iter(self._siblings_slice)

    def __len__(self) -> int:
        return len(self._siblings_slice)

    @abstractmethod
    def append(
        self, node: CommentNodeType | ProcessingInstructionNodeType
    ) -> CommentNodeType | ProcessingInstructionNodeType:
        pass

    def clear(self):
        for node in self._siblings_slice:
            self._siblings.remove(node)

    @abstractmethod
    def index(self, node: XMLNodeType) -> int | None:
        pass

    @abstractmethod
    def insert(self, index: int, node: XMLNodeType):
        pass

    def prepend(
        self, node: CommentNodeType | ProcessingInstructionNodeType
    ) -> CommentNodeType | ProcessingInstructionNodeType:
        self.insert(0, node)
        return node

    def remove(self, node: CommentNodeType | ProcessingInstructionNodeType):
        self._siblings.remove(node)

    @property
    def _root_index(self) -> int:
        return self._siblings.index(
            next(n for n in self._siblings if isinstance(n, TagNode))
        )

    @property
    @abstractmethod
    def _siblings_slice(self) -> list[XMLNodeType]:
        pass

    def _validate_new_node(self, node: XMLNodeType):
        if not isinstance(node, (CommentNode, ProcessingInstructionNode)):
            raise TypeError
        if node._parent is not None:
            raise InvalidOperation(
                "Only a detached node can be added to the tree. Use "
                ":meth:`XMLNodeType.clone` or :meth:`XMLNodeType.detach` to get one."
            )


class Epilogue(_Logue):
    def append(
        self, node: CommentNodeType | ProcessingInstructionNodeType
    ) -> CommentNodeType | ProcessingInstructionNodeType:
        self._validate_new_node(node)
        self._siblings.append(node)
        return node

    def index(self, node: XMLNodeType) -> int | None:
        if node in self._siblings:
            return self._siblings.index(node) - self._root_index - 1
        else:
            return None

    def insert(self, index: int, node: XMLNodeType):
        self._validate_new_node(node)
        self._siblings.insert(self._root_index + index + 1, node)

    @property
    def _siblings_slice(self) -> list[XMLNodeType]:
        return self._siblings[self._root_index + 1 :]


class Prologue(_Logue):
    def append(
        self, node: CommentNodeType | ProcessingInstructionNodeType
    ) -> CommentNodeType | ProcessingInstructionNodeType:
        self._validate_new_node(node)
        self._siblings.insert(self._root_index, node)
        return node

    def index(self, node: XMLNodeType) -> int | None:
        return self._siblings.index(node)

    def insert(self, index: int, node: XMLNodeType):
        self._validate_new_node(node)
        if index > self._root_index:
            raise IndexError
        self._siblings.insert(index, node)

    @property
    def _siblings_slice(self) -> list[XMLNodeType]:
        return self._siblings[: self._root_index]


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
    :param parser_options: A :class:`delb.parser.ParserOptions` instance to configure
                           the used parser.
    :param klass: Explicitly define the initialized class. This can be useful for
                  applications that have :ref:`default document subclasses
                  <document-subclasses>` in use.
    :param source_url: An optional source URL for situations where a reader can't
                       determine one.
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

    The string coercion of a document yields an XML encoded stream as string. See
    :doc:`/api/serialization` for details.

    >>> document = Document("<root/>")
    >>> str(document)
    '<?xml version="1.0" encoding="UTF-8"?><root/>'
    """

    _loaders: tuple[Loader, ...]
    __node: _DocumentNodeType

    __slots__ = ("config", "epilogue", "__node", "prologue", "source_url")

    def __new__(
        cls,
        source,
        /,
        parser_options=None,
        klass=None,
        source_url=None,
        **config_options,
    ):
        config = SimpleNamespace()
        if source_url is not None:
            config.source_url = source_url
        if DocumentMixinBase in cls.__mro__:
            assert hasattr(cls, "_init_config")
            cls._init_config(config, config_options)

        config.parser_options = parser_options or ParserOptions()
        loader_result = cls.__load_source(source, config)

        if klass is None:
            root = next(n for n in loader_result if isinstance(n, TagNode))
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
        instance.__node = _DocumentNode(instance, loader_result)
        instance.prologue = Prologue(instance.__node)
        instance.epilogue = Epilogue(instance.__node)
        return instance

    def __init__(
        self,
        source: Any,
        /,
        parser_options: Optional[ParserOptions] = None,
        klass: Optional[type[Document]] = None,
        source_url: Optional[str] = None,
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
        self.prologue: Prologue
        """
        A list-like accessor to the nodes that precede the document's root node.
        """
        self.epilogue: Epilogue
        """
        A list-like accessor to the nodes that follow the document's root node.
        """

    def __init_subclass__(cls):
        assert cls not in _plugin_manager.document_mixins
        _plugin_manager.document_subclasses.insert(0, cls)

    @classmethod
    def __load_source(
        cls, source: Any, config: SimpleNamespace
    ) -> Sequence[XMLNodeType]:
        loader_excuses: dict[Loader, str | Exception] = {}

        for loader in cls._loaders:
            try:
                loader_result = loader(source, config)
            except Exception as e:
                loader_excuses[loader] = e
            else:
                if isinstance(loader_result, str):
                    loader_excuses[loader] = loader_result
                else:
                    break
        else:
            vars(config).pop("source_url", None)
            raise FailedDocumentLoading(source, loader_excuses)

        assert isinstance(loader_result, Sequence)
        assert not isinstance(loader_result, str)
        return loader_result

    def __contains__(self, node: XMLNodeType) -> bool:
        return node.document is self

    def __str__(self) -> str:
        serializer = DefaultStringOptions._get_serializer()
        self.__serialize(serializer=serializer, encoding="utf-8")
        return serializer.writer.result

    def clone(self) -> Document:
        """
        Clones the document with its contents.

        :return: A new document instance.
        """
        result = Document(self.__node, klass=self.__class__)
        result.config = deepcopy(self.config)
        return result

    def css_select(
        self, expression: str, namespaces: Optional[NamespaceDeclarations] = None
    ) -> QueryResults:
        """
        This method proxies to the :meth:`delb.nodes.TagNode.css_select` method of the
        document's :attr:`root <Document.root>` node.
        """
        return self.root.css_select(expression, namespaces=namespaces)

    def merge_text_nodes(self, deep: bool = True):
        """
        This method proxies to the :meth:`delb.nodes.TagNode.merge_text_nodes` method of
        the document's :attr:`root <Document.root>` node.
        """
        self.root.merge_text_nodes(deep=deep)

    def reduce_whitespace(self):
        """
        Collapses and trims whitespace as described in this `TEI recommendation`_.
        Text in (sub-)trees with structured data should be trimmed further in
        subsequent processing.
        This routine implicitly merges all neighbouring text nodes.
        Note that the recommendation doesn't sufficiently cover situations with
        neighbouring comments and processing instructions. For determinable results one
        should remove such nodes before applying the whitespace reduction.

        .. _TEI recommendation: https://wiki.tei-c.org/index.php/XML_Whitespace
        """
        self.root._reduce_whitespace()

    @property
    def root(self) -> TagNodeType:
        """The root node of a document's *content* tree."""
        return next(n for n in self.__node._child_nodes if isinstance(n, TagNode))

    @root.setter
    def root(self, node: TagNodeType):
        if not isinstance(node, TagNode):
            raise TypeError(
                "The document root node must be a :class:`delb.nodes.TagNode` instance."
            )

        if node._parent is not None or node.document is not None:
            raise InvalidOperation(
                "Only a detached node can be set as root. Use "
                ":meth:`delb.nodes.TagNode.clone` or "
                ":meth:`delb.nodes.TagNode.detach` on the designated root node."
            )

        current_root = self.root
        node_index = self.__node._child_nodes.index(current_root)
        self.__node._child_nodes.remove(current_root)
        self.__node.insert_children(node_index, node)

    def save(
        self,
        path: Path,
        *,
        encoding: str = "utf-8",
        format_options: Optional[FormatOptions] = None,
        namespaces: Optional[NamespaceDeclarations] = None,
        newline: None | str = None,
    ):
        """
        Saves the serialized document contents to a file. See :doc:`/api/serialization`
        for details.

        :param path: The filesystem path to the target file.
        :param encoding: The desired text encoding.
        :param format_options: An instance of :class:`FormatOptions` can be
                               provided to configure formatting.
        :param namespaces: A mapping of prefixes to namespaces.  If not provided the
                           root node's namespace will serve as default namespace.
                           Prefixes for undeclared namespaces are enumerated with the
                           prefix ``ns``.
        :param newline: See :class:`io.TextIOWrapper` for a detailed explanation of the
                        parameter with the same name.
        """
        with path.open("bw") as file:
            self.write(
                buffer=file,
                encoding=encoding,
                format_options=format_options,
                namespaces=namespaces,
                newline=newline,
            )

    def __serialize(
        self,
        serializer: Serializer,
        encoding: str,
    ):
        possible_newline = "\n" if isinstance(serializer, PrettySerializer) else ""

        serializer.writer(
            f'<?xml version="1.0" encoding="{encoding.upper()}"?>{possible_newline}'
        )
        for node in self.prologue:
            serializer.writer(str(node) + possible_newline)
        serializer.serialize_root(self.root)
        if self.epilogue:
            serializer.writer(possible_newline)
            for node in self.epilogue[:-1]:
                serializer.writer(str(node) + possible_newline)
            serializer.writer(str(self.epilogue[-1]))
        serializer.writer.buffer.flush()

    def write(
        self,
        buffer: BinaryIO,
        *,
        encoding: str = "utf-8",
        format_options: Optional[FormatOptions] = None,
        namespaces: Optional[NamespaceDeclarations] = None,
        newline: None | str = None,
    ):
        """
        Writes the serialized document contents to a :term:`file-like object`. See
        :doc:`/api/serialization` for details.

        :param buffer: A :term:`file-like object` that the document is written to.
        :param encoding: The desired text encoding.
        :param format_options: An instance of :class:`FormatOptions` can be provided to
                               configure formatting.
        :param namespaces: A mapping of prefixes to namespaces.  If not provided the
                           root node's namespace will serve as default namespace.
                           Prefixes for undeclared namespaces are enumerated with the
                           prefix ``ns``.
        :param newline: See :class:`io.TextIOWrapper` for a detailed explanation of the
                        parameter with the same name.
        """
        # TODO figure out what's causing the "unclosed file <_io.TextIOWrapper …>"
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=ResourceWarning)
            self.__serialize(
                serializer=_get_serializer(
                    _TextBufferWriter(
                        TextIOWrapper(buffer), encoding=encoding, newline=newline
                    ),
                    format_options=format_options,
                    namespaces=namespaces,
                ),
                encoding=encoding,
            )

    def xpath(
        self, expression: str, namespaces: Optional[NamespaceDeclarations] = None
    ) -> QueryResults:
        """
        This method proxies to the :meth:`delb.nodes.TagNode.xpath` method of the
        document's :attr:`root <Document.root>` node.
        """
        return self.root.xpath(expression=expression, namespaces=namespaces)


__all__ = (
    DefaultStringOptions.__name__,
    Document.__name__,
    FormatOptions.__name__,
    ParserOptions.__name__,
    parse_nodes.__name__,
    parse_tree.__name__,
    tag.__name__,
)
