import re

import pytest

from _delb.xpath.tokenizer import named_group, string_pattern, tokenize, TokenType


@pytest.mark.parametrize(
    ("_in", "out"),
    (
        ("foo", ""),
        ("'foo'", "'foo'"),
        ("'foo", ""),
        ("foo'", ""),
        ("fo'o", ""),
        ("bar'foo'bar", "'foo'"),
        (r"'fo\'o'", r"'fo\'o'"),
        (r'"fo\"o"', r'"fo\"o"'),
    ),
)
def test_string_pattern(_in, out):
    result = re.compile(named_group("STRING", string_pattern), re.UNICODE).search(_in)
    if out:
        assert result is not None
        assert result.group("STRING") == out


@pytest.mark.parametrize(
    (
        "_in",
        "out",
    ),
    (
        (
            "starts-with(@foo,'a(b(c)')",
            ["starts-with", "(", "@", "foo", ",", "'a(b(c)'", ")"],
        ),
        (
            './/a[@href and not(starts-with(@href, "https://"))]',
            [
                ".",
                "//",
                "a",
                "[",
                "@",
                "href",
                "and",
                "not",
                "(",
                "starts-with",
                "(",
                "@",
                "href",
                ",",
                '"https://"',
                ")",
                ")",
                "]",
            ],
        ),
        (
            './entry/sense/cit[@type="translation"][@lang="en"]',
            [
                ".",
                "/",
                "entry",
                "/",
                "sense",
                "/",
                "cit",
                "[",
                "@",
                "type",
                "=",
                '"translation"',
                "]",
                "[",
                "@",
                "lang",
                "=",
                '"en"',
                "]",
            ],
        ),
        ('.//pb[@n="I"]', [".", "//", "pb", "[", "@", "n", "=", '"I"', "]"]),
    ),
)
def test_tokenize(_in, out):
    assert [x.string for x in tokenize(_in)] == out


@pytest.mark.parametrize(
    ("_in", "out"),
    (
        ("'foo'", TokenType.STRING),
        ("foo", TokenType.NAME),
        (" foo", TokenType.NAME),
        ("f-o-o", TokenType.NAME),
        ("f.oo", TokenType.NAME),
        ("🔥", TokenType.NAME),
        ("/", TokenType.SLASH),
        ("//", TokenType.SLASH_SLASH),
        ("*", TokenType.ASTERISK),
        ("::", TokenType.AXIS_SEPARATOR),
        (":", TokenType.COLON),
        ("..", TokenType.DOT_DOT),
        (".", TokenType.DOT),
        ("[", TokenType.OPEN_BRACKET),
        ("]", TokenType.CLOSE_BRACKET),
        ("@", TokenType.STRUDEL),
        ("=", TokenType.OTHER_OPS),
        ("(", TokenType.OPEN_PARENS),
        (" (", TokenType.OPEN_PARENS),
        (")", TokenType.CLOSE_PARENS),
        (",", TokenType.COMMA),
        (", ", TokenType.COMMA),
        ("|", TokenType.PASEQ),
        ("+", TokenType.OTHER_OPS),
        ("-", TokenType.OTHER_OPS),
        ("!=", TokenType.OTHER_OPS),
        (" != ", TokenType.OTHER_OPS),
        ("<", TokenType.OTHER_OPS),
        (">", TokenType.OTHER_OPS),
        ("<=", TokenType.OTHER_OPS),
        (">=", TokenType.OTHER_OPS),
        ("0", TokenType.NUMBER),
        ("99", TokenType.NUMBER),
    ),
)
def test_type_detection(_in, out):
    result = tokenize(_in)
    assert len(result) == 1, result
    assert result[0].type is out


@pytest.mark.parametrize("_in", (" ", "\t", "\n"))
def test_ignored_whitespace(_in):
    assert not tokenize(_in)
