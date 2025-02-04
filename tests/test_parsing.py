import pytest
from lxml import etree

from delb import (
    Document,
    ParserOptions,
    new_comment_node,
    new_tag_node,
    parse_tree,
    tag,
)
from delb.exceptions import ParsingError
from _delb.parser.expat import ExpatParser
from _delb.parser.lxml import LxmlParser

from tests.conftest import XML_FILES
from tests.utils import assert_equal_trees


pytestmark = pytest.mark.parametrize("parser", (ExpatParser, LxmlParser))


c = new_comment_node
t = new_tag_node


def test_external_entity_declaration(files_path, parser):
    document = Document(
        files_path / "external_dtd.xml", parser_options=ParserOptions(parser=parser)
    )
    assert document.root.full_text == "schüppsen"


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


def test_internal_entity_declaration(files_path, parser):
    document = Document(files_path / "serialization-example-input.xml")
    title = document.css_select("title").first
    assert title.full_text.startswith("Ü")


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
    Document(
        file,
        parser_options=ParserOptions(
            parser=parser,
            reduce_whitespace=reduced_content,
            remove_comments=reduced_content,
            remove_processing_instructions=reduced_content,
        ),
    )


def test_redundant_xml_ids(parser):
    exception = {"expat": ParsingError, "lxml": etree.XMLSyntaxError}[parser]
    with pytest.raises(exception):
        parse_tree(
            "<root xml:id='a'><node xml:id='a'/></root>",
            options=ParserOptions(parser=parser),
        )
