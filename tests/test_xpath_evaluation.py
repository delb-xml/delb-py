import pytest

from _delb.xpath.ast import Axis
from delb import altered_default_filters, is_tag_node, Document, TagNode, TextNode


# TODO remove when empty declarations are used as fallback
pytestmark = pytest.mark.filterwarnings("ignore:.* namespace declarations")


def test_any_name_test():
    document = Document("<root><node/><node xmlns='http://foo.bar'/></root>")

    assert document.xpath("//*").size == 3
    assert document.xpath("//p:*", namespaces={"p": "http://foo.bar"}).size == 1


@pytest.mark.parametrize(
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
            for node in root.iterate_descendants():
                if node.local_name == start_name:
                    break

        assert node.local_name == start_name
        result = "".join(
            n.local_name for n in axis.evaluate(node, {}) if isinstance(n, TagNode)
        )
        assert result == expected_order


def test_contributed_function_text():
    document = Document("<root><a>foo</a><b>bar</b><c>f<x/>oo</c></root>")
    result = document.xpath("//*[text()='foo']")
    assert result.size == 1
    assert result.first.local_name == "a"


def test_custom_functions():
    # this is used as example in the xpath module docstring
    document = Document("<root><node/><node foo='BAR'/></root>")
    result = document.xpath("//*[is-last() and lowercase(@foo)='bar']")
    assert result.size == 1
    assert result.first["foo"] == "BAR"


def test_evaluation_from_text_node():
    root = Document("<text><p>Elle dit: <hi>Ooh lala.</hi></p></text>").root
    p = root[0]
    node = p[1][0]
    assert isinstance(node, TextNode)
    assert "lala" in node

    result = node.xpath("ancestor::p")
    assert result.size == 1
    assert result.first is p


def test_multiple_identical_location_paths():
    document = Document("<root><foo/></root>")
    assert document.xpath("//foo | //foo").size == 1


def test_multiple_predicates():
    document = Document(
        "<root><n x='1'/><n a='' x='2'/><n a='' x='3'/><n x='4'/><n a='' x='5'/></root>"
    )
    result = document.xpath("//n[@a][2]")
    assert result.size == 1
    assert result.first["x"] == "3"


def test_processing_instruction():
    document = Document(
        """\
        <root>
          <header>
            <?delb yes?>
            <?delb-delb no?>
            <?delb yes?>
          </header>
        </root>
    """
    )

    result = document.xpath("//processing-instruction()")
    assert result.size == 3

    result = document.xpath("//processing-instruction('delb')")
    assert result.size == 2
    assert all(x.content == "yes" for x in result)

    assert not document.xpath("//processing-instruction()[@lang]")


def test_scope_on_descendant_or_self_axis():
    # this test is here to remind us how abbreviated XPath syntax is not intuitive
    first_record = (
        Document(
            """<root>
               <record id="a"><metadata id="1"/></record>
               <record id="b"><metadata id="2"/></record>
               </root>"""
        )
        .xpath("//record")
        .first
    )
    assert first_record["id"] == "a"

    result = first_record.xpath(".//metadata")
    assert len(result) == 1
    assert result.first["id"] == "1"

    assert len(first_record.xpath("//metadata")) == 2
