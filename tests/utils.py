import os
import sys

import pytest

from delb import (
    altered_default_filters,
    compare_trees,
    NodeBase,
)


if sys.version_info < (3, 10):  # DROPWITH Python 3.9
    from itertools import tee

    def pairwise(iterable):
        a, b = tee(iterable, 2)
        next(b, None)
        return zip(a, b)

else:
    from itertools import pairwise


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
def assert_equal_trees(a: NodeBase, b: NodeBase):
    result = compare_trees(a, b)
    if not result:
        raise AssertionError(str(result))


def assert_nodes_are_in_document_order(*nodes: NodeBase):
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
def index_path(node: NodeBase):
    result = []
    while node.parent is not None:
        result.append(node.index)
        node = node.parent
    result.reverse()
    return result


skip_long_running_test = pytest.mark.skipif(
    os.environ.get("SKIP_LONG_RUNNING_TESTS") is not None,
    reason="Long running tests are supposed to be skipped.",
)
