import os
import sys
from itertools import pairwise, product

import pytest

from delb.filters import altered_default_filters
from delb.nodes import TagNode
from delb.typing import XMLNodeType  # noqa: TC001
from delb.utils import compare_trees


if sys.version_info < (3, 11):  # DROPWITH Python 3.10
    from contextlib import contextmanager
    from pathlib import Path

    @contextmanager
    def chdir(path: Path):
        state = Path.cwd()
        os.chdir(path)
        yield
        os.chdir(state)

else:
    from contextlib import chdir  # noqa: F401


@altered_default_filters()
def assert_equal_trees(a: XMLNodeType, b: XMLNodeType):
    result = compare_trees(a, b)
    if not result:
        raise AssertionError(str(result))


def assert_nodes_are_in_document_order(*nodes: XMLNodeType):
    # this test avoids usage of .location_path and .xpath
    # it also can test all node types
    if len(nodes) <= 1:
        raise ValueError
    if len(nodes) > 2:
        for node_pair in pairwise(nodes):
            assert_nodes_are_in_document_order(*node_pair)
        return

    lhn, rhn = nodes
    assert lhn is not rhn

    for lhn_index, rhn_index in zip(index_path(lhn), index_path(rhn)):
        if lhn_index < rhn_index:
            return
        if lhn_index == rhn_index:
            continue
        raise AssertionError


@altered_default_filters()
def index_path(node: XMLNodeType):
    result = []
    while node.parent is not None:
        result.append(node.index)
        node = node.parent
    result.reverse()
    return result


def variety_forest():
    for assembly_axes in product(("child", "following"), repeat=9):
        root = TagNode("root")

        node = root.prepend_children(TagNode("begin"))[0]

        for i, direction in enumerate(assembly_axes):
            new_node = TagNode(chr(ord("a") + i))
            match direction:
                case "child":
                    node.append_children(new_node)
                case "following":
                    node.add_following_siblings(new_node)
            node = new_node

        root.append_children(TagNode("end"))

        yield root


skip_long_running_test = pytest.mark.skipif(
    os.environ.get("SKIP_LONG_RUNNING_TESTS") is not None,
    reason="Long running tests are supposed to be skipped.",
)
