from tokenize import TokenInfo

from pytest import mark

from _delb.xpath import parse
from _delb.xpath.ast import *


@mark.parametrize(
    ("expression", "paths"),
    (
        (
            "/foo",
            [
                LocationPath(
                    [LocationStep(Axis("child"), NameTest("foo"))], absolute=True
                )
            ],
        ),
        (
            "foo",
            [
                LocationPath(
                    [LocationStep(Axis("child"), NameTest("foo"))],
                )
            ],
        ),
        (
            "./foo",
            [
                LocationPath(
                    [
                        LocationStep(Axis("self"), None),
                        LocationStep(Axis("child"), NameTest("foo")),
                    ]
                )
            ],
        ),
        (
            "/foo|bar",
            [
                LocationPath(
                    [LocationStep(Axis("child"), NameTest("foo"))], absolute=True
                ),
                LocationPath([LocationStep(Axis("child"), NameTest("bar"))]),
            ],
        ),
        (
            "descendant-or-self::matrix",
            [
                LocationPath(
                    [LocationStep(Axis("descendant_or_self"), NameTest("matrix"))]
                )
            ],
        ),
    ),
)
def test_parse(expression, paths):
    result = parse(expression)
    assert isinstance(result, XPathExpression)
    assert result.location_paths == paths
