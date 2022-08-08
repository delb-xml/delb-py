from pytest import mark

from _delb.nodes import altered_default_filters, is_tag_node
from _delb.xpath.ast import Axis
from delb import Document


@mark.parametrize(
    ("name", "start_name", "expected_order"),
    (
        ("ancestor", "c", "ba"),
        ("ancestor-or-self", "c", "cba"),
        ("child", "b", "cde"),
        ("descendant", "a", "bcdefghi"),
        ("descendant-or-self", "a", "abcdefghi"),
        ("following", "b", "cdefghi"),
        ("following-sibling", "b", "f"),
        ("following-sibling", "c", "de"),
        ("parent", "a", ""),
        ("parent", "d", "b"),
        ("preceding", "i", "hgfedcba"),
        ("preceding-sibling", "f", "b"),
        ("preceding-sibling", "i", "hg"),
        ("self", "a", "a"),
    ),
)
def test_axes_order(name, start_name, expected_order):
    root = Document(
        """\
        <a>
            <b>
                <c/>
                <d/>
                <e/>
            </b>
            <f>
                <g/>
                <h/>
                <i/>
            </f>
        </a>
    """
    ).root

    with altered_default_filters(is_tag_node):
        axis = Axis(name)

        if start_name == "a":
            node = root
        else:
            for node in root.child_nodes(recurse=True):
                if node.local_name == start_name:
                    break

        assert node.local_name == start_name
        result = "".join(n.local_name for n in axis.evaluate(node, {}))
        assert result == expected_order


def test_multiple_identical_location_paths():
    document = Document("<root><foo/></root>")
    assert document.xpath("/foo | /foo").size == 1


def test_multiple_predicates():
    document = Document(
        "<root><n x='1'/><n a='' x='2'/><n a='' x='3'/><n x='4'/><n a='' x='5'/></root>"
    )
    result = document.xpath("/n[@a][2]")
    assert result.size == 1
    assert result.first["x"] == "3"
