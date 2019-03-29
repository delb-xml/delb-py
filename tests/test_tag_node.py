from copy import copy, deepcopy

import pytest
from lxml import etree

from lxml_domesque import Document, InvalidOperation, TagNode, TextNode, new_tag_node


def is_pagebreak(node):
    return isinstance(node, TagNode) and node.local_name == "pb"


def test_add_next_tag_before_tail():
    document = Document("<root><a/>b</root>")
    root = document.root

    root[0].add_next(root.new_tag_node("c"))

    assert str(document) == "<root><a/><c/>b</root>"


def test_add_next_text_node_before_text_sibling():
    document = Document("<root><a/>c</root>")

    a = document.root[0]
    a.add_next("b")

    assert str(document) == "<root><a/>bc</root>"


def test_add_previous_node():
    document = Document("<root><a/></root>")
    root = document.root

    a = root[0]
    a.add_previous(root.new_tag_node("z"))
    assert str(document) == "<root><z/><a/></root>"

    z = root[0]
    z.add_previous("x")
    assert str(document) == "<root>x<z/><a/></root>"

    z.add_previous("y")
    assert str(document) == "<root>xy<z/><a/></root>"

    a.add_previous(a.new_tag_node("boundary"))
    assert str(document) == "<root>xy<z/><boundary/><a/></root>"


def test_append_no_child():
    document = Document("<root/>")

    document.root.append_child()
    assert str(document) == "<root/>"


def test_attribute_access():
    document = Document('<root ham="spam"/>')
    assert document.root["ham"] == "spam"


def test_contains():
    document = Document('<root foo="bar"><node><descendant/></node></root>')
    root = document.root
    node = root[0]
    descendant = node[0]

    assert "foo" in root
    assert "bar" not in root

    assert node in root
    assert descendant not in root

    assert descendant in node

    with pytest.raises(TypeError):
        0 in root


def test_copy():
    node = Document("<x/>").root
    clone = copy(node)

    assert clone is not node
    assert clone._etree_obj is not node._etree_obj
    assert clone.qualified_name == clone.qualified_name
    assert clone.attributes == clone.attributes


def test_deepcopy():
    node = Document("<x><y/></x>").root
    clone = deepcopy(node)

    assert clone is not node
    assert clone._etree_obj is not node._etree_obj
    assert clone.qualified_name == clone.qualified_name
    assert clone.attributes == clone.attributes
    assert clone[0] is not node[0]


def test_depth():
    document = Document("<root><a><b/></a></root>")

    root = document.root
    assert root.depth == 0

    a = root[0]
    assert a.depth == 1

    assert a[0].depth == 2


def test_detach_and_document_property():
    document = Document("<root><node/></root>")
    root = document.root

    assert root.document is document

    node = root[0].detach()

    assert node.parent is None
    assert node.document is None
    assert root.document is document
    assert str(document) == "<root/>"


def test_detach_node_with_tail():
    document = Document("<root><a>c<c/></a>b<d/></root>")
    root = document.root

    root[1].add_next("c")
    root[0].detach()

    assert str(document) == "<root>bc<d/></root>"


def test_detach_root():
    unbound_node = new_tag_node("unbound")
    assert unbound_node.detach() is unbound_node

    document = Document("<root/>")
    with pytest.raises(InvalidOperation):
        document.root.detach()


def test_equality():
    document = Document("<root/>")
    a = document.new_tag_node("name", attributes={"x": "y"})
    b = document.new_tag_node("name", attributes={"x": "y"})
    c = document.new_tag_node("nome", attributes={"x": "y"})
    d = document.new_tag_node("name", attributes={"y": "x"})

    assert a == b
    assert b == a
    assert a != c
    assert a != d
    assert a != 0


def test_first_and_last_child():
    document = Document("<root/>")
    assert document.root.first_child is None
    assert document.root.last_child is None

    document = Document("<root><e1/><e2/></root>")
    assert document.root.first_child.local_name == "e1"
    assert document.root.last_child.local_name == "e2"

    document = Document("<root>first<e1/><e2/>last</root>")
    assert document.root.first_child.content == "first"
    assert document.root.last_child.content == "last"


def test_full_text():
    document = Document(
        "<root>The <em>quick <colored>red</colored> fox</em> "
        "<super>jumps over</super> the fence.</root>"
    )
    assert document.root.full_text == "The quick red fox jumps over the fence."


def test_getitem():
    document = Document('<root ham="spam"><a/><b/><c/><d/></root>')
    root = document.root

    assert root["ham"] == "spam"
    with pytest.raises(KeyError):
        root["foo"]

    assert root[-1].local_name == "d"

    assert "".join(x.local_name for x in root[1:]) == "bcd"
    assert "".join(x.local_name for x in root[1:3]) == "bc"
    assert "".join(x.local_name for x in root[:3]) == "abc"

    assert "".join(x.local_name for x in root[::-1]) == "dcba"


def test_insert():
    document = Document("<root><a>c</a></root>")
    root = document.root
    a = root[0]

    a.insert_child(0, root.new_tag_node("b"))
    assert str(document) == "<root><a><b/>c</a></root>"

    a.insert_child(0, "|aaa|")
    assert str(document) == "<root><a>|aaa|<b/>c</a></root>"

    a.insert_child(0, TextNode("|aa|"), clone=True)
    assert str(document) == "<root><a>|aa||aaa|<b/>c</a></root>"

    a.insert_child(1, "-")
    assert str(document) == "<root><a>|aa|-|aaa|<b/>c</a></root>"


def test_insert_first_child():
    document = Document("<root/>")
    document.root.insert_child(0, "a")
    assert str(document) == "<root>a</root>"


def test_insert_at_invalid_index():
    root = Document("<root><a/><b/></root>").root

    with pytest.raises(ValueError):
        root.insert_child(-1, "x")

    with pytest.raises(IndexError):
        root.insert_child(3, "x")


def test_iterate_next_nodes():
    document = Document("<root><a/><b><x/></b><c/>d<e>spam</e><f/></root>")

    expected = "bcdef"

    for i, node in enumerate(document.root[0].iterate_next_nodes()):
        if isinstance(node, TagNode):
            assert node.local_name == expected[i]
        else:
            assert node.content == expected[i]


def test_iterate_previous_nodes():
    document = Document("<root><a/><b><x/></b><c/>d<e>spam</e><f/></root>")

    expected = "abcde"[::-1]

    for i, node in enumerate(document.root[5].iterate_previous_nodes()):
        if isinstance(node, TagNode):
            assert node.local_name == expected[i]
        else:
            assert node.content == expected[i]


def test_iter_stream_to_left():
    document = Document(
        "<a><b><c/></b><d><e><f/><g/></e><h><i><j/><k/></i></h></d></a>"
    )
    k = document.root[1][1][0][1]
    chars = "abcdefghij"[::-1]
    for i, node in enumerate(k.iterate_previous_nodes_in_stream()):
        assert node.local_name == chars[i]


def test_iter_stream_to_right():
    document = Document(
        "<a><b><c/></b><d><e><f/><g/></e><h><i><j/><k/></i></h></d></a>"
    )
    a = document.root
    chars = "bcdefghijk"
    for i, node in enumerate(a.iterate_next_nodes_in_stream()):
        print(node)
        assert node.local_name == chars[i]


def test_make_node_with_additional_namespace():
    document = Document("<root/>")

    node = document.new_tag_node("foo", namespace="https://name.space")
    assert node.namespace == "https://name.space"
    assert node._etree_obj.tag == "{https://name.space}foo"


def test_make_node_namespace_inheritance():
    document = Document('<pfx:root xmlns:pfx="https://name.space"/>')
    node = document.new_tag_node("node")
    assert node.namespace == "https://name.space"
    assert node.prefix == "pfx"


def test_make_node_without_context():
    document = Document('<root xmlns="ham" />')
    node = new_tag_node("a", namespace="spam")

    document.root.append_child(node)

    assert str(document) == '<root xmlns="ham"><a xmlns="spam"/></root>'


def test_next_in_stream(files_path):
    document = Document(files_path / "marx_manifestws_1848.TEI-P5.xml")
    page_breaks = document.xpath(".//pb")

    cursor = page_breaks.pop(0)
    while len(page_breaks) > 1:
        _next = page_breaks.pop(0)
        assert cursor.next_node_in_stream(is_pagebreak) is _next
        cursor = _next


def test_no_siblings_on_root():
    document = Document("<root/>")

    with pytest.raises(InvalidOperation):
        document.root.add_next("sibling")

    with pytest.raises(InvalidOperation):
        document.root.add_previous("sibling")


def test_prefix():
    document = Document('<root xmlns:x="ham"><x:a/></root>')

    assert document.root[0].prefix == "x"


def test_prepend_child():
    document = Document("<root><b/></root>")
    document.root.prepend_child(document.new_tag_node("a"))
    assert str(document) == "<root><a/><b/></root>"


def test_previous_in_stream(files_path):
    document = Document(files_path / "marx_manifestws_1848.TEI-P5.xml")
    page_breaks = document.xpath(".//pb")

    cursor = page_breaks.pop()
    while len(page_breaks) > 1:
        prev = page_breaks.pop()
        assert cursor.previous_node_in_stream(is_pagebreak) is prev
        cursor = prev


def test_previous_node():
    document = Document("<root><a/></root>")
    assert document.root.previous_node() is None

    #

    document = Document("<root><a/><!-- bla --><b/></root>")

    b = document.root[1]
    a = b.previous_node()
    assert a is not None
    assert a.local_name == "a"


def test_serialization():
    root = Document("<root>a</root>").root
    root.append_child("b")

    assert str(root) == "<root>ab</root>"


def test_set_tag_components():
    document = Document("<root/>")
    root = document.root

    root.local_name = "top"
    assert str(document) == "<top/>"

    ns = "https://name.space"
    etree.register_namespace("prfx", ns)
    root.namespace = ns
    assert root.namespace == ns
    assert str(document) == '<prfx:top xmlns:prfx="https://name.space"/>'

    root.local_name = "root"
    assert str(document) == '<prfx:root xmlns:prfx="https://name.space"/>'
