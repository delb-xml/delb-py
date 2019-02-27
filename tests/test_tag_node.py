import pytest
from lxml import etree

from lxml_domesque import Document, InvalidOperation


def test_add_tag_before_tail():
    document = Document("<root><a/>b</root>")
    root = document.root

    root[0].add_next(root.new_tag_node("c"))

    assert str(document) == "<root><a/><c/>b</root>"


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


def test_detach_and_document():
    document = Document("<root><node/></root>")
    root = document.root

    assert root.document is document

    node = root[0].detach()

    assert node.parent is None
    assert node.document is None
    assert root.document is document
    assert str(document) == "<root/>"


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

    with pytest.raises(TypeError):
        a == 0


def test_first_and_last_child():
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


def test_insert():
    document = Document("<root><a>c</a></root>")
    root = document.root
    a = root[0]

    a.insert_child(0, root.new_tag_node("b"))
    assert str(document) == "<root><a><b/>c</a></root>"

    a.insert_child(0, "|aaa|")
    assert str(document) == "<root><a>|aaa|<b/>c</a></root>"

    a.insert_child(0, "|aa|")
    assert str(document) == "<root><a>|aa||aaa|<b/>c</a></root>"


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


def test_no_siblings_on_root():
    document = Document("<root/>")

    with pytest.raises(InvalidOperation):
        document.root.add_next("sibling")

    with pytest.raises(InvalidOperation):
        document.root.add_previous("sibling")


def test_set_tag_components():
    document = Document("<root/>")
    document.root.local_name = "top"
    assert str(document) == "<top/>"

    ns = "https://name.space"
    etree.register_namespace("prfx", ns)
    document.root.namespace = ns
    assert str(document) == '<prfx:top xmlns:prfx="https://name.space"/>'