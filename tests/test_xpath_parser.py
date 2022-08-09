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
        (
            "*[@lang='zw']",
            XPathExpression(
                [
                    LocationPath(
                        [
                            LocationStep(
                                Axis("child"),
                                NameStartTest(None, ""),
                                [
                                    BooleanOperator(
                                        operator.eq,
                                        AttributeValue(None, "lang"),
                                        AnyValue("zw"),
                                    )
                                ],
                            )
                        ]
                    )
                ]
            ),
        ),
        (
            "*[starts-with(@xml:id, '🔥')]",
            XPathExpression(
                [
                    LocationPath(
                        [
                            LocationStep(
                                Axis("child"),
                                NameStartTest(None, ""),
                                [
                                    Function(
                                        "starts-with",
                                        (AttributeValue("xml", "id"), AnyValue("🔥")),
                                    )
                                ],
                            )
                        ]
                    )
                ]
            ),
        ),
        (
            "*[@href and (@href = 'zw' or starts-with(@href, 'zw-'))]",
            XPathExpression(
                [
                    LocationPath(
                        [
                            LocationStep(
                                Axis("child"),
                                NameStartTest(None, ""),
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
                            )
                        ]
                    )
                ]
            ),
        ),
        (
            "*[@lang][1]",
            XPathExpression(
                [
                    LocationPath(
                        [
                            LocationStep(
                                Axis("child"),
                                NameStartTest(None, ""),
                                [
                                    HasAttribute(None, "lang"),
                                    BooleanOperator(
                                        operator.eq,
                                        Function("position", ()),
                                        AnyValue(1),
                                    ),
                                ],
                            )
                        ]
                    )
                ]
            ),
        ),
        (
            "*[concat('a', 'b') = 'ab']",
            XPathExpression(
                [
                    LocationPath(
                        [
                            LocationStep(
                                Axis("child"),
                                NameStartTest(None, ""),
                                [
                                    BooleanOperator(
                                        operator.eq,
                                        Function(
                                            "concat", (AnyValue("a"), AnyValue("b"))
                                        ),
                                        AnyValue("ab"),
                                    )
                                ],
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


# TODO throw in a bunch of CSS expressions to ensure that cssselect's results are usable
