from delb import Document


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


def test_css_select_or(files_path):
    document = Document(files_path / "stevenson_treasure_island.xml")

    result = document.css_select("titleStmt title, titleStmt author")

    assert len(result) == 2
    assert {x.local_name for x in result} == {"author", "title"}


def test_results_as_other_type():
    results = sample_document.css_select("node")

    as_list = results.as_list
    assert isinstance(as_list, list)
    assert len(as_list) == 4

    as_tuple = results.as_tuple
    assert isinstance(as_tuple, tuple)
    assert len(as_tuple) == 4

    as_set = results.as_set
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
