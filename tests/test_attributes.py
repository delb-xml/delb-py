from textwrap import dedent

import pytest

from delb import Document, new_tag_node, parse_tree
from delb.nodes import Attribute


@pytest.mark.parametrize(
    "accessor",
    ("ham", "{kitchen.sink}ham", ("kitchen.sink", "ham")),
)
def test_access_with_default_namespace(accessor):
    root = parse_tree('<root xmlns="kitchen.sink" ham="spam"/>')
    assert root[accessor] == "spam"
    assert root.attributes[accessor] == "spam"

    root[accessor] = "eggs"
    assert root[accessor] == "eggs"
    del root[accessor]
    assert accessor not in root
    assert accessor not in root.attributes

    root.attributes[accessor] = "eggs"
    assert root.attributes[accessor] == "eggs"
    del root.attributes[accessor]
    assert accessor not in root
    assert accessor not in root.attributes

    root.attributes[accessor] = "eggs"
    attribute = root.attributes.pop(accessor)
    assert isinstance(attribute, Attribute)
    assert attribute.namespace == "kitchen.sink"
    assert attribute.local_name == "ham"
    assert attribute.value == "eggs"
    assert accessor not in root.attributes

    with pytest.raises(TypeError):
        del root.attributes[0]


@pytest.mark.parametrize(
    "accessor",
    ("{kitchen.sink}ham", ("kitchen.sink", "ham")),
)
def test_access_with_other_namespace(accessor):
    root = parse_tree('<root xmlns:ns="kitchen.sink" ns:ham="spam"/>')
    assert root[accessor] == "spam"
    assert root.attributes[accessor] == "spam"

    root[accessor] = "eggs"
    assert root[accessor] == "eggs"
    del root[accessor]
    assert accessor not in root
    assert accessor not in root.attributes

    root.attributes[accessor] = "eggs"
    assert root.attributes[accessor] == "eggs"
    del root.attributes[accessor]
    assert accessor not in root
    assert accessor not in root.attributes

    root.attributes[accessor] = "eggs"
    attribute = root.attributes.pop(accessor)
    assert isinstance(attribute, Attribute)
    assert attribute.namespace == "kitchen.sink"
    assert attribute.local_name == "ham"
    assert attribute.value == "eggs"
    assert accessor not in root.attributes

    with pytest.raises(TypeError):
        del root.attributes[0]


def test_access_without_namespace():
    root = parse_tree('<root ham="spam"/>')
    assert root["ham"] == "spam"
    assert root.attributes["ham"] == "spam"

    root["ham"] = "eggs"
    assert root["ham"] == "eggs"
    del root["ham"]
    assert "ham" not in root
    assert "ham" not in root.attributes

    root.attributes["ham"] = "eggs"
    assert root.attributes["ham"] == "eggs"
    del root.attributes["ham"]
    assert "ham" not in root
    assert "ham" not in root.attributes


def test_attribute_object():
    node = parse_tree("<root/>")
    attributes = node.attributes

    attributes["ham"] = "spam"
    assert str(node) == '<root ham="spam"/>'

    attribute = node["ham"]
    assert attribute.namespace == ""
    assert attribute.universal_name == "ham"
    assert str(attribute) == attribute.value == "spam"

    attribute.namespace = "kitchen.sink"
    assert str(node) == '<root xmlns:ns0="kitchen.sink" ns0:ham="spam"/>'
    assert attribute.universal_name == "{kitchen.sink}ham"

    attribute.local_name = "clam"
    assert str(node) == '<root xmlns:ns0="kitchen.sink" ns0:clam="spam"/>'
    assert attribute.universal_name == "{kitchen.sink}clam"

    attribute.namespace = ""
    assert str(node) == '<root clam="spam"/>'
    assert attribute.universal_name == "clam"

    assert attribute.value == "spam"
    assert str(attribute) == attribute.value == "spam"

    attribute.value = "sham"
    assert str(attribute) == attribute.value == "sham"
    assert str(node) == '<root clam="sham"/>'

    with pytest.raises(TypeError):
        attribute.value = None

    attribute = attributes.pop("clam")
    assert attribute._attributes is None
    assert str(attribute) == attribute.value == "sham"
    attribute.value = "detached"
    assert attribute.universal_name == "clam"
    assert str(attribute) == attribute.value == "detached"


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
    assert d.attributes == {"od": "y", ("", "id"): "x"}

    assert e.attributes == e.attributes
    assert e.attributes == {"{https://u.rl}od": "y", ("https://u.rl", "id"): "x"}


def test_delete_namespaced_attribute():
    root = parse_tree('<root><node xmlns:p="ns" p:a="1" p:b="2"/></root>')
    node = root.css_select("node").first
    assert len(node.attributes) == 2
    del node.attributes[("ns", "a")]
    assert len(node.attributes) == 1


def test_detach_sustains_attributes():
    node = parse_tree(
        "<root xmlns='https://default.ns'><node foo='bar'/></root>"
    ).first_child
    attributes = node.attributes
    attributes_copy = attributes.as_dict_with_strings()

    node.detach()

    assert node.attributes is attributes
    assert node.attributes == attributes_copy


def test_namespaced_attributes():
    root = parse_tree('<root xmlns="http://foo.org" b="c"/>')
    for key, attribute in root.attributes.items():
        assert key == ("http://foo.org", "b")
        assert attribute.namespace == "http://foo.org"
        assert attribute.local_name == "b"
        assert attribute.universal_name == "{" + key[0] + "}" + key[1]
        assert attribute.value == "c"


def test_pop():
    attributes = new_tag_node("node", {"facs": "0001"}).attributes
    assert attributes.pop("facs") == "0001"
    assert attributes.pop("facs", None) is None
    with pytest.raises(KeyError):
        attributes.pop("facs")


def test_prefixed_source():
    root = parse_tree('<root xmlns:prfx="kitchen.sink" prfx:ham="spam"/>')
    assert "ham" not in root
    assert root["{kitchen.sink}ham"] == "spam"
    assert root[("kitchen.sink", "ham")] == "spam"


def test_update():
    root = parse_tree("<root><node foo='0'/><node bar='1'/></root>")
    root.first_child.attributes.update(root.last_child.attributes)
    assert root.first_child.attributes == {("", "foo"): "0", ("", "bar"): "1"}
