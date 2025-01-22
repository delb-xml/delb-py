from typing import Final


from delb import Document

from tests.utils import assert_nodes_are_in_document_order

TEI_NAMESPACE: Final = "http://www.tei-c.org/ns/1.0"


def test_as_sequences(queries_sample):
    results = queries_sample.css_select("node")

    as_list = results.as_list()
    assert isinstance(as_list, list)
    assert len(as_list) == 4

    as_tuple = results.as_tuple
    assert isinstance(as_tuple, tuple)
    assert len(as_tuple) == 4


def test_document_order(files_path):
    document = Document(files_path / "marx_manifestws_1848.TEI-P5.xml")
    ordered_nodes = document.xpath("//pb").in_document_order()
    assert all(n.local_name == "pb" for n in ordered_nodes)
    assert_nodes_are_in_document_order(*ordered_nodes)


def test_equality():
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


def test_filtered_by(queries_sample):
    def has_n_attribute(node):
        return node.attributes.get("n") is not None

    assert queries_sample.css_select("node").filtered_by(has_n_attribute).size == 3


def test_first_and_last(queries_sample):
    assert queries_sample.css_select("node").first.attributes["n"] == "1"
    assert queries_sample.css_select("node").last.attributes["n"] == "3"

    assert queries_sample.css_select("note").first is None
    assert queries_sample.css_select("note").last is None


def test_size(queries_sample):
    assert queries_sample.css_select("node").size == 4
