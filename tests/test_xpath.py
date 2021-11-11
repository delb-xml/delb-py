import pytest
from pkg_resources import get_distribution

from _delb.xpath import (
    _in_parenthesis,
    _partition_terms,
    _reduce_whitespace,
    _split,
    AttributePredicate,
    BooleanPredicate,
    FunctionExpression,
    Literal,
    PredicateExpression,
    XPathExpression,
)


DELB_VERSION = get_distribution("delb").parsed_version.release


def test_function():
    with pytest.raises(AssertionError):
        PredicateExpression.parse(")")
    predicates = PredicateExpression.parse("starts-with(@foo,'a(b(c)')")

    assert isinstance(predicates, FunctionExpression)
    assert predicates.name == "starts-with"
    assert len(predicates.arguments) == 2

    assert isinstance(predicates.arguments[0], AttributePredicate)
    assert predicates.arguments[0].name == "foo"

    assert isinstance(predicates.arguments[1], Literal)
    assert predicates.arguments[1].value == "a(b(c)"


@pytest.mark.xfail(
    DELB_VERSION < (0, 4),
    reason="A solid XPath parser will be implemented when a supported subset of XPath "
    "has been defined.",
)
def test_function_args():
    parsed_expression = XPathExpression(
        './/a[@href and not(starts-with(@href, "https://"))]'
    )
    predicates = parsed_expression.location_paths[0].location_steps[-1].predicates

    assert str(predicates) == '(@href and not(starts-with(@href,"https://")))'


def test_in_parenthesis():
    assert not _in_parenthesis("foo and bar")
    assert not _in_parenthesis("(foo)(bar)")
    assert not _in_parenthesis("foo)")
    assert not _in_parenthesis("(foo")
    assert _in_parenthesis("((foo)(bar))")


def test_multiple_predicates():
    parsed_expression = XPathExpression(
        './entry/sense/cit[@type="translation"][@lang="en"]'
    )

    predicates = parsed_expression.location_paths[0].location_steps[-1].predicates

    assert isinstance(predicates, BooleanPredicate)
    assert predicates.operator == "and"
    assert isinstance(predicates.left_operand, AttributePredicate)
    assert isinstance(predicates.right_operand, AttributePredicate)
    assert (
        str(parsed_expression) == "self::node()/child::entry/child::sense"
        '/child::cit[(@type="translation" and @lang="en")]'
    )


def test_partition_terms():
    assert _partition_terms('(@foo="1") and (@bar="2")') == [
        '@foo="1"',
        "and",
        '@bar="2"',
    ]
    assert _partition_terms('@foo = "1"') == ["@foo", "=", '"1"']
    assert _partition_terms('((@foo="1") or (@bar="2")) and @baz!="3"') == [
        '(@foo="1") or (@bar="2")',
        "and",
        '@baz!="3"',
    ]
    assert _partition_terms('@href and starts-with(@href,"https://")') == [
        "@href",
        "and",
        'starts-with(@href,"https://")',
    ]
    assert _partition_terms('@href and not(starts-with(@href,"https://"))') == [
        "@href",
        "and",
        'not(starts-with(@href,"https://"))',
    ]
    assert _partition_terms("not(@foo) and (@bar)") == ["not(@foo)", "and", "@bar"]


def test_predicate_order():
    parsed_expression = XPathExpression("./node[@foo and (@this or @that)]")
    predicates = parsed_expression.location_paths[0].location_steps[1].predicates

    assert isinstance(predicates, BooleanPredicate)
    assert predicates.operator == "and"

    left_operand, right_operand = predicates.left_operand, predicates.right_operand
    assert isinstance(left_operand, AttributePredicate)
    assert left_operand.name == "foo"
    assert isinstance(right_operand, BooleanPredicate)
    assert right_operand.operator == "or"

    left_operand, right_operand = (
        right_operand.left_operand,
        right_operand.right_operand,
    )
    assert isinstance(left_operand, AttributePredicate)
    assert left_operand.name == "this"
    assert isinstance(right_operand, AttributePredicate)
    assert right_operand.name == "that"


def test_reduce_whitespace():
    assert (
        _reduce_whitespace('[@a = "1" or  @b = "2"][@c = "3"]')
        == '[@a="1" or @b="2"][@c="3"]'
    )
    assert _reduce_whitespace('[contains(@a, "1")]') == '[contains(@a,"1")]'


def test_semantic_consistency():
    assert (
        str(XPathExpression('.//pb[@n="I"]'))
        == 'self::node()/descendant-or-self::node()/child::pb[@n="I"]'
    )


def test_split():
    assert list(_split('./root/path[@a="n/a"]', "/")) == [".", "root", 'path[@a="n/a"]']
    assert list(_split('@type="translation" and @xml:lang="en"', " and ")) == [
        '@type="translation"',
        '@xml:lang="en"',
    ]
