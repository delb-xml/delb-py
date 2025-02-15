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

import codecs
import re
import warnings
from enum import IntEnum, auto
from io import BytesIO
from typing import Final, TYPE_CHECKING, NamedTuple, Optional, TypeAlias, cast

from _delb.plugins import plugin_manager

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

    from _delb.plugins import XMLEventParserInterface
    from _delb.typing import BinaryReader, InputStream, _AttributesData


BOM_TO_ENCODING_NAME: Final = (
    (4, codecs.BOM_UTF32_LE, "utf-32-le"),
    (4, codecs.BOM_UTF32_BE, "utf-32-be"),
    (3, codecs.BOM_UTF8, "utf-8"),
    (2, codecs.BOM_UTF16_LE, "utf-16-le"),
    (2, codecs.BOM_UTF16_BE, "utf-16-be"),
)


_match_encoding: Final = re.compile(
    rb"""<\?xml\sversion=["']1\.0["']\sencoding=["']([A-Za-z0-9_-]+)["']\?>"""
).match


class _EncodingDetectingReader:
    __slots__ = ("buffer", "first_bytes", "reading")

    def __init__(self, buffer: BinaryReader):
        self.buffer = buffer
        self.first_bytes = b""
        self.reading = False

    def get_encoding(self) -> str | None:
        if self.reading:
            raise RuntimeError("Get the encoding before reading from the buffer!")

        self.first_bytes = self.buffer.read(64)
        return detect_encoding(self.first_bytes)

    def read(self, n: int = -1) -> bytes:
        if self.reading:
            return self.buffer.read(n)
        else:
            self.reading = True
            return self.first_bytes + self.buffer.read(n)


class EventType(IntEnum):
    Comment = auto()
    ProcessingInstruction = auto()
    TagStart = auto()
    TagEnd = auto()
    Text = auto()


class ParserOptions(NamedTuple):
    """
    The configuration options that define an XML parser's behaviour.

    The used parser backend is determined by their availability and the
    ``preferred_parsers`` setting.  *delb* comes with two contributed implementations
    and further can be added to the plugin manager based on
    :class:`_delb.plugins.XMLEventParserInterface`.

    Both contributed implementations should not be tasked with documents that refer
    invalid *Document Type Declarations* (DTDs), such may pass when their included
    character entity declarations aren't used in the character data of the document or
    lead to errors of different degrees of severity.  Character entity declarations are
    the only considered DTD feature to provide backward compatibility.

    Both will not allow some non-word characters as part of XML names that should be
    allowed with the 5th edition of the XML 1.0 specification, e.g. ``:`` or single
    combining characters.

    Beside the :exc:`_delb.exceptions.ParsingError` exception and its derivations the
    employed parsers may evoke their specific exceptions when confronted with invalid
    syntax and not-so-well-formed documents.

    The ``expat`` parser adapter depends on the :mod:`xml.sax.expatreader` module from
    the standard library that is available with many Python distributions.

    The ``lxml`` based parser requires the *lxml* package to be present in the
    interpreter environment.  This parser is prone to crashing when processing invalid
    DTDs, it also fails with uncommon, but still valid by spec, DTD contents.  It
    should not be used with other encodings than Unicode to avoid crashes.
    """  # noqa: RST304

    encoding: Optional[str] = None
    """
    This should be used for streams where the encoding is not noted in an XML document
    declaration or indicated by a BOM for Unicode encodings.  It doesn't affect parsing
    of data that is passed as :class:`str`.  Default: :obj:`None`.
    """
    load_referenced_resources: bool = False
    """Allows the loading of referenced external DTDs.  Default: :obj:`False`."""
    preferred_parsers: str | Sequence[str] = ("lxml", "expat")
    """
    A parser adapter name or a sequence of such that are preferably to be used.
    Default: ``("lxml", "expat")``.
    """
    reduce_whitespace: bool = False
    """
    :meth:`Reduce the content's whitespace <delb.Document.reduce_whitespace>`.
    Default: :obj:`False`.
    """
    remove_comments: bool = False
    """Ignore comments.  Default: :obj:`False`."""
    remove_processing_instructions: bool = False
    """
    Don't include processing instructions in the parsed tree.  Default: :obj:`False`.
    """
    unplugged: bool = False
    """Don't load referenced resources over network.  Default: :obj:`False`."""


class TagEventData(NamedTuple):
    namespace: str
    local_name: str
    attributes: _AttributesData | None
    """
    The attributes data must not contain XML namespace declarations.
    It is optional in case of a :py:enum:`EventType.TagEnd`.
    """


Event: TypeAlias = tuple[EventType, str | tuple[str, str] | TagEventData]
"""
An XML stream event tuple consists of two values.  The first is a member of
:class:`EventType` that signals the type of event, the second carries the relevant data.
All data must be stripped of XML markup characters and character data must be completely
parsed and normalized.  All XML names and character entities must be resolved.

.. list-table:: XML event tuples' structure
    :widths: auto

    * - Event member
      - Data type
      - Notes
    * - :py:enum:member:`EventType.Comment`
      - :class:`str`
      -
    * - :py:enum:member:`EventType.ProcessingInstruction`
      - :class:`tuple` [:class:`str`, :class:`str`]
      - ``(target, content)``
    * - :py:enum:member:`EventType.TagStart`
      - :class:`TagEventData`
      -
    * - :py:enum:member:`EventType.TagEnd`
      - :class:`TagEventData` | :class:`None`
      - If data is provided, the tree builder can detect inconsistent tagging in debug
        mode.
    * - :py:enum:member:`EventType.Text`
      - :class:`str`
      -
"""


def detect_encoding(stream: bytes) -> str | None:
    if (match := _match_encoding(stream)) is not None:
        return match.group(1).decode("ascii")
    else:
        for bom_size, bom, name in BOM_TO_ENCODING_NAME:
            if stream[:bom_size] == bom:
                return name
        else:
            return None


def _make_parser(
    options: ParserOptions, *, base_url: str | None, encoding: str
) -> XMLEventParserInterface:
    return plugin_manager.get_parser(options.preferred_parsers)(
        options, base_url=base_url, encoding=encoding
    )


def parse_events(
    input_: InputStream, options: ParserOptions, base_url: str | None
) -> Iterator[Event]:
    encoding = options.encoding
    if isinstance(input_, str):
        encoding = "utf-8"

    elif isinstance(input_, bytes):
        if encoding is None:
            encoding = detect_encoding(input_)
        input_ = BytesIO(input_)

    elif encoding is None:
        if input_.seekable():
            encoding = detect_encoding(input_.read(64))
            input_.seek(0)
        else:
            input_ = _EncodingDetectingReader(input_)
            encoding = input_.get_encoding()

    if encoding is None:
        warnings.warn(
            "No encoding known for parsing an XML stream. Defaulting to UTF-8.",
            category=UserWarning,
        )
        encoding = "utf-8"

    yield from _make_parser(options, base_url=base_url, encoding=encoding).parse(
        cast("BinaryReader", input_)
    )


__all__ = (
    "Event",
    "EventType",
    ParserOptions.__name__,
    TagEventData.__name__,
    detect_encoding.__name__,
)
