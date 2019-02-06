import pytest

from lxml_domesque import Document, InvalidOperation


def test_invalid_document():
    with pytest.raises(ValueError):
        Document(0)


def test_set_root():
    document = Document("<root><node/></root>")
    document.root = document.root[0].detach()
    assert str(document) == "<node/>"

    document_2 = Document("<root><replacement/>parts</root>")
    with pytest.raises(InvalidOperation):
        document.root = document_2.root[0]
