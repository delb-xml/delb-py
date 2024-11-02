import gc

import pytest

from delb import (
    Document,
    DocumentMixinBase,
    TagNode,
    new_comment_node,
    new_processing_instruction_node,
)
from delb.exceptions import FailedDocumentLoading, InvalidOperation

from tests.plugins import PlaygroundDocumentExtension


def test_config_initialization():
    document = Document("<root/>", playground_property="foo")

    assert document.config.playground.initialized is True
    assert document.config.playground.property == "foo"


def test_clone():
    document = Document("<root/>", playground_property="foo")
    document.clone()


def test_contains():
    document_a = Document("<root><a/></root>")
    document_b = Document("<root><a/></root>")

    a = document_a.root[0]
    gc.collect()

    assert a in document_a
    assert a not in document_b


def test_css_select():
    document = Document("<root><a><b/><c/><b/></a></root>")

    results = document.css_select("a b")
    assert len(results) == 2
    assert all(x.local_name == "b" for x in results)

    document = Document('<root xmlns="x" xmlns:y="y"><a><b/><y:c/><b/></a></root>')

    results = document.css_select("a b")
    assert len(results) == 2
    assert all(x.local_name == "b" for x in results)

    results = document.css_select("a y|c")
    assert len(results) == 1
    assert results[0].universal_name == "{y}c"


def test_invalid_document():
    with pytest.raises(FailedDocumentLoading):
        Document(0)


def test_mixin_method():
    document = Document("<root/>", playground_property="foo")
    assert document.playground_method() == "f00"


def test_mro():
    class DocumentSubclass(Document):
        pass

    assert DocumentSubclass.__mro__ == (
        DocumentSubclass,
        Document,
        PlaygroundDocumentExtension,
        DocumentMixinBase,
        object,
    )


def test_root_siblings():
    document = Document("<root/>")
    prologue = document.prologue
    with pytest.deprecated_call():
        assert document.head_nodes is prologue
    epilogue = document.epilogue
    with pytest.deprecated_call():
        assert document.tail_nodes is epilogue

    prologue.append(new_comment_node(" I Roy "))
    prologue.insert(0, new_processing_instruction_node("Blood", "Fire"))

    epilogue.prepend(new_comment_node(" Prince Jazzbo "))
    epilogue.append(new_processing_instruction_node("over", "out"))

    assert len(prologue) == len(epilogue) == 2

    assert str(document) == (
        '<?xml version="1.0" encoding="UTF-8"?><?Blood Fire?>'
        "<!-- I Roy --><root/><!-- Prince Jazzbo --><?over out?>"
    )

    assert prologue[0].target == "Blood"
    assert prologue[-1].content == " I Roy "

    epilogue += [new_comment_node("")]

    with pytest.raises(InvalidOperation):
        epilogue.append("nah")

    with pytest.raises(InvalidOperation):
        epilogue.pop(0)


def test_set_root():
    document = Document("<root><node/></root>")
    document.root = document.root[0].detach()
    assert str(document) == '<?xml version="1.0" encoding="UTF-8"?><node/>'

    document_2 = Document("<root><replacement/>parts</root>")
    with pytest.raises(ValueError, match="detached node"):
        document.root = document_2.root[0]


def test_xpath(files_path):
    document = Document(files_path / "marx_manifestws_1848.TEI-P5.xml")

    for i, page_break in enumerate(document.xpath("//pb")):
        assert isinstance(page_break, TagNode)
        assert page_break.universal_name == "{http://www.tei-c.org/ns/1.0}pb"

    assert i == 22

    for j, page_break in enumerate(document.xpath('.//pb[@n="I"]')):
        assert isinstance(page_break, TagNode)
        assert page_break.universal_name == "{http://www.tei-c.org/ns/1.0}pb"
        assert page_break.attributes["n"] == "I"

    assert j == 0
