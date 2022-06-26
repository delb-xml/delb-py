import re
from enum import Enum
from functools import lru_cache
from typing import NamedTuple, Sequence


# constants & data structures
from _delb.exceptions import InvalidXPathToken

TokenType = Enum(
    "TokenType",
    "STRING NAME SLASH_SLASH SLASH ASTERISK AXIS_SEPARATOR COLON DOT_DOT DOT "
    "OPEN_BRACKET CLOSE_BRACKET STRUDEL EQUALS OPEN_PARENS CLOSE_PARENS COMMA PASEQ "
    "OTHER_OPS NUMBER WHITESPACE",
)


class Token(NamedTuple):
    index: int
    string: str
    type: TokenType


# token definition


def alternatives(*choices: str) -> str:
    return "(" + "|".join(choices) + ")"


def named_group(name: str, content: str) -> str:
    return f"(?P<{name}>{content})"


def named_group_reference(name: str) -> str:
    return f"(?P={name})"


string_pattern = (
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
name_start_characters = (
    "A-Z_a-z"
    r"\u00c0-\u00d6\u00d8-\u00f6\u00f8-\u02ff\u0370-\u037d\u037f-\u1fff"
    r"\u200c-\u200d\u2070-\u218f\u2c00-\u2fef"
    r"\u3001-\ud7ff"
    r"\uf900-\ufdcf\ufdf0-\ufffd"
    r"\U00010000-\U000effff"
)
name_characters = name_start_characters + r"\.0-9\u00b7\u0300-\u036f\u203f-\u2040-"
name_pattern = f"[{name_start_characters}][{name_characters}]*"


grab_token = re.compile(
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
        named_group("OTHER_OPS", alternatives(r"\+", "-", "!=", "<=", ">=", "<", ">")),
        named_group("EQUALS", "="),
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
        match = grab_token(expression, index)

        if (token := match.groupdict().get("ERROR")) is not None:
            raise InvalidXPathToken(index, token)

        for type_name, token_type in TokenType.__members__.items():
            if (token := match.groupdict().get(type_name)) is not None:
                result.append(Token(index=index, string=token, type=token_type))
                break

        index += len(token)

    return result


__all__ = (tokenize.__name__,)
