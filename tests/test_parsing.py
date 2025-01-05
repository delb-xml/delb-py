import pytest

from delb import (
    new_comment_node,
    new_tag_node,
    parse_tree,
    tag,
)

from tests.utils import assert_equal_trees

c = new_comment_node
t = new_tag_node


@pytest.mark.parametrize("as_bytes", (True, False))
@pytest.mark.parametrize(
    ("in_", "out"),
    (
        (
            "<root><a/>b<c/></root>",
            t("root", children=[tag("a"), "b", tag("c")]),
        ),
        (
            "<root>a<b/></root>",
            t("root", children=["a", tag("b")]),
        ),
        (
            "<root><a/>b</root>",
            t("root", children=[tag("a"), "b"]),
        ),
        (
            "<root>a<b/>c</root>",
            t("root", children=["a", tag("b"), "c"]),
        ),
        (
            "<root><a>c</a>b<e/></root>",
            t("root", children=[tag("a", ["c"]), "b", tag("e")]),
        ),
        (
            "<root><a><c/></a>b<e/></root>",
            t("root", children=[tag("a", [tag("c")]), "b", tag("e")]),
        ),
        (
            "<root><a>c<d/></a>b<e/></root>",
            t("root", children=[tag("a", ["c", tag("d")]), "b", tag("e")]),
        ),
        (
            "<root><a><c/>d</a>b<e/></root>",
            t("root", children=[tag("a", [tag("c"), "d"]), "b", tag("e")]),
        ),
        (
            "<node>foo<child><!--bar--></child></node>",
            t("node", children=("foo", tag("child", [c("bar")]))),
        ),
    ),
)
def test_parse_tree(in_, out, as_bytes):
    if as_bytes:
        in_ = in_.encode()
    assert_equal_trees(parse_tree(in_), out)
