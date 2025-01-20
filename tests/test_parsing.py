import pytest

from delb import (
    ParserOptions,
    new_comment_node,
    new_tag_node,
    parse_tree,
    tag,
)

from tests.utils import assert_equal_trees

c = new_comment_node
t = new_tag_node


@pytest.mark.parametrize("extra", ("<!-- B -->", "<?B B?>"))
def test_ignoring_comments_and_pis(extra):
    # and that whitespace is trimmed correctly in these cases
    result = parse_tree(
        f"<node> A{extra}C </node>",
        options=ParserOptions(
            reduce_whitespace=True,
            remove_comments=True,
            remove_processing_instructions=True,
        ),
    )
    assert len(result) == 1
    assert result.first_child.content == "AC"


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
