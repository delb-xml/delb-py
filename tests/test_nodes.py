import pytest

from delb import (
    altered_default_filters,
    is_tag_node,
    is_text_node,
    new_tag_node,
    tag,
    Document,
    TagNode,
    TextNode,
)
from delb.exceptions import InvalidOperation


def test_add_previous():
    document = Document("<root><e1/></root>")
    document.root[0].add_previous(tag("e2"), tag("e3"))

    assert str(document) == "<root><e3/><e2/><e1/></root>"


def test_add_next():
    document = Document("<root><e1/></root>")
    document.root[0].add_next(tag("e2"), tag("e3"))

    assert str(document) == "<root><e1/><e2/><e3/></root>"


def test_ancestors():
    document = Document(
        "<root><left/>abc<middle><node>0</node></middle><right>xyz<xyz"
        "/></right></root>"
    )
    zero = document.root[2][0][0]
    assert isinstance(zero, TextNode)
    assert zero == "0"
    assert tuple(x.local_name for x in zero.ancestors()) == ("node", "middle", "root")


def test_ancestors_of_detached_node():
    node = TextNode("x")
    assert tuple(node.ancestors()) == ()


def insert_child():
    document = Document("<root><a>b</a></root>")
    root = document.root

    root[0].insert_child(1, root.new_tag_node("c"))

    assert str(document) == "<root><a>b<c/></a></root>"


def test_comment_is_ignored():
    root = Document("<root><a/><!-- bla --><b/></root>").root

    a = root[0]
    b = a.next_node()

    assert isinstance(b, TagNode)
    assert b.local_name == "b"


def test_index():
    root = Document("<root><zero/>is<my/>country</root>").root
    assert root.index is None
    for index in range(4):
        assert root[index].index == index

    #

    root = Document("<root><a/><!-- bla --><b/></root>").root

    a = root[0]
    assert isinstance(a, TagNode)
    assert a.local_name == "a"

    b = root[1]
    assert isinstance(b, TagNode)
    assert b.local_name == "b"

    assert len(root) == 2


def test_insert_issue_in_a_more_complex_situation():
    document = Document("<root><foo><div1><bar><div2/></bar> </div1></foo></root>")
    for node in document.root.css_select("bar,foo"):
        node.detach(retain_child_nodes=True)
    assert str(document) == "<root><div1><div2/> </div1></root>"


def test_wrapper_consistency():
    # this test is the result of an investigation that asked why
    # `test_insert_issue_in_a_more_complex_situation` failed.
    # as a result, the way how node wrapper are tracked has been refactored.
    # so this test is looking on under-the-hood-expectations for aspects of the
    # mentioned test. when maintaining this requires effort, it should rather be
    # dropped.
    def node_ids():
        return {
            "root": id(root),
            "foo": id(foo),
            "div1": id(div1),
            "div2": id(div2),
            "text": id(text),
        }

    document = Document("<root><foo><div1><div2/>text</div1></foo></root>")

    root = document.root
    foo = root.first_child
    div1 = foo.first_child
    div2 = div1.first_child
    text = div1.last_child

    original_ids = node_ids()

    div1.detach()
    foo = root.first_child
    div2 = div1.first_child
    text = div1.last_child
    assert node_ids() == original_ids

    foo.detach()
    assert node_ids() == original_ids

    root.insert_child(0, div1)
    div1 = root.first_child
    div2 = div1.first_child
    text = div1.last_child
    assert node_ids() == original_ids

    other_doc = Document(str(document))
    div1 = other_doc.css_select("div1").first
    div2 = other_doc.css_select("div2").first
    div2.detach()
    div1.insert_child(0, div2)

    div1 = document.css_select("div1").first
    div2 = document.css_select("div2").first

    div2.detach()
    div1 = root.first_child
    text = div1.first_child
    assert node_ids() == original_ids

    div1.insert_child(0, div2)


def test_invalid_operations():
    document_1 = Document("<root/>")
    document_2 = Document("<root><replacement/>parts</root>")

    with pytest.raises(InvalidOperation):
        document_1.root.append_child(document_2.root[0])

    new_node = new_tag_node("newNode")
    document_1.root.append_child(new_node)

    with pytest.raises(InvalidOperation):
        new_node.add_next(document_2.root[0])

    with pytest.raises(InvalidOperation):
        new_node.add_previous(document_2.root[0])


def test_iter_next_node_over_long_stream(files_path):
    root = Document(files_path / "marx_manifestws_1848.TEI-P5.xml").root

    node = root.next_node_in_stream(lambda _: False)
    assert node is None

    all_node_locations = set()
    for node in root.iterate_descendants(is_tag_node):
        all_node_locations.add(node.location_path)
    encountered_location_paths = set()
    for node in root.iterate_next_nodes_in_stream(is_tag_node):
        location_path = node.location_path
        assert location_path not in encountered_location_paths
        encountered_location_paths.add(location_path)
    assert encountered_location_paths == all_node_locations

    expected_text = root.full_text  # operates in tree dimension
    collected_text = ""
    for node in root.iterate_next_nodes_in_stream(is_text_node):
        collected_text += node.content
    assert collected_text == expected_text


def test_namespaces():
    node = Document("<node/>").root
    namespaces = node.namespaces

    namespaces["xmpl"] = "https:example.org"
    assert "xmpl" in namespaces

    assert len(namespaces) == 3
    assert set(namespaces.keys()) == {"xml", "xmlns", "xmpl"}

    namespaces.pop("xmpl")
    assert "xmpl" not in namespaces

    namespaces.pop("xml")
    assert "xml" in namespaces

    with pytest.raises(InvalidOperation):
        namespaces["xml"] = "something completely different"


def test_no_next_node_in_stream():
    document = Document("<root><a/></root>")
    assert document.root[0].next_node_in_stream() is None


def test_no_previous_node_in_stream():
    document = Document("<root><a/></root>")
    assert document.root.previous_node_in_stream() is None


@pytest.mark.parametrize("yes_or_no", (True, False))
def test_parse(yes_or_no):
    data = "<node>foo<child><!--bar--></child></node>"
    if yes_or_no:
        data = data.encode()
    node = TagNode.parse(data, collapse_whitespace=yes_or_no)
    child = node.last_child

    assert node.document is None
    assert node.local_name == "node"
    assert node.first_child.content == "foo"
    assert child.local_name == "child"
    with altered_default_filters():
        assert child.first_child.content == "bar"


def test_replace_with():
    document = Document("<root><a>b</a>c<d>e</d></root>")
    root = document.root

    b_text = root[0][0]
    b_text.replace_with(tag("b"))
    expected_new = root[0][0]

    assert b_text.parent is None
    assert expected_new is not b_text
    assert isinstance(expected_new, TagNode)
    assert expected_new.local_name == "b"
    assert str(document) == "<root><a><b/></a>c<d>e</d></root>"

    c_text = root[1]
    c_text.replace_with(tag("c"))
    expected_new = root[1]

    assert c_text.parent is None
    assert expected_new is not c_text
    assert isinstance(expected_new, TagNode)
    assert expected_new.local_name == "c"
    assert str(document) == "<root><a><b/></a><c/><d>e</d></root>"

    with pytest.raises(InvalidOperation):
        root.replace_with(tag("new"))


def test_replace_with_tag_definition():
    root = Document('<root xmlns="https://name.space"><node/></root>').root
    root.first_child.replace_with(tag("vertex", {"type": "xml"}))
    assert root.first_child.namespace == "https://name.space"
    assert str(root) == '<root xmlns="https://name.space"><vertex type="xml"/></root>'


def test_root_takes_no_siblings():
    root = Document("<root/>").root

    with pytest.raises(InvalidOperation):
        root.add_next(tag("x"))

    with pytest.raises(InvalidOperation):
        root.add_next("x")

    with pytest.raises(InvalidOperation):
        root.add_previous(tag("x"))

    with pytest.raises(InvalidOperation):
        root.add_previous("x")


def test_siblings_filter():
    document = Document("<root><e1/>ham<e2/>spam<e3/></root>")
    root = document.root

    e2 = root[2]

    assert isinstance(e2.previous_node(), TextNode)
    assert isinstance(e2.next_node(), TextNode)

    assert isinstance(e2.previous_node(is_tag_node), TagNode)
    assert isinstance(e2.next_node(is_tag_node), TagNode)

    spam = root[3]
    spam.add_next("plate")

    assert isinstance(spam.next_node(is_tag_node), TagNode)


def test_deprecated_methods():
    root = Document("<root/>").root

    assert root.qualified_name == "root"

    root.append_child("c")
    root.prepend_child("a")
    root.insert_child(1, "b")
    b = root[1]
    b.add_next("_")
    b.add_previous("_")

    assert str(root) == "<root>a_b_c</root>"
    assert tuple(b.ancestors()) == tuple(b.iterate_ancestors())
    assert tuple(root.child_nodes()) == tuple(root.iterate_children())
    assert tuple(root.iterate_children(recurse=True)) == tuple(
        root.iterate_descendants()
    )
    assert tuple(b.iterate_next_nodes()) == tuple(b.iterate_following_siblings())
    assert tuple(b.iterate_next_nodes_in_stream()) == tuple(b.iterate_following())
    assert tuple(b.iterate_previous_nodes()) == tuple(b.iterate_preceding_siblings())
    assert tuple(b.iterate_previous_nodes_in_stream()) == tuple(b.iterate_preceding())
    assert b.next_node() is b.fetch_following_sibling()
    assert b.next_node_in_stream() is b.fetch_following()
    assert b.previous_node() is b.fetch_preceding_sibling()
    assert b.previous_node_in_stream() is b.fetch_preceding()
