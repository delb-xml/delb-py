import pytest

from lxml_domesque import is_tag_node, Document, InvalidOperation, TagNode, TextNode


def test_add_previous():
    document = Document("<root><e1/></root>")
    document.root[0].add_previous(
        document.new_tag_node("e2"), document.new_tag_node("e3")
    )

    assert str(document) == "<root><e3/><e2/><e1/></root>"


def test_add_next():
    document = Document("<root><e1/></root>")
    document.root[0].add_next(document.new_tag_node("e2"), document.new_tag_node("e3"))

    assert str(document) == "<root><e1/><e2/><e3/></root>"


def test_ancestors():
    document = Document(
        "<root><left/>abc<middle><node>0</node></middle><right>xyz<xyz"
        "/></right></root>"
    )
    zero = document.root[2][0][0]
    assert isinstance(zero, TextNode)
    assert zero == "0"
    assert tuple(str(x) for x in zero.ancestors()) == ("<node>", "<middle>", "<root>")


def test_ancestors_of_detached_node():
    node = TextNode("x")
    assert tuple(node.ancestors()) == ()


def test_index():
    root = Document("<root><zero/>is<my/>country</root>").root
    assert root.index is None
    for index in range(4):
        assert root[index].index == index


def insert_child():
    document = Document("<root><a>b</a></root>")
    root = document.root

    root[0].insert_child(root.new_tag_node("c"), index=1)

    assert str(document) == "<root><a>b<c/></a></root>"


def test_invalid_operations():
    document = Document("<root/>")
    document_2 = Document("<root><replacement/>parts</root>")

    with pytest.raises(InvalidOperation):
        document.root.append_child(document_2.root[0])

    new_node = document.new_tag_node("newNode")
    document.root.append_child(new_node)

    with pytest.raises(InvalidOperation):
        new_node.add_next(document_2.root[0])

    with pytest.raises(InvalidOperation):
        new_node.add_previous(document_2.root[0])


def test_replace_with():
    document = Document("<root><a>b</a>c<d>e</d></root>")
    root = document.root

    b_text = root[0][0]
    b_text.replace_with(root.new_tag_node("b"))

    assert b_text.parent is None

    expected_new = root[0][0]
    assert expected_new is not b_text, str(document)
    assert isinstance(expected_new, TagNode)
    assert expected_new.local_name == "b"

    assert str(document) == "<root><a><b/></a>c<d>e</d></root>"


def test_siblings_filter():
    document = Document("<root><e1/>ham<e2/>spam<e3/></root>")
    e2 = document.root[2]

    assert isinstance(e2.previous_node(), TextNode)
    assert isinstance(e2.next_node(), TextNode)

    assert isinstance(e2.previous_node(is_tag_node), TagNode)
    assert isinstance(e2.next_node(is_tag_node), TagNode)
