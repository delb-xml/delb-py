import gc

import pytest

from delb import (
    Document,
    InvalidOperation,
    TagNode,
    new_comment_node,
    new_processing_instruction_node,
)


def test_cleanup_namespaces():
    document = Document('<root xmlns="D" xmlns:y="Y"><x:a xmlns:x="X"/></root>')

    document.cleanup_namespaces(retain_prefixes=("y",))
    assert str(document) == '<root xmlns="D" xmlns:y="Y"><x:a xmlns:x="X"/></root>'

    document.cleanup_namespaces()
    assert str(document) == '<root xmlns="D"><x:a xmlns:x="X"/></root>'

    document.cleanup_namespaces(namespaces={"x": "X"})
    assert str(document) == '<root xmlns="D" xmlns:x="X"><x:a/></root>'


def test_contains():
    document_a = Document("<root><a/></root>")
    document_b = Document("<root><a/></root>")

    assert document_a.root[0] in document_a
    assert document_a.root[0] not in document_b


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
    assert results[0].qualified_name == "{y}c"


def test_invalid_document():
    with pytest.raises(ValueError):
        Document(0)


def test_object_persistance():
    document = Document(
        "<eegohchivahgahsheiyeelooreepiaphahvaikohdaecobeavepaeyoicuevasan/>"
    )
    document_id = id(document)
    root = document.root

    del document
    gc.collect()
    assert root.document is not None

    del root
    gc.collect()
    for obj in gc.get_objects():
        if id(obj) == document_id and isinstance(obj, Document):
            assert (
                obj.root.local_name
                != "eegohchivahgahsheiyeelooreepiaphahvaikohdaecobeavepaeyoicuevasan"
            )


def test_set_root():
    document = Document("<root><node/></root>")
    document.root = document.root[0].detach()
    assert str(document) == "<node/>"

    document_2 = Document("<root><replacement/>parts</root>")
    with pytest.raises(InvalidOperation):
        document.root = document_2.root[0]


def test_root_siblings():
    document = Document("<root/>")
    head_nodes = document.head_nodes
    tail_nodes = document.tail_nodes

    head_nodes.append(new_comment_node(" I Roy "))
    head_nodes.insert(0, new_processing_instruction_node("Blood", "Fire"))

    tail_nodes.prepend(new_comment_node(" Prince Jazzbo "))
    tail_nodes.append(new_processing_instruction_node("over", "out"))

    assert len(head_nodes) == len(tail_nodes) == 2

    assert (
        str(document) == "<?Blood Fire?><!-- I Roy --><root/><!-- Prince Jazzbo "
        "--><?over out?>"
    )

    assert head_nodes[0].target == "Blood"
    assert head_nodes[-1].content == " I Roy "

    tail_nodes += [new_comment_node("")]

    with pytest.raises(InvalidOperation):
        tail_nodes.append("nah")

    with pytest.raises(InvalidOperation):
        tail_nodes.pop(0)


def test_xpath(files_path):
    document = Document(files_path / "marx_manifestws_1848.TEI-P5.xml")

    for i, page_break in enumerate(document.xpath(".//pb")):
        assert isinstance(page_break, TagNode)
        assert page_break.qualified_name == "{http://www.tei-c.org/ns/1.0}pb"

    assert i == 22

    for j, page_break in enumerate(document.xpath('.//pb[@n="I"]')):
        assert isinstance(page_break, TagNode)
        assert page_break.qualified_name == "{http://www.tei-c.org/ns/1.0}pb"
        assert page_break.attributes["n"] == "I"

    assert j == 0


def test_invalid_xpath(files_path):
    document = Document(files_path / "marx_manifestws_1848.TEI-P5.xml")

    with pytest.raises(InvalidOperation):
        tuple(document.xpath(".//pb/@facs"))

    with pytest.raises(InvalidOperation):
        tuple(document.xpath(".//comment()"))
