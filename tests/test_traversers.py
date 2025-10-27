import pytest

from delb import parse_tree
from delb.filters import is_tag_node
from delb.utils import get_traverser


root = parse_tree(
    """\
        <root>
            <a>
                <aa/>
                <ab>
                    <aba/>
                </ab>
                <ac/>
            </a>
            <b/>
            <c>
                <ca>
                    <caa/>
                    <cab/>
                </ca>
                <cb/>
            </c>
        </root>
    """
)


@pytest.mark.parametrize(
    ("from_left", "depth_first", "from_top", "expected"),
    (
        (
            True,
            True,
            True,
            ["root", "a", "aa", "ab", "aba", "ac", "b", "c", "ca", "caa", "cab", "cb"],
        ),
        (
            True,
            True,
            False,
            ["aa", "aba", "ab", "ac", "a", "b", "caa", "cab", "ca", "cb", "c", "root"],
        ),
        (
            True,
            False,
            True,
            ["root", "a", "b", "c", "aa", "ab", "ac", "ca", "cb", "aba", "caa", "cab"],
        ),
        (
            False,
            True,
            False,
            ["cb", "cab", "caa", "ca", "c", "b", "ac", "aba", "ab", "aa", "a", "root"],
        ),
    ),
)
def test_traverser(from_left, depth_first, from_top, expected):
    assert [
        x.local_name
        for x in get_traverser(
            from_left=from_left, depth_first=depth_first, from_top=from_top
        )(root, is_tag_node)
    ] == expected
