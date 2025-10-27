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

from abc import ABC
from io import StringIO, TextIOWrapper

from typing import (
    TYPE_CHECKING,
    ClassVar as ClassWar,
    Final,
    Literal,
    NamedTuple,
    Optional,
    TextIO,
)

from _delb.filters import is_tag_node
from _delb.names import GLOBAL_PREFIXES, Namespaces

from _delb.typing import (
    CommentNodeType,
    NamespaceDeclarations,
    ParentNodeType,
    ProcessingInstructionNodeType,
    TagNodeType,
    TextNodeType,
)
from _delb.utils import _crunch_whitespace, traverse_bf_ltr_ttb

if TYPE_CHECKING:
    from collections.abc import Iterator

    from _delb.nodes import Siblings
    from _delb.typing import XMLNodeType


# constants


CTRL_CHAR_ENTITY_NAME_MAPPING: Final = (
    ("&", "amp"),
    (">", "gt"),
    ("<", "lt"),
    ('"', "quot"),
)
CCE_TABLE_FOR_ATTRIBUTES: Final = str.maketrans(
    {ord(k): f"&{v};" for k, v in CTRL_CHAR_ENTITY_NAME_MAPPING}
)
CCE_TABLE_FOR_TEXT: Final = str.maketrans(
    {ord(k): f"&{v};" for k, v in CTRL_CHAR_ENTITY_NAME_MAPPING if k != '"'}
)


# configuration


class FormatOptions(NamedTuple):
    """
    Instances of this class can be used to define serialization formatting that is
    not so hard to interpret for instances of Homo sapiens s., but more costly to
    compute.

    When it's employed whitespace contents will be collapsed and trimmed, newlines will
    be inserted to improve readability, but only where further whitespace reduction
    would drop it again.

    The serialization respects when a tag node bears the ``xml:space`` attribute with
    the value ``preserve``. But if any descendent of such annotated node signals to
    allow whitespace alterations again that has no effect. Such attributes with invalid
    values are ignored.
    """

    align_attributes: bool = False
    """
    Determines whether attributes' names and values line up sharply around vertically
    aligned equal signs.
    """
    indentation: str = "\t"
    """ This string prefixes descending nodes' contents one time per depth level. """
    width: int = 0
    """
    A positive value indicates that text nodes shall get wrapped at this character
    position. Indentations are not considered as part of text. This parameter is
    purposed to define reasonable widths for text displays that could be scrolled
    horizontally.
    """


class DefaultStringOptions:
    """
    This object's class variables are used to configure the serialization parameters
    that are applied when nodes are coerced to :class:`str` objects. Hence it also
    applies when node objects are fed to the :func:`print` function and in other cases
    where objects are implicitly cast to strings.

    .. attention::

        Use this once to define behaviour on *application level*. For thread-safe
        serializations of nodes with diverging parameters use
        :meth:`XMLNodeType.serialize`! Think thrice whether you want to use this
        facility in a library.
    """

    namespaces: ClassWar[None | NamespaceDeclarations] = None
    """
    A mapping of prefixes to namespaces. Any other prefixes for undeclared namespaces
    are enumerated with the prefix ``ns``.
    """
    newline: ClassWar[None | str] = None
    """
    See :class:`io.TextIOWrapper` for a detailed explanation of the parameter with the
    same name.
    """
    format_options: ClassWar[None | FormatOptions] = None
    """
    An instance of :class:`delb.FormatOptions` can be provided to configure formatting.
    """

    @classmethod
    def _get_serializer(cls) -> Serializer:
        return _get_serializer(
            _StringWriter(newline=cls.newline),
            format_options=cls.format_options,
            namespaces=cls.namespaces,
        )

    @classmethod
    def reset_defaults(cls):
        """Restores the factory settings."""
        cls.format_options = None
        cls.namespaces = None
        cls.newline = None


# serializer


def _get_serializer(
    writer: _SerializationWriter,
    format_options: Optional[FormatOptions],
    namespaces: Optional[NamespaceDeclarations],
) -> Serializer:
    if format_options is None:
        return Serializer(
            writer=writer,
            namespaces=namespaces,
        )

    if format_options.indentation and not format_options.indentation.isspace():
        raise ValueError("Invalid indentation characters.")

    if format_options.width:
        return TextWrappingSerializer(
            writer=writer,
            format_options=format_options,
            namespaces=namespaces,
        )
    else:
        return PrettySerializer(
            writer=writer,
            format_options=format_options,
            namespaces=namespaces,
        )


class Serializer:
    __slots__ = (
        "_namespaces",
        "_prefixes",
        "writer",
    )

    def __init__(
        self,
        writer: _SerializationWriter,
        *,
        namespaces: Optional[NamespaceDeclarations] = None,
    ):
        self._namespaces: Final = (
            Namespaces({}) if namespaces is None else Namespaces(namespaces)
        )
        self._prefixes: dict[str, str] = {}
        self.writer = writer

    def _collect_prefixes(self, root: TagNodeType):
        if root.namespace not in self._namespaces.values():
            self._prefixes[root.namespace] = ""

        for node in traverse_bf_ltr_ttb(root, is_tag_node):
            assert isinstance(node, TagNodeType)
            for namespace in {node.namespace} | {
                a.namespace for a in node.attributes.values()
            }:
                if namespace in self._prefixes:
                    continue

                if not namespace:
                    # an empty/null namespace can't be assigned to a prefix,
                    # it must be the default namespace
                    self.__redeclare_empty_prefix()
                    self._prefixes[""] = ""
                    continue
                assert namespace is not None

                if (prefix := self._namespaces.lookup_prefix(namespace)) is None:
                    # the namespace isn't declared by the user
                    self._new_namespace_declaration(namespace)
                    continue

                if prefix == "" and "" in self._prefixes.values():
                    # a default namespace was declared, but that one is required for the
                    # empty/null namespace
                    self._new_namespace_declaration(namespace)
                    continue

                if len(prefix):
                    # that found prefix still needs a colon for faster serialisat
                    # composition later
                    assert f"{prefix}:" not in self._prefixes.values()
                    self._prefixes[namespace] = f"{prefix}:"
                else:
                    assert "" not in self._prefixes.values()
                    self._prefixes[namespace] = ""

    def __redeclare_empty_prefix(self):
        # a possibly collected declaration of an empty namespace needs to be mapped to
        # a prefix because an empty namespace needs to be serialized and such cannot be
        # mapped to a prefix in a declaration
        for other_namespace, prefix in self._prefixes.items():
            if prefix == "":
                # there is, it needs to use a prefix though as an empty namespace
                # can't be declared
                assert other_namespace is not None
                self._new_namespace_declaration(other_namespace)
                break

    def _generate_attributes_data(self, node: TagNodeType) -> dict[str, str]:
        data = {}
        for attribute in (node.attributes[a] for a in sorted(node.attributes)):
            data[self._prefixes[attribute.namespace] + attribute.local_name] = (
                f'"{attribute.value.translate(CCE_TABLE_FOR_ATTRIBUTES)}"'
            )
        return data

    def _handle_child_nodes(self, child_nodes: Siblings):
        for child_node in child_nodes:
            self.serialize_node(child_node)

    def _new_namespace_declaration(self, namespace: str):
        for i in range(2**16):
            prefix = f"ns{i}:"
            if prefix not in self._prefixes.values():
                self._prefixes[namespace] = prefix
                return
        else:  # pragma: no cover
            raise NotImplementedError("Just don't.")

    def _serialize_attributes(self, attributes_data):
        for key, value in attributes_data.items():
            self.writer(f" {key}={value}")

    def serialize_node(self, node: XMLNodeType):
        match node:
            case CommentNodeType() | ProcessingInstructionNodeType():
                self.writer(str(node))
            case TagNodeType():
                self._serialize_tag(
                    node,
                    attributes_data=self._generate_attributes_data(node),
                )
            case TextNodeType():
                if node.content:
                    self.writer(node.content.translate(CCE_TABLE_FOR_TEXT))

    def serialize_root(self, root: TagNodeType):
        self._collect_prefixes(root)
        attributes_data = {}
        declarations = {p: "" if n is None else n for n, p in self._prefixes.items()}
        if "" in declarations:
            default_namespace = declarations.pop("")
            if default_namespace:
                attributes_data["xmlns"] = f'"{default_namespace}"'
            # else it would be an unprefixed, empty namespace
        for prefix in sorted(p for p in declarations if p[:-1] not in GLOBAL_PREFIXES):
            assert len(prefix) >= 2  # at least a colon and one letter
            attributes_data[f"xmlns:{prefix[:-1]}"] = f'"{declarations[prefix]}"'

        attributes_data.update(self._generate_attributes_data(root))
        self._serialize_tag(root, attributes_data=attributes_data)

    def _serialize_tag(
        self,
        node: TagNodeType,
        attributes_data: dict[str, str],
    ):
        prefixed_name = self._prefixes[node.namespace] + node.local_name

        self.writer(f"<{prefixed_name}")
        if attributes_data:
            self._serialize_attributes(attributes_data)

        if node._child_nodes:
            self.writer(">")
            self._handle_child_nodes(node._child_nodes)
            self.writer(f"</{prefixed_name}>")
        else:
            self.writer("/>")


class _LineFittingSerializer(Serializer):
    __slots__ = ("space",)

    def __init__(
        self,
        writer: _SerializationWriter,
        *,
        namespaces: Optional[NamespaceDeclarations] = None,
    ):
        self.writer: _LengthTrackingWriter
        super().__init__(writer, namespaces=namespaces)
        self.space: Literal["default", "preserve"] = "default"

    def serialize_node(self, node: XMLNodeType):
        if isinstance(node, TextNodeType):
            if node.content:
                if self.space == "default":
                    content = _crunch_whitespace(node.content).translate(
                        CCE_TABLE_FOR_TEXT
                    )
                else:
                    content = node.content.translate(CCE_TABLE_FOR_TEXT)
                self.writer(content)
            return

        elif isinstance(node, TagNodeType):
            space_state = self.space
            space = node._get_normalize_space_directive(self.space)
            if space != space_state:
                self.space = space
                self.writer.preserve_space = space == "default"

        super().serialize_node(node)

        if isinstance(node, TagNodeType) and space != space_state:
            self.space = space_state
            self.writer.preserve_space = space_state == "default"


class PrettySerializer(Serializer):
    __slots__ = (
        "_align_attributes",
        "indentation",
        "_level",
        "_serialization_root",
        "_space_preserving_serializer",
        "_text_wrapper",
        "_unwritten_text_nodes",
    )

    def __init__(
        self,
        writer: _SerializationWriter,
        format_options: FormatOptions,
        *,
        namespaces: Optional[NamespaceDeclarations] = None,
    ):
        super().__init__(writer, namespaces=namespaces)
        self._align_attributes: Final = format_options.align_attributes
        self.indentation: Final = format_options.indentation
        self._level = 0
        self._serialization_root: None | TagNodeType = None
        self._space_preserving_serializer: Final = Serializer(
            self.writer, namespaces=self._namespaces
        )
        self._unwritten_text_nodes: Final[list[TextNodeType]] = []

    def _collect_prefixes(self, root: TagNodeType):
        super()._collect_prefixes(root)
        self._space_preserving_serializer._prefixes = self._prefixes

    def _handle_child_nodes(self, child_nodes: Siblings):
        # newline between an opening tag and its first child
        if self._whitespace_is_legit_before_node(child_nodes[0]):
            self.writer("\n")

        self._level += 1
        self._serialize_child_nodes(child_nodes)
        self._level -= 1

        if self.indentation and self._whitespace_is_legit_after_node(child_nodes[-1]):
            # indentation before closing tag
            # newline was possibly written in self.serialize_node()
            # or self._serialize_text
            self.writer(self._level * self.indentation)

    def _normalize_text(self, text: str) -> str:
        return _crunch_whitespace(text).translate(CCE_TABLE_FOR_TEXT)

    def _serialize_attributes(self, attributes_data: dict[str, str]):
        if self._align_attributes and len(attributes_data) > 1:
            key_width = max(len(k) for k in attributes_data)
            for key, value in attributes_data.items():
                self.writer(
                    f"\n{self._level * self.indentation} {self.indentation}"
                    f"{' ' * (key_width - len(key))}{key}={value}"
                )
            if self.indentation:
                self.writer(f"\n{self._level * self.indentation}")

        else:
            super()._serialize_attributes(attributes_data)

    def _serialize_child_nodes(self, child_nodes: Siblings):
        for node in child_nodes:
            if isinstance(node, TextNodeType):
                if node.content:
                    self._unwritten_text_nodes.append(node)
            else:
                self.serialize_node(node)

        if self._unwritten_text_nodes:
            self._serialize_text()

    def serialize_node(self, node: XMLNodeType):
        if self._unwritten_text_nodes:
            self._serialize_text()

        if self.indentation and self._whitespace_is_legit_before_node(node):
            self.writer(self._level * self.indentation)

        super().serialize_node(node)

        if self._whitespace_is_legit_after_node(node):
            self.writer("\n")

    def serialize_root(self, root: TagNodeType):
        self._serialization_root = root
        super().serialize_root(root)
        self._serialization_root = None

    def _serialize_tag(
        self,
        node: TagNodeType,
        attributes_data: dict[str, str],
    ):
        if node._get_normalize_space_directive() == "preserve":
            self._space_preserving_serializer._serialize_tag(
                node=node,
                attributes_data=attributes_data,
            )
        else:
            super()._serialize_tag(
                node,
                attributes_data=attributes_data,
            )

    def _serialize_text(self):
        nodes = self._unwritten_text_nodes
        content = self._normalize_text("".join(n.content for n in nodes))

        if content == " ":
            # a whitespace-only node can be omitted as a newline has been inserted
            # before
            pass

        else:
            if self.indentation and self._whitespace_is_legit_before_node(nodes[0]):
                content = self._level * self.indentation + content.lstrip()

            if self._whitespace_is_legit_after_node(nodes[-1]):
                content = content.rstrip() + "\n"

            assert content
            self.writer(content)

        nodes.clear()

    def _whitespace_is_legit_after_node(self, node: XMLNodeType) -> bool:
        if self._serialization_root is None or node is self._serialization_root:
            # end of stream
            return False

        assert node._parent is not None
        if node._parent._child_nodes[-1] is node:
            return True

        if isinstance(node, TextNodeType):
            return node.content[-1].isspace()

        following_sibling = node._fetch_following_sibling()
        assert following_sibling is not None
        if isinstance(following_sibling, TextNodeType):
            return self._whitespace_is_legit_before_node(following_sibling)
        else:
            return False

    def _whitespace_is_legit_before_node(self, node: XMLNodeType) -> bool:
        if self._serialization_root is None or node is self._serialization_root:
            # begin of stream
            return False

        assert isinstance(node._parent, TagNodeType)
        if node._parent._child_nodes[0] is node:
            return True

        if isinstance(node, TextNodeType):
            return node.content[0].isspace()

        preceding_sibling = node._fetch_preceding_sibling()
        assert preceding_sibling is not None
        if isinstance(preceding_sibling, TextNodeType):
            return self._whitespace_is_legit_after_node(preceding_sibling)
        else:
            return False


class TextWrappingSerializer(PrettySerializer):
    __slots__ = (
        "_line_fitting_serializer",
        "_width",
    )

    def __init__(
        self,
        writer: _SerializationWriter,
        format_options: FormatOptions,
        *,
        namespaces: Optional[NamespaceDeclarations] = None,
    ):
        if format_options.width < 1:
            raise ValueError("Invalid width option value.")
        self.writer: _LengthTrackingWriter
        super().__init__(
            writer=_LengthTrackingWriter(writer.buffer),
            format_options=format_options,
            namespaces=namespaces,
        )
        self._line_fitting_serializer: Final = _LineFittingSerializer(
            self.writer, namespaces=self._namespaces
        )
        self._width: Final = format_options.width

    @property
    def _available_space(self):
        return max(0, self._width - self._line_offset)

    def _collect_prefixes(self, root: TagNodeType):
        super()._collect_prefixes(root)
        self._line_fitting_serializer._prefixes = self._prefixes

    @property
    def _line_offset(self) -> int:
        if self.writer.offset:
            return self.writer.offset - self._level * len(self.indentation)
        else:
            return 0

    def _node_fits_remaining_line(self, node: XMLNodeType) -> bool:
        return self._required_space(node, self._available_space) is not None

    def _required_space(self, node: XMLNodeType, up_to: int) -> None | int:
        # counts required space for the serialisation of a node
        # a returned None signals that the limit up_to was hit

        if isinstance(node, TextNodeType):
            return self._required_space_for_text(node, up_to)
        if isinstance(node, (CommentNodeType, ProcessingInstructionNodeType)):
            length = len(str(node))
            return length if length <= up_to else None

        assert isinstance(node, TagNodeType)

        name_length = len(node.local_name) + len(self._prefixes[node.namespace])
        if len(node) == 0:
            used_space = 3 + name_length  # <N/>
        else:
            used_space = 5 + 2 * name_length  # <N>…<N/>

        if used_space > up_to:
            return None

        if (
            attributes_space := self._required_space_for_attributes(
                node, up_to - used_space
            )
        ) is None:
            return None
        used_space += attributes_space

        for child_node in node._child_nodes:
            if (
                child_space := self._required_space(child_node, up_to - used_space)
            ) is None:
                return None
            used_space += child_space

        if (
            following_space := self._required_space_for_following(
                node, up_to - used_space
            )
        ) is None:
            return None
        used_space += following_space

        return used_space

    def _required_space_for_attributes(
        self, node: TagNodeType, up_to: int
    ) -> None | int:
        result = 0

        attribute_names = tuple(node.attributes)
        for attribute in (node.attributes[n] for n in attribute_names):
            assert attribute is not None
            result += (
                4  # preceding space and »="…"«
                + len(attribute.local_name)
                + len(self._prefixes[attribute.namespace])
                + len(attribute.value.translate(CCE_TABLE_FOR_ATTRIBUTES))
            )
            if result > up_to:
                return None

        return result

    def _required_space_for_following(
        self, node: TagNodeType, up_to: int
    ) -> None | int:
        if self._whitespace_is_legit_after_node(node):
            return 0

        if (following := node._fetch_following()) is None:
            return 0

        if not isinstance(following, TextNodeType):
            return self._required_space(following, up_to)

        # indeed this doesn't consider the case where a first
        # whitespace would appear in one of possible subsequent text
        # nodes
        content = following.content.translate(CCE_TABLE_FOR_TEXT)
        if (length := content.find(" ")) == -1:
            length = len(content)

        return length if length <= up_to else None

    def _required_space_for_text(self, node: TextNodeType, up_to: int) -> None | int:
        content = self._normalize_text(node.content)
        if content.startswith(" ") and self._whitespace_is_legit_before_node(node):
            content = content.lstrip()
        if content.endswith(" ") and self._whitespace_is_legit_after_node(node):
            content = content.rstrip()
        length = len(content)
        return length if length <= up_to else None

    def _serialize_appendable_node(self, node: XMLNodeType):
        assert not isinstance(node, TextNodeType)

        if self.writer.offset == 0 and self.indentation:
            self.writer(self._level * self.indentation)

        match node:
            case TagNodeType():
                if node._get_normalize_space_directive() == "preserve":
                    serializer = self._space_preserving_serializer
                    self.writer.preserve_space = True
                else:
                    serializer = self._line_fitting_serializer
                serializer.serialize_node(node)
                self.writer.preserve_space = False
            case CommentNodeType() | ProcessingInstructionNodeType():
                self.writer(str(node))

    def serialize_node(self, node: XMLNodeType):
        if self._unwritten_text_nodes:
            self._serialize_text()

        if self._node_fits_remaining_line(node):
            self._serialize_appendable_node(node)
            assert node._parent is not None
            if (
                (not self._available_space) or (node is node._parent._child_nodes[-1])
            ) and self._whitespace_is_legit_after_node(node):
                self.writer("\n")
                return

        else:
            if self._line_offset > 0 and self._whitespace_is_legit_before_node(node):
                self.writer("\n")
                self.serialize_node(node)
                return

            if (
                self.indentation
                and self.writer.offset == 0
                and self._whitespace_is_legit_before_node(node)
            ):
                self.writer(self._level * self.indentation)

            if (
                isinstance(node, TagNodeType)
                and node._get_normalize_space_directive() == "preserve"
            ):
                self.writer.preserve_space = True
            super(PrettySerializer, self).serialize_node(node)
            self.writer.preserve_space = False

        if self._whitespace_is_legit_after_node(node) and not (
            (
                (following := node._fetch_following()) is not None
                and self._node_fits_remaining_line(following)
            )
        ):
            self.writer("\n")

    def _serialize_tag(
        self,
        node: TagNodeType,
        attributes_data: dict[str, str],
    ):
        if node is not self._serialization_root and self._node_fits_remaining_line(
            node
        ):
            self._serialize_appendable_node(node)
        else:
            super()._serialize_tag(node, attributes_data)

    def _serialize_text(self):
        nodes = self._unwritten_text_nodes
        content = self._normalize_text("".join(n.content for n in nodes))
        last_node = nodes[-1]
        assert isinstance(last_node._parent, ParentNodeType)

        if self._available_space == len(
            content.rstrip()
        ) and self._whitespace_is_legit_after_node(last_node):
            # text fits perfectly
            self.writer(content.rstrip() + "\n")

        elif self._available_space > len(content):
            # text fits current line
            if self._line_offset == 0:
                content = self._level * self.indentation + content.lstrip()

            if (
                (last_node is last_node._parent._child_nodes[-1])
                or (following := last_node._fetch_following()) is not None
                and (
                    self._whitespace_is_legit_before_node(following)
                    and self._required_space(
                        following, self._available_space - len(content)
                    )
                    is None
                )
            ):
                content = content.rstrip() + "\n"

            self.writer(content)

        elif content == " ":
            # " " doesn't fit line
            self.writer("\n")

        else:
            # text doesn't fit current line
            self._serialize_text_over_lines(content)

        nodes.clear()

    def _serialize_text_over_lines(self, content: str):
        lines: list[str] = []
        nodes = self._unwritten_text_nodes

        if self._line_offset == 0:
            # just a side note: this branch would also be interesting if
            # len(content) > self._width  # noqa: E800
            # and self._whitespace_is_legit_before_node(nodes[0])
            # and one would know that the line starts with text content
            #
            # so for now that's why text might start after a closing tag of an
            # element that spans multiple lines on their last one
            # (i.e. this prefers: "the <hi>A</hi> letter…" over the "A" on a
            # separate line which the next branch produces)

            if self._whitespace_is_legit_before_node(nodes[0]):
                lines.append("")
            lines.extend(self._wrap_text(content.lstrip(), self._width))

        else:
            if content.startswith(" "):
                filling = " " + next(
                    self._wrap_text(content[1:], self._available_space - 1)
                )
            else:
                filling = next(self._wrap_text(content, self._available_space))

            if not (
                len(filling) > self._available_space
                and self._whitespace_is_legit_before_node(nodes[0])
            ):
                self.writer(filling)
                content = content[len(filling) + 1 :]
                if not content:
                    return

            lines.append("")
            lines.extend(self._wrap_text(content, self._width))

        if (
            lines[-1].endswith(" ")
            and self._whitespace_is_legit_after_node(nodes[-1])
            and (following_sibling := nodes[-1]._fetch_following_sibling()) is not None
            and not self._required_space(
                following_sibling, self._width - len(lines[-1])
            )
        ):
            lines.append("")

        self._consolidate_text_lines(lines)

        prefix = self._level * self.indentation
        for line in lines[:-1]:
            if line == "":
                self.writer("\n")
            else:
                self.writer(f"{prefix}{line}\n")
        if lines[-1] != "":
            self.writer(f"{prefix}{lines[-1]}")

    def _consolidate_text_lines(self, lines: list[str]):
        last_node = self._unwritten_text_nodes[-1]
        assert last_node._parent is not None
        if (
            lines[0] == ""
            and last_node is last_node._parent._child_nodes[-1]
            and self._whitespace_is_legit_after_node(last_node)
        ):
            lines.append("")
        if self._line_offset == 0 and lines[0] == "":
            lines.pop(0)
        if len(lines) >= 2 and lines[-1] == "":
            lines[-2] = lines[-2].rstrip()

    @staticmethod
    def _wrap_text(text: str, width: int) -> Iterator[str]:
        while len(text) > width:

            if (index := text.rfind(" ", 0, width + 1)) > -1 or (
                index := text.find(" ", width)
            ) > 0:
                yield text[:index]
                text = text[index + 1 :]
            else:
                yield text
                return

        if text:
            yield text


# writer


class _SerializationWriter(ABC):
    __slots__ = ("buffer",)

    def __init__(self, buffer: TextIO):
        self.buffer: Final = buffer

    def __call__(self, data: str):
        self.buffer.write(data)

    @property
    def result(self):
        if isinstance(self.buffer, StringIO):
            return self.buffer.getvalue()
        raise TypeError(  # pragma: no cover
            "Underlying buffer must be an instance of `io.StingIO`"
        )


class _LengthTrackingWriter(_SerializationWriter):
    __slots__ = ("offset", "preserve_space")

    def __init__(self, buffer: TextIO):
        super().__init__(buffer)
        self.offset = 0
        self.preserve_space = False

    def __call__(self, data: str):
        if not self.preserve_space and self.offset == 0:
            data = data.lstrip("\n")

        if not data:
            return

        if data[-1] == "\n":
            self.offset = 0
        else:
            if (index := data.rfind("\n")) == -1:
                self.offset += len(data)
            else:
                self.offset = len(data) - (index + 1)
        super().__call__(data)


class _StringWriter(_SerializationWriter):
    def __init__(self, newline: Optional[str] = None):
        super().__init__(StringIO(newline=newline))


class _TextBufferWriter(_SerializationWriter):
    def __init__(
        self,
        buffer: TextIOWrapper,
        encoding: str = "utf-8",
        newline: Optional[str] = None,
    ):
        buffer.reconfigure(encoding=encoding, newline=newline)
        super().__init__(buffer)


#


__all__ = (
    DefaultStringOptions.__name__,
    FormatOptions.__name__,
)
