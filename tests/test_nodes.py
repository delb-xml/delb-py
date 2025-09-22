import pytest

from delb import parse_tree, tag, Document
from delb.exceptions import InvalidOperation
from delb.filters import altered_default_filters, is_tag_node, is_text_node
from delb.nodes import CommentNode, TagNode, TextNode


def test_add_preceding_siblings():
    root = parse_tree("<root><e1/></root>")
    result = root[0].add_preceding_siblings(tag("e2"), tag("e3"))
    assert str(root) == "<root><e3/><e2/><e1/></root>"
    assert isinstance(result, tuple)
    assert len(result) == 2
    assert all(isinstance(n, TagNode) for n in result)
    assert result[0].local_name == "e2"
    assert result[1].local_name == "e3"

    comment = CommentNode("comment")

    with pytest.raises(InvalidOperation):
        root.add_preceding_siblings(comment)

    with pytest.raises(InvalidOperation):
        TextNode("text").add_preceding_siblings(comment)

    document = Document("<root/>")
    document.root.add_preceding_siblings(comment)
    assert (
        str(document) == '<?xml version="1.0" encoding="UTF-8"?><!--comment--><root/>'
    )


def test_add_following_siblings():
    root = parse_tree("<root><e1/></root>")
    result = root[0].add_following_siblings(tag("e2"), tag("e3"))
    assert str(root) == "<root><e1/><e2/><e3/></root>"
    assert isinstance(result, tuple)
    assert len(result) == 2
    assert all(isinstance(n, TagNode) for n in result)
    assert result[0].local_name == "e2"
    assert result[1].local_name == "e3"

    comment = CommentNode("comment")

    with pytest.raises(InvalidOperation):
        root.add_following_siblings(comment)

    with pytest.raises(InvalidOperation):
        TextNode("text").add_following_siblings(comment)

    document = Document("<root/>")
    document.root.add_following_siblings(comment)
    assert (
        str(document) == '<?xml version="1.0" encoding="UTF-8"?><root/><!--comment-->'
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


def test_detach():
    root = parse_tree("<root> <x/> </root>")
    root[2].detach()
    assert str(root) == "<root> <x/></root>"


def test_fetch_preceding():
    root = parse_tree("<root><a/><b/></root>")
    b = root[1]
    assert b.local_name == "b"
    a = b.fetch_preceding()
    assert a.local_name == "a"
    assert a.fetch_preceding() is root
    assert a._fetch_preceding() is root
    assert root.fetch_preceding() is None
    assert root._fetch_preceding() is None


def test_fetch_preceding_sibling():
    root = parse_tree("<root><a/></root>")
    assert root._fetch_preceding_sibling() is None
    assert root[0].fetch_preceding_sibling() is None
    assert root[0]._fetch_preceding_sibling() is None

    root = Document("<!----><root/>").root
    with altered_default_filters():
        comment = root.fetch_preceding_sibling()
        assert comment == CommentNode("")
        comment.detach()
        assert root.fetch_preceding_sibling() is None


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


def test_invalid_operations():
    root_1 = parse_tree("<root/>")
    root_2 = parse_tree("<root><replacement/>parts</root>")

    with pytest.raises(InvalidOperation):
        root_1.append_children(root_2[0])

    new_node = TagNode("newNode")
    root_1.append_children(new_node)

    with pytest.raises(InvalidOperation):
        new_node.add_following_siblings(root_2[0])

    with pytest.raises(InvalidOperation):
        new_node.add_preceding_siblings(root_2[0])


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


def test_iterate_following():
    for _ in TagNode("a")._iterate_following():
        raise AssertionError


def test_iterate_following_siblings():
    root = Document("<root/><!--a--><!--b-->").root
    result = ""
    with altered_default_filters():
        for node in root.iterate_following():
            result += node.content
        for node in root.iterate_following_siblings():
            result += node.content

    assert result == "abab"


def test_iterate_following_nodes_over_long_stream(files_path):
    root = Document(files_path / "marx_manifestws_1848.TEI-P5.xml").root

    assert root.fetch_following(lambda _: False) is None

    all_location_paths = set()
    for node in root.iterate_descendants(is_tag_node):
        all_location_paths.add(node.location_path)
    encountered_location_paths = set()
    for node in root.iterate_following(is_tag_node):
        location_path = node.location_path
        assert location_path not in encountered_location_paths
        encountered_location_paths.add(location_path)
    assert encountered_location_paths == all_location_paths

    expected_text = root.full_text  # operates on the descendants axis
    collected_text = ""
    for node in root.iterate_following(is_text_node):
        collected_text += node.content
    assert collected_text == expected_text


def test_iterate_preceding_siblings():
    root = Document("<!--b--><!--a--><root/>").root
    result = ""
    with altered_default_filters():
        for node in root.iterate_preceding():
            result += node.content
        for node in root.iterate_preceding_siblings():
            result += node.content

    assert result == "abab"


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
    c_replacement = TagNode("c")
    c_text.replace_with(c_replacement, clone=True)
    expected_new = root[1]

    assert c_text.parent is None
    assert expected_new is not c_replacement
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


def test_root_takes_no_tag_and_text_siblings():
    root = Document("<root/>").root

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
