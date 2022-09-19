from delb import Document


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


def test_quotes_in_css_selector():
    document = Document('<a href="https://super.test/123"/>')
    assert document.css_select('a[href^="https://super.test/"]').size == 1
    assert document.css_select('a[href|="https://super.test/123"]').size == 1
    assert document.css_select('a[href*="super"]').size == 1
    assert document.css_select('a:not([href|="https"])').size == 1
