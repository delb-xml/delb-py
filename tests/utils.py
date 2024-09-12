import os
import re
import sys

import pytest

from delb import (
    altered_default_filters,
    compare_trees,
    NodeBase,
)

find_processing_instructions = re.compile(r"(<\?\w\S*?(\s.*?)?\?>)").findall


if sys.version_info < (3, 10):  # DROPWITH Python 3.9
    from itertools import tee

    def pairwise(iterable):
        a, b = tee(iterable, 2)
        next(b, None)
        return zip(a, b)

else:
    from itertools import pairwise


@altered_default_filters()
def assert_equal_trees(a: NodeBase, b: NodeBase):
    result = compare_trees(a, b)
    if not result:
        raise AssertionError(str(result))


def assert_nodes_are_in_document_order(*nodes):
    # this test avoids usage of .location_path and .xpath
    # it also can test all node types
    if len(nodes) <= 1:
        raise ValueError
    if len(nodes) > 2:
        for node_pair in pairwise(nodes):
            assert_nodes_are_in_document_order(*node_pair)
        return

    for index_one, index_two in zip(index_path(nodes[0]), index_path(nodes[1])):
        if index_one < index_two:
            return
        if index_one == index_two:
            continue
        raise AssertionError


@altered_default_filters()
def index_path(node):
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
