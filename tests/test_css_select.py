import pytest
from typing import Final

from delb import Document
from _delb.xpath import _css_to_xpath


TEI_NAMESPACE: Final = "http://www.tei-c.org/ns/1.0"


def test_css_select_or(files_path):
    document = Document(files_path / "tei_stevenson_treasure_island.xml")

    result = document.css_select("titleStmt title, titleStmt author")

    assert len(result) == 2
    assert {x.local_name for x in result} == {"author", "title"}


@pytest.mark.parametrize(("in_", "out"), (("metadata", "descendant::metadata"),))
def test_css_to_xpath(in_, out):
    assert _css_to_xpath(in_) == out


def test_namespace():
    document = Document('<root xmlns="isbn:1000" xmlns:p="file:/"><a/><p:a/></root>')

    results = document.css_select("a", namespaces=None)
    assert results.size == 1
    assert results.first.index == 0

    results = document.css_select("a", namespaces={None: "isbn:1000", "p": "file:/"})
    assert results.size == 1
    assert results.first.index == 0

    results = document.css_select("a", namespaces={"": "isbn:1000", "p": "file:/"})
    assert results.size == 1
    assert results.first.index == 0

    results = document.css_select("p|a", namespaces={"p": "isbn:1000"})
    assert results.size == 1
    assert results.first.index == 0

    results = document.css_select("p|a", namespaces={"p": "file:/"})
    assert results.size == 1
    assert results.first.index == 1


def test_quotes_in_css_selector():
    document = Document('<root><a href="https://super.test/123"/></root>')
    assert document.css_select('a[href^="https://super.test/"]').size == 1
    assert document.css_select('a[href|="https://super.test/123"]').size == 1
    assert document.css_select('a[href*="super"]').size == 1
    assert document.css_select('a:not([href|="https"])').size == 1


def test_xml_namespace(files_path):
    document = Document("<root><xml:node/><node/></root>")
    assert document.css_select("xml|node").size == 1

    document = Document(files_path / "marx_manifestws_1848.TEI-P5.xml")
    results = document.css_select("*[xml|id]")
    assert results.size == 1
    results = document.css_select("*[xml|lang]")
    assert results.size == 2
