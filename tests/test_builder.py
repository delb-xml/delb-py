import pytest

from delb import parse_tree, tag, ParserOptions
from delb.exceptions import ParsingValidityError


def test_extra_content():
    with pytest.raises(ParsingValidityError):
        parse_tree("<a/><!---->")


def test_invalid_xml_space():
    with pytest.warns(UserWarning, match="xml:space"):
        parse_tree(
            "<root xml:space='x'/>", options=ParserOptions(reduce_whitespace=True)
        )


def test_tag_with_invalid_args():
    with pytest.raises(TypeError):
        tag("a", (0,))
    with pytest.raises(TypeError):
        tag("a", {}, (0,))
    with pytest.raises(ValueError, match=r"Unrecognized arguments\."):
        tag()
    with pytest.raises(ValueError, match=r"Unrecognized arguments\."):
        tag("a", {}, (), ())
