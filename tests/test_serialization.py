from pytest import mark

from delb import (
    new_comment_node,
    new_processing_instruction_node,
    new_tag_node,
    StringSerializationConfigurator,
    TextNode,
)
from _delb.nodes import DETACHED


@mark.parametrize(
    ("declarations", "_in", "out"),
    (
        ({}, new_comment_node("foo"), "<!--foo-->"),
        ({}, new_processing_instruction_node("foo", 'bar="0"'), '<?foo bar="0"?>'),
        ({}, new_tag_node("foo"), "<foo/>"),
        ({}, new_tag_node("foo", {"bar": "0"}), '<foo bar="0"/>'),
        ({}, TextNode("foo", DETACHED), "foo"),
        (
            {None: "ftp://foo.bar"},
            new_tag_node("n", {}, "ftp://foo.bar"),
            '<n xmlns="ftp://foo.bar"/>',
        ),
        (
            {"p": "ftp://foo.bar"},
            new_tag_node("n", {}, "ftp://foo.bar"),
            '<p:n xmlns:p="ftp://foo.bar"/>',
        ),
    ),
)
def test_single_nodes(declarations, _in, out):
    StringSerializationConfigurator.namespaces = declarations
    assert str(_in) == out
