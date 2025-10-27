import gc
from typing import Final

import pytest

from delb import (
    CommentNode,
    Document,
    DocumentMixinBase,
    ProcessingInstructionNode,
    parse_tree,
)
from delb.exceptions import FailedDocumentLoading, InvalidOperation
from delb.filters import altered_default_filters, is_tag_node
from delb.nodes import TagNode, TextNode
from delb.utils import get_traverser

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
    cloned_document = document.clone()

    for node in get_traverser(from_left=True, depth_first=True, from_top=True)(
        document.root, is_tag_node
    ):
        cloned_node = cloned_document.xpath(node.location_path).first
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


def test_epilogue():
    document = Document("<root/><!--c-->")

    c = document.epilogue[0]
    assert document.epilogue.index(c) == 0

    document.epilogue.insert(0, CommentNode("d"))
    assert (
        str(document) == '<?xml version="1.0" encoding="UTF-8"?><root/><!--d--><!--c-->'
    )

    document.epilogue.clear()
    assert document.epilogue.index(c) is None
    assert str(document) == '<?xml version="1.0" encoding="UTF-8"?><root/>'

    with altered_default_filters():
        d = parse_tree("<root><!--d--></root>")[0]
    with pytest.raises(InvalidOperation, match=r"Only a detached .*"):
        document.epilogue.append(d)

    with pytest.raises(TypeError):
        document.epilogue.append(TextNode("text"))


def test_explicitly_passed_source_url():
    document = Document("<root/>", source_url="https://root.io/")
    assert document.source_url == "https://root.io/"


def test_invalid_document():
    with pytest.raises(FailedDocumentLoading):
        Document(0)


def test_metaclass():
    class DocumentSubclass(Document):
        pass

    # in case this fails, first check the import order in conftest!
    assert Document.__mro__ == (
        Document,
        PlaygroundDocumentExtension,
        DocumentMixinBase,
        object,
    )
    assert "describes PlaygroundDocumentExtension." in Document.__doc__

    assert DocumentSubclass.__mro__ == (
        DocumentSubclass,
        Document,
        PlaygroundDocumentExtension,
        DocumentMixinBase,
        object,
    )


def test_mixin_method():
    document = Document("<root/>", playground_property="foo")
    assert document.playground_method() == "f00"


def test_prologue():
    document = Document("<!--c--><root/>")

    c = document.prologue[0]
    assert document.prologue.index(c) == 0

    document.prologue.prepend(CommentNode("b"))
    document.prologue.remove(c)
    assert str(document) == '<?xml version="1.0" encoding="UTF-8"?><!--b--><root/>'

    document.prologue.clear()
    assert str(document) == '<?xml version="1.0" encoding="UTF-8"?><root/>'

    with pytest.raises(IndexError):
        document.prologue.insert(1, CommentNode("c"))


def test_root_siblings():
    document = Document("<root/>")
    prologue = document.prologue
    epilogue = document.epilogue

    prologue.append(CommentNode(" I Roy "))
    prologue.insert(0, ProcessingInstructionNode("Blood", "Fire"))

    epilogue.prepend(CommentNode(" Prince Jazzbo "))
    epilogue.append(ProcessingInstructionNode("over", "out"))

    assert len(prologue) == len(epilogue) == 2

    assert str(document) == (
        '<?xml version="1.0" encoding="UTF-8"?><?Blood Fire?>'
        "<!-- I Roy --><root/><!-- Prince Jazzbo --><?over out?>"
    )

    assert prologue[0].target == "Blood"
    assert prologue[-1].content == " I Roy "

    with pytest.raises(TypeError):
        epilogue.append("nah")


def test_set_root():
    document = Document("<root><node/></root>")
    document.root = document.root[0].detach()
    assert str(document) == '<?xml version="1.0" encoding="UTF-8"?><node/>'

    with pytest.raises(TypeError):
        document.root = TextNode("")

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
