import pytest

from delb import Document, TagNode, TextNode, is_text_node, tag
from delb.nodes import TAIL, APPENDED


def test_add_tag_before_tail():
    document = Document("<root><a/>b</root>")
    root = document.root

    root[1].add_previous(tag("c"))

    assert str(document) == "<root><a/><c/>b</root>"


def test_add_tag_after_tail_appended_text():
    document = Document("<root><a/>b</root>")
    root = document.root
    root.append_child("c")
    root.append_child(tag("d"))
    assert str(document) == "<root><a/>bc<d/></root>"


def test_add_tag_after_tail():
    document = Document("<root><node/>tail</root>")
    tail = document.root[1]

    tail.add_next(tag("end"))
    assert str(document) == "<root><node/>tail<end/></root>"


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


def test_add_tag_between_text_nodes_at_tail_position():
    document = Document("<root><a/>tail</root>")
    root = document.root

    root[1].add_next("the")
    root[2].add_next(" end")
    root[1].add_next(tag("node"))
    assert len(document.root) == 5
    assert str(document) == "<root><a/>tail<node/>the end</root>"


def test_add_text_before_data():
    document = Document("<root>data</root>")
    document.root[0].add_previous("head ")
    assert len(document.root) == 2
    assert str(document) == "<root>head data</root>"


def test_add_text_between_text_at_data_position():
    document = Document("<root>data</root>")
    node = document.root[0]
    node.add_next(" tailing")
    node.add_next(" more more more")
    assert len(document.root) == 3
    assert str(document) == "<root>data more more more tailing</root>"


def test_add_tag_between_two_appended():
    document = Document("<root>data</root>")
    root = document.root
    root.append_child("appended")

    document.root[0].add_next(tag("node"))

    assert str(document) == "<root>data<node/>appended</root>"

    document = Document("<root>data</root>")
    root = document.root
    root.append_child("appended")

    root[1].add_previous(tag("node"))

    assert str(document) == "<root>data<node/>appended</root>"


def test_add_text_between_two_appended():
    document = Document("<root>data</root>")
    root = document.root

    root[0].add_next(" appended_1")
    root[1].add_next(" appended_2")
    root[2].add_next(" appended_3")
    root[1].add_next(tag("tag"))

    assert len(document.root) == 5
    assert str(document) == "<root>data appended_1<tag/> appended_2 appended_3</root>"


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


def test_bindings(sample_document):
    p = sample_document.root[1][1]
    text_nodes = tuple(x for x in p.child_nodes(is_text_node))

    x, y = text_nodes[1], p[2]
    assert x is y


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


def test_content_is_coerced():
    node = TextNode("")
    with pytest.raises(TypeError):
        node.content = 0


def test_depth():
    document = Document("<root>1<a><b/>2</a></root>")

    root = document.root
    one = root[0]
    assert one.depth == 1

    two = root[1][1]
    assert two.depth == 2


def test_detach_data_node():
    document = Document("<root><a>b</a></root>")
    root = document.root

    b = root[0][0].detach()
    assert b.parent is None
    assert b.depth == 0
    assert b.content == "b"
    assert str(document) == "<root><a/></root>"

    document = Document("<root><a>b<c/></a></root>")
    root = document.root

    b = root[0][0].detach()
    assert b.parent is None
    assert b.depth == 0
    assert b.content == "b"

    assert str(document) == "<root><a><c/></a></root>"


def test_detach_tag_sandwiched_node():
    document = Document("<root><a/>tail<b/></root>")
    tail = document.root[1].detach()

    assert tail.parent is None
    assert tail.depth == 0
    assert isinstance(tail, TextNode)
    assert tail.content == "tail"

    assert str(document) == "<root><a/><b/></root>"


def test_detach_text_sandwiched_node():
    document = Document("<root>data</root>")
    root = document.root
    data = root[0]

    data.add_next(" tailing")
    data.add_next(" more more more")

    more = document.root[1].detach()
    assert str(more) == " more more more"
    assert str(document) == "<root>data tailing</root>"

    data.add_next(more)
    data.detach()
    assert str(document) == "<root> more more more tailing</root>"

    root.insert_child(0, tag("tag"))
    more.detach()
    assert str(document) == "<root><tag/> tailing</root>"


def test_document():
    document = Document("<root>data<node/>tail</root>")
    root = document.root
    root.append_child("more")
    assert root[0].document is document
    assert root[2].document is document
    assert root[3].document is document

    detached = TextNode("detached")
    assert detached.document is None


def test_entities():
    document = Document("<root>&lt; spock &gt;</root>")
    assert document.root[0].content == "< spock >"


def test_equality():
    assert not TextNode("1") == 1


def test_none_content_wrapping():
    document = Document("<root><e1/></root>")

    with pytest.raises(IndexError):
        document.root[1]

    e1 = document.root[0]
    assert e1.next_node() is None

    e1.add_next(tag("e2"))
    assert isinstance(e1.next_node(), TagNode)


def test_previous_node():
    document = Document("<root><a/>b</root>")
    root = document.root
    root.append_child("c")

    b = root[2].previous_node()
    assert b == "b"

    c = TextNode("c")
    root[0].append_child(c)

    assert c.previous_node() is None


def test_sample_document_structure_and_content(sample_document):
    p = sample_document.root[1][1]

    text_nodes = tuple(x for x in p.child_nodes(is_text_node))

    assert all(isinstance(x, TextNode) for x in text_nodes)

    assert len(text_nodes) == 2
    assert text_nodes[0] is p[0]
    assert text_nodes[1] is p[2]

    assert text_nodes[0].content.strip() == "Lorem ipsum"
    assert text_nodes[1].content.strip() == "dolor sit amet"


def test_string_methods():
    node = TextNode("Herrasmiehet Pitävät Laserista")
    assert node.count("ä") == 2
    assert node.split() == ["Herrasmiehet", "Pitävät", "Laserista"]
    assert "Laser" in node
    assert node[13:20] == "Pitävät"
    with pytest.raises(AttributeError):
        node.this_is_not_a_method()
