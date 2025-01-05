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

from abc import abstractmethod

from enum import auto, IntEnum
from typing import TYPE_CHECKING, BinaryIO, NamedTuple, Protocol, TypeAlias


if TYPE_CHECKING:
    from collections.abc import Iterator

    from _delb.parser import ParserOptions
    from _delb.typing import _AttributesData


class EventType(IntEnum):
    Comment = auto()
    ProcessingInstruction = auto()
    TagStart = auto()
    TagEnd = auto()
    Text = auto()


class TagEventData(NamedTuple):
    namespace: str
    local_name: str
    attributes: _AttributesData


Event: TypeAlias = tuple[EventType, str | tuple[str, str] | TagEventData]


class XMLEventParserInterface(Protocol):
    @abstractmethod
    def __init__(self, options: ParserOptions):
        raise NotImplementedError

    @abstractmethod
    def parse(self, data: BinaryIO) -> Iterator[Event]:
        raise NotImplementedError


__all__ = ("Event", XMLEventParserInterface.__name__)
