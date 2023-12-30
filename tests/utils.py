import re
import sys

from xmldiff import main as xmldiff

from delb import altered_default_filters

find_processing_instructions = re.compile(r"(<\?\w\S*?(\s.*?)?\?>)").findall


# REMOVE when support for Python 3.9 is dropped
if sys.version_info < (3, 10):
    from itertools import tee

    def pairwise(iterable):
        a, b = tee(iterable, 2)
        next(b, None)
        return zip(a, b)

else:
    from itertools import pairwise


def assert_documents_are_semantical_equal(old, new):
    changes = xmldiff.diff_files(
        str(old), str(new), diff_options={"F": 1.0, "ratio_mode": "accurate"}
    )
    assert not changes, changes


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
