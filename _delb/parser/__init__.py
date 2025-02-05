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
from io import BytesIO
from typing import TYPE_CHECKING, NamedTuple, Optional, cast

from _delb.parser.base import Event, EventType, XMLEventParserInterface
from _delb.parser.lxml import LxmlParser
from _delb.parser.utils import _EncodingDetectingReader, detect_encoding

if TYPE_CHECKING:
    from collections.abc import Iterator

    from _delb.typing import BinaryReader, InputStream


class ParserOptions(NamedTuple):
    """
    The configuration options that define an XML parser's behaviour.

    :param encoding: An optional encoding that is expected.  This should be used for
                     streams where the encoding is not noted in an XML document
                     declaration or indicated by a BOM for Unicode encodings.
                     It doesn't affect parsing of data that is passed as :class:`str`.
    :param load_referenced_resources: Allows the loading of referenced external DTDs.
    :param reduce_whitespace: :meth:`Reduce the content's whitespace
                                <delb.Document.reduce_whitespace>`.
    :param remove_comments: Ignore comments.
    :param remove_processing_instructions: Don't include processing instructions in the
                                           parsed tree.
    :param unplugged: Don't load referenced resources over network.
    """

    encoding: Optional[str] = None
    load_referenced_resources: bool = False
    reduce_whitespace: bool = False
    remove_comments: bool = False
    remove_processing_instructions: bool = False
    unplugged: bool = False
    parser: Optional[type[XMLEventParserInterface]] = None


def _make_parser(
    options: ParserOptions, *, base_url: str | None, encoding: str
) -> XMLEventParserInterface:
    return (options.parser or LxmlParser)(options, base_url=base_url, encoding=encoding)


def parse_events(
    input_: InputStream, options: ParserOptions, base_url: str | None
) -> Iterator[Event]:
    encoding = options.encoding
    if isinstance(input_, str):
        # TODO this isn't ideal at all
        encoding = "utf-8"
        input_ = BytesIO(input_.encode("utf-8"))

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
    XMLEventParserInterface.__name__,
    ParserOptions.__name__,
)
