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
from _delb.grammar import name_pattern


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
    return "|".join(choices)


def named_group(name: str, content: str) -> str:
    return f"(?P<{name}>{content})"


def named_group_reference(name: str) -> str:
    return f"(?P={name})"


string_pattern: Final = (
    named_group("stringDelimiter", """["']""")  # opening string delimiter
    + "("
    + alternatives(
        r"\\.",  # either a backslash followed by any character
        r"[^\\]",  # or any one character except a backslash
    )
    + ")"
    + "*?"  # non-greedy until the reoccurring opening delimiter as:
    + named_group_reference("stringDelimiter")  # closing string delimiter
)


iterate_tokens: Final = re.compile(
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
            "OTHER_OPS", alternatives(r"\+", "-", "!=", "<=", ">=", "<", ">", "==", "=")
        ),
        # https://www.w3.org/TR/REC-xml/#NT-S
        named_group("WHITESPACE", "[ \n\t]+"),
        named_group("ERROR", ".+"),
    ),
    re.UNICODE,
).finditer


# interface


@lru_cache(64)  # TODO? configurable
def tokenize(expression: str) -> Sequence[Token]:
    result = []

    for match in iterate_tokens(expression):
        assert match is not None
        match token_type := match.lastgroup:
            case "ERROR":
                raise XPathParsingError(
                    position=match.start(), message="Unrecognized token."
                )
            case "WHITESPACE":
                pass
            case _:
                assert token_type is not None
                result.append(
                    Token(
                        position=match.start(),
                        string=match.group(),
                        type=TokenType[token_type],
                    )
                )

    return result


__all__ = (tokenize.__name__,)  # type: ignore
