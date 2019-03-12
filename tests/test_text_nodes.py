import pytest

from lxml_domesque import Document, TagNode, TextNode
from lxml_domesque.nodes import TAIL, APPENDED


def test_add_tag_before_tail():
    document = Document("<root><a/>b</root>")
    root = document.root

    root[1].add_previous(root.new_tag_node("c"))

    assert str(document) == "<root><a/><c/>b</root>"


def test_add_tag_after_tail_appended_text():
    document = Document("<root><a/>b</root>")
    root = document.root
    root.append_child("c")
    root.append_child(root.new_tag_node("d"))
    assert str(document) == "<root><a/>bc<d/></root>"


def test_add_text_after_tag():
    document = Document("<root><tag/></root>")
    tag = document.root[0]

    tag.add_next(TextNode("foo"))

    assert tag._etree_obj.text is None
    assert tag._etree_obj.tail == "foo"

    foo = tag.next_node()
    assert isinstance(foo, TextNode)
    assert foo._position == TAIL
    assert foo.content == "foo"
    assert foo._appended_text_node is None


def test_add_tag_after_tail():
    document = Document("<root><node/>tail</root>")
    tail = document.root[1]

    tail.add_next(document.new_tag_node("end"))
    assert str(document) == "<root><node/>tail<end/></root>"


def test_add_text_after_tail():
    document = Document("<root><tag/>foo</root>")
    root = document.root
    foo = root[1]

    bar = TextNode("bar")
    foo.add_next(bar)

    assert foo.next_node() is bar
    assert len(root) == 3

    assert foo._appended_text_node is bar
    assert bar._bound_to is foo

    assert isinstance(bar, TextNode)
    assert bar._position == APPENDED
    assert bar.content == "bar"
    assert bar._appended_text_node is None

    document.merge_text_nodes()
    assert len(root) == 2
    assert root[0]._etree_obj.tail == "foobar"


def test_add_text_after_appended():
    document = Document("<root><tag/>foo</root>")
    root = document.root
    foo = root[1]

    bar = TextNode("bar")
    foo.add_next(bar)
    peng = TextNode("peng")
    bar.add_next(peng)

    assert len(root) == 4

    assert foo._appended_text_node is bar
    assert foo._position == TAIL
    assert bar._bound_to is foo

    assert bar._appended_text_node is peng
    assert bar._position == APPENDED
    assert peng._bound_to is bar

    assert peng._appended_text_node is None
    assert peng._position == APPENDED
    assert peng._bound_to is bar

    document.merge_text_nodes()

    assert len(root) == 2, [x for x in root.child_nodes()]
    assert root[0]._etree_obj.tail == "foobarpeng"


def test_add_text_before_data():
    document = Document("<root>data</root>")
    document.root[0].add_previous("head ")
    assert len(document.root) == 2
    assert str(document) == "<root>head data</root>"


def test_add_text_between_text():
    document = Document("<root>data</root>")
    node = document.root[0]
    node.add_next(" tailing")
    node.add_next(" more more more")
    assert len(document.root) == 3
    assert str(document) == "<root>data more more more tailing</root>"


def test_appended_text_nodes():
    document = Document("<root/>")
    tokens = ("How ", "much ", "is ", "the ", "fish", "?")

    root = document.root
    root.append_child(*tokens)

    assert len(root) == 6, len(root)

    for i, child in enumerate(root.child_nodes()):
        assert isinstance(child, TextNode)
        assert child.content == str(child) == tokens[i]

    document.merge_text_nodes()
    assert len(root) == 1, [x for x in root.child_nodes()]
    assert root[0].content == "How much is the fish?"


def test_construction():
    document = Document("<root><node>one </node>two </root>")
    root = document.root
    node, two = tuple(x for x in root.child_nodes())
    one = node[0]

    one.add_next(TextNode("threehalfs "))
    assert str(document) == "<root><node>one threehalfs </node>two </root>"

    three = TextNode("three ")
    two.add_next(three)
    assert str(document) == "<root><node>one threehalfs </node>two three </root>"

    three.add_next("four ")
    assert str(document) == "<root><node>one threehalfs </node>two three four </root>"

    node.append_child("sevenquarters ")
    assert (
        str(document)
        == "<root><node>one threehalfs sevenquarters </node>two three four </root>"
    )

    twoandahalf = TextNode("twoandahalf ")
    three.add_previous(twoandahalf)
    assert (
        str(document)
        == "<root><node>one threehalfs sevenquarters </node>two twoandahalf three "
        "four </root>"
    )

    twoandahalf.add_previous("2/3π ")
    assert (
        str(document)
        == "<root><node>one threehalfs sevenquarters </node>two 2/3π twoandahalf three "
        "four </root>"
    )

    two.add_previous("almosttwo ")
    assert (
        str(document)
        == "<root><node>one threehalfs sevenquarters </node>almosttwo two 2/3π "
        "twoandahalf three four </root>"
    )


def test_detach_data_node():
    document = Document("<root><a>b</a></root>")
    root = document.root

    b = root[0][0].detach()
    assert b.parent is None
    assert b.content == "b"
    assert str(document) == "<root><a/></root>"

    document = Document("<root><a>b<c/></a></root>")
    root = document.root

    b = root[0][0].detach()
    assert b.parent is None
    assert b.content == "b"

    assert str(document) == "<root><a><c/></a></root>"


def test_detach_tag_sandwiched_node():
    document = Document("<root><a/>tail<b/></root>")
    tail = document.root[1].detach()

    assert tail.parent is None
    assert isinstance(tail, TextNode)
    assert tail.content == "tail"

    assert str(document) == "<root><a/><b/></root>"


def test_detach_text_sandwiched_node():
    document = Document("<root>data</root>")
    node = document.root[0]
    node.add_next(" tailing")
    node.add_next(" more more more")

    more = document.root[1].detach()
    assert str(more) == " more more more"
    assert str(document) == "<root>data tailing</root>"


def test_document():
    document = Document("<root>data<node/>tail</root>")
    root = document.root
    root.append_child("more")
    assert root[0].document is document
    assert root[2].document is document
    assert root[3].document is document

    detached = TextNode("detached")
    assert detached.document is None


def test_none_content_wrapping():
    document = Document("<root><e1/></root>")

    with pytest.raises(IndexError):
        document.root[1]

    e1 = document.root[0]
    assert e1.next_node() is None

    e1.add_next(e1.new_tag_node("e1"))
    assert isinstance(e1.next_node(), TagNode)
