from lxml_domesque import is_text_node, Document, TagNode, TextNode

from lxml import etree


document = Document(
    """\
<doc xmlns="https://name.space">
    <header/>
    <text>
        <milestone unit="page"/>
        <p>Lorem ipsum
            <milestone unit="line"/>
            dolor sit amet
        </p>
    </text>
</doc>
"""
)


def test_bindings():
    tree = document._etree_obj
    assert isinstance(tree, etree._ElementTree), type(tree)

    root = document.root
    assert isinstance(root, TagNode), type(root)
    assert isinstance(root._etree_obj, etree._Element), type(root._etree_obj)

    assert document.root._etree_obj is tree.getroot()


def test_instance_caching():
    assert document.root is document.root


def test_tag_nodes():
    root = document.root

    assert isinstance(root, TagNode), type(root)
    # TODO assert_has_attrs
    assert root.namespace == "https://name.space"
    assert root.local_name == "doc"
    assert root.fully_qualified_name == "{https://name.space}doc"
    assert root.namespaces == {None: "https://name.space"}, root.namespaces
    assert root.parent is None

    first_level_children = tuple(x for x in root.child_nodes())
    assert len(first_level_children) == 2, first_level_children
    assert len(first_level_children) == len(root)

    header, text = first_level_children[0], first_level_children[1]

    assert root[0] is header
    assert isinstance(header, TagNode), type(header)
    assert header.namespace == "https://name.space"
    assert header.local_name == "header"
    assert header.namespaces == {None: "https://name.space"}, root.namespaces
    assert header.parent is root

    assert root[1] is text
    assert isinstance(text, TagNode), type(text)
    assert text.namespace == "https://name.space"
    assert text.local_name == "text"
    assert text.namespaces == {None: "https://name.space"}, root.namespaces
    assert text.parent is root


def test_caching():
    p = document.root[1][1]
    text_nodes = tuple(x for x in p.child_nodes(is_text_node))

    x, y = text_nodes[1], p[2]
    assert str(x) == str(y)
    assert x._position == y._position
    assert x._bound_to is y._bound_to
    assert x.parent is y.parent
    assert x is y


def test_text_nodes():
    p = document.root[1][1]

    text_nodes = tuple(x for x in p.child_nodes(is_text_node))

    assert len(text_nodes) == 2
    assert text_nodes[0] is p[0]

    assert text_nodes[1] is p[2]
    assert all(isinstance(x, TextNode) for x in text_nodes)
    assert text_nodes[0].content.strip() == "Lorem ipsum"
    assert text_nodes[1].content.strip() == "dolor sit amet"
