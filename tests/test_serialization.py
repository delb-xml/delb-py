from pytest import mark

from delb import (
    new_comment_node,
    new_processing_instruction_node,
    new_tag_node,
    TextNode,
)
from _delb.nodes import DETACHED


@mark.parametrize(
    ("_in", "out"),
    (
        (new_comment_node("foo"), "<!--foo-->"),
        (new_processing_instruction_node("foo", 'bar="0"'), '<?foo bar="0"?>'),
        (new_tag_node("foo"), "<foo/>"),
        (TextNode("foo", DETACHED), "foo"),
    ),
)
def test_single_nodes(_in, out):
    assert str(_in) == out
