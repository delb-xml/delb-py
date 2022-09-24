import gc

from delb import is_tag_node, is_text_node, tag, Document
from _delb.nodes import NodeBase, TagNode, _wrapper_cache


# the test order in this module matters!
# the thirst three tests ensure that the garbage collection doesn't act when not
# supposed to.
# also see test_aaa_setup_wrapper_cache.py
# the fourth one verifies that the garbage collection actually has cleaned everything
# when no delb objects were used by an application (test suite in this case)
# finally, the last test tests the gc in a nutshell


def test_document_root_sustains(long_term_references):
    gc.collect()
    document = long_term_references.pop("a_document")
    assert isinstance(document.root, TagNode)


def test_referenced_appendees_sustain(long_term_references):
    for name in ("appended_b", "appended_b_with_c"):
        gc.collect()
        b = long_term_references.pop(name)
        assert b in b.parent
        assert b.parent.first_child == "a"


def test_appended_text_contents_arent_lost():
    root = Document("<root><a><b><c><d/></c></b></a></root>").root

    for node in tuple(root.iterate_descendants(is_tag_node)):
        node.prepend_children("D")
        node.add_following_siblings("T")
    for node in tuple(root.iterate_descendants(is_text_node)):
        node.add_following_siblings("Z")

    gc.collect()
    assert str(root) == "<root><a>DZ<b>DZ<c>DZ<d>DZ</d>TZ</c>TZ</b>TZ</a>TZ</root>"


def test_no_dangling_objects(long_term_references):
    assert not long_term_references

    gc.collect()
    gc.collect()

    assert not _wrapper_cache.wrappers

    unexpected = []
    for obj in gc.get_objects():
        if isinstance(obj, (Document, NodeBase)):
            unexpected.append(obj)
    assert len(unexpected) == 0


def test_wrapper_cache():
    gc.collect()
    assert len(_wrapper_cache.wrappers) == 0

    root = Document("<root/>").root
    assert len(_wrapper_cache.wrappers) == 1

    root.append_children(tag("node"))
    assert len(_wrapper_cache.wrappers) == 2

    root.first_child.detach()
    gc.collect()
    assert len(_wrapper_cache.wrappers) == 1
