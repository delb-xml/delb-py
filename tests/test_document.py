import pytest

from lxml_domesque import Document


def test_invalid_document():
    with pytest.raises(ValueError):
        Document(0)


def test_set_root():
    document = Document("<root><node/></root>")
    node = document.root[0]
    document.root = node
    assert str(document) == "<node/>"
