import pytest
from lxml import etree

from lxml_domesque import Document, InvalidOperation


def test_attribute_access():
    document = Document('<root ham="spam"/>')
    assert document.root["ham"] == "spam"


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
