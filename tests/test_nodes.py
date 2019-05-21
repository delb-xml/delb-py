import pytest

from delb import (
    is_tag_node,
    new_tag_node,
    tag,
    Document,
    InvalidOperation,
    TagNode,
    TextNode,
)


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

    root[0].insert_child(root.new_tag_node("c"), index=1)

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


def test_no_next_node_in_stream():
    document = Document("<root><a/></root>")
    assert document.root[0].next_node_in_stream() is None


def test_no_previous_node_in_stream():
    document = Document("<root><a/></root>")
    assert document.root.previous_node_in_stream() is None


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
