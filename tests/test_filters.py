from delb import (
    Document,
    TagNode,
    parse_tree,
)
from _delb.filters import (
    altered_default_filters,
    any_of,
    default_filters,
    is_processing_instruction_node,
    is_root_node,
    not_,
)


def test_anyof_filter():
    def has_a_attribute(node):
        return isinstance(node, TagNode) and "a" in node.attributes

    def has_b_attribute(node):
        return isinstance(node, TagNode) and "b" in node.attributes

    root = parse_tree('<root><x a=""/><x b=""/><x c=""/></root>')

    results = tuple(root.iterate_children(any_of(has_a_attribute, has_b_attribute)))

    assert len(results) == 2
    assert all("c" not in x.attributes for x in results)


def test_extended_default_filters():
    assert len(default_filters) == 1
    assert len(default_filters[-1]) == 1
    with altered_default_filters(lambda n: True, extend=True):
        assert len(default_filters) == 2
        assert len(default_filters[-1]) == 2
    assert len(default_filters) == 1
    assert len(default_filters[-1]) == 1


def test_is_pi_node():
    document = Document("<root/><?a b?><!--c--><?d e?>")
    with altered_default_filters():
        for i, _ in enumerate(
            document.root.iterate_following(is_processing_instruction_node)
        ):
            pass
        assert i == 1


def test_is_root_node():
    root = parse_tree("<root><a><b/></a></root>")
    b = root.last_descendant
    assert b.local_name == "b"
    assert next(b.iterate_ancestors(is_root_node)) is root


def test_not_filter():
    def has_a_attribute(node):
        return isinstance(node, TagNode) and "a" in node.attributes

    def has_b_attribute(node):
        return isinstance(node, TagNode) and "b" in node.attributes

    root = parse_tree('<root><x a=""/><x b=""/><x a="" b=""/><x c=""/></root>')

    results = tuple(
        root.iterate_children(not_(any_of(has_a_attribute, has_b_attribute)))
    )

    assert len(results) == 1
    assert "c" in results[0].attributes

    results = tuple(root.iterate_children(not_(has_a_attribute, has_b_attribute)))

    assert len(results) == 3
