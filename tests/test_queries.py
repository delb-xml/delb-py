import pytest
from lxml.etree import XPathEvalError

from delb import Document, InvalidOperation, is_tag_node, tag


sample_document = Document(
    """\
<root>
    <node n="1"/>
    <node n="2"/>
    <node/>
    <node n="3"/>
</root>
"""
)


def test_css_considers_xml_namespace(files_path):
    document = Document("<root><xml:node/><node/></root>")
    assert document.css_select("xml|node").size == 1

    document = Document(files_path / "tei_marx_manifestws_1848.TEI-P5.xml")
    results = document.css_select("*[xml|id]")
    assert results.size == 1
    results = document.css_select("*[xml|lang]")
    assert results.size == 2


def test_css_select_or(files_path):
    document = Document(files_path / "tei_stevenson_treasure_island.xml")

    result = document.css_select("titleStmt title, titleStmt author")

    assert len(result) == 2
    assert {x.local_name for x in result} == {"author", "title"}


def test_fetch_or_create_by_xpath():
    root = Document("<root><intermediate/></root>").root

    assert str(root.fetch_or_create_by_xpath("./test")) == "<test/>"
    assert str(root) == "<root><intermediate/><test/></root>"

    assert str(root.fetch_or_create_by_xpath("./intermediate/target")) == "<target/>"
    assert str(root) == "<root><intermediate><target/></intermediate><test/></root>"

    assert str(root.fetch_or_create_by_xpath("./intermediate/target")) == "<target/>"
    assert str(root) == "<root><intermediate><target/></intermediate><test/></root>"

    root.append_child(tag("intermediate"))

    with pytest.raises(InvalidOperation):
        root.fetch_or_create_by_xpath("./intermediate")

    with pytest.raises(InvalidOperation):
        root.fetch_or_create_by_xpath("./intermediate/test")


def test_fetch_or_create_by_xpath_with_prefix():
    root = Document("<root xmlns:prfx='http://test.io'><intermediate/></root>").root
    assert (
        str(root.fetch_or_create_by_xpath("./intermediate/prfx:test"))
        == '<prfx:test xmlns:prfx="http://test.io"/>'
    )
    assert (
        str(root) == '<root xmlns:prfx="http://test.io">'
        "<intermediate><prfx:test/></intermediate>"
        "</root>"
    )

    with pytest.raises(XPathEvalError):
        root.fetch_or_create_by_xpath("./unknwn:test")


def test_fetch_or_create_by_xpath_with_attributes():
    root = Document("<root/>").root

    assert (
        str(root.fetch_or_create_by_xpath('./author/name[@type="surname"]'))
        == '<name type="surname"/>'
    )
    assert (
        str(root.fetch_or_create_by_xpath('./author/name[@type="forename"]'))
        == '<name type="forename"/>'
    )

    assert str(
        root.fetch_or_create_by_xpath("./author/name[@type='forename']/transcriptions")
        == "<transcriptions/>"
    )


def test_fetch_or_create_by_xpath_with_multiple_attributes():
    root = Document('<root xmlns:foo="bar"/>').root

    cit = root.fetch_or_create_by_xpath(
        './entry/sense/cit[@type="translation" and @lang="en"]'
    )
    assert str(cit) == '<cit type="translation" lang="en"/>'

    assert (
        root.fetch_or_create_by_xpath(
            './entry/sense/cit[@type="translation"][@lang="en"]'
        )
        is cit
    )


def test_fetch_or_create_by_xpath_with_prefixes_attributes():
    root = Document('<root xmlns:foo="bar"/>').root

    assert (
        str(root.fetch_or_create_by_xpath("./node[@foo:attr='value']"))
        == '<node xmlns:foo="bar" foo:attr="value"/>'
    )
    assert str(root) == '<root xmlns:foo="bar"><node foo:attr="value"/></root>'


@pytest.mark.parametrize(
    "expression",
    (
        "node",
        "./child[0]",
        './child[@locale="en-gb" or @locale="en-us"]',
        "./root/foo|./foo/bar",
        "./root/node/descendant-or-self::node()",
        "./body/div[@hidden]",
        "./root/node/child/../node",
        "./root[foo]",
    ),
)
def test_fetch_or_create_by_xpath_with_invalid_paths(expression):
    node = Document("<node/>").root
    with pytest.raises(InvalidOperation):
        node.fetch_or_create_by_xpath(expression)


def test_location_path_and_xpath_concordance(files_path):
    for doc_path in files_path.glob("*.xml"):
        document = Document(doc_path)

        for node in document.root.child_nodes(is_tag_node, recurse=True):
            queried_nodes = document.xpath(node.location_path)
            assert queried_nodes.size == 1
            assert queried_nodes.first is node


def test_quotes_in_css_selector():
    document = Document('<a href="https://super.test/123"/>')
    assert document.css_select('a[href^="https://super.test/"]').size == 1


def test_results_as_other_type():
    results = sample_document.css_select("node")

    as_list = results.as_list()
    assert isinstance(as_list, list)
    assert len(as_list) == 4

    as_tuple = results.as_tuple
    assert isinstance(as_tuple, tuple)
    assert len(as_tuple) == 4

    as_set = results.as_set()
    assert isinstance(as_set, set)
    assert len(as_list) == 4


def test_results_filtered_by():
    def has_n_attribute(node):
        return node.attributes.get("n") is not None

    assert sample_document.css_select("node").filtered_by(has_n_attribute).size == 3


def test_results_first_and_last():
    assert sample_document.css_select("node").first.attributes["n"] == "1"
    assert sample_document.css_select("node").last.attributes["n"] == "3"


def test_results_size():
    assert sample_document.css_select("node").size == 4
