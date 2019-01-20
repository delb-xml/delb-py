from lxml_domesque import Document, TagNode

from lxml import etree


document = Document(
    """\
<doc xmlns="https://name.space">
    <header/>
    <text>
        <milestone unit="page"/>
        <p>Lorem ipsum</p>
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
