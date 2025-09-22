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

import re
from typing import Final


# constants

# https://www.w3.org/TR/REC-xml/#NT-Char
char: Final = r"(?s)[\u0009\u000a\u000d\u0020-\ud7ff\ue000-\ufffd].*"

# https://www.w3.org/TR/REC-xml-names/#NT-NCName
# https://www.w3.org/TR/REC-xml/#NT-Name
name_start_characters: Final = (
    "A-Z_a-z"
    r"\u00c0-\u00d6\u00d8-\u00f6\u00f8-\u02ff\u0370-\u037d\u037f-\u1fff"
    r"\u200c-\u200d\u2070-\u218f\u2c00-\u2fef"
    r"\u3001-\ud7ff"
    r"\uf900-\ufdcf\ufdf0-\ufffd"
    r"\U00010000-\U000effff"
)
name_characters: Final = (
    name_start_characters + r"\.0-9\u00b7\u0300-\u036f\u203f-\u2040-"
)
name_pattern: Final = f"[{name_start_characters}][{name_characters}]*"


# functions

_is_xml_char: Final = re.compile(char).fullmatch
_is_xml_name: Final = re.compile(name_pattern).fullmatch
