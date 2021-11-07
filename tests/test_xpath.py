from _delb.xpath import (
    AttributePredicate,
    BooleanPredicate,
    PredicateExpression,
    XPathExpression,
)


def test_parsing_1():
    assert (
        str(XPathExpression('.//pb[@n="I"]'))
        == 'self::node()/descendant-or-self::node()/child::pb[@n="I"]'
    )


def test_parsing_2():
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


def test_parsing_3():
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


def test_parsing_4():
    predicate = PredicateExpression.parse('[@href and starts-with(@href,"https://")]')

    assert str(predicate) == '(@href and starts-with(@href,"https://"))'
