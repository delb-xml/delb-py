import pytest

from delb import altered_default_filters, compare_trees, first, is_tag_node, parse_tree


@pytest.mark.parametrize(
    ("a", "b"),
    (
        ("<node/>", "<mode/>"),
        ("<node/>", "<node xmlns='http://foo.ls'/>"),
        ("<node a=''/>", "<node b=''/>"),
        ("<node a=''/>", "<node xmlns:p='http://foo.ls' p:a=''/>"),
        ("<node><!--a--></node>", "<node><!-- a --></node>"),
        ("<node>foo</node>", "<node>bar</node>"),
        ("<node><a/></node>", "<node><a/><a/></node>"),
        ("<node><a/><b/></node>", "<node><a/><a/></node>"),
    ),
)
def test_compare_unequal_trees(a, b):
    with altered_default_filters():
        assert not compare_trees(parse_tree(a), parse_tree(b))


def test_first():
    assert first([]) is None
    assert first([1]) == 1
    assert first((1, 2)) == 1

    root = parse_tree("<root><a/><a/><b/></root>")
    assert (
        first(root.iterate_children(is_tag_node, lambda x: x.local_name == "c")) is None
    )
    assert (
        first(root.iterate_children(is_tag_node, lambda x: x.local_name == "b"))
        is root[2]
    )
    assert (
        first(root.iterate_children(is_tag_node, lambda x: x.local_name == "a"))
        is root[0]
    )

    with pytest.raises(TypeError):
        first({})


def test_string_methods_on_classes_with_text_capabilities():
    root = parse_tree("<root n='[III]'>[III]</root>")
    for obj in (root["n"], root.first_child):
        assert obj == "[III]"
        assert obj.startswith("[")
        assert "III" in obj
        assert obj.strip("[]") == "III"
        assert obj[1:-1] == "III"
