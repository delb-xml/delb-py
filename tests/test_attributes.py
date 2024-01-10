from textwrap import dedent

import pytest

from delb import new_tag_node, Document, InvalidOperation


def test_access_via_node():
    document = Document('<root ham="spam"/>')
    assert document.root["ham"] == "spam"

    root = Document('<root xmlns="kitchen.sink" ham="spam"/>').root
    assert root["ham"] == "spam"
    assert root.attributes["ham"] == "spam"
    assert root["{kitchen.sink}ham"] == "spam"
    assert root.attributes["{kitchen.sink}ham"] == "spam"
    assert root["kitchen.sink":"ham"] == "spam"
    assert root.attributes["kitchen.sink":"ham"] == "spam"

    root = Document('<root xmlns:prfx="kitchen.sink" prfx:ham="spam"/>').root
    assert "ham" not in root
    assert root["{kitchen.sink}ham"] == "spam"
    assert root["kitchen.sink":"ham"] == "spam"


def test_attribute_object():
    document = Document("<root/>")
    node = document.root
    attributes = node.attributes

    attributes["ham"] = "spam"
    assert str(node) == '<root ham="spam"/>'

    attribute = node["ham"]
    assert attribute.namespace is None
    assert attribute.universal_name == "ham"

    attribute.namespace = "kitchen.sink"
    assert str(node) == '<root xmlns:ns0="kitchen.sink" ns0:ham="spam"/>'
    assert attribute.universal_name == "{kitchen.sink}ham"

    attribute.local_name = "clam"
    assert str(node) == '<root xmlns:ns0="kitchen.sink" ns0:clam="spam"/>'
    assert attribute.universal_name == "{kitchen.sink}clam"

    attribute.namespace = None
    assert str(node) == '<root clam="spam"/>'
    assert attribute.universal_name == "clam"

    assert attribute.value == "spam"

    attribute.value = "sham"
    assert str(node) == '<root clam="sham"/>'

    with pytest.raises(TypeError):
        attribute.value = None

    attributes.pop("clam")
    with pytest.raises(InvalidOperation):
        attribute.value
    with pytest.raises(InvalidOperation):
        attribute.value = "obsolete"


def test_comparison():
    document = Document(
        dedent(
            """\
    <root>
        <a xml:id="x"/>
        <b id="x"/>
        <c id="x"/>
        <d id="x" od="y"/>
        <p:e xmlns:p="https://u.rl" p:id="x" p:od="y"/>
    </root>
    """
        )
    )
    a = document.css_select("a").first
    b = document.css_select("b").first
    c = document.css_select("c").first
    d = document.css_select("d").first
    e = document.css_select("p|e", namespaces={"p": "https://u.rl"}).first

    assert a.attributes == a.attributes
    assert a.attributes != b.attributes
    assert a.attributes != c.attributes
    assert a.attributes != d.attributes
    assert a.attributes != e.attributes
    assert a.attributes == {"{http://www.w3.org/XML/1998/namespace}id": "x"}

    assert b.attributes == b.attributes
    assert b.attributes == c.attributes
    assert b.attributes != d.attributes
    assert b.attributes != e.attributes
    assert b.attributes == {"id": "x"}

    assert c.attributes == c.attributes
    assert c.attributes != d.attributes
    assert c.attributes != e.attributes
    assert c.attributes == {"id": "x"}

    assert d.attributes == d.attributes
    assert d.attributes != e.attributes
    assert d.attributes == {"od": "y", "id": "x"}

    assert e.attributes == e.attributes
    assert e.attributes == {"{https://u.rl}od": "y", "{https://u.rl}id": "x"}


def test_delete_namespaced_attribute():
    root = Document('<root><node xmlns:p="ns" p:a="1" p:b="2"/></root>').root
    node = root.css_select("node").first
    assert len(node.attributes) == 2
    del node.attributes["ns":"a"]
    assert len(node.attributes) == 1


def test_detach_sustains_attributes():
    node = Document(
        "<root xmlns='https://default.ns'><node foo='bar'/></root>"
    ).root.first_child
    attributes = node.attributes
    attributes_copy = attributes.as_dict_with_strings()

    node.detach()

    assert node.attributes is attributes
    assert node.attributes == attributes_copy


def test_namespaced_attributes():
    root = Document('<root xmlns="http://foo.org" b="c"/>').root
    for key, attribute in root.attributes.items():
        assert key == "{http://foo.org}b"
        assert attribute.namespace == "http://foo.org"
        assert attribute.local_name == "b"
        assert attribute.universal_name == key
        assert attribute.value == "c"


def test_update():
    root = Document("<root><node foo='0'/><node bar='1'/></root>").root
    root.first_child.attributes.update(root.last_child.attributes)
    assert root.first_child.attributes == {"foo": "0", "bar": "1"}


def test_various_attribute_operations(sample_document):
    # une assemblage from back in the days
    milestone = sample_document.root[1][0]
    assert milestone.attributes == {"{https://name.space}unit": "page"}

    attributes = Document('<node xmlns="default" foo="0" bar="0"/>').root.attributes
    del attributes["foo"]
    del attributes["bar"]
    with pytest.raises(TypeError):
        del attributes[0]

    node = new_tag_node("node", attributes={"foo": "0", "bar": "0"})
    assert node.attributes.pop("bar") == "0"
