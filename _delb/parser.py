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

    :param encoding: An optional encoding that is expected.  This should be used for
                     streams where the encoding is not noted in an XML document
                     declaration or indicated by a BOM for Unicode encodings.
                     It doesn't affect parsing of data that is passed as :class:`str`.
    :param load_referenced_resources: Allows the loading of referenced external DTDs.
    :param preferred_parsers: A name or a sequence of names that are preferably to be
                              used.
    :param reduce_whitespace: :meth:`Reduce the content's whitespace
                                <delb.Document.reduce_whitespace>`.
    :param remove_comments: Ignore comments.
    :param remove_processing_instructions: Don't include processing instructions in the
                                           parsed tree.
    :param unplugged: Don't load referenced resources over network.
    """

    encoding: Optional[str] = None
    load_referenced_resources: bool = False
    preferred_parsers: str | Sequence[str] = ("lxml", "expat")
    reduce_whitespace: bool = False
    remove_comments: bool = False
    remove_processing_instructions: bool = False
    unplugged: bool = False


class TagEventData(NamedTuple):
    namespace: str
    local_name: str
    attributes: _AttributesData | None


Event: TypeAlias = tuple[EventType, str | tuple[str, str] | TagEventData]


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
)
