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

from dataclasses import dataclass
from io import BytesIO
from typing import TYPE_CHECKING, Optional

from _delb.parser.base import Event, EventType, XMLEventParserInterface
from _delb.parser.lxml import LxmlParser

if TYPE_CHECKING:
    from collections.abc import Iterator

    from _delb.typing import InputStream


@dataclass
class ParserOptions:
    """
    The configuration options that define an XML parser's behaviour.

    :param reduce_whitespace: :meth:`Reduce the content's whitespace
                                <delb.Document.reduce_whitespace>`.
    :param remove_comments: Ignore comments.
    :param remove_processing_instructions: Don't include processing instructions in the
                                           parsed tree.
    :param resolve_entities: Resolve entities.
    :param unplugged: Don't load referenced resources over network.
    """

    # TODO base_url?
    reduce_whitespace: bool = False
    remove_comments: bool = False
    remove_processing_instructions: bool = False
    resolve_entities: bool = True
    unplugged: bool = False
    parser: Optional[type[XMLEventParserInterface]] = None

    def _make_parser(self) -> XMLEventParserInterface:
        parser = self.parser or LxmlParser
        return parser(self)


def parse_events(input_: InputStream, options: ParserOptions) -> Iterator[Event]:
    if isinstance(input_, str):
        input_ = BytesIO(input_.encode())

    elif isinstance(input_, bytes):
        input_ = BytesIO(input_)

    yield from options._make_parser().parse(input_)


__all__ = (
    "Event",
    "EventType",
    XMLEventParserInterface.__name__,
    ParserOptions.__name__,
)
