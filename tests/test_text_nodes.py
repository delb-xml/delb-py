import pytest

from delb import Document, ParserOptions, TagNode, TextNode, is_text_node, tag
from _delb.nodes import TAIL, APPENDED


def test_add_tag_before_tail():
    root = Document("<root><a/>b</root>").root
    root[1].add_preceding_siblings(tag("c"))
    assert str(root) == "<root><a/><c/>b</root>"


def test_add_tag_after_tail_appended_text():
    root = Document("<root><a/>b</root>").root
    root.append_children("c", tag("d"))
    assert str(root) == "<root><a/>bc<d/></root>"


def test_add_tag_after_tail():
    root = Document("<root><node/>tail</root>").root
    tail = root[1]
    tail.add_following_siblings(tag("end"))
    assert str(root) == "<root><node/>tail<end/></root>"


def test_add_text_after_tag():
    document = Document("<root><tag/></root>")
    tag = document.root[0]

    tag.add_following_siblings(TextNode("foo"))

    assert tag._etree_obj.text is None
    assert tag._etree_obj.tail == "foo"

    foo = tag.fetch_following_sibling()
    assert isinstance(foo, TextNode)
    assert foo._position == TAIL
    assert foo.content == "foo"
    assert foo._appended_text_node is None


def test_add_text_after_tail():
    document = Document("<root><tag/>foo</root>")
    root = document.root
    foo = root[1]

    bar = TextNode("bar")
    foo.add_following_siblings(bar)

    assert foo.fetch_following_sibling() is bar
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
    foo.add_following_siblings(bar)
    peng = TextNode("peng")
    bar.add_following_siblings(peng)

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

    assert len(root) == 2
    assert root[0]._etree_obj.tail == "foobarpeng"


def test_add_tag_between_text_nodes_at_tail_position():
    root = Document("<root><a/>tail</root>").root

    root[1].add_following_siblings("the")
    root[2].add_following_siblings(" end")
    root[1].add_following_siblings(tag("node"))
    assert len(root) == 5
    assert str(root) == "<root><a/>tail<node/>the end</root>"


def test_add_text_before_data():
    root = Document("<root>data</root>").root
    root[0].add_preceding_siblings("head ")
    assert len(root) == 2
    assert str(root) == "<root>head data</root>"


def test_add_text_between_text_at_data_position():
    root = Document("<root>data</root>").root
    node = root[0]
    node.add_following_siblings(" tailing")
    node.add_following_siblings(" more more more")
    assert len(root) == 3
    assert str(root) == "<root>data more more more tailing</root>"


def test_add_tag_between_two_appended():
    root = Document("<root>data</root>").root
    root.append_children("appended")
    root[0].add_following_siblings(tag("node"))
    assert str(root) == "<root>data<node/>appended</root>"

    root = Document("<root>data</root>").root
    root.append_children("appended")
    root[1].add_preceding_siblings(tag("node"))
    assert str(root) == "<root>data<node/>appended</root>"


def test_add_text_between_two_appended():
    root = Document("<root>data</root>").root

    root[0].add_following_siblings(" appended_1")
    root[1].add_following_siblings(" appended_2")
    root[2].add_following_siblings(" appended_3")
    root[1].add_following_siblings(tag("tag"))

    assert len(root) == 5
    assert str(root) == "<root>data appended_1<tag/> appended_2 appended_3</root>"


def test_appended_text_nodes():
    document = Document("<root/>")
    tokens = ("How ", "much ", "is ", "the ", "fish", "?")

    root = document.root
    root.append_children(*tokens)

    assert len(root) == 6, len(root)

    for i, child in enumerate(root.iterate_children()):
        assert isinstance(child, TextNode)
        assert child.content == str(child) == tokens[i]

    document.merge_text_nodes()
    assert len(root) == 1
    assert root[0].content == "How much is the fish?"


def test_bindings(sample_document):
    p = sample_document.root[1][1]
    text_nodes = tuple(x for x in p.iterate_children(is_text_node))

    x, y = text_nodes[1], p[2]
    assert x is y


def test_construction():
    root = Document(
        "<root><node>one</node> two </root>",
        parser_options=ParserOptions(reduce_whitespace=True),
    ).root
    node, two = tuple(x for x in root.iterate_children())
    one = node[0]

    assert one.content == "one"
    assert two.content == " two"

    one.add_following_siblings(TextNode(" threehalfs"))
    assert str(root) == "<root><node>one threehalfs</node> two</root>"

    three = TextNode(" three")
    two.add_following_siblings(three)
    assert str(root) == "<root><node>one threehalfs</node> two three</root>"

    three.add_following_siblings(" four")
    assert str(root) == "<root><node>one threehalfs</node> two three four</root>"

    node.append_children(" sevenquarters")
    assert (
        str(root)
        == "<root><node>one threehalfs sevenquarters</node> two three four</root>"
    )

    twoandahalf = TextNode(" twoandahalf")
    three.add_preceding_siblings(twoandahalf)
    assert (
        str(root)
        == "<root><node>one threehalfs sevenquarters</node> two twoandahalf three "
        "four</root>"
    )

    twoandahalf.add_preceding_siblings(" 2/3π")
    assert (
        str(root)
        == "<root><node>one threehalfs sevenquarters</node> two 2/3π twoandahalf three "
        "four</root>"
    )

    two.add_preceding_siblings(" almosttwo")
    assert (
        str(root)
        == "<root><node>one threehalfs sevenquarters</node> almosttwo two 2/3π "
        "twoandahalf three four</root>"
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
    root = Document("<root><a>b</a></root>").root
    b = root[0][0].detach()
    assert b.parent is None
    assert b.depth == 0
    assert b.content == "b"
    assert str(root) == "<root><a/></root>"

    root = Document("<root><a>b<c/></a></root>").root
    b = root[0][0].detach()
    assert b.parent is None
    assert b.depth == 0
    assert b.content == "b"
    assert str(root) == "<root><a><c/></a></root>"


def test_detach_tag_sandwiched_node():
    root = Document("<root><a/>tail<b/></root>").root
    tail = root[1].detach()

    assert tail.parent is None
    assert tail.depth == 0
    assert isinstance(tail, TextNode)
    assert tail.content == "tail"

    assert str(root) == "<root><a/><b/></root>"


def test_detach_text_sandwiched_node():
    root = Document("<root>data</root>").root
    data = root[0]

    data.add_following_siblings(" tailing")
    data.add_following_siblings(" more more more")

    more = root[1].detach()
    assert str(more) == " more more more"
    assert str(root) == "<root>data tailing</root>"

    data.add_following_siblings(more)
    data.detach()
    assert str(root) == "<root> more more more tailing</root>"

    root.insert_children(0, tag("tag"))
    more.detach()
    assert str(root) == "<root><tag/> tailing</root>"


def test_document():
    document = Document("<root>data<node/>tail</root>")
    root = document.root
    root.append_children("more")
    assert root[0].document is document
    assert root[2].document is document
    assert root[3].document is document

    detached = TextNode("detached")
    assert detached.document is None


def test_entities():
    document = Document("<root>&lt; spock &gt;</root>")
    assert document.root[0].content == "< spock >"


def test_equality():
    assert TextNode("1") != 1


def test_index():
    assert Document("<root>test</root>").root.first_child.index == 0


def test_none_content_wrapping():
    document = Document("<root><e1/></root>")

    with pytest.raises(IndexError):
        document.root[1]

    e1 = document.root[0]
    assert e1.fetch_following_sibling() is None

    e1.add_following_siblings(tag("e2"))
    assert isinstance(e1.fetch_following_sibling(), TagNode)


def test_fetch_preceding_sibling():
    document = Document("<root><a/>b</root>")
    root = document.root
    root.append_children("c")

    b = root[2].fetch_preceding_sibling()
    assert b == "b"

    c = TextNode("c")
    root[0].append_children(c)

    assert c.fetch_preceding_sibling() is None


def test_sample_document_structure_and_content(sample_document):
    p = sample_document.root[1][1]

    text_nodes = tuple(x for x in p.iterate_children(is_text_node))

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
