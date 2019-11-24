from pytest import mark

from delb import Document, get_traverser, is_tag_node

document = Document(
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


@mark.parametrize(
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
    ),
)
def test_traverser(from_left, depth_first, from_top, result):
    assert [
        x.local_name
        for x in get_traverser(
            from_left=from_left, depth_first=depth_first, from_top=from_top
        )(document.root, is_tag_node)
    ] == result
