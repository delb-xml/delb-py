from _delb.xpath import AttributePredicate, BooleanPredicate, XPathExpression


def test_parsing_1():
    assert (
        str(XPathExpression('.//pb[@n="I"]'))
        == "self::node()/descendant-or-self::node()/child::pb[@n='I']"
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
        '/child::cit[@type="translation" and @lang="en"]'
    )
