import pytest

from _delb.nodes import _wrapper_cache
from delb import (
    is_tag_node,
    is_text_node,
    new_tag_node,
    parse_tree,
    tag,
    Document,
    TagNode,
    TextNode,
)
from delb.exceptions import InvalidOperation


def test_add_preceding_siblings():
    root = parse_tree("<root><e1/></root>")
    result = root[0].add_preceding_siblings(tag("e2"), tag("e3"))
    assert str(root) == "<root><e3/><e2/><e1/></root>"
    assert isinstance(result, tuple)
    assert len(result) == 2
    assert all(isinstance(n, TagNode) for n in result)
    assert result[0].local_name == "e2"
    assert result[1].local_name == "e3"


def test_add_following_siblings():
    root = parse_tree("<root><e1/></root>")
    result = root[0].add_following_siblings(tag("e2"), tag("e3"))
    assert str(root) == "<root><e1/><e2/><e3/></root>"
    assert isinstance(result, tuple)
    assert len(result) == 2
    assert all(isinstance(n, TagNode) for n in result)
    assert result[0].local_name == "e2"
    assert result[1].local_name == "e3"


def test_iterate_ancestors():
    root = parse_tree(
        "<root><left/>abc<middle><node>0</node></middle><right>xyz<xyz"
        "/></right></root>"
    )
    zero = root[2][0][0]
    assert isinstance(zero, TextNode)
    assert zero == "0"
    assert tuple(x.local_name for x in zero.iterate_ancestors()) == (
        "node",
        "middle",
        "root",
    )


def test_ancestors_of_detached_node():
    node = TextNode("x")
    assert tuple(node.iterate_ancestors()) == ()


def test_comment_is_ignored():
    root = parse_tree("<root><a/><!-- bla --><b/></root>")

    a = root[0]
    b = a.fetch_following_sibling()

    assert isinstance(b, TagNode)
    assert b.local_name == "b"


def test_index():
    root = parse_tree("<root><zero/>is<my/>country</root>")
    assert root.index is None
    for index in range(4):
        assert root[index].index == index

    #

    root = parse_tree("<root><a/><!-- bla --><b/></root>")

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
    assert str(document) == (
        '<?xml version="1.0" encoding="UTF-8"?>' "<root><div1><div2/> </div1></root>"
    )


# TODO remove with native data model
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

    with _wrapper_cache:
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

        root.insert_children(0, div1)
        div1 = root.first_child
        div2 = div1.first_child
        text = div1.last_child
        assert node_ids() == original_ids

        other_doc = Document(str(document))
        div1 = other_doc.css_select("div1").first
        div2 = other_doc.css_select("div2").first
        div2.detach()
        div1.insert_children(0, div2)

        div1 = document.css_select("div1").first
        div2 = document.css_select("div2").first

        div2.detach()
        div1 = root.first_child
        text = div1.first_child
        assert node_ids() == original_ids

        div1.insert_children(0, div2)


def test_invalid_operations():
    root_1 = parse_tree("<root/>")
    root_2 = parse_tree("<root><replacement/>parts</root>")

    with pytest.raises(InvalidOperation):
        root_1.append_children(root_2[0])

    new_node = new_tag_node("newNode")
    root_1.append_children(new_node)

    with pytest.raises(InvalidOperation):
        new_node.add_following_siblings(root_2[0])

    with pytest.raises(InvalidOperation):
        new_node.add_preceding_siblings(root_2[0])


def test_iter_following_nodes_over_long_stream(files_path):
    root = Document(files_path / "marx_manifestws_1848.TEI-P5.xml").root

    node = root.fetch_following(lambda _: False)
    assert node is None

    all_node_locations = set()
    for node in root.iterate_descendants(is_tag_node):
        all_node_locations.add(node.location_path)
    encountered_location_paths = set()
    for node in root.iterate_following(is_tag_node):
        location_path = node.location_path
        assert location_path not in encountered_location_paths
        encountered_location_paths.add(location_path)
    assert encountered_location_paths == all_node_locations

    expected_text = root.full_text  # operates in tree dimension
    collected_text = ""
    for node in root.iterate_following(is_text_node):
        collected_text += node.content
    assert collected_text == expected_text


def test_no_following_node():
    root = parse_tree("<root><a/></root>")
    assert root[0].fetch_following() is None


def test_no_preceding_node():
    root = parse_tree("<root><a/></root>")
    assert root.fetch_preceding() is None


def test_replace_with():
    root = parse_tree("<root><a>b</a>c<d>e</d></root>")

    b_text = root[0][0]
    b_text.replace_with(tag("b"))
    expected_new = root[0][0]

    assert b_text.parent is None
    assert expected_new is not b_text
    assert isinstance(expected_new, TagNode)
    assert expected_new.local_name == "b"
    assert str(root) == "<root><a><b/></a>c<d>e</d></root>"

    c_text = root[1]
    c_text.replace_with(tag("c"))
    expected_new = root[1]

    assert c_text.parent is None
    assert expected_new is not c_text
    assert isinstance(expected_new, TagNode)
    assert expected_new.local_name == "c"
    assert str(root) == "<root><a><b/></a><c/><d>e</d></root>"

    with pytest.raises(InvalidOperation):
        root.replace_with(tag("new"))


def test_replace_with_tag_definition():
    root = parse_tree('<root xmlns="https://name.space"><node/></root>')
    root.first_child.replace_with(tag("vertex", {"type": "xml"}))
    assert root.first_child.namespace == "https://name.space"
    assert str(root) == '<root xmlns="https://name.space"><vertex type="xml"/></root>'


def test_root_takes_no_siblings():
    root = parse_tree("<root/>")

    with pytest.raises(TypeError):
        root.add_following_siblings(tag("x"))

    with pytest.raises(TypeError):
        root.add_following_siblings("x")

    with pytest.raises(TypeError):
        root.add_preceding_siblings(tag("x"))

    with pytest.raises(TypeError):
        root.add_preceding_siblings("x")


def test_siblings_filter():
    root = parse_tree("<root><e1/>ham<e2/>spam<e3/></root>")

    e2 = root[2]

    assert isinstance(e2.fetch_preceding_sibling(), TextNode)
    assert isinstance(e2.fetch_following_sibling(), TextNode)

    assert isinstance(e2.fetch_preceding_sibling(is_tag_node), TagNode)
    assert isinstance(e2.fetch_following_sibling(is_tag_node), TagNode)

    spam = root[3]
    spam.add_following_siblings("plate")

    assert isinstance(spam.fetch_following_sibling(is_tag_node), TagNode)
