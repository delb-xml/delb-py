import pytest

from delb import get_traverser, is_tag_node, parse_tree


@pytest.mark.parametrize(
    ("from_left", "depth_first", "from_top", "result"),
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
    ),
)
def test_traverser(from_left, depth_first, from_top, result):
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
    assert [
        x.local_name
        for x in get_traverser(
            from_left=from_left, depth_first=depth_first, from_top=from_top
        )(root, is_tag_node)
    ] == result
