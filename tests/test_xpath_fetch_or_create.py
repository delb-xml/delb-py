from pytest import mark, raises

from delb import tag, Document
from delb.exceptions import InvalidOperation, XPathEvaluationError


def test_fetch_or_create_by_xpath():
    root = Document("<root><intermediate/></root>").root

    assert str(root.fetch_or_create_by_xpath("test")) == "<test/>"
    assert str(root) == "<root><intermediate/><test/></root>"

    assert str(root.fetch_or_create_by_xpath("intermediate/target")) == "<target/>"
    assert str(root) == "<root><intermediate><target/></intermediate><test/></root>"

    assert str(root.fetch_or_create_by_xpath("intermediate/target")) == "<target/>"
    assert str(root) == "<root><intermediate><target/></intermediate><test/></root>"

    root.append_child(tag("intermediate"))

    with raises(InvalidOperation):
        root.fetch_or_create_by_xpath("intermediate")

    with raises(InvalidOperation):
        root.fetch_or_create_by_xpath("intermediate/test")


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

    assert str(
        root.fetch_or_create_by_xpath("author/name[@type='forename']/transcriptions")
        == "<transcriptions/>"
    )


@mark.parametrize(
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
    with raises(InvalidOperation):
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

    with raises(XPathEvaluationError):
        root.fetch_or_create_by_xpath("unknwn:test")


@mark.parametrize(
    "expression",
    (
        'entry/sense/cit[@type="translation" and "en"=@lang]',
        'entry/sense/cit[@type="translation"]["en"=@lang]',
    ),
)
def test_fetch_or_create_by_xpath_with_multiple_attributes(expression):
    root = Document("<root/>").root
    cit = root.fetch_or_create_by_xpath(expression)
    assert str(cit) == '<cit type="translation" lang="en"/>'
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


def test_fetch_or_create_by_xpath_with_prefixes_attributes():
    root = Document('<root xmlns:foo="bar"/>').root

    assert (
        str(root.fetch_or_create_by_xpath("node[@foo:attr='value']"))
        == '<node xmlns:foo="bar" foo:attr="value"/>'
    )
    assert str(root) == '<root xmlns:foo="bar"><node foo:attr="value"/></root>'
