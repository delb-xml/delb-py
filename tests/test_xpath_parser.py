import operator

import pytest

from _delb.exceptions import XPathParsingError, XPathUnsupportedStandardFeature
from _delb.xpath import _css_to_xpath, parse
from _delb.xpath.ast import (
    AnyNameTest,
    AnyValue,
    AttributeValue,
    Axis,
    BooleanOperator,
    Function,
    HasAttribute,
    LocationPath,
    LocationStep,
    NameMatchTest,
    NodeTypeTest,
    ProcessingInstructionTest,
    XPathExpression,
)


@pytest.mark.parametrize(
    "selector",
    (
        "*[copyOf]",
        'fw[type="header"]',
        "pb",
        "titlePage,titlePart",
        "cell lb,head lb,note lb,p lb,quote lb",
        "table, table > row, table > supplied, table > supplied > row",
        "*[__level__]",
        "*[xml|id]",
        "name[type]",
        "section > head",
        'figure,fw,note[type="editorial"]',
    ),
)
def test_css_selectors(selector):
    # just test that common css selector expressions translated by cssselect are
    # parsable
    parse(_css_to_xpath(selector))


@pytest.mark.parametrize(
    ("expression", "string"),
    (
        ("", " 0: Missing location path."),
        ("ancestors::node()", r" 0 .*…`\): Invalid axis specifier\."),
        ("ancestor::", r" 10: Missing node test\."),
        ("::", r"0 \(`::`\): Unrecognized node test\."),
        ("::🔥", r"0 \(`::🔥`\): Unrecognized node test\."),
        ("*[5*6]", r" 2 .*: Unrecognized predicate expression\."),
        (
            "*[parent::node()/@id]='5446'",
            r" 2 .*…`\): Unrecognized predicate expression\.",
        ),
        (
            "*[last()=string(1*1*(1)]",
            r" 23 \(`]`\): Closing `]` doesn't match opening `\(` at position 15\.",
        ),
        ("[@xml:id]", r" 0 \(`\[@xml:id\]`\): Unrecognized node test\."),
        ("root[foo]", r" 5 \(`foo]`\): Unrecognized predicate expression\."),
        (
            "*[starts-with('nada')]",
            r" 2 .*…`\): Arguments to function `starts-with` don't match its "
            r"signature.",
        ),
        ("*[@lang", r" 1 \(`\[@lang`\): `\[` is never closed\."),
        ("foo*", r"3 \(`\*`\): Unrecognized expression\."),
        ("/p:foo*", r"6 \(`\*`\): Unrecognized expression\."),
        (":*", r" 0 \(`:\*`\): Unrecognized node test\."),
        ("*.", r" 1 \(`\.`\): Unrecognized expression\."),
        ("*[~lang]", r" 2 \(`~lang\]`\): Unrecognized token\."),
    ),
)
def test_invalid_expressions(expression, string):
    with pytest.raises(XPathParsingError, match=string):
        parse(expression)


@pytest.mark.parametrize(
    ("in_", "out"),
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
            "/*",
            XPathExpression(
                [
                    LocationPath(
                        [LocationStep(Axis("child"), AnyNameTest(None))],
                        absolute=True,
                    )
                ]
            ),
        ),
        (
            "/foo:*",
            XPathExpression(
                [
                    LocationPath(
                        [LocationStep(Axis("child"), AnyNameTest("foo"))],
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
            "/descendant-or-self::node()/foo",
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
            "//foo[@a='b']",
            XPathExpression(
                [
                    LocationPath(
                        [
                            LocationStep(
                                Axis("descendant-or-self"), NodeTypeTest("TagNode")
                            ),
                            LocationStep(
                                Axis("child"),
                                NameMatchTest(None, "foo"),
                                [
                                    BooleanOperator(
                                        operator.eq,
                                        AttributeValue(None, "a"),
                                        AnyValue("b"),
                                    )
                                ],
                            ),
                        ],
                        absolute=True,
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
            "processing-instruction('foo')",
            XPathExpression(
                [
                    LocationPath(
                        [
                            LocationStep(
                                Axis("child"), ProcessingInstructionTest("foo"), []
                            )
                        ],
                        absolute=False,
                    )
                ]
            ),
        ),
    ),
)
def test_parse(in_, out):
    assert parse(in_) == out, parse(in_)


@pytest.mark.parametrize(
    ("in_", "out"),
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
        (
            "[is-last()]",
            [Function("is-last", ())],
        ),
    ),
)
def test_parse_predicates(in_, out):
    assert parse(f"*{in_}").location_paths[0].location_steps[0].predicates == tuple(out)


def test_unsupported_feature():
    with pytest.raises(
        XPathUnsupportedStandardFeature, match=" 5 .*: Attribute " "lookup "
    ):
        parse("//pb/@facs")
