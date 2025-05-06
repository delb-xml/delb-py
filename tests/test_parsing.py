import pytest
from lxml import etree
from urllib.error import HTTPError

from delb import (
    Document,
    ParserOptions,
    new_comment_node,
    new_tag_node,
    parse_tree,
    tag,
)
from delb.exceptions import (
    FailedDocumentLoading,
    ParsingValidityError,
    ParsingProcessingError,
)
from _delb.plugins import plugin_manager
from _delb.plugins.core_loaders import path_loader

from tests.conftest import FILES_PATH, XML_FILES
from tests.utils import assert_equal_trees


assert len(AVAILABLE_PARSERS := tuple(plugin_manager.parsers)) == 2

pytestmark = pytest.mark.parametrize("parser", AVAILABLE_PARSERS)


c = new_comment_node
t = new_tag_node


def test_attributes(parser):
    root = parse_tree(
        """<root xmlns="http://fo.org" a="b"/>""",
        ParserOptions(preferred_parsers=parser),
    )
    assert "{http://fo.org}a" in root.attributes._etree_attrib
    assert ("http://fo.org", "a") in root.attributes


@pytest.mark.parametrize(
    ("unplugged", "exception"),
    (
        (True, {"expat": ParsingProcessingError, "lxml": etree.XMLSyntaxError}),
        (False, {"expat": HTTPError, "lxml": etree.XMLSyntaxError}),
    ),
)
def test_dtd_from_web(parser, unplugged, exception):
    try:
        Document(
            FILES_PATH / "web_dtd.ignored_xml",
            parser_options=ParserOptions(
                load_referenced_resources=True,
                preferred_parsers=parser,
                unplugged=unplugged,
            ),
        )
    except FailedDocumentLoading as e:
        assert isinstance(e.excuses[path_loader], exception[parser])  # noqa: PT017
    else:
        raise AssertionError("No exception raised.")


# TODO figure out why the expat parser uses an SSL socket (and leaves it unclosed)
@pytest.mark.filterwarnings("ignore:unclosed:ResourceWarning")
@pytest.mark.parametrize("load_referenced_resources", (True, False))
def test_external_entity_declaration(
    files_path,
    load_referenced_resources,
    parser,
):
    try:
        document = Document(
            files_path / "external_dtd.xml",
            parser_options=ParserOptions(
                load_referenced_resources=load_referenced_resources,
                preferred_parsers=parser,
            ),
        )
    except Exception:
        assert not load_referenced_resources
    else:
        assert load_referenced_resources
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
            preferred_parsers=parser,
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
    assert_equal_trees(
        parse_tree(in_, options=ParserOptions(preferred_parsers=parser)), out
    )


@pytest.mark.parametrize("reduced_content", (True, False))
@pytest.mark.parametrize("file", XML_FILES)
def test_parse_xml_documents(file, parser, reduced_content):
    Document(
        file,
        parser_options=ParserOptions(
            load_referenced_resources="external" in file.name,
            preferred_parsers=parser,
            reduce_whitespace=reduced_content,
            remove_comments=reduced_content,
            remove_processing_instructions=reduced_content,
        ),
    )


def test_redundant_xml_ids(parser):
    exception = {"expat": ParsingValidityError, "lxml": etree.XMLSyntaxError}[parser]
    with pytest.raises(exception):
        parse_tree(
            "<root xml:id='a'><node xml:id='a'/></root>",
            options=ParserOptions(preferred_parsers=parser),
        )


def test_safety(parser):
    # these are taken from Christian Heimes' test suite for the defused-xml project.
    # there's no expectation with regards to the resulting contents, it must be solely
    # ensured that nothing blows up.

    cascade = Document(
        """\
    <!DOCTYPE cascade [
    <!ENTITY a "1234567890" >
    <!ENTITY b "&a;&a;&a;&a;&a;&a;&a;&a;">
    <!ENTITY c "&b;&b;&b;&b;&b;&b;&b;&b;">
    <!ENTITY d "&c;&c;&c;&c;&c;&c;&c;&c;">
    ]>
    <cascade>&d;</cascade>""",
        parser_options=ParserOptions(preferred_parsers=parser),
    )
    assert len(cascade.root.full_text) == 5_120

    try:
        Document(
            """\
        <!DOCTYPE cyclic [
        <!ENTITY a "123 &b;" >
        <!ENTITY b "&a;">
        ]>
        <cyclic>&a;</cyclic>""",
            parser_options=ParserOptions(preferred_parsers=parser),
        )
    except Exception:
        pass
    else:
        raise AssertionError

    try:
        Document(
            '<!DOCTYPE quadratic [ <!ENTITY a "'
            + "B" * 10_000
            + '" > ]>\n<quadratic>'
            + "&a;" * 1_000
            + "</quadratic>",
            parser_options=ParserOptions(preferred_parsers=parser),
        )
    except Exception:
        pass
    else:
        raise AssertionError
