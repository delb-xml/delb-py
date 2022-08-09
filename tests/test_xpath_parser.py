import operator

from pytest import mark

from _delb.xpath import parse
from _delb.xpath.ast import (
    AnyValue,
    AttributeValue,
    Axis,
    BooleanOperator,
    Function,
    HasAttribute,
    LocationPath,
    LocationStep,
    NameMatchTest,
    NameStartTest,
    NodeTypeTest,
    XPathExpression,
)


# TODO processing-instruction(foo)
@mark.parametrize(
    ("_in", "out"),
    (
        (
            "node()",
            XPathExpression(
                [
                    LocationPath(
                        [LocationStep(Axis("child"), NodeTypeTest("TagNode"))],
                        absolute=False,
                    )
                ]
            ),
        ),
        (
            "/foo",
            XPathExpression(
                [
                    LocationPath(
                        [LocationStep(Axis("child"), NameMatchTest(None, "foo"))],
                        absolute=True,
                    )
                ]
            ),
        ),
        (
            "/p:foo",
            XPathExpression(
                [
                    LocationPath(
                        [LocationStep(Axis("child"), NameMatchTest("p", "foo"))],
                        absolute=True,
                    )
                ]
            ),
        ),
        (
            "/foo*",
            XPathExpression(
                [
                    LocationPath(
                        [LocationStep(Axis("child"), NameStartTest(None, "foo"))],
                        absolute=True,
                    )
                ]
            ),
        ),
        (
            "//foo",
            XPathExpression(
                [
                    LocationPath(
                        [
                            LocationStep(
                                Axis("descendant-or-self"),
                                NodeTypeTest("TagNode"),
                            ),
                            LocationStep(Axis("child"), NameMatchTest(None, "foo")),
                        ],
                        absolute=True,
                    )
                ]
            ),
        ),
        (
            "foo[@bar]",
            XPathExpression(
                [
                    LocationPath(
                        [
                            LocationStep(
                                Axis("child"),
                                NameMatchTest(None, "foo"),
                                [HasAttribute(None, "bar")],
                            )
                        ],
                        absolute=False,
                    )
                ]
            ),
        ),
        (
            "foo[@p:bar]",
            XPathExpression(
                [
                    LocationPath(
                        [
                            LocationStep(
                                Axis("child"),
                                NameMatchTest(None, "foo"),
                                [HasAttribute("p", "bar")],
                            )
                        ],
                        absolute=False,
                    )
                ]
            ),
        ),
    ),
)
def test_parse(_in, out):
    assert parse(_in) == out, parse(_in)


@mark.parametrize(
    ("_in", "out"),
    (
        (
            "[@lang='zw']",
            [
                BooleanOperator(
                    operator.eq,
                    AttributeValue(None, "lang"),
                    AnyValue("zw"),
                )
            ],
        ),
        (
            "[starts-with(@xml:id, '🔥')]",
            [
                Function(
                    "starts-with",
                    (AttributeValue("xml", "id"), AnyValue("🔥")),
                )
            ],
        ),
        (
            "[@href and (@href = 'zw' or starts-with(@href, 'zw-'))]",
            [
                BooleanOperator(
                    operator.and_,
                    HasAttribute(None, "href"),
                    BooleanOperator(
                        operator.or_,
                        BooleanOperator(
                            operator.eq,
                            AttributeValue(None, "href"),
                            AnyValue("zw"),
                        ),
                        Function(
                            "starts-with",
                            (
                                AttributeValue(None, "href"),
                                AnyValue("zw-"),
                            ),
                        ),
                    ),
                )
            ],
        ),
        (
            "[@lang][1]",
            [
                HasAttribute(None, "lang"),
                BooleanOperator(
                    operator.eq,
                    Function("position", ()),
                    AnyValue(1),
                ),
            ],
        ),
        (
            "[concat('a','b') = 'ab']",
            [
                BooleanOperator(
                    operator.eq,
                    Function("concat", (AnyValue("a"), AnyValue("b"))),
                    AnyValue("ab"),
                )
            ],
        ),
        (
            "[starts-with(@foo,'a(b(c)')]",
            [
                Function(
                    "starts-with", (AttributeValue(None, "foo"), AnyValue("a(b(c)"))
                )
            ],
        ),
        (
            '[@href and not(starts-with(@href, "https://"))]',
            [
                BooleanOperator(
                    operator.and_,
                    HasAttribute(None, "href"),
                    Function(
                        "not",
                        (
                            Function(
                                "starts-with",
                                (AttributeValue(None, "href"), AnyValue("https://")),
                            ),
                        ),
                    ),
                )
            ],
        ),
        (
            '[@type="translation"][@lang="en"]',
            [
                BooleanOperator(
                    operator.eq, AttributeValue(None, "type"), AnyValue("translation")
                ),
                BooleanOperator(
                    operator.eq, AttributeValue(None, "lang"), AnyValue("en")
                ),
            ],
        ),
        (
            '[(@foo="1") and (@bar="2")]',
            [
                BooleanOperator(
                    operator.and_,
                    BooleanOperator(
                        operator.eq, AttributeValue(None, "foo"), AnyValue("1")
                    ),
                    BooleanOperator(
                        operator.eq, AttributeValue(None, "bar"), AnyValue("2")
                    ),
                )
            ],
        ),
        (
            '[@foo = "1"]',
            [BooleanOperator(operator.eq, AttributeValue(None, "foo"), AnyValue("1"))],
        ),
        (
            '[((@foo="1") or (@bar="2")) and @baz!="3"]',
            [
                BooleanOperator(
                    operator.and_,
                    BooleanOperator(
                        operator.or_,
                        BooleanOperator(
                            operator.eq, AttributeValue(None, "foo"), AnyValue("1")
                        ),
                        BooleanOperator(
                            operator.eq, AttributeValue(None, "bar"), AnyValue("2")
                        ),
                    ),
                    BooleanOperator(
                        operator.ne, AttributeValue(None, "baz"), AnyValue("3")
                    ),
                )
            ],
        ),
    ),
)
def test_parse_predicates(_in, out):
    assert parse(f"*{_in}") == XPathExpression(
        [LocationPath([LocationStep(Axis("child"), NameStartTest(None, ""), out)])]
    ), parse(_in)


# TODO throw in a bunch of CSS expressions to ensure that cssselect's results are usable
