import pytest

from delb import (
    ParserOptions,
    new_comment_node,
    new_tag_node,
    parse_nodes,
    parse_tree,
    tag,
)
from _delb.parser.expat import ExpatParser
from _delb.parser.lxml import LxmlParser


from tests.conftest import XML_FILES
from tests.utils import assert_equal_trees


pytestmark = pytest.mark.parametrize("parser", (ExpatParser, LxmlParser))


c = new_comment_node
t = new_tag_node


@pytest.mark.parametrize("extra", ("<!-- B -->", "<?B B?>"))
def test_ignoring_comments_and_pis(extra, parser):
    # and that whitespace is trimmed correctly in these cases
    result = parse_tree(
        f"<node> A{extra}C </node>",
        options=ParserOptions(
            reduce_whitespace=True,
            remove_comments=True,
            remove_processing_instructions=True,
            parser=parser,
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
def test_parse_tree(in_, out, as_bytes, parser):
    if as_bytes:
        in_ = in_.encode()
    assert_equal_trees(parse_tree(in_, options=ParserOptions(parser=parser)), out)


@pytest.mark.parametrize("reduced_content", (True, False))
@pytest.mark.parametrize("file", XML_FILES)
def test_parse_xml_documents(file, parser, reduced_content):
    with file.open("rb") as f:
        nodes = list(
            parse_nodes(
                f,
                options=ParserOptions(
                    parser=parser,
                    reduce_whitespace=reduced_content,
                    remove_comments=reduced_content,
                    remove_processing_instructions=reduced_content,
                ),
            )
        )

    assert nodes
