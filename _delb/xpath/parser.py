from __future__ import annotations

from functools import lru_cache
from typing import Sequence

from _delb.xpath.ast import XPathExpression
from _delb.xpath.tokenizer import tokenize, Token


class XPathParser:
    def __int__(self):
        raise NotImplementedError

    def __call__(self, tokens: Sequence[Token]) -> XPathExpression:
        raise NotImplementedError


@lru_cache(64)  # TODO? configurable
def parse(expression: str) -> XPathExpression:
    tokens = tokenize(expression)
    parser = XPathParser()
    return parser(tokens)


__all__ = (parse.__name__,)
