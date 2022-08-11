import pytest

from delb import tag, Document, InvalidOperation


def test_fetch_or_create_by_xpath():
    root = Document("<root><intermediate/></root>").root

    assert str(root.fetch_or_create_by_xpath("test")) == "<test/>"
    assert str(root) == "<root><intermediate/><test/></root>"

    assert str(root.fetch_or_create_by_xpath("intermediate/target")) == "<target/>"
    assert str(root) == "<root><intermediate><target/></intermediate><test/></root>"

    assert str(root.fetch_or_create_by_xpath("intermediate/target")) == "<target/>"
    assert str(root) == "<root><intermediate><target/></intermediate><test/></root>"

    root.append_child(tag("intermediate"))

    with pytest.raises(InvalidOperation):
        root.fetch_or_create_by_xpath("intermediate")

    with pytest.raises(InvalidOperation):
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


@pytest.mark.parametrize(
    "expression",
    (
        "child[0]",
        'child[@locale="en-gb" or @locale="en-us"]',
        "root/foo|./foo/bar",
        "root/node/descendant-or-self::node()",
        "body/div[@hidden]",
        "root/node/child/../node",
        "root[foo]",
    ),
)
def test_fetch_or_create_by_xpath_with_invalid_paths(expression):
    node = Document("<node/>").root
    # TODO remove AssertionError when error handling is implemented
    with pytest.raises((AssertionError, InvalidOperation)):
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

    with pytest.raises(RuntimeError):
        root.fetch_or_create_by_xpath("unknwn:test")


def test_fetch_or_create_by_xpath_with_multiple_attributes():
    root = Document("<root/>").root

    cit = root.fetch_or_create_by_xpath(
        'entry/sense/cit[@type="translation" and @lang="en"]'
    )
    assert str(cit) == '<cit type="translation" lang="en"/>'

    assert (
        root.fetch_or_create_by_xpath(
            'entry/sense/cit[@type="translation"][@lang="en"]'
        )
        is cit
    )


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
