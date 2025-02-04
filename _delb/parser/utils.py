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
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from _delb.typing import BinaryReader


BOM_TO_ENCODING_NAME: Final = (
    (4, codecs.BOM_UTF32_LE, "utf-32-le"),
    (4, codecs.BOM_UTF32_BE, "utf-32-be"),
    (3, codecs.BOM_UTF8, "utf-8"),
    (2, codecs.BOM_UTF16_LE, "utf-16-le"),
    (2, codecs.BOM_UTF16_BE, "utf-16-be"),
)


match_encoding: Final = re.compile(
    rb"""<\?xml\sversion=["']1\.0["']\sencoding=["']([A-Za-z0-9_-]+)["']\?>"""
).match


def detect_encoding(stream: bytes) -> str | None:
    if (match := match_encoding(stream)) is not None:
        return match.group(1).decode("ascii")
    else:
        for bom_size, bom, name in BOM_TO_ENCODING_NAME:
            if stream[:bom_size] == bom:
                return name
        else:
            return None


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
