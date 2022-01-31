import pkg_resources
import pytest
from lxml.etree import XPathEvalError

from delb import Document, InvalidOperation, is_tag_node, tag


DELB_VERSION = pkg_resources.get_distribution("delb").parsed_version.release


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
    root = Document("<root/>").root

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


def test_fetch_or_create_by_xpath_with_predicates_in_parentheses():
    root = Document("<root/>").root

    cit = root.fetch_or_create_by_xpath(
        './entry/sense/cit[((@type="translation") and (@lang="en"))]'
    )
    assert (
        root.fetch_or_create_by_xpath(
            './entry/sense/cit[(@type="translation")][((@lang="en"))]'
        )
        is cit
    )
    assert root.css_select('entry > sense > cit[lang="en"]').size == 1


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
    assert document.css_select('a[href|="https://super.test/123"]').size == 1
    assert document.css_select('a[href*="super"]').size == 1

    # TODO
    if DELB_VERSION >= (0, 4):
        assert document.css_select('a:not([href|="https"])').size == 1
        # TODO specify an `ends-with` function for XPath
        assert document.css_select('a[href$="123"]').size == 1


def test_results_as_other_type(queries_sample):
    results = queries_sample.css_select("node")

    as_list = results.as_list()
    assert isinstance(as_list, list)
    assert len(as_list) == 4

    as_tuple = results.as_tuple
    assert isinstance(as_tuple, tuple)
    assert len(as_tuple) == 4


def test_results_euqality():
    document = Document(
        """\
        <root>
            <s corresp="src:tlaIBUBd4DTggLNoE2MvPgWWka2UdY">
                <w corresp="src:tlaIBUBdzQ3wWIW60TVhNy3cRxYmgg"><unclear/></w>
                <w corresp="src:tlaIBUBd7n0fy1OPU1DjVU66j2B4Qc"><unclear/></w>
                <w corresp="src:tlaIBUBdzMdqTkhlEFpidr4rYPFyro"><unclear/></w>
                <w corresp="src:tlaIBUBd8yCk7rXFEayk6Xvs3N1jXE"><unclear/></w>
                <w corresp="src:tlaIBUBdyjtg3DJX0rwjyrdHZc26is"><unclear/></w>
                <w corresp="src:tlaIBUBd7UZxeumekGAks0Y5ht3nvs"><unclear/></w>
                <w corresp="src:tlaIBUBd4NQUh0FikJ0stCGrcxq9wk"><unclear/></w>
                <w corresp="src:tlaIBUBd7VHAfkj20bDsv3QzaQ4eoo"><unclear/></w>
                <w corresp="src:tlaIBUBd5L0JpJVZUOWoGFGhqXAfqc"><unclear/></w>
                <w corresp="src:tlaIBUBd9zrhmbxrkyqpG7t84kiw2s"><unclear/></w>
                <w corresp="src:tlaIBUBd18UraAwdkCUgzqNsZplqIw"><unclear/></w>
                <w corresp="src:tlaIBUBd8EjhpjvSERfoCg6pz5qYxc"><unclear/></w>
                <w corresp="src:tlaIBUBdQbsUzWoU0ZAg6KyIT74EPU"><unclear/></w>
                <w corresp="src:tlaIBUBd4C0OAENyE3Ti62GjqGFmto"><unclear/></w>
                <w corresp="src:tlaIBUBd8XAOdLv8k7WiQ1f7ZFe3IQ"><unclear/></w>
                <w corresp="src:tlaIBUBd37vHGdUYkiYqNF8ExKiO6M"><unclear/></w>
            </s>
        </root>
        """
    )
    words = document.css_select("s w")
    assert words == words.filtered_by(lambda n: True)


def test_results_filtered_by(queries_sample):
    def has_n_attribute(node):
        return node.attributes.get("n") is not None

    assert queries_sample.css_select("node").filtered_by(has_n_attribute).size == 3


def test_results_first_and_last(queries_sample):
    assert queries_sample.css_select("node").first.attributes["n"] == "1"
    assert queries_sample.css_select("node").last.attributes["n"] == "3"


def test_results_size(queries_sample):
    assert queries_sample.css_select("node").size == 4
