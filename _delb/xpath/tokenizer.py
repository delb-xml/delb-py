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
from enum import Enum
from functools import lru_cache
from typing import TYPE_CHECKING, NamedTuple

from _delb.exceptions import XPathParsingError

if TYPE_CHECKING:
    from collections.abc import Sequence
    from typing import Final


# constants & data structures

TokenType: Final = Enum(
    "TokenType",
    "STRING NAME SLASH_SLASH SLASH ASTERISK AXIS_SEPARATOR COLON DOT_DOT DOT "
    "OPEN_BRACKET CLOSE_BRACKET STRUDEL EQUALS OPEN_PARENS CLOSE_PARENS COMMA PASEQ "
    "OTHER_OPS NUMBER WHITESPACE",
)


COMPLEMENTING_TOKEN_TYPES: Final = {
    TokenType.OPEN_BRACKET: TokenType.CLOSE_BRACKET,
    TokenType.OPEN_PARENS: TokenType.CLOSE_PARENS,
}


class Token(NamedTuple):
    position: int
    string: str
    type: TokenType


# token definition


def alternatives(*choices: str) -> str:
    return "(" + "|".join(choices) + ")"


def named_group(name: str, content: str) -> str:
    return f"(?P<{name}>{content})"


def named_group_reference(name: str) -> str:
    return f"(?P={name})"


string_pattern: Final = (
    named_group("stringDelimiter", """["']""")  # opening string delimiter
    + alternatives(
        r"\\.",  # either a backslash followed by any character
        r"[^\\]",  # or any one character except a backslash
    )
    + "*?"  # non-greedy until the reoccurring opening delimiter as:
    + named_group_reference("stringDelimiter")  # closing string delimiter
)

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
name_characters = name_start_characters + r"\.0-9\u00b7\u0300-\u036f\u203f-\u2040-"
name_pattern = f"[{name_start_characters}][{name_characters}]*"


grab_token: Final = re.compile(
    alternatives(
        named_group("STRING", string_pattern),
        named_group("NUMBER", r"\d+"),
        named_group("NAME", name_pattern),
        named_group("SLASH_SLASH", "//"),
        named_group("SLASH", "/"),
        named_group("ASTERISK", r"\*"),
        named_group("AXIS_SEPARATOR", "::"),
        named_group("COLON", ":"),
        named_group("DOT_DOT", r"\.\."),
        named_group("DOT", r"\."),
        named_group("OPEN_BRACKET", r"\["),
        named_group("CLOSE_BRACKET", r"\]"),
        named_group("STRUDEL", "@"),
        named_group("OPEN_PARENS", r"\("),
        named_group("CLOSE_PARENS", r"\)"),
        named_group("COMMA", ","),
        named_group("PASEQ", r"\|"),
        named_group(
            "OTHER_OPS", alternatives(r"\+", "-", "!=", "<=", ">=", "<", ">", "=")
        ),
        # https://www.w3.org/TR/REC-xml/#NT-S
        named_group("WHITESPACE", "[ \n\t]+"),
        named_group("ERROR", ".*"),
    ),
    re.UNICODE,
).search


# interface


@lru_cache(64)  # TODO? configurable
def tokenize(expression: str) -> Sequence[Token]:
    result = []
    index = 0
    end = len(expression)

    while index < end:
        match = grab_token(expression, pos=index)
        assert match is not None

        if match.groupdict().get("ERROR") is not None:
            raise XPathParsingError(position=index, message="Unrecognized token.")

        for token_type, value in match.groupdict().items():
            if value is not None:
                break
        else:  # pragma: no cover
            raise RuntimeError

        token = match[token_type]
        assert isinstance(token, str)

        if token_type != "WHITESPACE":
            result.append(
                Token(position=index, string=token, type=getattr(TokenType, token_type))
            )

        index += len(token)

    return result


__all__ = (tokenize.__name__,)  # type: ignore
