import gc
from typing import Final

import pytest
from delb import (
    Document,
    DocumentMixinBase,
    TagNode,
    get_traverser,
    is_tag_node,
    new_comment_node,
    new_processing_instruction_node,
)
from delb.exceptions import FailedDocumentLoading, InvalidOperation
from tests.plugins import PlaygroundDocumentExtension


TEI_NAMESPACE: Final = "http://www.tei-c.org/ns/1.0"


def test_config_initialization():
    document = Document("<root/>", playground_property="foo")

    assert document.config.playground.initialized is True
    assert document.config.playground.property == "foo"


def test_clone():
    document = Document("<root/>", playground_property="foo")
    document.clone()


def test_clone_integrity(files_path):
    # this is a super specific regression test. the contents must have exactly the same
    # structure as given. e.g. with the 'language' or 'teiHeader' tag removed, the test
    # would pass.
    # weirdly, the unit test here only fails on the second and subsequent invocations
    # after any file edit (even here in the comment). and that not even in every
    # execution environment.
    # yet originally the false behaviour surfaced within the integration test suite,
    # particularly the 'location-paths' test with documents from the ELTeC corpus that
    # contains this slightly off structural pattern.
    # i mean i understand, handling with lxml's and delb's semantics and always XML's
    # at the same time is a gruesome hobby. come on encoders, put in some consistency!
    # now as the solution is to move away from the lxml API it will be very a good
    # question what to do with this test in the future.

    document = Document(
        """\
    <TEI xmlns="http://www.tei-c.org/ns/1.0">
    <teiHeader>
    <profileDesc xmlns:e="http://distantreading.net/eltec/ns">
      <langUsage>
        <language ident="hr"/>
      </langUsage>
      <textDesc>
        <authorGender xmlns="http://distantreading.net/eltec/ns" key="M"/>
      </textDesc>
    </profileDesc>
    </teiHeader>
    </TEI>"""
    )
    clone = document.clone()

    for node in get_traverser(from_left=True, depth_first=True, from_top=True)(
        document.root, is_tag_node
    ):
        cloned_node = clone.xpath(node.location_path).first
        assert node.universal_name == cloned_node.universal_name
        assert node.attributes == cloned_node.attributes


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

    #

    document = Document('<root xmlns:y="y"><a><b/><y:c/><b/></a></root>')

    results = document.css_select("a b")
    assert len(results) == 2
    assert all(x.local_name == "b" for x in results)

    results = document.css_select("a y|c", {"y": "y"})
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

    # in case this fails, first check the import order in conftest!
    assert Document.__mro__ == (
        Document,
        PlaygroundDocumentExtension,
        DocumentMixinBase,
        object,
    )

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
    epilogue = document.epilogue

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


def test_set_root():
    document = Document("<root><node/></root>")
    document.root = document.root[0].detach()
    assert str(document) == '<?xml version="1.0" encoding="UTF-8"?><node/>'

    document_2 = Document("<root><replacement/>parts</root>")
    with pytest.raises(InvalidOperation, match="detached node"):
        document.root = document_2.root[0]


def test_xpath(files_path):
    document = Document(files_path / "marx_manifestws_1848.TEI-P5.xml")

    for i, page_break in enumerate(document.xpath("//pb")):
        assert isinstance(page_break, TagNode)
        assert page_break.universal_name == "{http://www.tei-c.org/ns/1.0}pb"

    assert i == 22

    for j, page_break in enumerate(document.xpath('//pb[@n="I"]')):
        assert isinstance(page_break, TagNode)
        assert page_break.universal_name == "{http://www.tei-c.org/ns/1.0}pb"
        assert page_break.attributes["n"] == "I"

    assert j == 0
