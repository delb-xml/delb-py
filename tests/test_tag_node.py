from copy import copy, deepcopy

import pytest
from lxml import etree

from _delb.nodes import XML_ATT_ID
from delb import (
    Document,
    TagNode,
    TextNode,
    new_tag_node,
    register_namespace,
    tag,
)
from delb.exceptions import InvalidOperation


def is_pagebreak(node):
    return isinstance(node, TagNode) and node.local_name == "pb"


def test_add_next_tag_before_tail():
    document = Document("<root><a/>b</root>")
    root = document.root

    root[0].add_next(tag("c"))

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
    a.add_previous(tag("z"))
    assert str(document) == "<root><z/><a/></root>"

    z = root[0]
    z.add_previous("x")
    assert str(document) == "<root>x<z/><a/></root>"

    z.add_previous("y")
    assert str(document) == "<root>xy<z/><a/></root>"

    a.add_previous(tag("boundary"))
    assert str(document) == "<root>xy<z/><boundary/><a/></root>"


def test_append_no_child():
    document = Document("<root/>")

    document.root.append_child()
    assert str(document) == "<root/>"


def test_attributes(sample_document):
    milestone = sample_document.root[1][0]
    assert milestone.attributes == {"unit": "page"}


def test_attribute_access_via_getitem():
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


def test_detach_node_with_tail_1():
    document = Document("<root><a>c<c/></a>b<d/></root>")
    root = document.root

    root[1].add_next("c")
    root[0].detach()
    assert str(document) == "<root>bc<d/></root>"

    root.append_child(tag("e"), "f")
    e = root[3]
    e.detach()
    assert str(document) == "<root>bc<d/>f</root>"

    root.append_child(tag("g"), "h")

    root[-2].detach()
    assert str(document) == "<root>bc<d/>fh</root>"


def test_detach_node_with_tail_2():
    root = Document("<root><node><child/>childish</node></root>").root

    node = root.first_child
    child = node.first_child

    child.detach()
    assert str(node) == "<node>childish</node>"
    assert child.next_node() is None


def test_detach_node_retain_child_nodes():
    root = Document("<root><node><child/>childish<!-- [~.ö] --></node></root>").root
    node = root.first_child

    node.detach(retain_child_nodes=True)

    assert len(node) == 0
    assert str(root) == "<root><child/>childish<!-- [~.ö] --></root>"

    child = root.first_child
    child.detach(retain_child_nodes=True)
    assert str(root) == "<root>childish<!-- [~.ö] --></root>"


def test_detach_node_without_a_document():
    root = new_tag_node("root", children=[tag("node")])
    root.first_child.detach()
    assert str(root) == "<root/>"


def test_detach_root():
    unbound_node = new_tag_node("unbound")
    assert unbound_node.detach() is unbound_node

    document = Document("<root/>")
    with pytest.raises(InvalidOperation):
        document.root.detach()


def test_equality():
    a = new_tag_node("name", attributes={"x": "y"})
    b = new_tag_node("name", attributes={"x": "y"})
    c = new_tag_node("nome", attributes={"x": "y"})
    d = new_tag_node("name", attributes={"y": "x"})

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


def test_id_property(files_path):
    document = Document(files_path / "tei_marx_manifestws_1848.TEI-P5.xml")
    publisher = document.css_select("publicationStmt publisher").first

    assert publisher.id == "DTACorpusPublisher"
    with pytest.raises(TypeError):
        publisher.id = 1234
    publisher.id = None
    assert XML_ATT_ID not in publisher.attributes
    publisher.id = "foo"
    assert publisher.attributes[XML_ATT_ID] == "foo"
    with pytest.raises(InvalidOperation):
        publisher.parent.id = "foo"


def test_insert():
    document = Document("<root><a>c</a></root>")
    root = document.root
    a = root[0]

    a.insert_child(0, tag("b"))
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
        assert node.local_name == chars[i]


def test_last_descendant():
    document = Document(
        "<root>"
        "<a><aa><aaa/><aab/></aa><ab><aba/><abb/></ab></a>"
        "<b><ba>baa</ba></b>"
        "<c/>"
        "</root>"
    )
    a, b, c = tuple(document.root.child_nodes())

    a_ld = a.last_descendant
    assert a.last_child.last_descendant is a_ld
    assert isinstance(a_ld, TagNode)
    assert a_ld.local_name == "abb"
    assert a_ld.last_descendant is None

    b_ld = b.last_descendant
    assert isinstance(b_ld, TextNode)
    assert b_ld.content == "baa"
    assert b_ld.last_descendant is None

    assert c.last_descendant is None


def test_make_node_namespace_inheritance():
    document = Document('<pfx:root xmlns:pfx="https://name.space"/>')
    node = document.new_tag_node("node")
    assert node.namespace == "https://name.space"
    assert node.prefix == "pfx"


def test_make_node_with_children():
    result = new_tag_node("infocard", children=[tag("label")])
    assert str(result) == "<infocard><label/></infocard>"

    result = new_tag_node("infocard", children=[tag("label", {"updated": "never"})])
    assert str(result) == '<infocard><label updated="never"/></infocard>'

    result = new_tag_node("infocard", children=[tag("label", "Monty Python")])
    assert str(result) == "<infocard><label>Monty Python</label></infocard>"

    result = new_tag_node(
        "infocard", children=[tag("label", ("Monty Python", tag("fullstop")))]
    )
    assert str(result) == "<infocard><label>Monty Python<fullstop/></label></infocard>"

    result = new_tag_node(
        "infocard", children=[tag("label", {"updated": "never"}, "Monty Python")]
    )
    assert (
        str(result) == '<infocard><label updated="never">Monty '
        "Python</label></infocard>"
    )

    result = new_tag_node(
        "infocard", children=[tag("label", {"updated": "never"}, ("Monty ", "Python"))]
    )
    assert (
        str(result) == '<infocard><label updated="never">Monty '
        "Python</label></infocard>"
    )

    register_namespace("foo", "https://foo.org")
    result = new_tag_node("root", namespace="https://foo.org", children=[tag("node")])
    assert str(result) == '<foo:root xmlns:foo="https://foo.org"><foo:node/></foo:root>'


def test_make_node_outside_context():
    document = Document('<root xmlns="ham" />')

    register_namespace("spam", "https://spam")
    node = new_tag_node("a", namespace="https://spam")

    document.root.append_child(node)

    assert (
        str(document) == '<root xmlns="ham"><spam:a xmlns:spam="https://spam"/></root>'
    )


def test_make_node_in_context_with_namespace():
    document = Document("<root/>")

    node = document.new_tag_node("foo", namespace="https://name.space")
    assert node.namespace == "https://name.space"
    assert node._etree_obj.tag == "{https://name.space}foo"


def test_names(sample_document):
    root = sample_document.root

    assert root.namespace == "https://name.space"
    assert root.local_name == "doc"
    assert root.qualified_name == "{https://name.space}doc"
    assert root.namespaces == {None: "https://name.space"}

    first_level_children = tuple(x for x in root.child_nodes())
    header, text = first_level_children[0], first_level_children[1]

    assert header.namespace == "https://name.space"
    assert header.local_name == "header"
    assert header.namespaces == {None: "https://name.space"}

    assert text.namespace == "https://name.space"
    assert text.local_name == "text"
    assert text.namespaces == {None: "https://name.space"}, root.namespaces

    text.namespace = "https://space.name"
    assert text.qualified_name == "{https://space.name}text"


def test_next_in_stream(files_path):
    document = Document(files_path / "tei_marx_manifestws_1848.TEI-P5.xml")
    page_breaks = document.xpath(".//pb").as_list()

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

    document = Document("<root><a/></root>")
    assert document.root[0].prefix is None


def test_prepend_child():
    document = Document("<root><b/></root>")
    document.root.prepend_child(tag("a"))
    assert str(document) == "<root><a/><b/></root>"


def test_previous_in_stream(files_path):
    document = Document(files_path / "tei_marx_manifestws_1848.TEI-P5.xml")
    page_breaks = document.xpath(".//pb").as_list()

    cursor = page_breaks.pop()
    while len(page_breaks) > 1:
        prev = page_breaks.pop()
        assert cursor.previous_node_in_stream(is_pagebreak) is prev
        cursor = prev


def test_previous_node():
    document = Document("<root><a/></root>")
    assert document.root.previous_node() is None

    #

    document = Document("<root>a<c/></root>")
    root = document.root
    c = root[1]

    assert c.local_name == "c"

    a = c.previous_node()
    assert a.content == "a"

    a.add_next("b")
    assert c.previous_node().content == "b"

    #

    document = Document("<root><a/><!-- bla --><b/></root>")

    b = document.root[1]
    a = b.previous_node()
    assert a is not None
    assert a.local_name == "a"


def test_sample_document_structure(sample_document):
    root = sample_document.root

    assert root.parent is None

    first_level_children = tuple(x for x in root.child_nodes())
    assert len(first_level_children) == 2, first_level_children
    assert len(first_level_children) == len(root)

    header, text = first_level_children

    assert root[0] is header
    assert isinstance(header, TagNode), type(header)
    assert header.parent is root

    assert root[1] is text
    assert isinstance(text, TagNode), type(text)
    assert text.parent is root


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
