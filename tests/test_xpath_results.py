import pytest

from delb import Document


def test_results_as_sequences(queries_sample):
    results = queries_sample.css_select("node")

    as_list = results.as_list()
    assert isinstance(as_list, list)
    assert len(as_list) == 4

    as_tuple = results.as_tuple
    assert isinstance(as_tuple, tuple)
    assert len(as_tuple) == 4


def test_results_equality():
    document = Document(
        """\
        <root>
            <s corresp="src:tlaIBUBd4DTggLNoE2MvPgWWka2UdY">
                <w corresp="src:tlaIBUBdzQ3wWIW60TVhNy3cRxYmgg"><unclear/></w>
                <w corresp="src:tlaIBUBd7n0fy1OPU1DjVU66j2B4Qc"><unclear/></w>
            </s>
        </root>
        """
    )
    word_nodes = document.css_select("s w")
    assert word_nodes == word_nodes.filtered_by(lambda n: True)
    assert word_nodes == word_nodes.as_list()
    assert word_nodes == tuple(reversed(word_nodes.as_list()))
    assert word_nodes != 2 * word_nodes.as_list()
    assert [document.root] == document.css_select("root")
    with pytest.raises(TypeError):
        document.css_select("root") == document.root


def test_results_filtered_by(queries_sample):
    def has_n_attribute(node):
        return node.attributes.get("n") is not None

    assert queries_sample.css_select("node").filtered_by(has_n_attribute).size == 3


def test_results_first_and_last(queries_sample):
    assert queries_sample.css_select("node").first.attributes["n"] == "1"
    assert queries_sample.css_select("node").last.attributes["n"] == "3"


def test_results_size(queries_sample):
    assert queries_sample.css_select("node").size == 4
