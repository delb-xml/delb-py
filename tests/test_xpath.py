from tokenize import TokenInfo

from pytest import mark

from _delb.xpath import parse
from _delb.xpath.ast import *


# fake _delb.xpath.ast.…
_NameTest = NameTest


def NameTest(pattern):
    return _NameTest(TokenInfo(0, pattern, (1, 0), (1, len(pattern)), pattern))


#


@mark.parametrize(
    ("expression", "ast"),
    (
        (
            "foo",
            XPathExpression([LocationPath([LocationStep(NameTest("foo"))])]),
        ),
        (
            "./foo",
            XPathExpression(
                [
                    LocationPath(
                        [LocationStep(NameTest(".")), LocationStep(NameTest("foo"))]
                    )
                ]
            ),
        ),
        (
            "foo|bar",
            XPathExpression(
                [
                    LocationPath([LocationStep(NameTest("foo"))]),
                    LocationPath([LocationStep(NameTest("bar"))]),
                ]
            ),
        ),
    ),
)
def test_parse(expression, ast):
    assert parse(expression) == ast
