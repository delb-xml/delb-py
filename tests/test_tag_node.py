from copy import copy, deepcopy
from typing import Final

import pytest

from _delb.names import XML_NAMESPACE
from _delb.nodes import DefaultStringOptions, altered_default_filters
from delb import (
    Document,
    ParserOptions,
    TagNode,
    TextNode,
    is_tag_node,
    new_tag_node,
    parse_tree,
    tag,
)
from delb.exceptions import InvalidOperation
from tests.conftest import XML_FILES

from tests.utils import assert_nodes_are_in_document_order, skip_long_running_test

TEI_NAMESPACE: Final = "http://www.tei-c.org/ns/1.0"


def is_pagebreak(node):
    return isinstance(node, TagNode) and node.local_name == "pb"


def test_add_following_sibling_tag_before_tail():
    root = parse_tree("<root><a/>b</root>")
    root[0].add_following_siblings(tag("c"))
    assert str(root) == "<root><a/><c/>b</root>"


def test_add_following_sibling_text_node_before_text_sibling():
    root = parse_tree("<root><a/>c</root>")
    a = root[0]
    a.add_following_siblings("b")
    assert str(root) == "<root><a/>bc</root>"


def test_add_preceding_node():
    root = parse_tree("<root><a/></root>")

    a = root[0]
    a.add_preceding_siblings(tag("z"))
    assert str(root) == "<root><z/><a/></root>"

    z = root[0]
    z.add_preceding_siblings("x")
    assert str(root) == "<root>x<z/><a/></root>"

    z.add_preceding_siblings("y")
    assert str(root) == "<root>xy<z/><a/></root>"

    a.add_preceding_siblings(tag("boundary"))
    assert str(root) == "<root>xy<z/><boundary/><a/></root>"


def test_append_children():
    root = parse_tree("<root/>")
    result = root.append_children(tag("a"), "b")
    assert isinstance(result, tuple)
    assert len(result) == 2
    assert isinstance(result[0], TagNode)
    assert isinstance(result[1], TextNode)
    assert str(root) == "<root><a/>b</root>"


def test_append_no_child():
    root = parse_tree("<root/>")
    root.append_children()
    assert str(root) == "<root/>"


def test_contains():
    root = parse_tree('<root foo="bar"><node><descendant/></node></root>')
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
    node = parse_tree("<x/>")
    clone = copy(node)

    assert clone is not node
    assert clone._etree_obj is not node._etree_obj
    assert clone.universal_name == clone.universal_name
    assert clone.attributes == clone.attributes


def test_deepcopy():
    node = parse_tree("<x><y/></x>")
    clone = deepcopy(node)

    assert clone is not node
    assert clone._etree_obj is not node._etree_obj
    assert clone.universal_name == clone.universal_name
    assert clone.attributes == clone.attributes
    assert clone[0] is not node[0]


def test_delitem():
    namespace = "https://foo"
    root = parse_tree(f"<root xmlns='{namespace}' A='' B='' C=''><a/></root>")
    del root["A"]
    del root[namespace:"B"]
    del root[(namespace, "C")]
    del root[0]
    assert str(root) == f'<root xmlns="{namespace}"/>'
    with pytest.raises(IndexError):
        del root[0]
    with pytest.raises(KeyError):
        del root["A"]


def test_depth():
    root = parse_tree("<root><a><b/></a></root>")

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
    assert str(document) == '<?xml version="1.0" encoding="UTF-8"?><root/>'


def test_detach_node_with_tail_1():
    root = parse_tree("<root><a>c<c/></a>b<d/></root>")

    root[1].add_following_siblings("c")
    assert str(root) == "<root><a>c<c/></a>bc<d/></root>"
    root[0].detach()
    assert str(root) == "<root>bc<d/></root>"

    root.append_children(tag("e"), "f")
    assert str(root) == "<root>bc<d/><e/>f</root>"

    e = root.css_select("e").first
    assert isinstance(e, TagNode)
    assert e.local_name == "e"
    e.detach()
    assert str(root) == "<root>bc<d/>f</root>"

    root.append_children(tag("g"), "h")

    root[-2].detach()
    assert str(root) == "<root>bc<d/>fh</root>"


def test_detach_node_with_tail_2():
    root = parse_tree("<root><node><child/>childish</node></root>")

    node = root.first_child
    child = node.first_child

    child.detach()
    assert str(node) == "<node>childish</node>"
    assert child.fetch_following_sibling() is None


def test_detach_node_retain_child_nodes():
    root = parse_tree("<root><node><child/>childish<!-- [~.ö] --></node></root>")
    node = root.first_child

    node.detach(retain_child_nodes=True)

    assert len(node) == 0
    with altered_default_filters():
        assert str(root) == "<root><child/>childish<!-- [~.ö] --></root>"

    child = root.first_child
    child.detach(retain_child_nodes=True)
    with altered_default_filters():
        assert str(root) == "<root>childish<!-- [~.ö] --></root>"

    with pytest.raises(InvalidOperation):
        root.detach(retain_child_nodes=True)


def test_detach_node_retains_namespace_prefixes():
    # libxml2 loses the notion if a default prefix for nodes that have been
    # removed from a parent node
    root = parse_tree(
        """\
        <root xmlns="schema://default/">
            <child><grandchild/></child>
        </root>
        """
    )
    child = root.css_select("child").first.detach()
    assert child.css_select("grandchild").size == 1


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


def test_first_and_last_child():
    root = parse_tree("<root/>")
    assert root.first_child is None
    assert root.last_child is None

    root = parse_tree("<root><e1/><e2/></root>")
    assert root.first_child.local_name == "e1"
    assert root.last_child.local_name == "e2"

    root = parse_tree("<root>first<e1/><e2/>last</root>")
    assert root.first_child.content == "first"
    assert root.last_child.content == "last"


def test_full_text():
    root = parse_tree(
        "<root>The <em>quick <colored>red</colored> fox</em> "
        "<super>jumps over</super> the fence.</root>"
    )
    assert root.full_text == "The quick red fox jumps over the fence."


def test_getitem():
    namespace = "http://foo"
    root = parse_tree(f'<root xmlns="{namespace}" ham="spam"><a/><b/><c/><d/></root>')

    assert root["ham"] == "spam"
    assert root[(namespace, "ham")] == "spam"

    with pytest.raises(KeyError):
        root["foo"]

    assert root[-1].local_name == "d"

    assert "".join(x.local_name for x in root[1:]) == "bcd"
    assert "".join(x.local_name for x in root[1:3]) == "bc"
    assert "".join(x.local_name for x in root[:3]) == "abc"

    assert "".join(x.local_name for x in root[::-1]) == "dcba"

    with pytest.raises(IndexError):
        root[4]


def test_id_property(files_path):
    document = Document(files_path / "marx_manifestws_1848.TEI-P5.xml")
    publisher = document.css_select("publicationStmt publisher").first

    assert publisher.id == "DTACorpusPublisher"

    publisher.id = None
    assert (XML_NAMESPACE, "id") not in publisher.attributes

    publisher.id = "foo"
    assert publisher.attributes[(XML_NAMESPACE, "id")] == "foo"

    with pytest.raises(TypeError):
        publisher.id = 1234

    with pytest.raises(ValueError, match="already assigned"):
        publisher.parent.id = "foo"

    publisher.detach()
    a_tag_child_node = next(publisher.iterate_children(is_tag_node))
    with pytest.raises(ValueError, match="already assigned"):
        a_tag_child_node.id = "foo"


def test_insert_children():
    root = parse_tree("<root><a>c</a></root>")
    a = root[0]

    result = a.insert_children(0, tag("b"))
    assert isinstance(result, tuple)
    assert len(result) == 1
    assert isinstance(result[0], TagNode)

    assert str(root) == "<root><a><b/>c</a></root>"

    a.insert_children(0, "|aaa|")
    assert str(root) == "<root><a>|aaa|<b/>c</a></root>"

    a.insert_children(0, TextNode("|aa|"), clone=True)
    assert str(root) == "<root><a>|aa||aaa|<b/>c</a></root>"

    a.insert_children(1, "-")
    assert str(root) == "<root><a>|aa|-|aaa|<b/>c</a></root>"

    a.insert_children(3, new_tag_node("aaaa"))
    assert str(root) == "<root><a>|aa|-|aaa|<aaaa/><b/>c</a></root>"


def test_insert_first_child():
    root = parse_tree("<root/>")
    root.insert_children(0, "a")
    assert str(root) == "<root>a</root>"


def test_insert_at_invalid_index():
    root = parse_tree("<root><a/><b/></root>")

    with pytest.raises(ValueError, match="positive"):
        root.insert_children(-1, "x")

    with pytest.raises(IndexError):
        root.insert_children(3, "x")


def test_iterate_following_siblings():
    root = parse_tree("<root><a/><b><x/></b><c/>d<e>spam</e><f/></root>")
    expected = "bcdef"

    for i, node in enumerate(root[0].iterate_following_siblings()):
        if isinstance(node, TagNode):
            assert node.local_name == expected[i]
        else:
            assert node.content == expected[i]


def test_iterate_preceding_siblings():
    root = parse_tree("<root><a/><b><x/></b><c/>d<e>spam</e><f/></root>")
    expected = "abcde"[::-1]

    for i, node in enumerate(root[5].iterate_preceding_siblings()):
        if isinstance(node, TagNode):
            assert node.local_name == expected[i]
        else:
            assert node.content == expected[i]


def test_iterate_preceding():
    root = parse_tree("<a><b><c/></b><d><e><f/><g/></e><h><i><j/><k/></i></h></d></a>")
    k = root[1][1][0][1]
    assert k.local_name == "k"
    expected = "abcdefghij"[::-1]
    for i, node in enumerate(k.iterate_preceding()):
        assert node.local_name == expected[i]


def test_iterate_following():
    a = parse_tree("<a><b><c/></b><d><e><f/><g/></e><h><i><j/><k/></i></h></d></a>")
    expected = "bcdefghijk"
    for i, node in enumerate(a.iterate_following()):
        assert node.local_name == expected[i]


def test_last_descendant():
    root = parse_tree(
        "<root>"
        "<a><aa><aaa/><aab/></aa><ab><aba/><abb/></ab></a>"
        "<b><ba>baa</ba></b>"
        "<c/>"
        "</root>"
    )
    a, b, c = tuple(root.iterate_children())

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


@skip_long_running_test
@pytest.mark.parametrize("file", XML_FILES)
def test_location_path_and_xpath_concordance(file):
    document = Document(
        file,
        parser_options=ParserOptions(load_referenced_resources="external" in file.name),
    )
    assert document.xpath(document.root.location_path).first is document.root

    for node in document.root.iterate_descendants(is_tag_node):
        queried_nodes = document.xpath(node.location_path)
        assert queried_nodes.size == 1, node.location_path
        assert queried_nodes.first is node


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
    assert str(result) == (
        '<infocard><label updated="never">Monty Python</label></infocard>'
    )

    result = new_tag_node(
        "infocard", children=[tag("label", {"updated": "never"}, ("Monty ", "Python"))]
    )
    assert str(result) == (
        '<infocard><label updated="never">Monty Python</label></infocard>'
    )

    DefaultStringOptions.namespaces = {"foo": "https://foo.org"}
    result = new_tag_node("root", namespace="https://foo.org", children=[tag("node")])
    assert str(result) == '<foo:root xmlns:foo="https://foo.org"><foo:node/></foo:root>'


def test_make_node_outside_context():
    root = parse_tree('<root xmlns="ham" />')
    root.append_children(new_tag_node("a", namespace="https://spam"))
    DefaultStringOptions.namespaces = {"spam": "https://spam"}
    assert str(root) == '<root xmlns="ham" xmlns:spam="https://spam"><spam:a/></root>'


def test_make_node_with_namespace():
    node = new_tag_node("foo", namespace="https://name.space")
    assert node.namespace == "https://name.space"
    assert node._etree_obj.tag == "{https://name.space}foo"


@pytest.mark.parametrize(
    ("child_nodes", "expected_count"),
    (([""], 0), ([" "], 1), ([" ", " "], 1), (["", "", tag("child"), "", ""], 1)),
)
def test_merge_text_nodes(child_nodes, expected_count):
    node = new_tag_node("node", children=child_nodes)
    node.merge_text_nodes()
    assert len(node) == expected_count


def test_names(sample_document):
    root = sample_document.root

    assert root.namespace == "https://name.space"
    assert root.local_name == "doc"
    assert root.universal_name == "{https://name.space}doc"

    first_level_children = tuple(x for x in root.iterate_children())
    header, text = first_level_children[0], first_level_children[1]

    assert header.namespace == "https://name.space"
    assert header.local_name == "header"

    assert text.namespace == "https://name.space"
    assert text.local_name == "text"

    text.namespace = "https://space.name"
    assert text.universal_name == "{https://space.name}text"


def test_new_tag_node_with_tag_attributes_input():
    attributes = new_tag_node("node_1", {"a": "b", "{http://}c": "d"}).attributes
    assert new_tag_node("node_2", attributes).attributes == {
        "a": "b",
        ("http://", "c"): "d",
    }

    attributes = new_tag_node("node_1", {"a": "b"}, namespace="http://").attributes
    assert new_tag_node("node_2", attributes).attributes == {
        ("http://", "a"): "b",
    }


def test_fetch_following(files_path):
    document = Document(files_path / "marx_manifestws_1848.TEI-P5.xml")

    result = []
    for node in document.root.iterate_descendants(is_pagebreak):
        break

    while node is not None:
        result.append(node)
        node = node.fetch_following(is_pagebreak)

    assert len(result) == 23
    assert_nodes_are_in_document_order(*result)


def test_no_siblings_on_root():
    root = parse_tree("<root/>")

    with pytest.raises(TypeError):
        root.add_following_siblings("sibling")

    with pytest.raises(TypeError):
        root.add_preceding_siblings("sibling")


def test_prepend_children():
    root = parse_tree("<root><b/></root>")
    result = root.prepend_children(tag("a"))
    assert isinstance(result, tuple)
    assert len(result) == 1
    assert isinstance(result[0], TagNode)
    assert str(root) == "<root><a/><b/></root>"


def test_fetch_preceding(files_path):
    root = Document(files_path / "marx_manifestws_1848.TEI-P5.xml").root

    result = []
    for node in root.iterate_descendants(is_pagebreak):
        if isinstance(node, TagNode) and node.local_name == "pb":
            pass

    while node is not None:
        result.append(node)
        node = node.fetch_preceding(is_pagebreak)

    assert len(result) == 23
    assert_nodes_are_in_document_order(*reversed(result))


def test_fetch_preceding_sibling():
    root = parse_tree("<root><a/></root>")
    assert root.fetch_preceding_sibling() is None

    #

    root = parse_tree("<root>a<c/></root>")
    c = root[1]

    assert c.local_name == "c"

    a = c.fetch_preceding_sibling()
    assert a.content == "a"

    a.add_following_siblings("b")
    assert c.fetch_preceding_sibling().content == "b"

    #

    root = parse_tree("<root><a/><!-- bla --><b/></root>")

    b = root[1]
    a = b.fetch_preceding_sibling()
    assert a is not None
    assert a.local_name == "a"


def test_sample_document_structure(sample_document):
    root = sample_document.root

    assert root.parent is None

    first_level_children = tuple(x for x in root.iterate_children())
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
    root = parse_tree("<root>a</root>")
    root.append_children("b")

    assert str(root) == "<root>ab</root>"


def test_set_tag_components():
    root = parse_tree("<root/>")

    root.local_name = "top"
    assert str(root) == "<top/>"

    ns = "https://name.space"
    DefaultStringOptions.namespaces = {"prfx": ns}
    root.namespace = ns

    assert root.namespace == ns
    assert str(root) == '<prfx:top xmlns:prfx="https://name.space"/>'

    root.local_name = "root"
    assert str(root) == '<prfx:root xmlns:prfx="https://name.space"/>'


def test_set_item():
    namespace = "http://foo"
    root = parse_tree("<root/>")
    root[0] = tag("b")
    root[0] = tag("a")
    root["A"] = "1"
    root[(namespace, "B")] = "2"
    assert str(root) == '<root xmlns:ns0="http://foo" A="1" ns0:B="2"/>'
    with pytest.raises(IndexError):
        root[-1] = "text"
    with pytest.raises(IndexError):
        root[1] = "text"


def test_tag_definition_copies_attributes():
    root = parse_tree('<root foo="bar"/>')
    definition = tag("test", root.attributes)
    root.attributes["bar"] = "foo"
    root.append_children(definition)
    assert root.attributes == {("", "bar"): "foo", ("", "foo"): "bar"}
    assert root.first_child.attributes == {("", "foo"): "bar"}


def test_tag_definition_considers_namespace():
    root = parse_tree('<root xmlns="http://"/>')
    definition = tag("test", {"a": "b"})
    root.append_children(definition)
    test = root.first_child
    assert test.namespace == "http://"
    assert test.attributes == {("http://", "a"): "b"}
