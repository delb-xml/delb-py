import pytest

from delb import first, is_tag_node, Document


def test_first():
    assert first([]) is None
    assert first([1]) == 1
    assert first((1, 2)) == 1

    root = Document("<root><a/><a/><b/></root>").root
    assert first(root.child_nodes(is_tag_node, lambda x: x.local_name == "c")) is None
    assert (
        first(root.child_nodes(is_tag_node, lambda x: x.local_name == "b")) is root[2]
    )
    assert (
        first(root.child_nodes(is_tag_node, lambda x: x.local_name == "a")) is root[0]
    )

    with pytest.raises(TypeError):
        first({})
