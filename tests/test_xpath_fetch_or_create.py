import pytest

from delb import tag, Document
from delb.exceptions import AmbiguousTreeError, XPathEvaluationError


# TODO remove when empty declarations are used as fallback
pytestmark = pytest.mark.filterwarnings("ignore:.* namespace declarations")


@pytest.mark.parametrize("absolute", ("", "/root/"))
def test_fetch_or_create_by_xpath(absolute):
    root = Document("<root><intermediate/></root>").root

    assert str(root.fetch_or_create_by_xpath(f"{absolute}test")) == "<test/>"
    assert str(root) == "<root><intermediate/><test/></root>"

    assert (
        str(root.fetch_or_create_by_xpath(f"{absolute}intermediate/target"))
        == "<target/>"
    )
    assert str(root) == "<root><intermediate><target/></intermediate><test/></root>"

    assert (
        str(root.fetch_or_create_by_xpath(f"{absolute}intermediate/target"))
        == "<target/>"
    )
    assert str(root) == "<root><intermediate><target/></intermediate><test/></root>"

    root.append_children(tag("intermediate"))

    with pytest.raises(AmbiguousTreeError):
        root.fetch_or_create_by_xpath(f"{absolute}intermediate")

    with pytest.raises(AmbiguousTreeError):
        root.fetch_or_create_by_xpath(f"{absolute}intermediate/test")


def test_fetch_or_create_by_xpath_with_attributes():
    root = Document("<root/>").root

    assert (
        str(root.fetch_or_create_by_xpath('author/name[@type="surname"]'))
        == '<name type="surname"/>'
    )
    assert (
        str(root.fetch_or_create_by_xpath('author/name[@type="forename"]'))
        == '<name type="forename"/>'
    )

    assert (
        str(
            root.fetch_or_create_by_xpath(
                "author/name[@type='forename']/transcriptions"
            )
        )
        == "<transcriptions/>"
    )


@pytest.mark.parametrize(
    "expression",
    (
        "child[0]",
        'child[@locale="en-gb" or @locale="en-us"]',
        "root/foo|./foo/bar",
        "root/node/descendant-or-self::node()",
        "body/div[@hidden]",
        "root/node/child/../node",
    ),
)
def test_fetch_or_create_by_xpath_with_invalid_paths(expression):
    node = Document("<node/>").root
    with pytest.raises(ValueError, match="distinct branch"):
        node.fetch_or_create_by_xpath(expression)


def test_fetch_or_create_by_xpath_with_prefix():
    root = Document("<root xmlns:prfx='http://test.io'><intermediate/></root>").root
    assert (
        str(root.fetch_or_create_by_xpath("intermediate/prfx:test"))
        == '<prfx:test xmlns:prfx="http://test.io"/>'
    )
    assert (
        str(root) == '<root xmlns:prfx="http://test.io">'
        "<intermediate><prfx:test/></intermediate>"
        "</root>"
    )

    with pytest.raises(XPathEvaluationError):
        root.fetch_or_create_by_xpath("unknwn:test")


@pytest.mark.parametrize(
    "expression",
    (
        'entry/sense/cit[@type="translation" and "en"=@lang]',
        'entry/sense/cit[@type="translation"]["en"=@lang]',
    ),
)
def test_fetch_or_create_by_xpath_with_multiple_attributes(expression):
    root = Document("<root/>").root
    cit = root.fetch_or_create_by_xpath(expression)
    assert str(cit) == '<cit lang="en" type="translation"/>'
    assert root.fetch_or_create_by_xpath(expression) is cit


def test_fetch_or_create_by_xpath_with_predicates_in_parentheses():
    root = Document("<root/>").root

    cit = root.fetch_or_create_by_xpath(
        'entry/sense/cit[((@type="translation") and (@lang="en"))]'
    )
    assert (
        root.fetch_or_create_by_xpath(
            'entry/sense/cit[(@type="translation")][((@lang="en"))]'
        )
        is cit
    )
    assert root.css_select('entry > sense > cit[lang="en"]').size == 1


def test_fetch_or_create_by_xpath_with_prefixed_attributes():
    root = Document('<root xmlns:foo="bar"/>').root

    assert (
        str(root.fetch_or_create_by_xpath("node[@foo:attr='value']"))
        == '<node xmlns:foo="bar" foo:attr="value"/>'
    )
    assert str(root) == '<root xmlns:foo="bar"><node foo:attr="value"/></root>'
