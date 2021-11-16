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
    document.cleanup_namespaces()
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


def test_delete_namespaced_attribute():
    root = Document('<root><node xmlns:p="ns" p:a="1" p:b="2"/></root>').root
    node = root.css_select("root > node")[0]
    assert len(node.attributes) == 2
    del node.attributes["ns":"a"]
    assert len(node.attributes) == 1


def test_value_slicing():
    node = Document("<node foo='bar'/>").root
    assert node.attributes["foo"][1:-1] == "a"


def test_various_attribute_operations(sample_document):
    # une assemblage from back in the days
    milestone = sample_document.root[1][0]
    assert milestone.attributes == {"unit": "page"}

    attributes = Document('<node xmlns="default" foo="0" bar="0"/>').root.attributes
    del attributes["foo"]
    del attributes["bar"]
    with pytest.raises(TypeError):
        del attributes[0]

    node = new_tag_node("node", attributes={"foo": "0", "bar": "0"})
    assert node.attributes.pop("bar") == "0"
